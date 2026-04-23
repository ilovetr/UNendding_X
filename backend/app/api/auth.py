"""Authentication API endpoints."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, Field
from passlib.context import CryptContext
from jose import JWTError, jwt

from app.config import settings
from app.database import get_db, AsyncSession
from app.models.agent import Agent, AgentStatus
from app.models.audit_log import AuditLog
from app.models.refresh_token import RefreshToken

router = APIRouter()
# Use sha256_crypt to avoid bcrypt/passlib version compatibility issues
pwd_context = CryptContext(schemes=["sha256_crypt"], deprecated="auto")
security = HTTPBearer()


# Pydantic schemas
class AgentRegisterRequest(BaseModel):
    """Request model for agent registration."""
    name: str = Field(..., min_length=1, max_length=255)
    did: Optional[str] = None
    endpoint: Optional[str] = None


class AgentInitRequest(BaseModel):
    """Request model for agent init (register + login in one step)."""
    name: str = Field(..., min_length=1, max_length=255)
    did: Optional[str] = None
    endpoint: Optional[str] = None
    server_url: Optional[str] = None
    device_id: Optional[str] = None  # Client-generated device identifier


class AgentRegisterResponse(BaseModel):
    """Response model for agent registration."""
    id: str
    name: str
    api_key: str
    created_at: datetime


class AgentLoginRequest(BaseModel):
    """Request model for agent login."""
    id: str
    api_key: str


class TokenResponse(BaseModel):
    """Response model for JWT token."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AgentInitResponse(BaseModel):
    """Response model for agent init (register + login)."""
    agent_id: str
    name: str
    api_key: str
    access_token: str
    refresh_token: str  # Client should store this securely
    expires_in: int     # Access token expiry in seconds
    refresh_expires_in: int  # Refresh token expiry in seconds


def verify_api_key(plain_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash."""
    return pwd_context.verify(plain_key, hashed_key)


def get_password_hash(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.utcnow() + (expires_delta or timedelta(minutes=settings.JWT_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


async def get_current_agent(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> Agent:
    """Dependency to get the current authenticated agent."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid authentication credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        token = credentials.credentials
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        agent_id: str = payload.get("sub")
        if agent_id is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    # Try UUID first (PostgreSQL), fall back to str (SQLite)
    try:
        pk = uuid.UUID(agent_id)
    except (ValueError, AttributeError):
        pk = agent_id
    result = await db.get(Agent, pk)
    if result is None:
        # Fallback: query by string id for SQLite compatibility
        from sqlalchemy import select
        stmt = select(Agent).where(Agent.id == agent_id)
        r = await db.execute(stmt)
        result = r.scalar_one_or_none()
    if result is None:
        raise credentials_exception
    return result


@router.post("/register", response_model=AgentRegisterResponse)
async def register_agent(
    request: AgentRegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register a new agent and return API key."""
    # Check if name already exists
    from sqlalchemy import select
    stmt = select(Agent).where(Agent.name == request.name)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent with this name already exists",
        )

    # Generate API key
    api_key = f"unendingx_{uuid.uuid4().hex}{uuid.uuid4().hex[:8]}"
    hashed_key = get_password_hash(api_key)

    # Create agent
    agent = Agent(
        name=request.name,
        did=request.did,
        endpoint=request.endpoint,
        api_key=hashed_key,
        agent_card={
            "name": request.name,
            "url": request.endpoint or "",
            "version": settings.A2A_VERSION,
        },
        status=AgentStatus.ACTIVE,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    # Create audit log
    audit = AuditLog(
        agent_id=agent.id,
        action="agent_register",
        details={"name": request.name},
    )
    db.add(audit)
    await db.commit()

    return AgentRegisterResponse(
        id=str(agent.id),
        name=agent.name,
        api_key=api_key,  # Return plain key (only time it's visible)
        created_at=agent.created_at,
    )


@router.post("/token", response_model=TokenResponse)
async def login_agent(
    request: AgentLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Login with agent ID and API key, return JWT token."""
    try:
        agent = await db.get(Agent, uuid.UUID(request.id))
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid agent ID format",
        )

    if agent is None or not verify_api_key(request.api_key, agent.api_key or ""):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    # Create JWT token
    access_token = create_access_token(data={"sub": str(agent.id)})

    # Audit log
    audit = AuditLog(
        agent_id=agent.id,
        action="agent_login",
        details={"agent_name": agent.name},
    )
    db.add(audit)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )


