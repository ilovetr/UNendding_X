"""A2A Authentication - SKILL Token verification for A2A endpoints."""
from typing import Optional
from fastapi import HTTPException, Header, status, Depends
from fastapi.security import APIKeyHeader
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from jose import jwt, JWTError

from app.config import settings
from app.database import get_db
from app.models.skill_token import SkillToken
from app.models.ability import Ability, AccessLevel

# A2A uses X-SKILL-TOKEN header
x_skill_token_header = APIKeyHeader(name="X-SKILL-TOKEN", auto_error=False)


class TokenContext:
    """Parsed and verified token context."""
    def __init__(
        self,
        token: Optional[str],
        jti: Optional[str],
        agent_id: Optional[str],
        permissions: list,
        group_id: Optional[str],
        is_valid: bool,
        is_public_fallback: bool = False,
        quota_remaining: Optional[int] = None,
        has_quota: bool = False,
    ):
        self.token = token
        self.jti = jti
        self.agent_id = agent_id
        self.permissions = permissions
        self.group_id = group_id
        self.is_valid = is_valid
        self.is_public_fallback = is_public_fallback
        self.quota_remaining = quota_remaining
        self.has_quota = has_quota


async def verify_skill_token(
    x_skill_token: Optional[str] = Header(None, alias="X-SKILL-TOKEN"),
    db: AsyncSession = Depends(get_db),
) -> TokenContext:
    """
    Verify SKILL token for A2A endpoints.

    - If no token provided: caller must pass target ability_id for public check
    - If token provided: JWT + DB JTI + group ownership check
    """
    if not x_skill_token:
        # No token provided - public ability fallback will be handled by caller
        return TokenContext(
            token=None,
            jti=None,
            agent_id=None,
            permissions=[],
            group_id=None,
            is_valid=False,
            is_public_fallback=False,
        )

    # Decode JWT
    try:
        payload = jwt.decode(
            x_skill_token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid SKILL token signature",
        )

    # Check expiry
    exp = payload.get("exp", 0)
    from datetime import datetime
    if datetime.utcnow().timestamp() > exp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SKILL token expired",
        )

    # Check DB JTI
    jti = payload.get("jti")
    if not jti:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing JTI",
        )

    result = await db.execute(select(SkillToken).where(SkillToken.token_jti == jti))
    db_token = result.scalar_one_or_none()

    if db_token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SKILL token revoked or not found",
        )

    # Check if token is expired in DB (may be different from JWT expiry)
    from datetime import datetime as dt
    if db_token.expires_at < dt.utcnow():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SKILL token expired",
        )

    return TokenContext(
        token=x_skill_token,
        jti=jti,
        agent_id=payload.get("sub"),
        permissions=payload.get("permissions", []),
        group_id=db_token.group_id,
        is_valid=True,
        is_public_fallback=False,
        quota_remaining=db_token.quota_remaining,
        has_quota=db_token.has_quota,
    )


async def verify_ability_access(
    token_ctx: TokenContext,
    ability_id: str,
    db: AsyncSession = Depends(get_db),
) -> bool:
    """
    Verify if the token context has access to a specific ability.

    Three-tier access control:
    - PUBLIC: Anyone can call, no token required
    - PROTECTED: Token required, unlimited usage
    - LIMITED: Token required, quota-limited usage

    Returns True if access granted.
    For LIMITED abilities, decrements quota on successful verification.

    Raises HTTPException if access denied.
    """
    # Get ability
    try:
        from uuid import UUID
        ability_uuid = UUID(ability_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid ability_id format",
        )

    ability = await db.get(Ability, ability_uuid)
    if ability is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ability not found",
        )

    # Check access level
    if ability.access_level == AccessLevel.PUBLIC:
        # L1: Public service - no auth needed
        return True

    # Non-public ability requires valid token
    if not token_ctx.is_valid:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: ability requires authentication",
        )

    if ability_id not in token_ctx.permissions:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Permission denied: ability not in token permissions",
        )

    # Check and decrement quota for LIMITED abilities
    if ability.access_level == AccessLevel.LIMITED:
        # Check if token has quota tracking
        if token_ctx.has_quota:
            # Fetch latest from DB to avoid stale data
            result = await db.execute(
                select(SkillToken).where(SkillToken.token_jti == token_ctx.jti)
            )
            db_token = result.scalar_one_or_none()

            if db_token is None:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token not found",
                )

            quota = db_token.quota_remaining
            if quota is None or quota <= 0:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Quota exhausted: no remaining calls for this ability",
                )

            # Decrement quota
            db_token.quota_remaining = quota - 1
            await db.commit()
        else:
            # Token doesn't have quota tracking but ability is LIMITED
            # This shouldn't happen if install was done correctly
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Permission denied: ability requires quota tracking",
            )

    return True
