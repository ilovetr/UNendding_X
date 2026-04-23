"""Tests for P5: GUI Group Chat functionality.

Covers:
- Message model and API
- @ mention functionality
- Discussion mode API
"""
import pytest
import uuid
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker

# Test the Message model fields
def test_message_model_fields():
    """Verify Message model has all required fields."""
    from app.models.message import Message

    # Check expected columns exist
    fields = [c.name for c in Message.__table__.columns]
    assert 'id' in fields
    assert 'group_id' in fields
    assert 'sender_type' in fields
    assert 'sender_id' in fields
    assert 'sender_name' in fields
    assert 'content' in fields
    assert 'mentions' in fields
    assert 'is_broadcast' in fields
    assert 'is_a2a_triggered' in fields
    assert 'timestamp' in fields


def test_agent_discussion_setting_fields():
    """Verify AgentDiscussionSetting model has all required fields."""
    from app.models.message import AgentDiscussionSetting

    fields = [c.name for c in AgentDiscussionSetting.__table__.columns]
    assert 'id' in fields
    assert 'agent_id' in fields
    assert 'group_id' in fields
    assert 'discussion_mode' in fields
    assert 'public_abilities' in fields
    assert 'limited_abilities' in fields


def test_agent_model_has_discussion_mode():
    """Verify Agent model has discussion_mode field."""
    from app.models.agent import Agent

    fields = [c.name for c in Agent.__table__.columns]
    assert 'discussion_mode' in fields


# ── Integration tests (require running app) ───────────────────────────────────

pytestmark = pytest.mark.asyncio


async def _get_client():
    """Get async test client."""
    from app.main import app
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


async def _setup_test_agent(client: AsyncClient):
    """Register and login a test agent."""
    import random
    name = f"TestAgent_{random.randint(1000,9999)}"

    # Register
    reg_resp = await client.post("/api/auth/register", json={
        "name": name,
        "endpoint": "http://localhost:9000",
    })
    assert reg_resp.status_code == 201
    reg_data = reg_resp.json()
    agent_id = reg_data["id"]
    api_key = reg_data["api_key"]

    # Login
    login_resp = await client.post("/api/auth/token", json={
        "id": agent_id,
        "api_key": api_key,
    })
    assert login_resp.status_code == 200
    token = login_resp.json()["access_token"]

    return agent_id, api_key, token


