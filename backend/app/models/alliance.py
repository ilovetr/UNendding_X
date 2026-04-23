"""Agent Alliance model — linked agents under the same human user."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey, Enum as SQLEnum
from sqlalchemy.orm import relationship
import enum

from app.database import Base
from app.db_types import JsonField, UUIDField


class AllianceStatus(str, enum.Enum):
    """Alliance relationship status."""
    PENDING = "pending"   # handshake not accepted
    ACTIVE = "active"     # both parties accepted
    REJECTED = "rejected" # target rejected
    REMOVED = "removed"   # removed by either party


class AgentAlliance(Base):
    """Bidirectional agent alliance relationship."""

    __tablename__ = "agent_alliances"

    id = Column(UUIDField, primary_key=True, default=uuid.uuid4)

    # The agent who initiated the alliance request
    requester_id = Column(UUIDField, ForeignKey("agents.id"), nullable=False, index=True)

    # The agent being invited
    target_id = Column(UUIDField, ForeignKey("agents.id"), nullable=False, index=True)

    # Who accepted the alliance (null until accepted)
    accepted_by_id = Column(UUIDField, ForeignKey("agents.id"), nullable=True)

    # Status
    status = Column(
        SQLEnum(AllianceStatus),
        default=AllianceStatus.ACTIVE,
        nullable=False,
        index=True,
    )

    # Human-readable note (e.g. "我的Claude", "备用智能体")
    label = Column(String(255), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    requester = relationship("Agent", foreign_keys=[requester_id])
    target = relationship("Agent", foreign_keys=[target_id])
    accepted_by = relationship("Agent", foreign_keys=[accepted_by_id])

    def __repr__(self):
        return f"<AgentAlliance({self.requester_id} ↔ {self.target_id}, status={self.status})>"