@router.post("/init", response_model=AgentInitResponse)
async def init_agent(
    request: AgentInitRequest,
    db: AsyncSession = Depends(get_db),
):
    """Initialize agent: register + login in one step.
    
    This is the recommended way to set up a new agent.
    Returns both access_token and refresh_token.
    """
    # Check if name already exists
    from sqlalchemy import select
    stmt = select(Agent).where(Agent.name == request.name)
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent with this name already exists",
        )

    # Generate API key
    api_key = f"unendingx_{uuid.uuid4().hex}{uuid.uuid4().hex[:8]}"
    hashed_key = get_password_hash(api_key)

    # Create agent
    agent = Agent(
        name=request.name,
        did=request.did,
        endpoint=request.endpoint,
        api_key=hashed_key,
        agent_card={
            "name": request.name,
            "url": request.endpoint or "",
            "version": settings.A2A_VERSION,
        },
        status=AgentStatus.ACTIVE,
    )
    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    # Create JWT access token
    access_token = create_access_token(data={"sub": str(agent.id)})

    # Create refresh token (store hash in database)
    refresh_token = secrets.token_urlsafe(32)
    refresh_token_hash = hashlib.sha256(refresh_token.encode()).hexdigest()
    device_id = request.device_id or str(uuid.uuid4())
    
    refresh = RefreshToken(
        agent_id=agent.id,
        token_hash=refresh_token_hash,
        device_id=device_id,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh)
    
    # Audit log
    audit = AuditLog(
        agent_id=agent.id,
        action="agent_init",
        details={"name": request.name, "device_id": device_id},
    )
    db.add(audit)
    await db.commit()

    return AgentInitResponse(
        agent_id=str(agent.id),
        name=agent.name,
        api_key=api_key,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
        refresh_expires_in=settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600,
    )


class RefreshRequest(BaseModel):
    """Request model for token refresh."""
    refresh_token: str


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Refresh access token using refresh token.
    
    The refresh token hash is verified against the database.
    If valid, a new access token is issued and the refresh token is rotated.
    """
    from sqlalchemy import select, update
    
    # Hash the provided refresh token
    token_hash = hashlib.sha256(request.refresh_token.encode()).hexdigest()
    
    # Find the refresh token in database
    stmt = select(RefreshToken).where(
        RefreshToken.token_hash == token_hash,
        RefreshToken.revoked == False,
    )
    result = await db.execute(stmt)
    refresh = result.scalar_one_or_none()
    
    if refresh is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )
    
    # Check if expired
    if datetime.utcnow() > refresh.expires_at:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has expired",
        )
    
    # Revoke old refresh token (rotation)
    refresh.revoked = True
    
    # Get the agent
    try:
        agent = await db.get(Agent, refresh.agent_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent not found",
        )
    
    if agent is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Agent not found",
        )
    
    # Create new access token
    access_token = create_access_token(data={"sub": str(agent.id)})
    
    # Create new refresh token (rotation)
    new_refresh_token = secrets.token_urlsafe(32)
    new_refresh_hash = hashlib.sha256(new_refresh_token.encode()).hexdigest()
    
    new_refresh = RefreshToken(
        agent_id=agent.id,
        token_hash=new_refresh_hash,
        device_id=refresh.device_id,
        expires_at=datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(new_refresh)
    
    # Audit log
    audit = AuditLog(
        agent_id=agent.id,
        action="token_refresh",
        details={"device_id": refresh.device_id},
    )
    db.add(audit)
    await db.commit()

    return TokenResponse(
        access_token=access_token,
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )
