from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import ClassVar, Literal

from aurora.research.extractors import (
    extract_json,
    extract_markdown,
    extract_pdf,
    extract_txt,
)
from aurora.research.schema import (
    ResearchDocumentRecord,
    ResearchIndex,
)


class ResearchIngestor:
    EXTRACTORS: ClassVar[dict[str, Callable]] = {
        ".pdf": extract_pdf,
        ".txt": extract_txt,
        ".md": extract_markdown,
        ".json": extract_json,
    }

    def __init__(self, root: str | Path, output_dir: str | Path | None = None):
        self.root = Path(root)
        self.output_dir = Path(output_dir) if output_dir else self.root.parent / "extracted"

    @staticmethod
    def _sha256(path: Path) -> str:
        digest = hashlib.sha256()
        with path.open("rb") as fh:
            for chunk in iter(lambda: fh.read(1024 * 1024), b""):
                digest.update(chunk)
        return digest.hexdigest()

    def ingest_all(self) -> ResearchIndex:
        self.output_dir.mkdir(parents=True, exist_ok=True)
        documents: list[ResearchDocumentRecord] = []
        for path in sorted(self.root.rglob("*")):
            if not path.is_file():
                continue
            suffix = path.suffix.lower()
            if suffix not in self.EXTRACTORS:
                continue
            record = self.ingest_file(path)
            documents.append(record)
        return ResearchIndex(
            created_at=datetime.now(timezone.utc),
            document_count=len(documents),
            documents=documents,
        )

    def ingest_file(self, path: Path) -> ResearchDocumentRecord:
        suffix = path.suffix.lower()
        sha = self._sha256(path)
        document_id = sha[:16]
        text_location = str(self.output_dir / f"{document_id}.txt")

        extractor = self.EXTRACTORS.get(suffix)
        if extractor is None:
            return ResearchDocumentRecord(
                document_id=document_id,
                filename=path.name,
                source_path=str(path),
                suffix=suffix,
                size_bytes=path.stat().st_size,
                sha256=sha,
                page_count=0,
                extraction_status="failed",
                extraction_timestamp=datetime.now(timezone.utc),
                source_type=suffix.lstrip("."),  # type: ignore[arg-type]
                text_location="",
            )

        now = datetime.now(timezone.utc)
        structure, errors = extractor(path)
        page_count = len(structure.pages)
        ok_pages = sum(1 for p in structure.pages if p.extraction_ok)

        if ok_pages == page_count and page_count > 0:
            status: Literal["success", "partial", "failed"] = "success"
        elif ok_pages > 0:
            status = "partial"
        else:
            status = "failed"

        full_text = "\n\n".join(
            p.text for p in structure.pages if p.extraction_ok and p.text
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        out_path = Path(text_location)
        out_path.write_text(full_text, encoding="utf-8")

        return ResearchDocumentRecord(
            document_id=document_id,
            filename=path.name,
            source_path=str(path),
            suffix=suffix,
            size_bytes=path.stat().st_size,
            sha256=sha,
            page_count=page_count,
            extraction_status=status,
            extraction_timestamp=now,
            source_type=suffix.lstrip("."),  # type: ignore[arg-type]
            text_location=text_location,
            structure=structure,
            errors=errors,
        )

    def write_index(self, index: ResearchIndex, output: str | Path) -> Path:
        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        payload = index.model_dump(mode="json")
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        return destination

    def load_index(self, path: str | Path) -> ResearchIndex:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return ResearchIndex.model_validate(data)
