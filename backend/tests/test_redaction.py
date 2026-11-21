from __future__ import annotations

from backend.app.core.redaction import redact_secrets


def test_redact_bearer_token() -> None:
    text = "Ecco il token: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.xyz per accedere"
    result = redact_secrets(text)
    assert "Bearer [REDACTED_TOKEN]" in result
    assert "eyJhbGciOiJIUzI1Ni" not in result


def test_redact_google_api_key() -> None:
    text = "Usa questa chiave AIzaSyD3x92jfk309slkd0293kd0293kd0293kd per Gemini"
    result = redact_secrets(text)
    assert "[REDACTED_API_KEY]" in result
    assert "AIzaSy" not in result


def test_redact_password_assignments() -> None:
    text = "Credenziali utente: password=SuperSecretPassword123! e pwd: myPass99"
    result = redact_secrets(text)
    assert "password: [REDACTED_PASSWORD]" in result
    assert "pwd: [REDACTED_PASSWORD]" in result
    assert "SuperSecretPassword123!" not in result
    assert "myPass99" not in result


def test_redact_token_assignments() -> None:
    text = "Configurazione: api_key='sk_live_9083204928340293840293' access_token: secret_12345678"
    result = redact_secrets(text)
    assert "api_key: [REDACTED_TOKEN]" in result
    assert "access_token: [REDACTED_TOKEN]" in result
    assert "sk_live_" not in result


def test_preserve_natural_language() -> None:
    """Ensure natural discussion about passwords or tokens is NOT redacted."""
    safe_texts = [
        "Ho dimenticato la mia password della mail aziendale.",
        "Qual è la procedura per resettare la password?",
        "La password scade tra due giorni.",
        "Il mio token fisico OTP per l'accesso VPN non si accende.",
        "Ho problemi ad accedere al portale paghe.",
    ]
    for text in safe_texts:
        assert redact_secrets(text) == text, f"False positive redaction on: '{text}'"


def test_empty_and_none() -> None:
    assert redact_secrets("") == ""
