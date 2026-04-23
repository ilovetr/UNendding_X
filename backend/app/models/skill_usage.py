"""Skill Usage Log model - records each ability invocation."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Integer, Boolean, Text
from sqlalchemy.orm import relationship

from app.database import Base
from app.db_types import JsonField, UUIDField


class SkillUsage(Base):
    """
    Skill Usage Log model - records each ability invocation for audit and quota tracking.

    Used for:
    - Quota deduction (LIMITED access abilities)
    - Usage auditing
    - Analytics
    """

    __tablename__ = "skill_usages"

    id = Column(UUIDField, primary_key=True, default=uuid.uuid4)
    # Token that was used
    token_id = Column(UUIDField, ForeignKey("skill_tokens.id"), nullable=False)
    # Ability that was called
    ability_id = Column(UUIDField, ForeignKey("abilities.id"), nullable=False)
    # Agent who issued the token (for quota tracking)
    issuer_agent_id = Column(UUIDField, ForeignKey("agents.id"), nullable=False)
    # Result
    success = Column(Boolean, nullable=False, default=True)
    error_message = Column(Text, nullable=True)
    # Extra info (renamed from 'metadata' to avoid SQLAlchemy conflict)
    extra_data = Column(JsonField, nullable=True)
    # Timestamp
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Relationships (lazy loaded to avoid circular imports)
    token = relationship("SkillToken", lazy="select")
    ability = relationship("Ability", lazy="select")
    issuer = relationship("Agent", lazy="select")

    def __repr__(self):
        return f"<SkillUsage(id={self.id}, ability={self.ability_id}, success={self.success})>"
