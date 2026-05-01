"""Messages API endpoints for group chat."""
import uuid
from datetime import datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, and_, or_, delete
from sqlalchemy.orm import selectinload

from app.database import get_db, AsyncSession
from app.models.group import Group, GroupMember
from app.models.agent import Agent
from app.models.message import Message, AgentDiscussionSetting
from app.api.auth import get_current_agent

router = APIRouter(prefix="/{group_id}/messages", tags=["messages"])


# ── Pydantic schemas ──────────────────────────────────────────────────────────

class SenderInfo(BaseModel):
    type: str  # 'agent' or 'human'
    id: str
    name: str


class MessageCreateRequest(BaseModel):
    sender: SenderInfo
    content: str = Field(..., min_length=1, max_length=10000)
    mentions: List[str] = Field(default_factory=list)  # agent IDs mentioned
    is_broadcast: bool = False


class MessageResponse(BaseModel):
    id: str
    group_id: str
    sender: SenderInfo
    content: str
    mentions: List[str]
    is_broadcast: bool
    is_a2a_triggered: bool
    a2a_response_to: Optional[str]
    timestamp: datetime
    direction: str = "incoming"  # computed client-side


class DiscussionSettingResponse(BaseModel):
    discussion_mode: bool
    public_abilities: List[dict] = []
    limited_abilities: List[dict] = []


class DiscussionSettingUpdateRequest(BaseModel):
    discussion_mode: Optional[bool] = None
    public_abilities: Optional[List[dict]] = None
    limited_abilities: Optional[List[dict]] = None


# ── Helpers ───────────────────────────────────────────────────────────────────

def _is_member(db: AsyncSession, group_id: uuid.UUID, agent_id: uuid.UUID) -> bool:
    """Check if agent is a member of the group."""
    stmt = select(GroupMember).where(
        and_(GroupMember.group_id == group_id, GroupMember.agent_id == agent_id)
    )
    # This needs to be awaited by caller
    return stmt


