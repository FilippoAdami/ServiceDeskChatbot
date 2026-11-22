from __future__ import annotations

import enum
from typing import List, Optional


class TaskCategory(str, enum.Enum):
    """Canonical categories defined in docs/task.md."""

    RESET_PASSWORD = "Reset Password"
    EMAIL_ISSUES = "Problemi Email"
    SOFTWARE_ISSUES = "Malfunzionamenti Software"
    GENERIC_SUPPORT = "Richiesta Generica"


TASK_CATEGORIES: List[str] = [cat.value for cat in TaskCategory]

# Keywords mapping for intent and categorization
AUTH_KEYWORDS = [
    "password",
    "accesso",
    "login",
    "credenziali",
    "account",
    "mfa",
    "authenticator",
    "bloccato",
    "blocco",
    "sblocco",
    "autenticazione",
    "pin",
    "ad",
    "active directory",
]

EMAIL_KEYWORDS = [
    "outlook",
    "email",
    "posta",
    "mail",
    "inbox",
    "allegato",
    "allegati",
    "casella",
    "messaggi",
    "exchange",
    "spam",
    "invio",
    "ricezione",
]

SOFTWARE_KEYWORDS = [
    "software",
    "programma",
    "programmi",
    "installare",
    "installazione",
    "licenza",
    "app",
    "applicativo",
    "applicazione",
    "crash",
    "errore",
    "blocco",
    "teams",
    "office",
    "excel",
    "word",
    "powerpoint",
    "browser",
    "chrome",
    "edge",
    "pc",
    "computer",
    "schermo",
    "monitor",
    "mouse",
    "tastiera",
    "stampante",
    "stampa",
    "hardware",
    "vpn",
    "wi-fi",
    "wifi",
    "rete",
    "connessione",
    "internet",
]


def normalize_task_category(
    raw_category: Optional[str] = None,
    text: Optional[str] = None,
) -> str:
    """Normalize any raw category string or text snippet into one of the 4 canonical TaskCategory values."""
    # 1. Match explicit canonical category values
    if raw_category:
        clean_raw = raw_category.strip()
        for cat in TaskCategory:
            if clean_raw.lower() == cat.value.lower():
                return cat.value

        clean_lower = clean_raw.lower()
        if any(k in clean_lower for k in ["email", "posta", "outlook", "mail"]):
            return TaskCategory.EMAIL_ISSUES.value
        if any(k in clean_lower for k in ["password", "account", "access", "auth", "mfa", "credenzial"]):
            return TaskCategory.RESET_PASSWORD.value
        if any(k in clean_lower for k in ["software", "applicaz", "app", "crash", "program", "hardware", "stamp"]):
            return TaskCategory.SOFTWARE_ISSUES.value

    # 2. If text is provided, analyze user text
    if text:
        text_lower = text.lower()
        # Check email first (e.g. "problemi accesso alla posta" has "accesso" but refers to email)
        if any(k in text_lower for k in EMAIL_KEYWORDS):
            return TaskCategory.EMAIL_ISSUES.value
        if any(k in text_lower for k in AUTH_KEYWORDS):
            return TaskCategory.RESET_PASSWORD.value
        if any(k in text_lower for k in SOFTWARE_KEYWORDS):
            return TaskCategory.SOFTWARE_ISSUES.value

    # 3. Fallback to generic support
    return TaskCategory.GENERIC_SUPPORT.value
