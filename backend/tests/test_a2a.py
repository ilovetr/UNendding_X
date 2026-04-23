"""Tests for A2A endpoints."""
import pytest
from httpx import AsyncClient
from app.models.ability import Ability


@pytest.mark.asyncio
async def test_agent_card(client: AsyncClient):
    """Test the agent card endpoint."""
    response = await client.get("/.well-known/agent.json")
    assert response.status_code == 200
    data = response.json()
    assert "name" in data
    assert "url" in data
    assert "version" in data
    assert "capabilities" in data


@pytest.mark.asyncio
async def test_send_message(client: AsyncClient):
    """Test sending a message without token (for public abilities)."""
    response = await client.post(
        "/a2a/message:send",
        json={
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "Hello Agent"}],
            }
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "taskId" in data
    assert data["status"] in ["working", "completed"]


@pytest.mark.asyncio
async def test_send_message_with_invalid_token(client: AsyncClient):
    """Test sending a message with invalid SKILL token."""
    response = await client.post(
        "/a2a/message:send",
        headers={"X-SKILL-TOKEN": "invalid_token"},
        json={
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "Hello Agent"}],
            },
            "abilityId": "00000000-0000-0000-0000-000000000001",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_send_message_with_valid_token_and_public_ability(
    client: AsyncClient, db_session, test_agent, public_ability
):
    """Test sending a message with valid token targeting a public ability."""
    # Install skill to get a valid token
    install_response = await client.post(
        "/api/skills/install",
        headers={"X-API-Key": test_agent["api_key"]},
        json={
            "skill_name": "test-skill",
            "ability_ids": [str(public_ability.id)],
        },
    )
    assert install_response.status_code == 201
    skill_token = install_response.json()["token"]

    # Send message with valid token and public ability
    response = await client.post(
        "/a2a/message:send",
        headers={"X-SKILL-TOKEN": skill_token},
        json={
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "Hello Agent"}],
            },
            "abilityId": str(public_ability.id),
        },
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_send_message_without_token_on_protected_ability(
    client: AsyncClient, db_session, test_agent, protected_ability
):
    """Test sending a message without token on protected ability fails."""
    response = await client.post(
        "/a2a/message:send",
        json={
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "Hello Agent"}],
            },
            "abilityId": str(protected_ability.id),
        },
    )
    # Should fail because ability is protected and no token provided
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_get_task(client: AsyncClient):
    """Test getting task status."""
    # Create a task first
    send_response = await client.post(
        "/a2a/message:send",
        json={
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "Test"}],
            }
        },
    )
    task_id = send_response.json()["taskId"]

    # Get task
    response = await client.get(f"/a2a/tasks/{task_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["taskId"] == task_id
    assert "status" in data


@pytest.mark.asyncio
async def test_list_tasks(client: AsyncClient):
    """Test listing tasks."""
    # Create a task first
    await client.post(
        "/a2a/message:send",
        json={
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "Test"}],
            }
        },
    )

    response = await client.get("/a2a/tasks")
    assert response.status_code == 200
    data = response.json()
    assert "tasks" in data


@pytest.mark.asyncio
async def test_cancel_task(client: AsyncClient):
    """Test canceling a task."""
    # Create a task
    send_response = await client.post(
        "/a2a/message:send",
        json={
            "message": {
                "role": "user",
                "parts": [{"type": "text", "text": "To be cancelled"}],
            }
        },
    )
    task_id = send_response.json()["taskId"]

    # Cancel
    response = await client.post(f"/a2a/tasks/{task_id}:cancel")
    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


@pytest.mark.asyncio
async def test_get_nonexistent_task(client: AsyncClient):
    """Test getting a nonexistent task."""
    response = await client.get("/a2a/tasks/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