def _message_to_response(msg: Message) -> MessageResponse:
    return MessageResponse(
        id=str(msg.id),
        group_id=str(msg.group_id),
        sender=SenderInfo(
            type=msg.sender_type,
            id=str(msg.sender_id),
            name=msg.sender_name,
        ),
        content=msg.content,
        mentions=msg.mentions or [],
        is_broadcast=msg.is_broadcast,
        is_a2a_triggered=msg.is_a2a_triggered,
        a2a_response_to=str(msg.a2a_response_to) if msg.a2a_response_to else None,
        timestamp=msg.timestamp,
        direction="incoming",
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("", response_model=List[MessageResponse])
async def list_messages(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
    skip: int = 0,
    limit: int = 50,
    before_timestamp: Optional[datetime] = None,
):
    """
    List messages for a group (paginated, newest first by default).
    Only group members can view messages.
    """
    # Verify membership
    member_stmt = select(GroupMember).where(
        and_(
            GroupMember.group_id == group_id,
            GroupMember.agent_id == current_agent.id,
        )
    )
    member_result = await db.execute(member_stmt)
    if member_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a group member")

    # Query messages
    stmt = (
        select(Message)
        .where(Message.group_id == group_id)
        .order_by(Message.timestamp.desc())
    )
    if before_timestamp:
        stmt = stmt.where(Message.timestamp < before_timestamp)
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    messages = result.scalars().all()
    # Return in chronological order
    return [_message_to_response(m) for m in reversed(list(messages))]


@router.post("", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
async def create_message(
    group_id: uuid.UUID,
    request: MessageCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """
    Post a message to a group chat.

    Routing logic:
    - @all: broadcast to all members
    - @agent_id: route to specific agent via A2A
    - plain message: save locally only (no A2A)
    """
    # Verify membership
    member_stmt = select(GroupMember).where(
        and_(
            GroupMember.group_id == group_id,
            GroupMember.agent_id == current_agent.id,
        )
    )
    member_result = await db.execute(member_stmt)
    if member_result.scalar_one_or_none() is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not a group member")

    # Load group to get members
    group_stmt = (
        select(Group)
        .options(selectinload(Group.members).selectinload(GroupMember.agent))
        .where(Group.id == group_id)
    )
    group_result = await db.execute(group_stmt)
    group = group_result.scalar_one_or_none()
    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    # Determine is_broadcast
    is_broadcast = request.is_broadcast or ("@all" in request.mentions)

    # Create message record
    message = Message(
        group_id=group_id,
        sender_type=request.sender.type,
        sender_id=uuid.UUID(request.sender.id) if request.sender.type == "agent" else current_agent.id,
        sender_name=request.sender.name,
        content=request.content,
        mentions=request.mentions if request.mentions else [],
        is_broadcast=is_broadcast,
        is_a2a_triggered=False,
    )
    db.add(message)
    await db.flush()

    # Handle A2A routing for @ mentions
    if request.mentions and not is_broadcast:
        for mentioned_id in request.mentions:
            if mentioned_id == "@all":
                continue
            try:
                target_uuid = uuid.UUID(mentioned_id)
            except ValueError:
                continue

            # Find target agent
            target_stmt = select(Agent).where(Agent.id == target_uuid)
            target_result = await db.execute(target_stmt)
            target_agent = target_result.scalar_one_or_none()

            if target_agent and target_agent.endpoint:
                # Mark as A2A triggered
                message.is_a2a_triggered = True
                # In production: dispatch A2A message to target_agent.endpoint
                # For now, we'll rely on the target agent's SSE subscription

    await db.commit()
    await db.refresh(message)
    return _message_to_response(message)


@router.delete("/{message_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_message(
    group_id: uuid.UUID,
    message_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """
    Delete a message. Only the sender or group admin can delete.
    """
    stmt = select(Message).where(
        and_(Message.id == message_id, Message.group_id == group_id)
    )
    result = await db.execute(stmt)
    message = result.scalar_one_or_none()

    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Message not found")

    # Only sender or admin can delete
    is_sender = str(message.sender_id) == str(current_agent.id)
    is_admin = any(
        m.agent_id == current_agent.id and m.role in ("admin",)
        for m in (await db.execute(
            select(GroupMember).where(
                and_(GroupMember.group_id == group_id, GroupMember.agent_id == current_agent.id)
            )
        )).scalars().all()
    )

    if not is_sender and not is_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot delete this message")

    await db.delete(message)
    await db.commit()


# ── Discussion mode settings ──────────────────────────────────────────────────

@router.get("/discussion", response_model=DiscussionSettingResponse)
async def get_discussion_setting(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """
    Get discussion mode setting for the current agent in this group.
    """
    stmt = select(AgentDiscussionSetting).where(
        and_(
            AgentDiscussionSetting.agent_id == current_agent.id,
            AgentDiscussionSetting.group_id == group_id,
        )
    )
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()

    if setting is None:
        # Return default from agent's global setting
        return DiscussionSettingResponse(
            discussion_mode=current_agent.discussion_mode,
            public_abilities=[],
            limited_abilities=[],
        )

    return DiscussionSettingResponse(
        discussion_mode=setting.discussion_mode,
        public_abilities=setting.public_abilities or [],
        limited_abilities=setting.limited_abilities or [],
    )


@router.put("/discussion", response_model=DiscussionSettingResponse)
async def update_discussion_setting(
    group_id: uuid.UUID,
    request: DiscussionSettingUpdateRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """
    Update discussion mode setting for the current agent in this group.

    - discussion_mode: whether to receive group broadcasts and @ mentions
    - public_abilities: abilities to show publicly in group chat
    - limited_abilities: abilities that require explicit @ to invoke
    """
    stmt = select(AgentDiscussionSetting).where(
        and_(
            AgentDiscussionSetting.agent_id == current_agent.id,
            AgentDiscussionSetting.group_id == group_id,
        )
    )
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()

    if setting is None:
        setting = AgentDiscussionSetting(
            agent_id=current_agent.id,
            group_id=group_id,
            discussion_mode=request.discussion_mode if request.discussion_mode is not None else current_agent.discussion_mode,
            public_abilities=request.public_abilities or [],
            limited_abilities=request.limited_abilities or [],
        )
        db.add(setting)
    else:
        if request.discussion_mode is not None:
            setting.discussion_mode = request.discussion_mode
        if request.public_abilities is not None:
            setting.public_abilities = request.public_abilities
        if request.limited_abilities is not None:
            setting.limited_abilities = request.limited_abilities

    await db.commit()
    await db.refresh(setting)

    return DiscussionSettingResponse(
        discussion_mode=setting.discussion_mode,
        public_abilities=setting.public_abilities or [],
        limited_abilities=setting.limited_abilities or [],
    )
