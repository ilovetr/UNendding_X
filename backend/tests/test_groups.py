"""Tests for groups endpoints."""
import pytest
from httpx import AsyncClient


async def get_auth_token(client: AsyncClient) -> tuple[str, str]:
    """Helper to register and login an agent."""
    reg_response = await client.post(
        "/api/auth/register",
        json={"name": "group_test_agent"},
    )
    agent_id = reg_response.json()["id"]
    api_key = reg_response.json()["api_key"]

    login_response = await client.post(
        "/api/auth/token",
        json={"id": agent_id, "api_key": api_key},
    )
    token = login_response.json()["access_token"]
    return agent_id, token


@pytest.mark.asyncio
async def test_create_group(client: AsyncClient):
    """Test group creation."""
    _, token = await get_auth_token(client)

    response = await client.post(
        "/api/groups",
        json={
            "name": "Test Group",
            "description": "A test group",
            "privacy": "public",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Test Group"
    assert data["invite_code"] is not None
    assert len(data["invite_code"]) == 6


@pytest.mark.asyncio
async def test_list_groups(client: AsyncClient):
    """Test listing groups."""
    _, token = await get_auth_token(client)

    # Create a group first
    await client.post(
        "/api/groups",
        json={"name": "List Test Group"},
        headers={"Authorization": f"Bearer {token}"},
    )

    response = await client.get("/api/groups")
    assert response.status_code == 200
    groups = response.json()
    assert isinstance(groups, list)


@pytest.mark.asyncio
async def test_join_group(client: AsyncClient):
    """Test joining a group with invite code."""
    # Agent 1 creates group
    id1, token1 = await get_auth_token(client)
    create_response = await client.post(
        "/api/groups",
        json={"name": "Join Test Group"},
        headers={"Authorization": f"Bearer {token1}"},
    )
    invite_code = create_response.json()["invite_code"]

    # Agent 2 joins
    id2, token2 = await get_auth_token(client)
    join_response = await client.post(
        "/api/groups/join",
        json={"invite_code": invite_code},
        headers={"Authorization": f"Bearer {token2}"},
    )
    assert join_response.status_code == 200
    assert join_response.json()["member_count"] >= 2


@pytest.mark.asyncio
async def test_join_invalid_code(client: AsyncClient):
    """Test joining with invalid invite code."""
    _, token = await get_auth_token(client)

    response = await client.post(
        "/api/groups/join",
        json={"invite_code": "XXXXXX"},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 404
