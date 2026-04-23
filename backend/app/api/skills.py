"""Skills (SKILL Token) API endpoints."""
import uuid
import secrets
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, delete

from app.config import settings
from app.database import get_db, AsyncSession
from app.models.skill_token import SkillToken
from app.models.ability import Ability, AbilityStatus, AccessLevel
from app.models.agent import Agent
from app.api.auth import get_current_agent, create_access_token

router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class SkillInstallRequest(BaseModel):
    skill_name: str = Field(..., min_length=1, max_length=255)
    ability_ids: List[uuid.UUID] = Field(default_factory=list)
    group_id: Optional[uuid.UUID] = None
    version: str = Field(default="1.0.0")
    # Optional quota override for LIMITED abilities
    quota: Optional[int] = Field(None, ge=1, description="Quota for LIMITED abilities (1-N)")


class SkillInstallResponse(BaseModel):
    token: str
    skill_name: str
    version: str
    permissions: List[str]
    expires_at: datetime
    token_id: str


class SkillVerifyRequest(BaseModel):
    token: str


class SkillVerifyResponse(BaseModel):
    valid: bool
    agent_id: Optional[str] = None
    skill_name: Optional[str] = None
    permissions: Optional[List[str]] = None
    expires_at: Optional[datetime] = None
    revoked: bool = False


class SkillCheckRequest(BaseModel):
    """Check whether a token has a specific permission."""
    token: str
    ability_id: str


class SkillCheckResponse(BaseModel):
    allowed: bool
    reason: Optional[str] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _decode_skill_token(token: str):
    """Decode JWT, return payload or raise HTTPException."""
    from jose import jwt, JWTError
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {e}")


async def _get_db_token(jti: str, db: AsyncSession) -> Optional[SkillToken]:
    """Fetch SkillToken from DB by JTI."""
    result = await db.execute(select(SkillToken).where(SkillToken.token_jti == jti))
    return result.scalar_one_or_none()


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.post("/install", response_model=SkillInstallResponse, status_code=201)
async def install_skill(
    request: SkillInstallRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Install a skill and get a SKILL JWT token for capability access.

    For LIMITED abilities, quota will be tracked per token.
    """
    permissions = []
    has_quota = False
    quota_remaining = None

    for ability_id in request.ability_ids:
        ability = await db.get(Ability, ability_id)
        if ability and ability.status == AbilityStatus.ACTIVE:
            permissions.append(str(ability_id))

            # Check if this ability is LIMITED
            if ability.access_level == AccessLevel.LIMITED:
                has_quota = True
                # Use installer's quota if provided, otherwise use ability's quota_per_token
                if request.quota is not None:
                    quota_remaining = request.quota
                elif ability.quota_per_token is not None:
                    quota_remaining = ability.quota_per_token
                # else: None means unlimited (though this shouldn't happen for LIMITED)

    token_jti = secrets.token_urlsafe(16)
    expires_at = datetime.utcnow() + timedelta(minutes=settings.JWT_EXPIRE_MINUTES)

    # Resolve group_id to str for JSONB/SQLite compat
    group_id_val = str(request.group_id) if request.group_id else None

    skill_token = SkillToken(
        agent_id=current_agent.id,
        group_id=group_id_val,
        skill_name=request.skill_name,
        version=request.version,
        permissions=permissions,
        token_jti=token_jti,
        expires_at=expires_at,
        has_quota=has_quota,
        quota_remaining=quota_remaining if has_quota else None,
    )
    db.add(skill_token)
    await db.commit()
    await db.refresh(skill_token)

    token_data = {
        "sub": str(current_agent.id),
        "skill_name": request.skill_name,
        "permissions": permissions,
        "jti": token_jti,
        "type": "skill",
    }
    jwt_token = create_access_token(token_data)

    return SkillInstallResponse(
        token=jwt_token,
        skill_name=request.skill_name,
        version=request.version,
        permissions=permissions,
        expires_at=expires_at,
        token_id=str(skill_token.id),
    )


@router.post("/verify", response_model=SkillVerifyResponse)
async def verify_skill(
    request: SkillVerifyRequest,
    db: AsyncSession = Depends(get_db),
):
    """Verify a SKILL token: JWT signature + DB existence + expiry check."""
    from jose import jwt, JWTError

    try:
        payload = jwt.decode(
            request.token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        return SkillVerifyResponse(valid=False, revoked=False)

    jti = payload.get("jti")
    exp = payload.get("exp", 0)

    if datetime.utcnow().timestamp() > exp:
        return SkillVerifyResponse(valid=False)

    # Check DB (may have been revoked)
    db_token = await _get_db_token(jti, db) if jti else None
    if db_token is None:
        return SkillVerifyResponse(valid=False, revoked=True)

    return SkillVerifyResponse(
        valid=True,
        agent_id=payload.get("sub"),
        skill_name=payload.get("skill_name"),
        permissions=payload.get("permissions", []),
        expires_at=datetime.fromtimestamp(exp),
        revoked=False,
    )


@router.post("/check", response_model=SkillCheckResponse)
async def check_permission(
    request: SkillCheckRequest,
    db: AsyncSession = Depends(get_db),
):
    """Check whether a SKILL token has permission to use a specific ability."""
    from jose import jwt, JWTError

    try:
        payload = jwt.decode(
            request.token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        return SkillCheckResponse(allowed=False, reason="invalid_token")

    exp = payload.get("exp", 0)
    if datetime.utcnow().timestamp() > exp:
        return SkillCheckResponse(allowed=False, reason="token_expired")

    jti = payload.get("jti")
    db_token = await _get_db_token(jti, db) if jti else None
    if db_token is None:
        return SkillCheckResponse(allowed=False, reason="token_revoked")

    permissions: list = payload.get("permissions", [])
    if request.ability_id in permissions:
        return SkillCheckResponse(allowed=True)

    return SkillCheckResponse(allowed=False, reason="no_permission")


@router.delete("/{token_id}", status_code=204)
async def revoke_skill_token(
    token_id: str,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Revoke (delete) a SKILL token. Only the issuing agent can revoke."""
    try:
        tid = uuid.UUID(token_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid token_id format")

    db_token = await db.get(SkillToken, tid)
    if db_token is None:
        raise HTTPException(status_code=404, detail="Token not found")

    # Normalize IDs for comparison (SQLite returns str, PG returns UUID)
    if str(db_token.agent_id) != str(current_agent.id):
        raise HTTPException(status_code=403, detail="Not your token")

    await db.delete(db_token)
    await db.commit()


@router.get("/my-tokens", response_model=List[dict])
async def list_my_tokens(
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """List all active SKILL tokens for the current agent."""
    stmt = (
        select(SkillToken)
        .where(SkillToken.agent_id == current_agent.id)
        .order_by(SkillToken.issued_at.desc())
    )
    result = await db.execute(stmt)
    tokens = result.scalars().all()

    return [
        {
            "id": str(t.id),
            "skill_name": t.skill_name,
            "version": t.version,
            "permissions": t.permissions,
            "expires_at": t.expires_at.isoformat(),
            "issued_at": t.issued_at.isoformat(),
        }
        for t in tokens
    ]
