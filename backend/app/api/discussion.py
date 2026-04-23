"""Discussion mode API for agents subscribing to group broadcasts."""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload

from app.database import get_db, AsyncSession
from app.models.group import Group, GroupMember
from app.models.agent import Agent
from app.models.message import Message, AgentDiscussionSetting
from app.api.auth import get_current_agent

router = APIRouter(prefix="/groups/{group_id}/discussion", tags=["discussion"])


# ── Schemas ───────────────────────────────────────────────────────────────────

class AgentBroadcastSubscribeRequest(BaseModel):
    """Subscribe agent to group message stream."""
    agent_id: str
    subscribe: bool = True  # True = subscribe, False = unsubscribe


class BroadcastMessageRequest(BaseModel):
    """Send a broadcast message to all subscribed agents."""
    content: str
    sender_name: str = "System"


class SubscribedMemberResponse(BaseModel):
    agent_id: str
    agent_name: str
    discussion_mode: bool
    joined_at: str


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/subscribers", response_model=List[SubscribedMemberResponse])
async def list_subscribed_members(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """
    List all agents in the group that have discussion_mode enabled.
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

    # Load group members with discussion settings
    group_stmt = (
        select(Group)
        .options(selectinload(Group.members).selectinload(GroupMember.agent))
        .where(Group.id == group_id)
    )
    group_result = await db.execute(group_stmt)
    group = group_result.scalar_one_or_none()

    if group is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Group not found")

    # Get all discussion settings for this group
    settings_stmt = select(AgentDiscussionSetting).where(
        AgentDiscussionSetting.group_id == group_id
    )
    settings_result = await db.execute(settings_stmt)
    settings_map = {str(s.agent_id): s for s in settings_result.scalars().all()}

    subscribers = []
    for member in group.members:
        if member.agent is None:
            continue
        setting = settings_map.get(str(member.agent_id))
        # Show if: has per-group setting with discussion_mode=True, OR has global discussion_mode=True
        enabled = (
            (setting and setting.discussion_mode) or
            (member.agent.discussion_mode and setting is None)
        )
        if enabled:
            subscribers.append(SubscribedMemberResponse(
                agent_id=str(member.agent_id),
                agent_name=member.agent.name,
                discussion_mode=enabled,
                joined_at=member.joined_at.isoformat(),
            ))

    return subscribers


@router.post("/broadcast", status_code=status.HTTP_202_ACCEPTED)
async def send_broadcast(
    group_id: uuid.UUID,
    request: BroadcastMessageRequest,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """
    Send a broadcast message to all discussion-mode-enabled agents in the group.

    In production, this would trigger:
    1. SSE/WebSocket push to all subscribed agents
    2. A2A message dispatch to each agent's endpoint
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

    # Create broadcast message
    message = Message(
        group_id=group_id,
        sender_type="agent",
        sender_id=current_agent.id,
        sender_name=request.sender_name,
        content=request.content,
        mentions=["@all"],
        is_broadcast=True,
        is_a2a_triggered=False,
    )
    db.add(message)
    await db.commit()

    # In production: push via SSE/WebSocket to subscribed agents
    # The target agents would receive this via their SSE subscription

    return {"message_id": str(message.id), "status": "broadcast_sent"}


@router.post("/subscribe", status_code=status.HTTP_200_OK)
async def subscribe_to_discussion(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """
    Subscribe current agent to group discussion broadcasts.
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

    # Upsert setting
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
            discussion_mode=True,
        )
        db.add(setting)
    else:
        setting.discussion_mode = True

    await db.commit()
    return {"status": "subscribed", "discussion_mode": True}


@router.post("/unsubscribe", status_code=status.HTTP_200_OK)
async def unsubscribe_from_discussion(
    group_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_agent: Agent = Depends(get_current_agent),
):
    """
    Unsubscribe current agent from group discussion broadcasts.
    """
    stmt = select(AgentDiscussionSetting).where(
        and_(
            AgentDiscussionSetting.agent_id == current_agent.id,
            AgentDiscussionSetting.group_id == group_id,
        )
    )
    result = await db.execute(stmt)
    setting = result.scalar_one_or_none()

    if setting is not None:
        setting.discussion_mode = False
        await db.commit()

    return {"status": "unsubscribed", "discussion_mode": False}
