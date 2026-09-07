"""Runtime Security — validate inference inputs, enforce safety boundaries.

No arbitrary code execution. No prompt injection. No secret leakage.
"""

from __future__ import annotations

from aurora.ai.security import redact_secrets, validate_no_secrets


def validate_inference_prompt(prompt: str) -> str:
    """Validate and sanitize inference prompt. Raises ValueError on violation."""
    if not prompt or not prompt.strip():
        raise ValueError("Prompt must not be empty")

    if len(prompt) > 8192:
        raise ValueError(f"Prompt exceeds maximum length: {len(prompt)} > 8192")

    forbidden_patterns = [
        "import os",
        "import subprocess",
        "os.system(",
        "exec(",
        "eval(",
        "__import__",
        "compile(",
        "shell=True",
        "rm -rf",
        "drop table",
        "delete from",
        "curl http",
        "wget http",
        "requests.get(",
        "requests.post(",
        "urllib.request",
        "http.client",
        "subprocess.run",
        "subprocess.call",
        "subprocess.Popen",
    ]

    lower = prompt.lower()
    for pattern in forbidden_patterns:
        if pattern.lower() in lower:
            raise ValueError(f"Prompt contains forbidden pattern: {pattern}")

    validate_no_secrets(prompt)

    return redact_secrets(prompt)


def validate_model_id(model_id: str) -> str:
    """Validate model ID format."""
    if not model_id or not model_id.strip():
        raise ValueError("Model ID must not be empty")

    import re
    if not re.match(r"^[a-zA-Z0-9._-]+$", model_id):
        raise ValueError(
            f"Model ID contains invalid characters: {model_id}"
        )

    if len(model_id) > 128:
        raise ValueError(f"Model ID too long: {len(model_id)} > 128")

    return model_id


def validate_worker_id(worker_id: str) -> str:
    """Validate worker ID format."""
    if not worker_id or not worker_id.strip():
        raise ValueError("Worker ID must not be empty")

    if len(worker_id) > 128:
        raise ValueError(f"Worker ID too long: {len(worker_id)} > 128")

    return worker_id
