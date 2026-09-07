"""Compute Fabric — audit log.

Tracks compute events for observability. No secrets logged.

NO_DEPLOYMENT_SIGNAL.
"""

from __future__ import annotations

import logging

from aurora.compute.schemas import AuditAction, AuditRecord

logger = logging.getLogger(__name__)


class ComputeAuditLog:
    """In-memory audit log for compute events."""

    def __init__(self, max_entries: int = 500) -> None:
        self._entries: list[AuditRecord] = []
        self._max = max_entries

    def record(
        self,
        action: AuditAction,
        provider_id: str | None = None,
        worker_id: str | None = None,
        job_id: str | None = None,
        detail: str = "",
        success: bool = True,
    ) -> AuditRecord:
        entry = AuditRecord(
            action=action,
            provider_id=provider_id,
            worker_id=worker_id,
            job_id=job_id,
            detail=detail,
            success=success,
        )
        self._entries.append(entry)
        if len(self._entries) > self._max:
            self._entries = self._entries[-self._max // 2:]
        logger.info("AUDIT: %s provider=%s worker=%s job=%s ok=%s",
                     action.value, provider_id, worker_id, job_id, success)
        return entry

    def get_entries(self, limit: int = 50) -> list[AuditRecord]:
        return self._entries[-limit:]

    def clear(self) -> None:
        self._entries.clear()
