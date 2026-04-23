"""A2A Protocol type definitions."""
from enum import Enum
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field
import uuid


class TaskStatus(str, Enum):
    """Task status enum per A2A spec."""
    SUBMITTED = "submitted"
    WORKING = "working"
    INPUT_REQUIRED = "input-required"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class MessageRole(str, Enum):
    """Message role enum per A2A spec."""
    AGENT = "agent"
    USER = "user"


class TextPart(BaseModel):
    """Text part of a message."""
    type: str = "text"
    text: str


class DataPart(BaseModel):
    """Data part of a message."""
    type: str = "data"
    data: Dict[str, Any]


class Message(BaseModel):
    """A2A Message model."""
    role: MessageRole
    parts: List[TextPart | DataPart]
    metadata: Optional[Dict[str, Any]] = None


class Task(BaseModel):
    """A2A Task model."""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    sessionId: Optional[str] = None
    status: TaskStatus = TaskStatus.SUBMITTED
    messages: List[Message] = []
    metadata: Optional[Dict[str, Any]] = None


class TaskSendRequest(BaseModel):
    """Request to send a message and create/update a task."""
    taskId: Optional[str] = None
    sessionId: Optional[str] = None
    message: Message
    metadata: Optional[Dict[str, Any]] = None
    # Extended field: target ability for SKILL token permission check
    abilityId: Optional[str] = None


class TaskSendResponse(BaseModel):
    """Response for task send."""
    taskId: str
    status: TaskStatus
    messages: List[Message]


class TaskStatusRequest(BaseModel):
    """Request to get task status."""
    taskId: str


class TaskStatusResponse(BaseModel):
    """Response for task status."""
    taskId: str
    status: TaskStatus
    metadata: Optional[Dict[str, Any]] = None


class TaskCancelRequest(BaseModel):
    """Request to cancel a task."""
    taskId: str


class TaskQueryRequest(BaseModel):
    """Request to query task history."""
    taskId: str
    historyLength: Optional[int] = 10
