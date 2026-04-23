"""Groups API endpoints."""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.database import get_db, AsyncSession
from app.models.group import Group, GroupMember, Privacy, Category, CATEGORY_LABELS, CATEGORY_LABELS_EN, hash_password, verify_password
from app.models.agent import Agent
from app.models.audit_log import AuditLog
from app.api.auth import get_current_agent

router = APIRouter()


# ── Category list endpoint ────────────────────────────────────────────────────

class CategoryInfo(BaseModel):
    value: str
    label_zh: str
    label_en: str


@router.get("/categories", response_model=List[CategoryInfo])
async def list_categories():
    """Return all available group categories with bilingual labels."""
    return [
        CategoryInfo(value=k, label_zh=v, label_en=CATEGORY_LABELS_EN.get(k, v))
        for k, v in CATEGORY_LABELS.items()
    ]


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class GroupCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    privacy: Privacy = Privacy.PUBLIC
    category: Category = Category.OTHER
    password: Optional[str] = Field(None, min_length=4, max_length=32)  # required when privacy=private
    config: dict = Field(default_factory=dict)


class GroupUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    privacy: Optional[Privacy] = None
    category: Optional[Category] = None
    config: Optional[dict] = None


class GroupResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    privacy: Privacy
    category: Category
    owner_id: str
    invite_code: str
    config: dict
    created_at: datetime
    member_count: int = 0
    category_label_zh: str = ""  # computed from CATEGORY_LABELS
    category_label_en: str = ""  # computed from CATEGORY_LABELS_EN
    has_password: bool = False  # true when the group requires a password


class GroupDetailResponse(GroupResponse):
    members: List[dict] = []


class GroupJoinRequest(BaseModel):
    invite_code: str = Field(..., min_length=6, max_length=6)
    password: Optional[str] = None  # required when joining a private group


class MemberRoleUpdateRequest(BaseModel):
    role: str = Field(..., pattern="^(admin|member|guest)$")


# ── Helper ────────────────────────────────────────────────────────────────────

async def _get_group_or_404(db: AsyncSession, group_id: uuid.UUID) -> Group:
    stmt = (
        select(Group)
        .options(selectinload(Group.members))
        .where(Group.id == group_id)
    )
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")
    return group


def _group_response(group: Group, extra_count: int = 0) -> GroupResponse:
    return GroupResponse(
        id=str(group.id),
        name=group.name,
        description=group.description,
        privacy=group.privacy,
        category=group.category,
        owner_id=str(group.owner_id),
        invite_code=group.invite_code,
        config=group.config or {},
        created_at=group.created_at,
        member_count=len(group.members) + extra_count,
        category_label_zh=CATEGORY_LABELS.get(group.category.value, group.category.value),
        category_label_en=CATEGORY_LABELS_EN.get(group.category.value, group.category.value),
        has_password=bool(group.password_hash),
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[GroupResponse])
async def list_groups(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 50,
    category: Optional[str] = None,
):
    """List all public groups, optionally filtered by category."""
    stmt = (
        select(Group)
        .where(Group.privacy == Privacy.PUBLIC)
        .options(selectinload(Group.members))
    )
    if category:
        stmt = stmt.where(Group.category == category)
    stmt = stmt.offset(skip).limit(limit).order_by(Group.created_at.desc())
    result = await db.execute(stmt)
    return [_group_response(g) for g in result.scalars().all()]


