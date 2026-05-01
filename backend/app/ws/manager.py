"""WebSocket connection manager for group chat real-time messaging."""
import uuid
import asyncio
import logging
from typing import Dict

from fastapi import WebSocket

logger = logging.getLogger(__name__)


class GroupConnectionManager:
    """
    Manages WebSocket connections per group.
    Structure: _groups[group_id][agent_id] = WebSocket
    """

    def __init__(self):
        self._groups: Dict[uuid.UUID, Dict[uuid.UUID, WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, ws: WebSocket, group_id: uuid.UUID, agent_id: uuid.UUID) -> None:
        """Register a WebSocket connection for an agent in a group."""
        await ws.accept()
        async with self._lock:
            if group_id not in self._groups:
                self._groups[group_id] = {}
            self._groups[group_id][agent_id] = ws
        logger.info(f"Agent {agent_id} connected to group {group_id}")

    async def disconnect(self, group_id: uuid.UUID, agent_id: uuid.UUID) -> None:
        """Remove a WebSocket connection."""
        async with self._lock:
            if group_id in self._groups:
                self._groups[group_id].pop(agent_id, None)
                if not self._groups[group_id]:
                    del self._groups[group_id]
        logger.info(f"Agent {agent_id} disconnected from group {group_id}")

    async def broadcast_to_group(self, group_id: uuid.UUID, event: dict) -> None:
        """
        Send event to all connected agents in a group.
        Silently drops dead connections.
        """
        async with self._lock:
            group_conns = dict(self._groups.get(group_id, {}))
        dead = []
        for agent_id, ws in group_conns.items():
            try:
                await ws.send_json(event)
            except Exception:
                dead.append(agent_id)
        if dead:
            async with self._lock:
                for agent_id in dead:
                    if group_id in self._groups:
                        self._groups[group_id].pop(agent_id, None)
            logger.warning(f"Dropped {len(dead)} dead connections in group {group_id}")

    async def send_to_agent(self, group_id: uuid.UUID, agent_id: uuid.UUID, event: dict) -> bool:
        """Send event to a specific agent in a group. Returns False if not connected."""
        async with self._lock:
            ws = self._groups.get(group_id, {}).get(agent_id)
        if ws is None:
            return False
        try:
            await ws.send_json(event)
            return True
        except Exception:
            return False

    def get_connected_agents(self, group_id: uuid.UUID) -> list[uuid.UUID]:
        """Get list of agent IDs currently connected to a group."""
        return list(self._groups.get(group_id, {}).keys())

    @property
    def connection_count(self) -> int:
        """Total number of active connections."""
        return sum(len(g) for g in self._groups.values())


# Global manager instance
manager = GroupConnectionManager()