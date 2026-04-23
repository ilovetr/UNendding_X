"""Agent model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.db_types import JsonField, UUIDField


class AgentStatus(str, enum.Enum):
    """Agent status enum."""
    ACTIVE = "active"
    INACTIVE = "inactive"


class Agent(Base):
    """Agent model representing an AI agent in the system."""

    __tablename__ = "agents"

    id = Column(UUIDField, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    did = Column(String(512), unique=True, nullable=True, index=True)
    agent_card = Column(JsonField, nullable=False, default=dict)
    endpoint = Column(String(512), nullable=True)
    api_key = Column(String(255), nullable=True)  # bcrypt hashed
    status = Column(
        SQLEnum(AgentStatus),
        default=AgentStatus.ACTIVE,
        nullable=False
    )
    # Default discussion mode for new groups (can be overridden per-group)
    discussion_mode = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owned_groups = relationship("Group", back_populates="owner")
    abilities = relationship("Ability", back_populates="agent", cascade="all, delete-orphan")
    skill_tokens = relationship("SkillToken", back_populates="agent", cascade="all, delete-orphan")
    group_memberships = relationship("GroupMember", back_populates="agent")

    def __repr__(self):
        return f"<Agent(id={self.id}, name={self.name}, status={self.status})>"
