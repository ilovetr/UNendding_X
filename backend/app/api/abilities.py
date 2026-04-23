"""Abilities API endpoints."""
import uuid
import hashlib
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db, AsyncSession
from app.models.ability import Ability, AbilityStatus, AccessLevel


def _parse_version(v: str) -> tuple[int, int, int]:
    """Parse version string into tuple for comparison."""
    parts = v.split(".")
    return (int(parts[0]), int(parts[1]), int(parts[2]))


def _is_newer_version(new: str, current: str) -> bool:
    """Return True if new version is strictly greater than current."""
    return _parse_version(new) > _parse_version(current)
from app.models.agent import Agent
from app.models.group import Group, GroupMember
from app.models.audit_log import AuditLog
from app.api.auth import get_current_agent

router = APIRouter()


def compute_ability_hash(definition: dict) -> str:
    import json
    content = json.dumps(definition, sort_keys=True)
    return hashlib.sha256(content.encode()).hexdigest()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class AbilityCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    group_id: Optional[str] = None  # UUID as string for cross-db compat
    definition: dict = Field(...)
    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    # Legacy field, use access_level instead
    is_public: bool = Field(default=True, description="Deprecated: use access_level instead")
    # Three-tier access control
    access_level: AccessLevel = Field(
        default=AccessLevel.PROTECTED,
        description="Access level: public (no auth), protected (token, unlimited), limited (token, quota)"
    )
    # Quota per token (only for LIMITED access)
    quota_per_token: Optional[int] = Field(
        None,
        ge=1,
        description="Max calls per token for LIMITED abilities (None=unlimited)"
    )
    description: Optional[str] = None


class AbilityUpdateRequest(BaseModel):
    definition: Optional[dict] = None
    version: Optional[str] = Field(None, pattern=r"^\d+\.\d+\.\d+$")
    # Legacy field
    is_public: Optional[bool] = None
    # Three-tier access control
    access_level: Optional[AccessLevel] = None
    quota_per_token: Optional[int] = Field(None, ge=1)
    status: Optional[AbilityStatus] = None
    description: Optional[str] = None


