"""Audit Log model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Text

from app.database import Base
from app.db_types import JsonField, UUIDField


class AuditAction(str):
    """Audit action types."""
    AGENT_REGISTER = "agent_register"
    AGENT_LOGIN = "agent_login"
    GROUP_CREATE = "group_create"
    GROUP_JOIN = "group_join"
    GROUP_LEAVE = "group_leave"
    ABILITY_REGISTER = "ability_register"
    ABILITY_CALL = "ability_call"
    SKILL_INSTALL = "skill_install"
    SKILL_VERIFY = "skill_verify"
    PERMISSION_DENIED = "permission_denied"


class AuditLog(Base):
    """Audit log model for tracking all operations."""

    __tablename__ = "audit_logs"

    id = Column(UUIDField, primary_key=True, default=uuid.uuid4)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    agent_id = Column(UUIDField, nullable=True, index=True)
    action = Column(String(100), nullable=False, index=True)
    resource_type = Column(String(100), nullable=True)
    resource_id = Column(UUIDField, nullable=True)
    details = Column(JsonField, nullable=True, default=dict)
    ip_address = Column(String(45), nullable=True)
    user_agent = Column(Text, nullable=True)

    def __repr__(self):
        return f"<AuditLog(id={self.id}, action={self.action}, timestamp={self.timestamp})>"
