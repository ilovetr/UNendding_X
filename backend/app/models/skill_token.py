"""Skill Token model."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean
from sqlalchemy.orm import relationship

from app.database import Base
from app.db_types import JsonField, UUIDField


class SkillToken(Base):
    """Skill Token model for capability access control."""

    __tablename__ = "skill_tokens"

    id = Column(UUIDField, primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUIDField, ForeignKey("agents.id"), nullable=False)
    group_id = Column(UUIDField, ForeignKey("groups.id"), nullable=True)
    skill_name = Column(String(255), nullable=False, index=True)
    version = Column(String(50), default="1.0.0", nullable=False)
    permissions = Column(JsonField, nullable=False, default=list)
    token_jti = Column(String(255), unique=True, nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    issued_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Quota tracking for LIMITED access abilities
    # quota_remaining: None = unlimited, 0 = exhausted, N = N calls left
    quota_remaining = Column(Integer, nullable=True)
    # has_quota: True if this token has quota-limited permissions
    has_quota = Column(Boolean, default=False, nullable=False)

    # Relationships
    agent = relationship("Agent", back_populates="skill_tokens")

    def __repr__(self):
        return f"<SkillToken(id={self.id}, skill_name={self.skill_name}, quota={self.quota_remaining})>"