@router.get("/mine", response_model=List[GroupResponse])
async def my_groups(
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """List groups the current agent is a member of."""
    stmt = (
        select(Group)
        .join(GroupMember, GroupMember.group_id == Group.id)
        .where(GroupMember.agent_id == current_agent.id)
        .options(selectinload(Group.members))
        .order_by(Group.created_at.desc())
    )
    result = await db.execute(stmt)
    return [_group_response(g) for g in result.scalars().all()]


@router.post("", response_model=GroupResponse, status_code=status.HTTP_201_CREATED)
async def create_group(
    request: GroupCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Create a new group. Creator becomes owner and admin member."""
    # Private groups must have a password
    password_hash = None
    if request.privacy == Privacy.PRIVATE:
        if not request.password:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password is required for private groups",
            )
        password_hash = hash_password(request.password)
    elif request.password:
        # Password provided for public group - still hash it but ignore (or warn)
        password_hash = hash_password(request.password)

    group = Group(
        name=request.name,
        description=request.description,
        privacy=request.privacy,
        category=request.category,
        password_hash=password_hash,
        owner_id=current_agent.id,
        config=request.config or {},
    )
    db.add(group)
    await db.flush()  # get group.id without committing

    # Add owner as admin
    member = GroupMember(group_id=group.id, agent_id=current_agent.id, role="admin")
    db.add(member)

    audit = AuditLog(
        agent_id=current_agent.id,
        action="group_create",
        resource_type="group",
        details={"group_name": request.name},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(group)

    return GroupResponse(
        id=str(group.id),
        name=group.name,
        description=group.description,
        privacy=group.privacy,
        category=group.category,
        owner_id=str(group.owner_id),
        invite_code=group.invite_code,
        config=group.config or {},
        created_at=group.created_at,
        member_count=1,
        category_label_zh=CATEGORY_LABELS.get(group.category.value, group.category.value),
        category_label_en=CATEGORY_LABELS_EN.get(group.category.value, group.category.value),
        has_password=bool(group.password_hash),
    )


@router.get("/{group_id}", response_model=GroupDetailResponse)
async def get_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get group details with member list."""
    stmt = (
        select(Group)
        .options(selectinload(Group.members).selectinload(GroupMember.agent))
        .where(Group.id == group_id)
    )
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    members = [
        {
            "agent_id": str(m.agent_id),
            "agent_name": m.agent.name if m.agent else "Unknown",
            "role": m.role,
            "joined_at": m.joined_at.isoformat(),
        }
        for m in group.members
    ]

    return GroupDetailResponse(
        id=str(group.id),
        name=group.name,
        description=group.description,
        privacy=group.privacy,
        category=group.category,
        owner_id=str(group.owner_id),
        invite_code=group.invite_code,
        config=group.config or {},
        created_at=group.created_at,
        member_count=len(group.members),
        members=members,
        category_label_zh=CATEGORY_LABELS.get(group.category.value, group.category.value),
        category_label_en=CATEGORY_LABELS_EN.get(group.category.value, group.category.value),
        has_password=bool(group.password_hash),
    )


@router.put("/{group_id}", response_model=GroupResponse)
async def update_group(
    group_id: uuid.UUID,
    request: GroupUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Update group info. Only admin/owner can update."""
    group = await _get_group_or_404(db, group_id)

    # Check admin permission
    caller_member = next(
        (m for m in group.members if m.agent_id == current_agent.id and m.role in ("admin",)),
        None,
    )
    if caller_member is None and group.owner_id != current_agent.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")

    if request.name is not None:
        group.name = request.name
    if request.description is not None:
        group.description = request.description
    if request.privacy is not None:
        group.privacy = request.privacy
    if request.category is not None:
        group.category = request.category
    if request.config is not None:
        group.config = request.config

    group.updated_at = datetime.utcnow()
    await db.commit()
    await db.refresh(group)
    return _group_response(group)


@router.delete("/{group_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Delete a group. Only owner can delete."""
    group = await _get_group_or_404(db, group_id)

    if group.owner_id != current_agent.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can delete group")

    await db.delete(group)
    await db.commit()


@router.post("/join", response_model=GroupResponse)
async def join_group(
    request: GroupJoinRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Join a group using invite code."""
    stmt = (
        select(Group)
        .options(selectinload(Group.members))
        .where(Group.invite_code == request.invite_code.upper())
    )
    result = await db.execute(stmt)
    group = result.scalar_one_or_none()

    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Invalid invite code")

    # Verify password for private groups
    if group.password_hash:
        if not request.password:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This group requires a password",
            )
        if not verify_password(request.password, group.password_hash):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Incorrect password",
            )

    # Already member?
    if any(m.agent_id == current_agent.id for m in group.members):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Already a member")

    member = GroupMember(group_id=group.id, agent_id=current_agent.id, role="member")
    db.add(member)

    audit = AuditLog(
        agent_id=current_agent.id,
        action="group_join",
        resource_type="group",
        details={"group_id": str(group.id), "group_name": group.name},
    )
    db.add(audit)
    await db.commit()
    await db.refresh(group)

    return _group_response(group)


@router.post("/{group_id}/leave", status_code=status.HTTP_204_NO_CONTENT)
async def leave_group(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Leave a group. Owner must transfer ownership first.

    On leave: revoke all SKILL tokens issued for this group to this agent.
    """
    group = await _get_group_or_404(db, group_id)

    if group.owner_id == current_agent.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Owner must transfer ownership before leaving",
        )

    stmt = (
        select(GroupMember)
        .where(GroupMember.group_id == group_id)
        .where(GroupMember.agent_id == current_agent.id)
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Not a member")

    # Cascade: revoke all SKILL tokens for this group issued to this agent
    from app.models.skill_token import SkillToken
    stmt_tokens = select(SkillToken).where(
        SkillToken.agent_id == current_agent.id,
        SkillToken.group_id == str(group_id),
    )
    result_tokens = await db.execute(stmt_tokens)
    revoked_count = 0
    for token in result_tokens.scalars().all():
        await db.delete(token)
        revoked_count += 1

    if revoked_count > 0:
        audit = AuditLog(
            agent_id=current_agent.id,
            action="skill_tokens_revoked_on_leave",
            resource_type="skill_token",
            details={
                "group_id": str(group_id),
                "group_name": group.name,
                "revoked_count": revoked_count,
            },
        )
        db.add(audit)

    await db.delete(member)
    audit = AuditLog(
        agent_id=current_agent.id,
        action="group_leave",
        resource_type="group",
        details={"group_id": str(group_id), "revoked_tokens": revoked_count},
    )
    db.add(audit)
    await db.commit()


@router.put("/{group_id}/members/{agent_id}/role", response_model=dict)
async def update_member_role(
    group_id: uuid.UUID,
    agent_id: uuid.UUID,
    request: MemberRoleUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Update a member's role. Only owner/admin can do this."""
    group = await _get_group_or_404(db, group_id)

    # Caller must be admin or owner
    caller_is_admin = any(
        m.agent_id == current_agent.id and m.role == "admin"
        for m in group.members
    )
    if not caller_is_admin and group.owner_id != current_agent.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")

    stmt = (
        select(GroupMember)
        .where(GroupMember.group_id == group_id)
        .where(GroupMember.agent_id == agent_id)
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    member.role = request.role
    await db.commit()
    return {"agent_id": str(agent_id), "role": request.role}


@router.delete("/{group_id}/members/{agent_id}", status_code=status.HTTP_204_NO_CONTENT)
async def kick_member(
    group_id: uuid.UUID,
    agent_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Kick a member from a group. Only admin/owner can kick.

    On kick: revoke all SKILL tokens for this group issued to the kicked agent.
    """
    group = await _get_group_or_404(db, group_id)

    caller_is_admin = any(
        m.agent_id == current_agent.id and m.role == "admin"
        for m in group.members
    )
    if not caller_is_admin and group.owner_id != current_agent.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin permission required")

    if agent_id == group.owner_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Cannot kick the owner")

    stmt = (
        select(GroupMember)
        .where(GroupMember.group_id == group_id)
        .where(GroupMember.agent_id == agent_id)
    )
    result = await db.execute(stmt)
    member = result.scalar_one_or_none()

    if member is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Member not found")

    # Cascade: revoke all SKILL tokens for this group issued to the kicked agent
    from app.models.skill_token import SkillToken
    stmt_tokens = select(SkillToken).where(
        SkillToken.agent_id == agent_id,
        SkillToken.group_id == str(group_id),
    )
    result_tokens = await db.execute(stmt_tokens)
    revoked_count = 0
    for token in result_tokens.scalars().all():
        await db.delete(token)
        revoked_count += 1

    if revoked_count > 0:
        audit = AuditLog(
            agent_id=current_agent.id,
            action="skill_tokens_revoked_on_kick",
            resource_type="skill_token",
            details={
                "group_id": str(group_id),
                "kicked_agent_id": str(agent_id),
                "revoked_count": revoked_count,
            },
        )
        db.add(audit)

    await db.delete(member)
    audit = AuditLog(
        agent_id=current_agent.id,
        action="group_kick",
        resource_type="group",
        details={"group_id": str(group_id), "kicked_agent_id": str(agent_id)},
    )
    db.add(audit)
    await db.commit()


@router.post("/{group_id}/transfer", response_model=dict)
async def transfer_ownership(
    group_id: uuid.UUID,
    new_owner_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """Transfer group ownership to another member."""
    group = await _get_group_or_404(db, group_id)

    if group.owner_id != current_agent.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only owner can transfer ownership")

    # New owner must be a member
    new_owner_member = next(
        (m for m in group.members if m.agent_id == new_owner_id), None
    )
    if new_owner_member is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="New owner must be a current member")

    # Transfer
    group.owner_id = new_owner_id
    new_owner_member.role = "admin"
    group.updated_at = datetime.utcnow()
    await db.commit()

    return {"group_id": str(group_id), "new_owner_id": str(new_owner_id)}
