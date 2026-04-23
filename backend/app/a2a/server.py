"""A2A Server implementation."""
import uuid
from datetime import datetime
from typing import Dict, Optional, AsyncIterator, List
from fastapi import APIRouter, HTTPException, Header, Depends, Body
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import json
import asyncio

from app.a2a.types import (
    Task,
    TaskStatus,
    Message,
    TaskSendRequest,
    TaskSendResponse,
    TaskStatusResponse,
    TaskCancelRequest,
)
from app.a2a.auth import verify_skill_token, verify_ability_access, TokenContext
from app.config import settings
from app.database import get_db, AsyncSession

router = APIRouter()

# In-memory task store (replace with Redis/DB in production)
tasks: Dict[str, Task] = {}


async def event_generator(task_id: str) -> AsyncIterator[str]:
    """Generate SSE events for task streaming."""
    while True:
        task = tasks.get(task_id)
        if task is None:
            yield f"event: error\ndata: Task not found\n\n"
            break

        if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
            yield f"event: task_update\ndata: {json.dumps({'status': task.status})}\n\n"
            break

        yield f"event: heartbeat\ndata: {json.dumps({'timestamp': datetime.utcnow().isoformat()})}\n\n"
        await asyncio.sleep(5)  # Heartbeat every 5 seconds


@router.post("/message:send")
async def send_message(
    request: TaskSendRequest,
    token_ctx: TokenContext = Depends(verify_skill_token),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the agent (synchronous).

    Requires X-SKILL-TOKEN header unless target ability is public.
    Quota is decremented during verification for LIMITED abilities.
    """
    # Verify ability access if ability_id specified
    # This also decrements quota for LIMITED abilities
    if request.abilityId:
        await verify_ability_access(token_ctx, request.abilityId, db)

    # Get or create task
    if request.taskId and request.taskId in tasks:
        task = tasks[request.taskId]
    else:
        task_id = request.taskId or str(uuid.uuid4())
        task = Task(
            id=task_id,
            sessionId=request.sessionId,
            status=TaskStatus.WORKING,
        )
        tasks[task_id] = task

    # Add message to task
    task.messages.append(request.message)

    # Process the message (placeholder - implement agent logic here)
    # In a real implementation, this would call the agent's processing logic
    task.status = TaskStatus.COMPLETED

    return TaskSendResponse(
        taskId=task.id,
        status=task.status,
        messages=task.messages,
    )


@router.post("/message:stream")
async def send_message_stream(
    request: TaskSendRequest,
    token_ctx: TokenContext = Depends(verify_skill_token),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the agent with streaming response (SSE).

    Requires X-SKILL-TOKEN header unless target ability is public.
    """
    # Verify ability access if ability_id specified
    if request.abilityId:
        await verify_ability_access(token_ctx, request.abilityId, db)

    # Get or create task
    if request.taskId and request.taskId in tasks:
        task = tasks[request.taskId]
    else:
        task_id = request.taskId or str(uuid.uuid4())
        task = Task(
            id=task_id,
            sessionId=request.sessionId,
            status=TaskStatus.WORKING,
        )
        tasks[task_id] = task

    # Add message to task
    task.messages.append(request.message)

    async def stream_response():
        # Send initial task ID
        yield f"event: task_id\ndata: {json.dumps({'taskId': task.id})}\n\n"

        # Simulate processing
        await asyncio.sleep(0.5)

        # Mark as completed
        task.status = TaskStatus.COMPLETED
        yield f"event: task_update\ndata: {json.dumps({'status': task.status})}\n\n"

    return StreamingResponse(
        stream_response(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """Get the status of a task."""
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatusResponse(
        taskId=task.id,
        status=task.status,
        metadata={"message_count": len(task.messages)},
    )


@router.get("/tasks")
async def list_tasks(
    session_id: Optional[str] = None,
    x_api_key: Optional[str] = Header(None),
):
    """List tasks with optional session filter."""
    task_list = list(tasks.values())

    if session_id:
        task_list = [t for t in task_list if t.sessionId == session_id]

    return {
        "tasks": [
            {
                "id": t.id,
                "sessionId": t.sessionId,
                "status": t.status,
                "messageCount": len(t.messages),
            }
            for t in task_list[-50:]  # Last 50 tasks
        ]
    }


@router.post("/tasks/{task_id}:cancel")
async def cancel_task(
    task_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """Cancel a task."""
    task = tasks.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status in [TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot cancel task with status: {task.status}",
        )

    task.status = TaskStatus.CANCELLED
    return TaskStatusResponse(
        taskId=task.id,
        status=task.status,
    )


@router.delete("/tasks/{task_id}")
async def delete_task(
    task_id: str,
    x_api_key: Optional[str] = Header(None),
):
    """Delete/archive a task."""
    if task_id in tasks:
        del tasks[task_id]
    return {"status": "deleted", "taskId": task_id}
