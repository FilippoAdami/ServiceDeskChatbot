from __future__ import annotations

from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from backend.app.db.models import AuditEvent


def record_audit_event(
    db: Session,
    event_type: str,
    conversation_id: Optional[str] = None,
    request_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> AuditEvent:
    """Record a synchronous audit event with sanitized payload.

    Audit events must never record full message contents or raw credentials.
    """
    clean_payload = dict(payload or {})

    # Strip any accidentally passed full text or credential fields
    for forbidden_key in ("content", "text", "password", "token", "key", "secret"):
        if forbidden_key in clean_payload:
            del clean_payload[forbidden_key]

    event = AuditEvent(
        event_type=event_type,
        conversation_id=conversation_id,
        request_id=request_id,
        payload=clean_payload,
    )
    db.add(event)
    return event
