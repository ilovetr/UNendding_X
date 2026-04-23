"""
Database type compatibility layer.
Automatically selects JSONB (PostgreSQL) or JSON (SQLite/others) based on configured DATABASE_URL.
"""
import os
from sqlalchemy import String, JSON
from sqlalchemy.types import TypeDecorator
import uuid as _uuid_module


def _is_pg() -> bool:
    """Check if the configured database is PostgreSQL."""
    url = os.environ.get("DATABASE_URL", "")
    return "postgresql" in url or "postgres" in url


# ── JSON field ──────────────────────────────────────────────────────────────
if _is_pg():
    from sqlalchemy.dialects.postgresql import JSONB as _JSON_TYPE
else:
    _JSON_TYPE = JSON  # type: ignore

JsonField = _JSON_TYPE


# ── UUID field ──────────────────────────────────────────────────────────────
class UUIDType(TypeDecorator):
    """
    Platform-independent UUID type.
    Uses PostgreSQL's native UUID in PG, stores as VARCHAR(36) elsewhere.
    """
    impl = String(36)
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, _uuid_module.UUID):
            return str(value)
        return str(_uuid_module.UUID(str(value)))

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return _uuid_module.UUID(str(value))

    @classmethod
    def default_uuid(cls):
        return _uuid_module.uuid4


# Expose a unified UUID column type
if _is_pg():
    from sqlalchemy.dialects.postgresql import UUID as _PG_UUID

    class PlatformUUID(TypeDecorator):
        """Uses PostgreSQL UUID natively, falls back to UUIDType for others."""
        impl = _PG_UUID(as_uuid=True)
        cache_ok = True

        def process_bind_param(self, value, dialect):
            return value

        def process_result_value(self, value, dialect):
            return value

    UUIDField = _PG_UUID(as_uuid=True)
else:
    UUIDField = UUIDType()  # type: ignore
