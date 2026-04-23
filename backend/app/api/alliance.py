"""Agent Alliance API endpoints."""
import uuid
from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.database import get_db, AsyncSession
from app.models.agent import Agent
from app.models.alliance import AgentAlliance, AllianceStatus
from app.api.auth import get_current_agent

router = APIRouter()


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class AllianceInfo(BaseModel):
    """Minimal agent info shown in alliance."""
    id: str
    name: str
    endpoint: Optional[str] = None
    status: str


class AllianceMember(BaseModel):
    """Full alliance member with relationship metadata."""
    alliance_id: str
    agent: AllianceInfo
    label: Optional[str] = None
    status: AllianceStatus
    created_at: datetime
    # Shared data (fetched from server-side DB)
    group_count: int = 0
    ability_count: int = 0
    skill_token_count: int = 0


class AllianceAddRequest(BaseModel):
    target_agent_id: str = Field(..., description="Target agent ID to add")
    label: Optional[str] = Field(None, description="Human-friendly label for this agent")


class AllianceUpdateLabelRequest(BaseModel):
    label: str = Field(..., min_length=1, max_length=255)


class AllianceGroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    privacy: str
    category: str
    category_label_zh: str
    category_label_en: str
    member_count: int
    invite_code: Optional[str] = None


class AllianceAbilityResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    version: str
    status: str
    definition: dict


class AllianceSkillTokenResponse(BaseModel):
    id: str
    skill_name: str
    permissions: List[str]
    expires_at: datetime
    created_at: datetime
    status: str


def _agent_info(a: Agent) -> AllianceInfo:
    return AllianceInfo(id=str(a.id), name=a.name, endpoint=a.endpoint, status=a.status.value)


def _build_member(
    alliance: AgentAlliance,
    agent: Agent,
    db: AsyncSession,
) -> AllianceMember:
    """Build AllianceMember from alliance record + agent info + DB counts."""
    from app.models.group import Group
    from app.models.ability import Ability
    from app.models.skill_token import SkillToken

    group_count = 0
    ability_count = 0
    token_count = 0

    # Count from server-side DB (shared data)
    try:
        from sqlalchemy import select, func
        group_count = db.scalar(
            select(func.count()).select_from(Group).where(Group.owner_id == agent.id)
        ) or 0
        ability_count = db.scalar(
            select(func.count()).select_from(Ability).where(Ability.agent_id == agent.id)
        ) or 0
        token_count = db.scalar(
            select(func.count()).select_from(SkillToken).where(SkillToken.agent_id == agent.id)
        ) or 0
    except Exception:
        pass  # Non-critical — counts might fail in some DB configs

    return AllianceMember(
        alliance_id=str(alliance.id),
        agent=_agent_info(agent),
        label=alliance.label,
        status=alliance.status,
        created_at=alliance.created_at,
        group_count=group_count,
        ability_count=ability_count,
        skill_token_count=token_count,
    )


# ── Alliance CRUD ─────────────────────────────────────────────────────────────

@router.get("/members", response_model=List[AllianceMember])
async def list_alliance_members(
    db: AsyncSession = Depends(get_db),
    current: Agent = Depends(get_current_agent),
):
    """
    List all alliance members for the current agent.
    Returns bidirectional relationships (both directions merged).
    """
    from sqlalchemy import select, or_, and_

    # Find all alliances where current agent is either requester or target
    stmt = select(AgentAlliance).where(
        or_(
            AgentAlliance.requester_id == current.id,
            AgentAlliance.target_id == current.id,
        ),
        AgentAlliance.status == AllianceStatus.ACTIVE,
    )
    result = await db.execute(stmt)
    alliances = result.scalars().all()

    members: List[AllianceMember] = []
    seen_ids: set[str] = set()

    for a in alliances:
        # The "other" agent in this alliance
        other_id = a.target_id if a.requester_id == current.id else a.requester_id

        stmt2 = select(Agent).where(Agent.id == other_id)
        result2 = await db.execute(stmt2)
        other = result2.scalar_one_or_none()
        if other and str(other.id) not in seen_ids:
            seen_ids.add(str(other.id))
            members.append(_build_member(a, other, db))

    return members


