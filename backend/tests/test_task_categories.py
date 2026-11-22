from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.app.db.models import Conversation, SupportRequest, Ticket, TicketPriority, TicketStatus
from backend.app.knowledge.categories import (
    TASK_CATEGORIES,
    TaskCategory,
    normalize_task_category,
)
from backend.app.main import app


def test_normalize_task_category_direct_matches():
    """Verify that exact and case-insensitive canonical categories match perfectly."""
    assert len(TASK_CATEGORIES) == 4
    assert normalize_task_category("Reset Password") == TaskCategory.RESET_PASSWORD.value
    assert normalize_task_category("problemi email") == TaskCategory.EMAIL_ISSUES.value
    assert normalize_task_category("Malfunzionamenti Software") == TaskCategory.SOFTWARE_ISSUES.value
    assert normalize_task_category("richiesta generica") == TaskCategory.GENERIC_SUPPORT.value


def test_normalize_task_category_aliases():
    """Verify legacy or partial aliases map to canonical categories."""
    assert normalize_task_category("account") == TaskCategory.RESET_PASSWORD.value
    assert normalize_task_category("auth") == TaskCategory.RESET_PASSWORD.value
    assert normalize_task_category("email") == TaskCategory.EMAIL_ISSUES.value
    assert normalize_task_category("software") == TaskCategory.SOFTWARE_ISSUES.value
    assert normalize_task_category("hardware") == TaskCategory.SOFTWARE_ISSUES.value
    assert normalize_task_category("general") == TaskCategory.GENERIC_SUPPORT.value
    assert normalize_task_category("other") == TaskCategory.GENERIC_SUPPORT.value
    assert normalize_task_category(None) == TaskCategory.GENERIC_SUPPORT.value


def test_normalize_task_category_from_user_text():
    """Verify natural language text inference matches appropriate category."""
    # Email issue with words like 'accesso' should still classify as Email
    email_text = "Non riesco ad accedere alla casella di posta Outlook questa mattina"
    assert normalize_task_category(None, text=email_text) == TaskCategory.EMAIL_ISSUES.value

    # Password reset
    pw_text = "Ho dimenticato la mia password del pc e l'account è bloccato"
    assert normalize_task_category(None, text=pw_text) == TaskCategory.RESET_PASSWORD.value

    # Software crash
    sw_text = "L'applicativo Teams crasha continuamente e il programma si chiude da solo"
    assert normalize_task_category(None, text=sw_text) == TaskCategory.SOFTWARE_ISSUES.value

    # Generic request
    gen_text = "Vorrei informazioni sulla procedura per le ferie aziendali"
    assert normalize_task_category(None, text=gen_text) == TaskCategory.GENERIC_SUPPORT.value


def test_ticket_api_category_filtering(db_session: Session):
    """Verify that GET /api/tickets filters correctly by category and populates category field."""
    client = TestClient(app)

    # 1. Setup Conversation and SupportRequests with different categories
    conv = Conversation(user_id="user_cat_demo")
    db_session.add(conv)
    db_session.flush()

    req_pw = SupportRequest(
        conversation_id=conv.id,
        title="Problema Password",
        description="Password dimenticata",
        initial_category=TaskCategory.RESET_PASSWORD.value,
    )
    req_mail = SupportRequest(
        conversation_id=conv.id,
        title="Problema Email",
        description="Outlook bloccato",
        initial_category=TaskCategory.EMAIL_ISSUES.value,
    )
    req_sw = SupportRequest(
        conversation_id=conv.id,
        title="Crash Software",
        description="Excel in crash",
        initial_category=TaskCategory.SOFTWARE_ISSUES.value,
    )
    db_session.add_all([req_pw, req_mail, req_sw])
    db_session.flush()

    # 2. Create Tickets
    ticket_pw = Ticket(
        support_request_id=req_pw.id,
        conversation_id=conv.id,
        status=TicketStatus.OPEN.value,
        priority=TicketPriority.HIGH.value,
        title="Ticket Reset Password",
        summary="Reset password richiesta",
        symptoms="Accesso negato",
        attempted_steps="Nessuno",
        diagnostic_findings="Account valido",
    )
    ticket_mail = Ticket(
        support_request_id=req_mail.id,
        conversation_id=conv.id,
        status=TicketStatus.OPEN.value,
        priority=TicketPriority.MEDIUM.value,
        title="Ticket Posta",
        summary="Outlook non recapita",
        symptoms="Invio fallito",
        attempted_steps="Riavvio",
        diagnostic_findings="Server ok",
    )
    ticket_sw = Ticket(
        support_request_id=req_sw.id,
        conversation_id=conv.id,
        status=TicketStatus.OPEN.value,
        priority=TicketPriority.LOW.value,
        title="Ticket Software",
        summary="Excel crash all'avvio",
        symptoms="Chiusura anomala",
        attempted_steps="Riavvio PC",
        diagnostic_findings="File corrotto",
    )
    db_session.add_all([ticket_pw, ticket_mail, ticket_sw])
    db_session.commit()

    # 3. Test filtering by Reset Password
    res_pw = client.get(f"/api/tickets?category={TaskCategory.RESET_PASSWORD.value}")
    assert res_pw.status_code == 200
    data_pw = res_pw.json()
    assert any(t["id"] == ticket_pw.id for t in data_pw["items"])
    assert all(t["category"] == TaskCategory.RESET_PASSWORD.value for t in data_pw["items"])

    # 4. Test filtering by Problemi Email
    res_mail = client.get(f"/api/tickets?category={TaskCategory.EMAIL_ISSUES.value}")
    assert res_mail.status_code == 200
    data_mail = res_mail.json()
    assert any(t["id"] == ticket_mail.id for t in data_mail["items"])
    assert all(t["category"] == TaskCategory.EMAIL_ISSUES.value for t in data_mail["items"])

    # 5. Test filtering by Malfunzionamenti Software
    res_sw = client.get(f"/api/tickets?category={TaskCategory.SOFTWARE_ISSUES.value}")
    assert res_sw.status_code == 200
    data_sw = res_sw.json()
    assert any(t["id"] == ticket_sw.id for t in data_sw["items"])
    assert all(t["category"] == TaskCategory.SOFTWARE_ISSUES.value for t in data_sw["items"])

    # 6. Test Single Ticket Detail includes category
    res_detail = client.get(f"/api/tickets/{ticket_pw.id}")
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert detail_data["category"] == TaskCategory.RESET_PASSWORD.value
