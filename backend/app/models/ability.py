"""Ability model."""
import uuid
import hashlib
from datetime import datetime
from sqlalchemy import Column, String, DateTime, Boolean, ForeignKey, Enum as SQLEnum, Text, Integer
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.db_types import JsonField, UUIDField


class AbilityStatus(str, enum.Enum):
    """Ability status enum."""
    ACTIVE = "active"
    DEPRECATED = "deprecated"


class AccessLevel(str, enum.Enum):
    """
    Three-tier access control for abilities.

    - public: Anyone can call, no authentication required
    - protected: Requires valid SKILL token, unlimited usage
    - limited: Requires valid SKILL token, limited usage per token
    """
    PUBLIC = "public"      # L1: Public service - no auth needed
    PROTECTED = "protected"  # L2: Open authorization - token required, unlimited
    LIMITED = "limited"      # L3: Restricted - token required, limited quota


def compute_hash(content: str) -> str:
    """Compute SHA256 hash of content."""
    return hashlib.sha256(content.encode()).hexdigest()


class Ability(Base):
    """Ability model representing a callable capability of an agent."""

    __tablename__ = "abilities"

    id = Column(UUIDField, primary_key=True, default=uuid.uuid4)
    name = Column(String(255), nullable=False, index=True)
    group_id = Column(UUIDField, ForeignKey("groups.id"), nullable=True)
    agent_id = Column(UUIDField, ForeignKey("agents.id"), nullable=False)
    definition = Column(JsonField, nullable=False, default=dict)
    version = Column(String(50), default="1.0.0", nullable=False)
    hash = Column(String(64), nullable=True)
    # Access control: three-tier system
    access_level = Column(
        SQLEnum(AccessLevel),
        default=AccessLevel.PROTECTED,
        nullable=False,
    )
    # Quota per token (only meaningful when access_level=LIMITED)
    # None means unlimited, positive integer means max calls per token
    quota_per_token = Column(Integer, nullable=True)
    status = Column(SQLEnum(AbilityStatus), default=AbilityStatus.ACTIVE, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    group = relationship("Group", back_populates="abilities")
    agent = relationship("Agent", back_populates="abilities")

    def __repr__(self):
        return f"<Ability(id={self.id}, name={self.name}, version={self.version}, access={self.access_level})>"
