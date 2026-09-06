"""AURORA Reasoning Core — Security Layer.

Protects against prompt injection, malicious research text,
secret leakage, and instruction injection inside documents.
"""

from __future__ import annotations

import re

from aurora.ai.errors import SecurityViolation

_INJECTION_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
    r"you\s+are\s+now\s+(a|an)\s+",
    r"disregard\s+(all\s+)?(previous|prior|above)",
    r"forget\s+(all\s+)?(previous|prior|above)",
    r"override\s+(all\s+)?(previous|prior|above)",
    r"system\s*:\s*",
    r"<\|system\|>",
    r"<\|user\|>",
    r"<\|assistant\|>",
    r"\[INST\]",
    r"<<SYS>>",
    r"###\s*(system|user|assistant)\s*:",
    r"act\s+as\s+if\s+you",
    r"pretend\s+you\s+are",
    r"roleplay\s+as",
    r"jailbreak",
    r"DAN\s+mode",
]

_SECRET_PATTERNS = [
    (r"(?i)(api[_\s]?key|apikey)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-]{20,})", "API key"),
    (r"(?i)(secret|password|passwd|pwd)\s*[:=]\s*['\"]?([^\s'\"]{8,})", "Secret"),
    (r"(?i)(bearer)\s+([a-zA-Z0-9_\-\.]{20,})", "Bearer token"),
    (r"sk-[a-zA-Z0-9]{20,}", "OpenAI key"),
    (r"(?i)BEGIN\s+(RSA\s+)?PRIVATE\s+KEY", "Private key"),
]

_INSTRUCTION_DELIMITERS = [
    "=== SYSTEM INSTRUCTION",
    "--- BEGIN INSTRUCTION",
    "### NEW INSTRUCTION",
    "[SYSTEM]",
    "IMPORTANT: You must",
    "Your new instructions are",
]

_INJECTION_RE = [re.compile(p, re.IGNORECASE) for p in _INJECTION_PATTERNS]
_SECRET_RE = [(re.compile(p), desc) for p, desc in _SECRET_PATTERNS]


def sanitize_user_input(text: str) -> str:
    """Check user input for prompt injection patterns.

    Raises SecurityViolation if injection detected.
    Returns cleaned text.
    """
    for pattern in _INJECTION_RE:
        if pattern.search(text):
            raise SecurityViolation("Prompt injection detected in user input")

    return text.strip()


def sanitize_evidence(text: str, field_name: str = "claim") -> str:
    """Check evidence text for instruction injection.

    Research documents are DATA, not system instructions.
    Raises SecurityViolation if injection patterns found.
    """
    for delimiter in _INSTRUCTION_DELIMITERS:
        if delimiter.lower() in text.lower():
            raise SecurityViolation(
                f"Instruction injection detected in evidence field '{field_name}'"
            )

    for pattern, desc in _SECRET_RE:
        if pattern.search(text):
            raise SecurityViolation(f"Secret detected in evidence field '{field_name}': {desc}")

    return text


def redact_secrets(text: str) -> str:
    """Redact potential secrets from text before sending to LLM."""
    redacted = text
    for pattern, desc in _SECRET_RE:
        redacted = pattern.sub(f"[REDACTED {desc}]", redacted)
    return redacted


def validate_no_secrets(*texts: str) -> None:
    """Validate that no secrets are present in the combined text."""
    combined = " ".join(texts)
    for pattern, desc in _SECRET_RE:
        if pattern.search(combined):
            raise SecurityViolation(f"Secret found in output: {desc}")
