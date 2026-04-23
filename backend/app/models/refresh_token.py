"""RefreshToken model for temporary access token mechanism."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, String, Text
from sqlalchemy.orm import declarative_base

from app.db_types import UUIDField

Base = declarative_base()


class RefreshToken(Base):
    """Store refresh token hashes for token rotation.

    Note: We only store the SHA256 hash of the refresh token, not the token itself.
    This is a security measure - even if the database is compromised,
    attackers cannot use the tokens directly.
    """
    __tablename__ = "refresh_tokens"

    id = Column(UUIDField, primary_key=True, default=uuid.uuid4)
    agent_id = Column(UUIDField, nullable=False, index=True)
    token_hash = Column(Text, nullable=False, unique=True)  # SHA256 hash
    device_id = Column(String(255), nullable=False)  # Device/client identifier
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked = Column(Boolean, default=False, nullable=False)

    def __repr__(self):
        return f"<RefreshToken(id={self.id}, agent_id={self.agent_id}, revoked={self.revoked})>"
