"""Audit Log API endpoints + write helper."""
import uuid
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.audit_log import AuditLog
from app.api.auth import get_current_agent

router = APIRouter()


# ── Write helper (import-anywhere) ───────────────────────────────────────────

async def write_audit(
    db: AsyncSession,
    action: str,
    agent_id=None,
    resource_type: Optional[str] = None,
    resource_id=None,
    details: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
):
    """Write a single audit log entry. Call from any API handler."""
    log = AuditLog(
        agent_id=str(agent_id) if agent_id else None,
        action=action,
        resource_type=resource_type,
        resource_id=str(resource_id) if resource_id else None,
        details=details or {},
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    # Caller is responsible for commit; we do flush so ID is assigned
    await db.flush()
    return log


# ── Response schemas ──────────────────────────────────────────────────────────

class AuditLogResponse(BaseModel):
    id: str
    timestamp: datetime
    agent_id: Optional[str]
    action: str
    resource_type: Optional[str]
    resource_id: Optional[str]
    details: dict
    ip_address: Optional[str]


def _to_resp(log: AuditLog) -> AuditLogResponse:
    return AuditLogResponse(
        id=str(log.id),
        timestamp=log.timestamp,
        agent_id=str(log.agent_id) if log.agent_id else None,
        action=log.action,
        resource_type=log.resource_type,
        resource_id=str(log.resource_id) if log.resource_id else None,
        details=log.details or {},
        ip_address=log.ip_address,
    )


# ── Endpoints ─────────────────────────────────────────────────────────────────

@router.get("/mine", response_model=List[AuditLogResponse])
async def list_my_audit_logs(
    db: AsyncSession = Depends(get_db),
    current_agent=Depends(get_current_agent),
    action: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    """Return audit logs for the currently authenticated agent."""
    stmt = (
        select(AuditLog)
        .where(AuditLog.agent_id == str(current_agent.id))
        .order_by(desc(AuditLog.timestamp))
    )
    if action:
        stmt = stmt.where(AuditLog.action == action)
    stmt = stmt.offset(skip).limit(limit)

    result = await db.execute(stmt)
    return [_to_resp(log) for log in result.scalars().all()]


@router.get("", response_model=List[AuditLogResponse])
async def list_audit_logs(
    db: AsyncSession = Depends(get_db),
    agent_id: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """List all audit logs (open for now; add admin guard in P5)."""
    stmt = select(AuditLog).order_by(desc(AuditLog.timestamp))

    if agent_id:
        stmt = stmt.where(AuditLog.agent_id == agent_id)
    if action:
        stmt = stmt.where(AuditLog.action == action)
    if start_date:
        stmt = stmt.where(AuditLog.timestamp >= start_date)
    if end_date:
        stmt = stmt.where(AuditLog.timestamp <= end_date)

    stmt = stmt.offset(skip).limit(limit)
    result = await db.execute(stmt)
    return [_to_resp(log) for log in result.scalars().all()]
