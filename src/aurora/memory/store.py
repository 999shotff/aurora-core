"""
LLM-3: Memory Store — file-based JSON persistence.

Follows the ResearchStorage pattern from src/aurora/research/storage.py.
Provides create, get, update, archive, list, search, history operations.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from aurora.memory.schemas import (
    MemoryRecord,
    MemoryStatus,
    MemoryType,
    MemoryVersion,
    generate_version_id,
)


class MemoryStore:
    """
    File-based memory store.

    Directory structure:
    memory/
    ├── records/
    │   ├── mem-abc123.json
    │   └── mem-def456.json
    ├── versions/
    │   ├── mem-abc123/
    │   │   ├── v1.json
    │   │   └── v2.json
    │   └── mem-def456/
    │       └── v1.json
    ├── conflicts/
    │   └── con-xyz789.json
    └── index/
        └── index.json
    """

    def __init__(self, base_dir: str | Path) -> None:
        self._base = Path(base_dir)
        self._records_dir = self._base / "records"
        self._versions_dir = self._base / "versions"
        self._conflicts_dir = self._base / "conflicts"
        self._index_file = self._base / "index" / "index.json"
        self._ensure_dirs()

    def _ensure_dirs(self) -> None:
        """Create directory structure if it doesn't exist."""
        for d in [self._records_dir, self._versions_dir, self._conflicts_dir, self._base / "index"]:
            d.mkdir(parents=True, exist_ok=True)

    # ── Records ────────────────────────────────────────────────────────────

    def create(self, record: MemoryRecord) -> MemoryRecord:
        """Create a new memory record."""
        path = self._record_path(record.memory_id)
        if path.exists():
            raise ValueError(f"Memory {record.memory_id} already exists")
        self._write_json(path, record.model_dump())
        self._update_index()
        return record

    def get(self, memory_id: str) -> MemoryRecord | None:
        """Retrieve a memory record by ID."""
        path = self._record_path(memory_id)
        if not path.exists():
            return None
        data = self._read_json(path)
        return MemoryRecord.model_validate(data)

    def update(self, record: MemoryRecord) -> MemoryRecord:
        """Update an existing memory record (creates new version)."""
        existing = self.get(record.memory_id)
        if existing is None:
            raise ValueError(f"Memory {record.memory_id} not found")

        # Save version before updating
        self._save_version(existing)

        # Update record
        record.version = existing.version + 1
        record.updated_at = time.time()
        record.previous_version_id = existing.memory_id
        path = self._record_path(record.memory_id)
        self._write_json(path, record.model_dump())
        self._update_index()
        return record

    def archive(self, memory_id: str) -> MemoryRecord | None:
        """Archive a memory record (soft delete)."""
        record = self.get(memory_id)
        if record is None:
            return None
        record.status = MemoryStatus.ARCHIVED
        record.updated_at = time.time()
        path = self._record_path(memory_id)
        self._write_json(path, record.model_dump())
        self._update_index()
        return record

    def delete(self, memory_id: str) -> bool:
        """Hard delete a memory record (use with caution)."""
        path = self._record_path(memory_id)
        if not path.exists():
            return False
        path.unlink()
        # Remove versions
        versions_dir = self._versions_dir / memory_id
        if versions_dir.exists():
            import shutil
            shutil.rmtree(versions_dir)
        self._update_index()
        return True

    def list_all(
        self,
        memory_type: MemoryType | None = None,
        domain: str | None = None,
        status: MemoryStatus | None = None,
        tags: list[str] | None = None,
        limit: int = 50,
    ) -> list[MemoryRecord]:
        """List memory records with optional filters."""
        records = []
        for path in self._records_dir.glob("*.json"):
            try:
                data = self._read_json(path)
                record = MemoryRecord.model_validate(data)
                if memory_type and record.memory_type != memory_type:
                    continue
                if domain and record.domain != domain:
                    continue
                if status and record.status != status:
                    continue
                if tags and not any(t in record.tags for t in tags):
                    continue
                records.append(record)
            except Exception:
                continue
        # Sort by created_at descending
        records.sort(key=lambda r: r.created_at, reverse=True)
        return records[:limit]

    # ── Versions ───────────────────────────────────────────────────────────

    def _save_version(self, record: MemoryRecord) -> MemoryVersion:
        """Save a version snapshot."""
        ver_dir = self._versions_dir / record.memory_id
        ver_dir.mkdir(parents=True, exist_ok=True)

        version = MemoryVersion(
            version_id=generate_version_id(),
            memory_id=record.memory_id,
            version=record.version,
            snapshot=record,
            created_at=time.time(),
            change_reason=record.change_reason,
        )
        path = ver_dir / f"v{record.version}.json"
        self._write_json(path, version.model_dump())
        return version

    def get_versions(self, memory_id: str) -> list[MemoryVersion]:
        """Get all versions of a memory record."""
        ver_dir = self._versions_dir / memory_id
        if not ver_dir.exists():
            return []
        versions = []
        for path in sorted(ver_dir.glob("v*.json")):
            try:
                data = self._read_json(path)
                versions.append(MemoryVersion.model_validate(data))
            except Exception:
                continue
        return versions

    # ── Conflicts ──────────────────────────────────────────────────────────

    def save_conflict(self, conflict: dict[str, Any]) -> None:
        """Save a conflict record."""
        conflict_id = conflict.get("conflict_id", "unknown")
        path = self._conflicts_dir / f"{conflict_id}.json"
        self._write_json(path, conflict)

    def list_conflicts(self) -> list[dict[str, Any]]:
        """List all conflict records."""
        conflicts = []
        for path in self._conflicts_dir.glob("*.json"):
            try:
                conflicts.append(self._read_json(path))
            except Exception:
                continue
        return conflicts

    # ── Search ─────────────────────────────────────────────────────────────

    def search(
        self,
        query: str = "",
        entity_id: str | None = None,
        domain: str | None = None,
        memory_type: MemoryType | None = None,
        status: MemoryStatus | None = None,
        evidence_ref: str | None = None,
        start_time: float | None = None,
        end_time: float | None = None,
        limit: int = 50,
    ) -> list[MemoryRecord]:
        """Search memory records with multiple criteria."""
        results = []
        query_lower = query.lower() if query else ""

        for path in self._records_dir.glob("*.json"):
            try:
                data = self._read_json(path)
                record = MemoryRecord.model_validate(data)

                # Text match
                if query_lower and query_lower not in record.title.lower() and query_lower not in record.content.lower():
                    continue

                # Entity match
                if entity_id and entity_id not in record.entity_refs:
                    continue

                # Domain match
                if domain and record.domain != domain:
                    continue

                # Type match
                if memory_type and record.memory_type != memory_type:
                    continue

                # Status match
                if status and record.status != status:
                    continue

                # Evidence match
                if evidence_ref and evidence_ref not in record.evidence_refs:
                    continue

                # Time range
                if start_time and record.created_at < start_time:
                    continue
                if end_time and record.created_at > end_time:
                    continue

                results.append(record)
            except Exception:
                continue

        results.sort(key=lambda r: r.created_at, reverse=True)
        return results[:limit]

    # ── Index ──────────────────────────────────────────────────────────────

    def _update_index(self) -> None:
        """Update the lightweight index."""
        index = {}
        for path in self._records_dir.glob("*.json"):
            try:
                data = self._read_json(path)
                record = MemoryRecord.model_validate(data)
                index[record.memory_id] = {
                    "type": record.memory_type.value,
                    "domain": record.domain,
                    "status": record.status.value,
                    "title": record.title,
                    "created_at": record.created_at,
                    "tags": record.tags,
                    "entity_refs": record.entity_refs,
                    "evidence_refs": record.evidence_refs,
                }
            except Exception:
                continue
        self._write_json(self._index_file, index)

    def load_index(self) -> dict[str, Any]:
        """Load the lightweight index."""
        if not self._index_file.exists():
            return {}
        return self._read_json(self._index_file)

    # ── Export ─────────────────────────────────────────────────────────────

    def export_all(self) -> dict[str, Any]:
        """Export all memory data."""
        records = [self.get(p.stem) for p in self._records_dir.glob("*.json")]
        records = [r for r in records if r is not None]

        all_versions = []
        for record in records:
            all_versions.extend(self.get_versions(record.memory_id))

        return {
            "records": [r.model_dump() for r in records],
            "versions": [v.model_dump() for v in all_versions],
            "conflicts": self.list_conflicts(),
            "exported_at": time.time(),
        }

    # ── Helpers ────────────────────────────────────────────────────────────

    def _record_path(self, memory_id: str) -> Path:
        return self._records_dir / f"{memory_id}.json"

    @staticmethod
    def _write_json(path: Path, data: Any) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)

    @staticmethod
    def _read_json(path: Path) -> Any:
        with open(path) as f:
            return json.load(f)

    def count(self, memory_type: MemoryType | None = None) -> int:
        """Count memory records."""
        if memory_type:
            return len(self.list_all(memory_type=memory_type, limit=10000))
        return len(list(self._records_dir.glob("*.json")))
