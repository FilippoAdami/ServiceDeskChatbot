from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.audit import record_audit_event
from backend.app.db.models import (
    AgentPhase,
    Conversation,
    ConversationStatus,
    RequestOutcome,
    RequestStatus,
    SupportRequest,
    Ticket,
    TicketStatus,
    utc_now,
)
from backend.app.db.session import get_db
from backend.app.schemas.support_request import (
    ConfirmResolutionRequest,
    SupportRequestListResponse,
    SupportRequestResponse,
)

router = APIRouter(prefix="/requests", tags=["Support Requests"])


@router.get(
    "",
    response_model=SupportRequestListResponse,
    summary="List all SupportRequests with filtering and pagination",
)
def list_support_requests(
    status_filter: Optional[str] = Query(
        default=None,
        alias="status",
        description="Filter by status (open, in_progress, closed)",
    ),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> SupportRequestListResponse:
    """Retrieve support requests for the technician view."""
    base_query = select(SupportRequest)
    count_query = select(func.count(SupportRequest.id))

    if status_filter:
        base_query = base_query.where(SupportRequest.status == status_filter.strip())
        count_query = count_query.where(SupportRequest.status == status_filter.strip())

    total = db.scalar(count_query) or 0

    stmt = base_query.order_by(SupportRequest.created_at.desc()).limit(limit).offset(offset)
    records = db.scalars(stmt).all()

    items = [SupportRequestResponse.model_validate(r) for r in records]

    return SupportRequestListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{request_id}",
    response_model=SupportRequestResponse,
    summary="Get single SupportRequest by ID",
)
def get_support_request(
    request_id: str,
    db: Session = Depends(get_db),
) -> SupportRequestResponse:
    """Retrieve details for a single SupportRequest."""
    req = db.execute(select(SupportRequest).where(SupportRequest.id == request_id)).scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Support request '{request_id}' not found",
        )

    return SupportRequestResponse.model_validate(req)


@router.post(
    "/{request_id}/confirm-resolution",
    response_model=SupportRequestResponse,
    summary="Confirm or auto-close a bot-resolved support request",
)
def confirm_support_request_resolution(
    request_id: str,
    payload: ConfirmResolutionRequest = ConfirmResolutionRequest(),
    db: Session = Depends(get_db),
) -> SupportRequestResponse:
    """Confirm resolution for a self-service support request handled by the bot.

    Guards:
    - Rejects with HTTP 400 if a human technician ticket (Ticket) is currently open or assigned.
    - Transitions SupportRequest.status to CLOSED.
    - Sets outcome to RESOLVED_CONFIRMED.
    - Sets phase to FINALIZATION.
    - Emits structured audit event recording whether it was confirmed by user or auto-timer.
    """
    req = db.execute(select(SupportRequest).where(SupportRequest.id == request_id)).scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Support request '{request_id}' not found",
        )

    # Invariant: Bot or user cannot close a request that has an active human technician ticket
    active_ticket = db.scalar(
        select(Ticket).where(
            Ticket.support_request_id == req.id,
            Ticket.status != TicketStatus.CLOSED.value,
        )
    )
    if active_ticket:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "I ticket aperti assegnati ai tecnici non possono essere chiusi dal bot o dall'utente. "
                "La chiusura deve essere gestita dal tecnico assegnato."
            ),
        )

    now = utc_now()
    req.status = RequestStatus.CLOSED.value
    req.outcome = RequestOutcome.RESOLVED_CONFIRMED.value
    req.phase = AgentPhase.FINALIZATION.value
    req.updated_at = now

    conv = db.scalar(select(Conversation).where(Conversation.id == req.conversation_id))
    if conv:
        conv.status = ConversationStatus.ARCHIVED.value
        conv.updated_at = now

    record_audit_event(
        db=db,
        event_type="support_request_resolved_confirmed",
        conversation_id=req.conversation_id,
        request_id=req.id,
        payload={
            "confirmed_by_user": payload.confirmed_by_user,
            "status": req.status,
            "outcome": req.outcome,
            "closed_at": now.isoformat(),
        },
    )

    db.commit()
    db.refresh(req)

    return SupportRequestResponse.model_validate(req)


@router.post(
    "/{request_id}/reopen",
    response_model=SupportRequestResponse,
    summary="Keep conversation open / reopen support request for further assistance",
)
def reopen_support_request(
    request_id: str,
    db: Session = Depends(get_db),
) -> SupportRequestResponse:
    """Keep conversation open or reopen request if user has additional questions."""
    req = db.execute(select(SupportRequest).where(SupportRequest.id == request_id)).scalar_one_or_none()

    if not req:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Support request '{request_id}' not found",
        )

    now = utc_now()
    req.status = RequestStatus.OPEN.value
    req.phase = AgentPhase.DIAGNOSIS.value
    req.outcome = None
    req.updated_at = now

    conv = db.scalar(select(Conversation).where(Conversation.id == req.conversation_id))
    if conv:
        conv.status = ConversationStatus.ACTIVE.value
        conv.updated_at = now

    record_audit_event(
        db=db,
        event_type="support_request_reopened",
        conversation_id=req.conversation_id,
        request_id=req.id,
        payload={
            "status": req.status,
            "phase": req.phase,
        },
    )

    db.commit()
    db.refresh(req)

    return SupportRequestResponse.model_validate(req)

