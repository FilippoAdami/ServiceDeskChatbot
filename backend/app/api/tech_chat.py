from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.app.agent.tech_assistant import (
    TechnicianAssistantService,
    get_tech_assistant_service,
)
from backend.app.db.session import get_db
from backend.app.schemas.tech_chat import (
    TechnicianChatHistoryResponse,
    TechnicianChatMessageRequest,
    TechnicianChatMessageResponse,
    TechnicianChatTurnResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tickets", tags=["Technician Chat"])


@router.get("/{ticket_id}/chat", response_model=TechnicianChatHistoryResponse)
def get_ticket_chat_history(
    ticket_id: str,
    db: Session = Depends(get_db),
    service: TechnicianAssistantService = Depends(get_tech_assistant_service),
) -> TechnicianChatHistoryResponse:
    """Restituisce la cronologia dei messaggi scambiati tra tecnico e assistente AI per il ticket."""
    try:
        messages = service.get_chat_history(db=db, ticket_id=ticket_id)
        return TechnicianChatHistoryResponse(
            items=[TechnicianChatMessageResponse.model_validate(m) for m in messages],
            total=len(messages),
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Errore nel recupero della chat tecnica per il ticket {ticket_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore interno nel recupero della cronologia: {exc}",
        )


@router.post("/{ticket_id}/chat", response_model=TechnicianChatTurnResponse)
async def post_ticket_chat_message(
    ticket_id: str,
    payload: TechnicianChatMessageRequest,
    db: Session = Depends(get_db),
    service: TechnicianAssistantService = Depends(get_tech_assistant_service),
) -> TechnicianChatTurnResponse:
    """Invia un messaggio del tecnico all'assistente AI e riceve risposta e proposte operative."""
    try:
        tech_msg, assistant_msg, proposals = await service.handle_turn(
            db=db,
            ticket_id=ticket_id,
            technician_message=payload.content,
            author=payload.author,
        )
        return TechnicianChatTurnResponse(
            technician_message=TechnicianChatMessageResponse.model_validate(tech_msg),
            assistant_message=TechnicianChatMessageResponse.model_validate(assistant_msg),
            proposals=proposals if isinstance(proposals, dict) else {},
        )
    except HTTPException:
        raise
    except Exception as exc:
        logger.error(f"Errore nel turno di chat tecnica per il ticket {ticket_id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Errore nell'elaborazione del messaggio tecnico: {exc}",
        )