@router.post("/add", response_model=AllianceMember, status_code=status.HTTP_201_CREATED)
async def add_alliance_member(
    req: AllianceAddRequest,
    db: AsyncSession = Depends(get_db),
    current: Agent = Depends(get_current_agent),
):
    """
    Add another agent to the alliance by ID.
    Currently auto-accepts for simplicity (both agents belong to the same human).
    """
    try:
        target_uuid = uuid.UUID(req.target_agent_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid agent ID format")

    if target_uuid == current.id:
        raise HTTPException(status_code=400, detail="Cannot add yourself")

    # Check if already exists
    from sqlalchemy import select, or_, and_
    stmt = select(AgentAlliance).where(
        or_(
            and_(AgentAlliance.requester_id == current.id, AgentAlliance.target_id == target_uuid),
            and_(AgentAlliance.requester_id == target_uuid, AgentAlliance.target_id == current.id),
        ),
        AgentAlliance.status != AllianceStatus.REMOVED,
    )
    result = await db.execute(stmt)
    existing = result.scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Already in alliance")

    # Verify target agent exists
    stmt2 = select(Agent).where(Agent.id == target_uuid)
    result2 = await db.execute(stmt2)
    target = result2.scalar_one_or_none()
    if not target:
        raise HTTPException(status_code=404, detail="Target agent not found")

    alliance = AgentAlliance(
        requester_id=current.id,
        target_id=target_uuid,
        accepted_by_id=current.id,  # auto-accept
        status=AllianceStatus.ACTIVE,
        label=req.label,
    )
    db.add(alliance)
    await db.commit()
    await db.refresh(alliance)

    return _build_member(alliance, target, db)


@router.delete("/{alliance_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_alliance_member(
    alliance_id: str,
    db: AsyncSession = Depends(get_db),
    current: Agent = Depends(get_current_agent),
):
    """Remove an alliance member."""
    try:
        uid = uuid.UUID(alliance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alliance ID")

    from sqlalchemy import select
    stmt = select(AgentAlliance).where(
        AgentAlliance.id == uid,
        or_(
            AgentAlliance.requester_id == current.id,
            AgentAlliance.target_id == current.id,
        ),
    )
    result = await db.execute(stmt)
    alliance = result.scalar_one_or_none()
    if not alliance:
        raise HTTPException(status_code=404, detail="Alliance not found")

    alliance.status = AllianceStatus.REMOVED
    await db.commit()


@router.patch("/{alliance_id}/label", response_model=dict)
async def update_alliance_label(
    alliance_id: str,
    req: AllianceUpdateLabelRequest,
    db: AsyncSession = Depends(get_db),
    current: Agent = Depends(get_current_agent),
):
    """Update the human-readable label for an alliance member."""
    try:
        uid = uuid.UUID(alliance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alliance ID")

    from sqlalchemy import select
    stmt = select(AgentAlliance).where(
        AgentAlliance.id == uid,
        or_(
            AgentAlliance.requester_id == current.id,
            AgentAlliance.target_id == current.id,
        ),
    )
    result = await db.execute(stmt)
    alliance = result.scalar_one_or_none()
    if not alliance:
        raise HTTPException(status_code=404, detail="Alliance not found")

    alliance.label = req.label
    await db.commit()
    return {"ok": True, "label": req.label}


# ── Shared data from alliance members ─────────────────────────────────────────

@router.get("/{alliance_id}/groups", response_model=List[AllianceGroupResponse])
async def get_alliance_groups(
    alliance_id: str,
    db: AsyncSession = Depends(get_db),
    current: Agent = Depends(get_current_agent),
):
    """Get all groups owned by an alliance member."""
    try:
        uid = uuid.UUID(alliance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alliance ID")

    from sqlalchemy import select
    from app.models.group import Group, CATEGORY_LABELS, CATEGORY_LABELS_EN

    stmt = select(AgentAlliance).where(
        AgentAlliance.id == uid,
        or_(
            AgentAlliance.requester_id == current.id,
            AgentAlliance.target_id == current.id,
        ),
        AgentAlliance.status == AllianceStatus.ACTIVE,
    )
    result = await db.execute(stmt)
    alliance = result.scalar_one_or_none()
    if not alliance:
        raise HTTPException(status_code=404, detail="Alliance not found")

    # The other agent's ID
    target_id = alliance.target_id if alliance.requester_id == current.id else alliance.requester_id

    stmt2 = select(Group).where(Group.owner_id == target_id)
    result2 = await db.execute(stmt2)
    groups = result2.scalars().all()

    return [
        AllianceGroupResponse(
            id=str(g.id),
            name=g.name,
            description=g.description,
            privacy=g.privacy.value if hasattr(g.privacy, 'value') else str(g.privacy),
            category=g.category.value if hasattr(g.category, 'value') else str(g.category),
            category_label_zh=CATEGORY_LABELS.get(g.category.value if hasattr(g.category, 'value') else str(g.category), '其他'),
            category_label_en=CATEGORY_LABELS_EN.get(g.category.value if hasattr(g.category, 'value') else str(g.category), 'Other'),
            member_count=len(g.members) if g.members else 0,
            invite_code=g.invite_code if g.privacy.value == 'public' else None,
        )
        for g in groups
    ]


@router.get("/{alliance_id}/abilities", response_model=List[AllianceAbilityResponse])
async def get_alliance_abilities(
    alliance_id: str,
    db: AsyncSession = Depends(get_db),
    current: Agent = Depends(get_current_agent),
):
    """Get all abilities of an alliance member."""
    try:
        uid = uuid.UUID(alliance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alliance ID")

    from sqlalchemy import select
    from app.models.ability import Ability

    stmt = select(AgentAlliance).where(
        AgentAlliance.id == uid,
        or_(
            AgentAlliance.requester_id == current.id,
            AgentAlliance.target_id == current.id,
        ),
        AgentAlliance.status == AllianceStatus.ACTIVE,
    )
    result = await db.execute(stmt)
    alliance = result.scalar_one_or_none()
    if not alliance:
        raise HTTPException(status_code=404, detail="Alliance not found")

    target_id = alliance.target_id if alliance.requester_id == current.id else alliance.requester_id

    stmt2 = select(Ability).where(Ability.agent_id == target_id)
    result2 = await db.execute(stmt2)
    abilities = result2.scalars().all()

    return [
        AllianceAbilityResponse(
            id=str(a.id),
            name=a.name,
            description=a.description,
            version=a.version,
            status=a.status.value if hasattr(a.status, 'value') else str(a.status),
            definition=a.definition,
        )
        for a in abilities
    ]


@router.get("/{alliance_id}/skills", response_model=List[AllianceSkillTokenResponse])
async def get_alliance_skills(
    alliance_id: str,
    db: AsyncSession = Depends(get_db),
    current: Agent = Depends(get_current_agent),
):
    """Get all SKILL tokens of an alliance member."""
    try:
        uid = uuid.UUID(alliance_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid alliance ID")

    from sqlalchemy import select
    from app.models.skill_token import SkillToken

    stmt = select(AgentAlliance).where(
        AgentAlliance.id == uid,
        or_(
            AgentAlliance.requester_id == current.id,
            AgentAlliance.target_id == current.id,
        ),
        AgentAlliance.status == AllianceStatus.ACTIVE,
    )
    result = await db.execute(stmt)
    alliance = result.scalar_one_or_none()
    if not alliance:
        raise HTTPException(status_code=404, detail="Alliance not found")

    target_id = alliance.target_id if alliance.requester_id == current.id else alliance.requester_id

    stmt2 = select(SkillToken).where(SkillToken.agent_id == target_id)
    result2 = await db.execute(stmt2)
    tokens = result2.scalars().all()

    return [
        AllianceSkillTokenResponse(
            id=str(t.id),
            skill_name=t.skill_name,
            permissions=t.permissions or [],
            expires_at=t.expires_at,
            created_at=t.created_at,
            status=t.status.value if hasattr(t.status, 'value') else str(t.status),
        )
        for t in tokens
    ]