class AbilityBatchItem(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    group_id: Optional[str] = None
    definition: dict = Field(...)
    version: str = Field(default="1.0.0", pattern=r"^\d+\.\d+\.\d+$")
    access_level: AccessLevel = AccessLevel.PROTECTED
    quota_per_token: Optional[int] = Field(None, ge=1)
    description: Optional[str] = None


class AbilityBatchRequest(BaseModel):
    abilities: list[AbilityBatchItem]


class AbilityResponse(BaseModel):
    id: str
    name: str
    group_id: Optional[str]
    agent_id: str
    definition: dict
    version: str
    hash: str
    # Legacy field
    is_public: bool
    # Three-tier access control
    access_level: AccessLevel
    quota_per_token: Optional[int]
    status: AbilityStatus
    description: Optional[str]
    created_at: datetime


def _ability_resp(a: Ability) -> AbilityResponse:
    return AbilityResponse(
        id=str(a.id),
        name=a.name,
        group_id=str(a.group_id) if a.group_id else None,
        agent_id=str(a.agent_id),
        definition=a.definition or {},
        version=a.version,
        hash=a.hash or "",
        is_public=a.access_level == AccessLevel.PUBLIC,
        access_level=a.access_level,
        quota_per_token=a.quota_per_token,
        status=a.status,
        description=a.description,
        created_at=a.created_at,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[AbilityResponse])
async def list_abilities(
    db: AsyncSession = Depends(get_db),
    group_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    is_public: Optional[bool] = None,
    access_level: Optional[AccessLevel] = None,
    include_deprecated: bool = False,
    skip: int = 0,
    limit: int = 50,
):
    """List abilities with optional filters."""
    stmt = select(Ability)

    if not include_deprecated:
        stmt = stmt.where(Ability.status == AbilityStatus.ACTIVE)
    if group_id:
        stmt = stmt.where(Ability.group_id == group_id)
    if agent_id:
        stmt = stmt.where(Ability.agent_id == agent_id)
    if is_public is not None:
        # Legacy filter: is_public=True maps to PUBLIC, is_public=False maps to PROTECTED or LIMITED
        if is_public:
            stmt = stmt.where(Ability.access_level == AccessLevel.PUBLIC)
        else:
            stmt = stmt.where(Ability.access_level.in_([AccessLevel.PROTECTED, AccessLevel.LIMITED]))
    if access_level is not None:
        stmt = stmt.where(Ability.access_level == access_level)

    stmt = stmt.offset(skip).limit(limit).order_by(Ability.created_at.desc())
    result = await db.execute(stmt)
    return [_ability_resp(a) for a in result.scalars().all()]


@router.post("", response_model=AbilityResponse, status_code=status.HTTP_201_CREATED)
async def create_ability(
    request: AbilityCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Register a new ability for the current agent."""
    group_id_val = None
    if request.group_id:
        try:
            group_id_val = uuid.UUID(request.group_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid group_id format")

        group = await db.get(Group, group_id_val)
        if group is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

        # Must be a member to register ability in group
        stmt = select(GroupMember).where(
            GroupMember.group_id == group_id_val,
            GroupMember.agent_id == current_agent.id,
        )
        result = await db.execute(stmt)
        if result.scalar_one_or_none() is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Must be a group member")

    ability_hash = compute_ability_hash(request.definition)

    ability = Ability(
        name=request.name,
        group_id=group_id_val,
        agent_id=current_agent.id,
        definition=request.definition,
        version=request.version,
        hash=ability_hash,
        access_level=request.access_level,
        quota_per_token=request.quota_per_token if request.access_level == AccessLevel.LIMITED else None,
        description=request.description,
        status=AbilityStatus.ACTIVE,
    )
    db.add(ability)

    audit = AuditLog(
        agent_id=current_agent.id,
        action="ability_register",
        resource_type="ability",
        details={"name": request.name, "version": request.version},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(ability)
    return _ability_resp(ability)


@router.post("/batch", response_model=List[AbilityResponse], status_code=status.HTTP_201_CREATED)
async def batch_register_abilities(
    request: AbilityBatchRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """
    Batch register or update abilities for the current agent.
    If an ability with the same name exists, update it only if the new version is higher.
    This endpoint is designed for auto-registration by agent plugins.
    """
    results: list[AbilityResponse] = []
    for item in request.abilities:
        group_id_val: Optional[uuid.UUID] = None
        if item.group_id:
            try:
                group_id_val = uuid.UUID(item.group_id)
            except ValueError:
                raise HTTPException(status_code=400, detail=f"Invalid group_id: {item.group_id}")

            group = await db.get(Group, group_id_val)
            if group is None:
                raise HTTPException(status_code=404, detail=f"Group {item.group_id} not found")

            stmt = select(GroupMember).where(
                GroupMember.group_id == group_id_val,
                GroupMember.agent_id == current_agent.id,
            )
            result = await db.execute(stmt)
            if result.scalar_one_or_none() is None:
                raise HTTPException(status_code=403, detail=f"Not a member of group {item.group_id}")

        # Check if ability with same name already exists
        stmt = select(Ability).where(
            Ability.name == item.name,
            Ability.agent_id == current_agent.id,
        )
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            # Update only if version is higher
            if _is_newer_version(item.version, existing.version):
                existing.definition = item.definition
                existing.hash = compute_ability_hash(item.definition)
                existing.version = item.version
                existing.access_level = item.access_level
                existing.quota_per_token = item.quota_per_token if item.access_level == AccessLevel.LIMITED else None
                existing.description = item.description
                existing.updated_at = datetime.utcnow()
                await db.flush()
                results.append(_ability_resp(existing))
            else:
                # Keep existing, return it as-is
                results.append(_ability_resp(existing))
        else:
            # Create new
            ability_hash = compute_ability_hash(item.definition)
            ability = Ability(
                name=item.name,
                group_id=group_id_val,
                agent_id=current_agent.id,
                definition=item.definition,
                version=item.version,
                hash=ability_hash,
                access_level=item.access_level,
                quota_per_token=item.quota_per_token if item.access_level == AccessLevel.LIMITED else None,
                description=item.description,
                status=AbilityStatus.ACTIVE,
            )
            db.add(ability)
            await db.flush()
            results.append(_ability_resp(ability))

    audit = AuditLog(
        agent_id=current_agent.id,
        action="ability_batch_register",
        resource_type="ability",
        details={"count": len(request.abilities)},
    )
    db.add(audit)
    await db.commit()
    return results


@router.get("/mine", response_model=List[AbilityResponse])
async def my_abilities(
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """List all abilities registered by the current agent."""
    stmt = (
        select(Ability)
        .where(Ability.agent_id == current_agent.id)
        .order_by(Ability.created_at.desc())
    )
    result = await db.execute(stmt)
    return [_ability_resp(a) for a in result.scalars().all()]


@router.get("/{ability_id}", response_model=AbilityResponse)
async def get_ability(
    ability_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get ability details by ID."""
    ability = await db.get(Ability, ability_id)
    if ability is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ability not found")
    return _ability_resp(ability)


@router.put("/{ability_id}", response_model=AbilityResponse)
async def update_ability(
    ability_id: uuid.UUID,
    request: AbilityUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Update an ability. Only the registering agent can update."""
    ability = await db.get(Ability, ability_id)
    if ability is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ability not found")

    if ability.agent_id != current_agent.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    if request.definition is not None:
        ability.definition = request.definition
        ability.hash = compute_ability_hash(request.definition)
    if request.version is not None:
        # Version can only increase
        if not _is_newer_version(request.version, ability.version):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Version must be greater than current ({ability.version})",
            )
        ability.version = request.version
    if request.is_public is not None:
        ability.is_public = request.is_public
    if request.status is not None:
        ability.status = request.status
    if request.description is not None:
        ability.description = request.description

    ability.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(ability)
    return _ability_resp(ability)


@router.post("/{ability_id}/deprecate", response_model=AbilityResponse)
async def deprecate_ability(
    ability_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Mark an ability as deprecated."""
    ability = await db.get(Ability, ability_id)
    if ability is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ability not found")

    if ability.agent_id != current_agent.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    ability.status = AbilityStatus.DEPRECATED
    ability.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(ability)
    return _ability_resp(ability)


@router.delete("/{ability_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ability(
    ability_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Delete an ability."""
    ability = await db.get(Ability, ability_id)
    if ability is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ability not found")

    if ability.agent_id != current_agent.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized")

    await db.delete(ability)
    await db.commit()
