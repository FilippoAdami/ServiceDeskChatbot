from __future__ import annotations

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.audit import record_audit_event
from backend.app.core.redaction import redact_secrets
from backend.app.db.models import Conversation, Message, MessageRole, SupportRequest, utc_now
from backend.app.db.session import get_db
from backend.app.schemas.conversation import (
    ConversationCreate,
    ConversationDetailResponse,
    ConversationListResponse,
    ConversationSummaryResponse,
)
from backend.app.schemas.message import MessageCreate, MessageResponse
from backend.app.schemas.support_request import SupportRequestCreate, SupportRequestResponse

router = APIRouter(prefix="/conversations", tags=["Conversations"])


@router.post(
    "",
    response_model=ConversationDetailResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation thread",
)
def create_conversation(
    payload: ConversationCreate,
    db: Session = Depends(get_db),
) -> ConversationDetailResponse:
    """Create a new conversation thread for the demo employee."""
    title = payload.title.strip() if payload.title and payload.title.strip() else "Nuova Conversazione"
    user_id = payload.user_id.strip() if payload.user_id and payload.user_id.strip() else "user_demo_01"

    conv = Conversation(
        title=title,
        user_id=user_id,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(conv)
    db.flush()

    record_audit_event(
        db=db,
        event_type="conversation_created",
        conversation_id=conv.id,
        payload={"title": conv.title, "user_id": conv.user_id},
    )
    db.commit()
    db.refresh(conv)

    return ConversationDetailResponse.model_validate(conv)


@router.get(
    "",
    response_model=ConversationListResponse,
    summary="List conversations with pagination",
)
def list_conversations(
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
) -> ConversationListResponse:
    """List conversations ordered by most recently updated."""
    total = db.scalar(select(func.count(Conversation.id))) or 0

    stmt = (
        select(Conversation)
        .order_by(Conversation.updated_at.desc())
        .limit(limit)
        .offset(offset)
    )
    conversations = db.scalars(stmt).all()

    items: List[ConversationSummaryResponse] = []
    for conv in conversations:
        msg_count = db.scalar(
            select(func.count(Message.id)).where(Message.conversation_id == conv.id)
        ) or 0
        req_count = db.scalar(
            select(func.count(SupportRequest.id)).where(SupportRequest.conversation_id == conv.id)
        ) or 0

        items.append(
            ConversationSummaryResponse(
                id=conv.id,
                user_id=conv.user_id,
                title=conv.title,
                status=conv.status,
                created_at=conv.created_at,
                updated_at=conv.updated_at,
                message_count=msg_count,
                request_count=req_count,
            )
        )

    return ConversationListResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation details and ordered messages",
)
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db),
) -> ConversationDetailResponse:
    """Retrieve conversation details with all chronological messages and linked requests."""
    conv = db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    ).scalar_one_or_none()

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found",
        )

    return ConversationDetailResponse.model_validate(conv)


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add a user message to a conversation",
)
def add_message(
    conversation_id: str,
    payload: MessageCreate,
    db: Session = Depends(get_db),
) -> MessageResponse:
    """Add a user message to the conversation.

    Public API in G02 strictly restricts role to 'user'. Redacts secrets
    before saving and records a synchronous audit event.
    """
    conv = db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    ).scalar_one_or_none()

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found",
        )

    raw_content = payload.content.strip()
    if not raw_content:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Message content cannot be empty or whitespace",
        )

    # Redact secrets prior to persistence
    redacted_content = redact_secrets(raw_content)

    msg = Message(
        conversation_id=conv.id,
        role=MessageRole.USER.value,
        content=redacted_content,
        created_at=utc_now(),
    )
    db.add(msg)

    # Update conversation updated_at timestamp
    conv.updated_at = utc_now()

    # Record audit event (without full text or secrets)
    record_audit_event(
        db=db,
        event_type="message_sent",
        conversation_id=conv.id,
        payload={
            "role": MessageRole.USER.value,
            "char_count": len(raw_content),
            "had_redacted_secrets": (redacted_content != raw_content),
        },
    )

    db.commit()
    db.refresh(msg)

    return MessageResponse.model_validate(msg)


@router.post(
    "/{conversation_id}/requests",
    response_model=SupportRequestResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a SupportRequest under this conversation",
)
def create_support_request(
    conversation_id: str,
    payload: SupportRequestCreate,
    db: Session = Depends(get_db),
) -> SupportRequestResponse:
    """Explicitly register an IT support problem associated with this conversation thread."""
    conv = db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    ).scalar_one_or_none()

    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation '{conversation_id}' not found",
        )

    req = SupportRequest(
        conversation_id=conv.id,
        title=payload.title.strip(),
        description=payload.description.strip(),
        initial_category=payload.initial_category.strip() if payload.initial_category else None,
        created_at=utc_now(),
        updated_at=utc_now(),
    )
    db.add(req)

    # Update conversation updated_at timestamp
    conv.updated_at = utc_now()

    record_audit_event(
        db=db,
        event_type="support_request_created",
        conversation_id=conv.id,
        request_id=req.id,
        payload={
            "title": req.title,
            "category": req.initial_category,
            "status": req.status,
        },
    )

    db.commit()
    db.refresh(req)

    return SupportRequestResponse.model_validate(req)
