"""Message model for group chat."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.db_types import JsonField, UUIDField


class Message(Base):
    """Message model for group chat history."""

    __tablename__ = "messages"

    id = Column(UUIDField, primary_key=True, default=uuid.uuid4)
    group_id = Column(UUIDField, ForeignKey("groups.id"), nullable=False, index=True)
    sender_type = Column(String(20), nullable=False)  # 'agent' or 'human'
    sender_id = Column(UUIDField, nullable=False)
    sender_name = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    mentions = Column(JsonField, nullable=True, default=list)  # ['agent_id_1', 'agent_id_2']
    is_broadcast = Column(Boolean, default=False)  # @all message
    is_a2a_triggered = Column(Boolean, default=False)  # triggered an A2A call
    a2a_response_to = Column(UUIDField, nullable=True)  # message_id this is response to
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    group = relationship("Group", backref="messages")

    def __repr__(self):
        return f"<Message(id={self.id}, sender={self.sender_name}, group={self.group_id})>"


class AgentDiscussionSetting(Base):
    """Per-agent discussion mode setting for a specific group."""

    __tablename__ = "agent_discussion_settings"

    id = Column(UUIDField, primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUIDField, ForeignKey("agents.id"), nullable=False)
    group_id = Column(UUIDField, ForeignKey("groups.id"), nullable=False)
    discussion_mode = Column(Boolean, default=False, nullable=False)
    # Public abilities exposed in this group's chat
    public_abilities = Column(JsonField, nullable=True, default=list)
    # Limited abilities exposed in this group's chat
    limited_abilities = Column(JsonField, nullable=True, default=list)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Unique constraint
    __table_args__ = (
        # SQLite / PG compatible unique constraint via UniqueConstraint
    )

    def __repr__(self):
        return f"<AgentDiscussionSetting(agent={self.agent_id}, group={self.group_id}, mode={self.discussion_mode})>"
