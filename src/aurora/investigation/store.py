"""
LLM-4: Investigation Store — file-based JSON persistence for investigations.

Follows the same pattern as MemoryStore and ResearchStorage.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from aurora.investigation.schemas import (
    InvestigationRecord,
    InvestigationEvent,
    InvestigationResult,
)


class InvestigationStore:
    """
    File-based persistence for investigations.

    Directory structure:
    investigations/
      records/     (one JSON per investigation)
      events/      ({investigation_id}/events.json)
      results/     ({investigation_id}/result.json)
    """

    def __init__(self, base_dir: str | Path) -> None:
        self._base = Path(base_dir)
        self._records = self._base / "records"
        self._events = self._base / "events"
        self._results = self._base / "results"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        self._records.mkdir(parents=True, exist_ok=True)
        self._events.mkdir(parents=True, exist_ok=True)
        self._results.mkdir(parents=True, exist_ok=True)

    def _record_path(self, investigation_id: str) -> Path:
        return self._records / f"{investigation_id}.json"

    def _events_path(self, investigation_id: str) -> Path:
        return self._events / f"{investigation_id}.json"

    def _result_path(self, investigation_id: str) -> Path:
        return self._results / f"{investigation_id}.json"

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    @staticmethod
    def _read_json(path: Path) -> Any:
        if not path.exists():
            return None
        return json.loads(path.read_text(encoding="utf-8"))

    # ── Record Operations ──────────────────────────────────────────────────

    def create(self, record: InvestigationRecord) -> InvestigationRecord:
        """Create a new investigation record. Raises ValueError on duplicate."""
        path = self._record_path(record.investigation_id)
        if path.exists():
            raise ValueError(
                f"Investigation {record.investigation_id} already exists"
            )
        self._write_json(path, record.model_dump())
        return record

    def get(self, investigation_id: str) -> InvestigationRecord | None:
        """Get an investigation by ID."""
        data = self._read_json(self._record_path(investigation_id))
        if data is None:
            return None
        return InvestigationRecord.model_validate(data)

    def update(self, record: InvestigationRecord) -> InvestigationRecord:
        """Update an investigation record."""
        record.updated_at = time.time()
        self._write_json(self._record_path(record.investigation_id), record.model_dump())
        return record

    def list_all(
        self,
        status: str | None = None,
        domain: str | None = None,
        limit: int = 50,
    ) -> list[InvestigationRecord]:
        """List investigation records with optional filters."""
        records: list[InvestigationRecord] = []
        for path in sorted(self._records.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            data = self._read_json(path)
            if data is None:
                continue
            record = InvestigationRecord.model_validate(data)
            if status and record.status.value != status:
                continue
            if domain and record.objective.domain.value != domain:
                continue
            records.append(record)
            if len(records) >= limit:
                break
        return records

    def find_by_idempotency_key(self, key: str) -> InvestigationRecord | None:
        """Find an investigation by idempotency key."""
        for path in self._records.glob("*.json"):
            data = self._read_json(path)
            if data is None:
                continue
            record = InvestigationRecord.model_validate(data)
            if record.idempotency_key == key:
                return record
        return None

    # ── Event Operations ───────────────────────────────────────────────────

    def append_event(self, event: InvestigationEvent) -> None:
        """Append an event to the investigation's event log."""
        events = self._read_json(self._events_path(event.investigation_id)) or []
        events.append(event.model_dump())
        self._write_json(self._events_path(event.investigation_id), events)

    def get_events(self, investigation_id: str) -> list[InvestigationEvent]:
        """Get all events for an investigation."""
        events_data = self._read_json(self._events_path(investigation_id)) or []
        return [InvestigationEvent.model_validate(e) for e in events_data]

    # ── Result Operations ──────────────────────────────────────────────────

    def save_result(self, result: InvestigationResult) -> None:
        """Save an investigation result."""
        self._write_json(self._result_path(result.investigation_id), result.model_dump())

    def get_result(self, investigation_id: str) -> InvestigationResult | None:
        """Get an investigation result."""
        data = self._read_json(self._result_path(investigation_id))
        if data is None:
            return None
        return InvestigationResult.model_validate(data)

    # ── Export ─────────────────────────────────────────────────────────────

    def export_all(self) -> dict[str, Any]:
        """Export all investigation data."""
        records = []
        for path in self._records.glob("*.json"):
            data = self._read_json(path)
            if data:
                records.append(data)
        return {
            "records": records,
            "record_count": len(records),
            "exported_at": time.time(),
        }
