"""Tests for authentication endpoints."""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_agent(client: AsyncClient):
    """Test agent registration."""
    response = await client.post(
        "/api/auth/register",
        json={
            "name": "test_agent",
            "did": "did:test:123",
            "endpoint": "http://localhost:9000",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "test_agent"
    assert "api_key" in data
    assert data["api_key"].startswith("ah_")


@pytest.mark.asyncio
async def test_register_duplicate_name(client: AsyncClient):
    """Test registration with duplicate name."""
    # First registration
    await client.post(
        "/api/auth/register",
        json={"name": "duplicate_agent"},
    )

    # Second registration with same name
    response = await client.post(
        "/api/auth/register",
        json={"name": "duplicate_agent"},
    )
    assert response.status_code == 400
    assert "already exists" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_agent(client: AsyncClient):
    """Test agent login."""
    # Register
    reg_response = await client.post(
        "/api/auth/register",
        json={"name": "login_agent"},
    )
    api_key = reg_response.json()["api_key"]
    agent_id = reg_response.json()["id"]

    # Login
    response = await client.post(
        "/api/auth/token",
        json={
            "id": agent_id,
            "api_key": api_key,
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with invalid credentials."""
    response = await client.post(
        "/api/auth/token",
        json={
            "id": "00000000-0000-0000-0000-000000000000",
            "api_key": "invalid_key",
        },
    )
    assert response.status_code == 401
