from __future__ import annotations

import re

# Compiled regex patterns for redaction
# Pattern for authorization headers: Bearer <token>
BEARER_PATTERN = re.compile(r"(?i)\bBearer\s+([A-Za-z0-9_\-\.]{10,})\b")

# Pattern for Google AI Studio / Cloud keys: AIzaSy...
GOOGLE_API_KEY_PATTERN = re.compile(r"\bAIza[0-9A-Za-z\-_]{35}\b")

# Pattern for generic sk-... API keys (OpenAI / Anthropic format)
SK_KEY_PATTERN = re.compile(r"\b(sk-[a-zA-Z0-9_\-]{20,})\b")

# Pattern for private keys
PRIVATE_KEY_PATTERN = re.compile(
    r"-----BEGIN [A-Z ]+ PRIVATE KEY-----[\s\S]*?-----END [A-Z ]+ PRIVATE KEY-----",
    re.MULTILINE,
)

# Pattern for explicit assignment or key-value format of passwords and tokens:
# e.g., "password: mySecret123", "password = 'secret'", "pwd: xxx", "token=yyy"
# Look for explicit key names followed by ':' or '=' and the secret value.
# Notice we avoid matching plain conversational phrases like "la password è scaduta".
PASSWORD_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(password|passwd|pwd)\s*[:=]\s*([\"\']?)([^\s,;\"\']{3,})\2",
)

TOKEN_ASSIGNMENT_PATTERN = re.compile(
    r"(?i)\b(api_key|apikey|access_token|secret_key|auth_token)\s*[:=]\s*([\"\']?)([^\s,;\"\']{6,})\2",
)


def redact_secrets(text: str) -> str:
    """Sanitize text by redacting common secret and credential patterns.

    Protects credentials without altering regular conversational text (e.g.
    'Ho dimenticato la password' remains untouched).
    """
    if not text:
        return text

    # Redact private key blocks
    redacted = PRIVATE_KEY_PATTERN.sub("[REDACTED_PRIVATE_KEY]", text)

    # Redact Bearer tokens
    redacted = BEARER_PATTERN.sub("Bearer [REDACTED_TOKEN]", redacted)

    # Redact Google API keys
    redacted = GOOGLE_API_KEY_PATTERN.sub("[REDACTED_API_KEY]", redacted)

    # Redact sk- style keys
    redacted = SK_KEY_PATTERN.sub("[REDACTED_API_KEY]", redacted)

    # Redact explicit token assignments: token: xyz -> token: [REDACTED_TOKEN]
    redacted = TOKEN_ASSIGNMENT_PATTERN.sub(r"\1: [REDACTED_TOKEN]", redacted)

    # Redact explicit password assignments: password: xyz -> password: [REDACTED_PASSWORD]
    redacted = PASSWORD_ASSIGNMENT_PATTERN.sub(r"\1: [REDACTED_PASSWORD]", redacted)

    return redacted