async def _create_test_group(client: AsyncClient, token: str, name: str = None) -> dict:
    """Create a test group and return group data."""
    import random
    if name is None:
        name = f"TestGroup_{random.randint(1000,9999)}"

    resp = await client.post(
        "/api/groups",
        json={"name": name, "description": "Test group", "privacy": "public", "category": "tech"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    return resp.json()


async def test_messages_api_list_empty(app):
    """T1: List messages for a new group returns empty list."""
    client = await _get_client()
    agent_id, api_key, token = await _setup_test_agent(client)
    group = await _create_test_group(client, token)

    resp = await client.get(
        f"/api/groups/{group['id']}/messages",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    assert resp.json() == []


async def test_messages_api_create_message(app):
    """T2: Create a message in a group."""
    client = await _get_client()
    agent_id, api_key, token = await _setup_test_agent(client)
    group = await _create_test_group(client, token)

    resp = await client.post(
        f"/api/groups/{group['id']}/messages",
        json={
            "sender": {"type": "human", "id": agent_id, "name": "TestUser"},
            "content": "Hello, world!",
            "mentions": [],
            "is_broadcast": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Hello, world!"
    assert data["sender"]["name"] == "TestUser"
    assert data["is_broadcast"] is False
    assert data["is_a2a_triggered"] is False


async def test_messages_api_create_broadcast(app):
    """T3: Create a broadcast message with @all."""
    client = await _get_client()
    agent_id, api_key, token = await _setup_test_agent(client)
    group = await _create_test_group(client, token)

    resp = await client.post(
        f"/api/groups/{group['id']}/messages",
        json={
            "sender": {"type": "agent", "id": agent_id, "name": "TestAgent"},
            "content": "@all 大家好！",
            "mentions": ["@all"],
            "is_broadcast": True,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["is_broadcast"] is True
    assert "@all" in data["mentions"]


async def test_messages_api_create_with_mentions(app):
    """T4: Create a message with specific @mentions."""
    client = await _get_client()
    agent_id, api_key, token = await _setup_test_agent(client)
    group = await _create_test_group(client, token)

    resp = await client.post(
        f"/api/groups/{group['id']}/messages",
        json={
            "sender": {"type": "human", "id": agent_id, "name": "TestUser"},
            "content": "@Agent-B 你好",
            "mentions": ["@all"],
            "is_broadcast": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201
    data = resp.json()
    assert "@all" in data["mentions"]


async def test_messages_api_non_member_forbidden(app):
    """T5: Non-member cannot view group messages."""
    client = await _get_client()

    # Create two agents
    _, _, token1 = await _setup_test_agent(client)
    _, _, token2 = await _setup_test_agent(client)

    # Agent 1 creates a group
    group = await _create_test_group(client, token1)

    # Agent 2 tries to view messages (not a member)
    resp = await client.get(
        f"/api/groups/{group['id']}/messages",
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert resp.status_code == 403


async def test_messages_api_delete_own_message(app):
    """T6: Sender can delete their own message."""
    client = await _get_client()
    agent_id, api_key, token = await _setup_test_agent(client)
    group = await _create_test_group(client, token)

    # Create a message
    create_resp = await client.post(
        f"/api/groups/{group['id']}/messages",
        json={
            "sender": {"type": "human", "id": agent_id, "name": "TestUser"},
            "content": "To be deleted",
            "mentions": [],
            "is_broadcast": False,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    msg_id = create_resp.json()["id"]

    # Delete the message
    del_resp = await client.delete(
        f"/api/groups/{group['id']}/messages/{msg_id}",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert del_resp.status_code == 204


async def test_discussion_api_get_setting(app):
    """T7: Get discussion mode setting returns default."""
    client = await _get_client()
    agent_id, api_key, token = await _setup_test_agent(client)
    group = await _create_test_group(client, token)

    resp = await client.get(
        f"/api/groups/{group['id']}/messages/discussion",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "discussion_mode" in data
    assert "public_abilities" in data
    assert "limited_abilities" in data


async def test_discussion_api_update_setting(app):
    """T8: Update discussion mode setting."""
    client = await _get_client()
    agent_id, api_key, token = await _setup_test_agent(client)
    group = await _create_test_group(client, token)

    resp = await client.put(
        f"/api/groups/{group['id']}/messages/discussion",
        json={"discussion_mode": True},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["discussion_mode"] is True


async def test_discussion_api_subscribe(app):
    """T9: Subscribe to discussion broadcasts."""
    client = await _get_client()
    agent_id, api_key, token = await _setup_test_agent(client)
    group = await _create_test_group(client, token)

    resp = await client.post(
        f"/api/groups/{group['id']}/discussion/subscribe",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "subscribed"
    assert data["discussion_mode"] is True


async def test_discussion_api_unsubscribe(app):
    """T10: Unsubscribe from discussion broadcasts."""
    client = await _get_client()
    agent_id, api_key, token = await _setup_test_agent(client)
    group = await _create_test_group(client, token)

    # First subscribe
    await client.post(
        f"/api/groups/{group['id']}/discussion/subscribe",
        headers={"Authorization": f"Bearer {token}"},
    )

    # Then unsubscribe
    resp = await client.post(
        f"/api/groups/{group['id']}/discussion/unsubscribe",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "unsubscribed"
    assert data["discussion_mode"] is False


async def test_discussion_api_list_subscribers(app):
    """T11: List subscribed members in a group."""
    client = await _get_client()
    agent_id, api_key, token = await _setup_test_agent(client)
    group = await _create_test_group(client, token)

    # Subscribe
    await client.post(
        f"/api/groups/{group['id']}/discussion/subscribe",
        headers={"Authorization": f"Bearer {token}"},
    )

    # List subscribers
    resp = await client.get(
        f"/api/groups/{group['id']}/discussion/subscribers",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    assert data[0]["agent_id"] == agent_id
    assert data[0]["discussion_mode"] is True


async def test_discussion_api_broadcast(app):
    """T12: Send a broadcast message to all subscribers."""
    client = await _get_client()
    agent_id, api_key, token = await _setup_test_agent(client)
    group = await _create_test_group(client, token)

    resp = await client.post(
        f"/api/groups/{group['id']}/discussion/broadcast",
        json={"content": "Hello everyone!", "sender_name": "TestAgent"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "message_id" in data
    assert data["status"] == "broadcast_sent"


# Run with: pytest test_p5_gui_chat.py -v
