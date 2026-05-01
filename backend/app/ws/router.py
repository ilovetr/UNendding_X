"""WebSocket endpoint for group chat real-time messaging."""
import uuid
import asyncio
import logging
from datetime import datetime

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query, Depends
from sqlalchemy import select, and_
from jose import JWTError, jwt

from app.config import settings
from app.database import get_db, AsyncSession
from app.models.group import GroupMember
from app.models.agent import Agent
from app.ws.manager import manager

logger = logging.getLogger(__name__)
router = APIRouter()


async def verify_ws_token(token: str) -> uuid.UUID | None:
    """Decode JWT and return agent_id. Returns None if invalid."""
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        agent_id = payload.get("sub")
        if agent_id:
            return uuid.UUID(agent_id)
    except (JWTError, ValueError):
        pass
    return None


async def verify_group_membership(db: AsyncSession, group_id: uuid.UUID, agent_id: uuid.UUID) -> bool:
    """Check if agent is a member of the group."""
    stmt = select(GroupMember).where(
        and_(GroupMember.group_id == group_id, GroupMember.agent_id == agent_id)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


@router.websocket("/ws/groups/{group_id}")
async def ws_group_chat(
    ws: WebSocket,
    group_id: uuid.UUID,
    token: str = Query(...),
):
    """
    WebSocket endpoint for real-time group chat.

    Connection flow:
    1. Validate JWT token
    2. Verify group membership
    3. Register connection
    4. Send connected event
    5. Handle messages (ping/pong heartbeat)
    6. On disconnect: cleanup connection
    """
    # 1. Validate JWT
    agent_id = await verify_ws_token(token)
    if agent_id is None:
        await ws.close(code=4001, reason="Invalid or expired token")
        return

    # 2. Verify group membership via DB
    async for db in get_db():
        is_member = await verify_group_membership(db, group_id, agent_id)
        if not is_member:
            await ws.close(code=4003, reason="Not a group member")
            return
        break

    # 3. Register connection
    await manager.connect(ws, group_id, agent_id)

    # 4. Send connected event
    await ws.send_json({
        "type": "connected",
        "data": {
            "agent_id": str(agent_id),
            "group_id": str(group_id),
            "connected_at": datetime.utcnow().isoformat(),
        }
    })

    # 5. Message loop with heartbeat
    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "")

            if msg_type == "ping":
                await ws.send_json({
                    "type": "pong",
                    "data": {"timestamp": datetime.utcnow().isoformat()}
                })
            elif msg_type == "pong":
                pass  # Client is alive

    except WebSocketDisconnect:
        pass
    except Exception as e:
        logger.error(f"WS error for agent {agent_id} in group {group_id}: {e}")

    # 6. Cleanup on disconnect
    await manager.disconnect(group_id, agent_id)