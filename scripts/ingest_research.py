"""Phase 3 Research Ingestion — Run against actual PDFs."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

from aurora.research.extractors import extract_pdf
from aurora.research.models import (
    ResearchDocument,
    ResearchPage,
    ResearchSource,
)
from aurora.research.storage import ResearchStorage


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def ingest_all_pdfs(pdfs_dir: Path, output_dir: Path) -> dict:
    pdf_files = sorted(pdfs_dir.glob("*.pdf"))
    print(f"Discovered {len(pdf_files)} PDF files")

    storage = ResearchStorage(output_dir)
    storage.ensure_dirs()

    documents: list[ResearchDocument] = []
    sha_to_docs: dict[str, list[str]] = {}
    total_pages = 0
    good_pages = 0
    partial_pages = 0
    failed_pages = 0
    ocr_required_pages = 0
    total_text_size = 0
    failures: list[dict] = []

    for pdf_path in pdf_files:
        print(f"  Processing: {pdf_path.name}")
        sha = sha256_file(pdf_path)
        doc_id = sha[:16]

        # Track duplicates
        sha_to_docs.setdefault(sha, []).append(doc_id)

        # Extract
        structure, errors = extract_pdf(pdf_path)
        page_count = len(structure.pages)

        # Classify pages
        page_qualities: list[str] = []
        doc_good = 0
        doc_partial = 0
        doc_failed = 0
        doc_ocr = 0
        doc_text_size = 0

        pages: list[ResearchPage] = []
        for p in structure.pages:
            if not p.extraction_ok or not p.text.strip():
                if p.error and ("ocr" in p.error.lower() or "scanned" in p.error.lower()):
                    quality = "ocr_required"
                    doc_ocr += 1
                elif not p.extraction_ok:
                    quality = "failed"
                    doc_failed += 1
                else:
                    quality = "partial"
                    doc_partial += 1
            elif len(p.text.strip()) < 50:
                quality = "partial"
                doc_partial += 1
            else:
                quality = "good"
                doc_good += 1

            page_qualities.append(quality)
            doc_text_size += len(p.text)

            page_obj = ResearchPage(
                page_id=f"{doc_id}_p{p.page_number}",
                document_id=doc_id,
                page_number=p.page_number,
                text=p.text,
                char_count=p.char_count,
                extraction_quality=quality,  # type: ignore[arg-type]
                error=p.error,
            )
            pages.append(page_obj)

        total_pages += page_count
        good_pages += doc_good
        partial_pages += doc_partial
        failed_pages += doc_failed
        ocr_required_pages += doc_ocr
        total_text_size += doc_text_size

        # Determine overall quality
        if doc_failed > page_count * 0.5:
            overall_quality = "failed"
        elif doc_ocr > page_count * 0.3:
            overall_quality = "ocr_required"
        elif doc_good == page_count and page_count > 0:
            overall_quality = "good"
        else:
            overall_quality = "partial"

        # Record failures
        if errors:
            for e in errors:
                failures.append({
                    "document": pdf_path.name,
                    "document_id": doc_id,
                    "error_type": e.error_type,
                    "message": e.message,
                    "page": e.page_number,
                })

        source = ResearchSource(
            source_path=str(pdf_path),
            sha256=sha,
            source_type="pdf",
            size_bytes=pdf_path.stat().st_size,
            filename=pdf_path.name,
        )

        doc = ResearchDocument(
            document_id=doc_id,
            title=pdf_path.stem,
            source=source,
            page_count=page_count,
            extraction_quality=overall_quality,  # type: ignore[arg-type]
            extraction_version="1.0.0",
            extraction_timestamp=datetime.now(timezone.utc),
            page_ids=[p.page_id for p in pages],
        )

        # Save document
        storage.save_document(doc)

        # Save pages
        for page in pages:
            page_path = output_dir / "pages" / f"{page.page_id}.json"
            page_path.parent.mkdir(parents=True, exist_ok=True)
            page_path.write_text(json.dumps(page.model_dump(mode="json"), indent=2), encoding="utf-8")

        documents.append(doc)
        print(f"    -> {page_count} pages, quality={overall_quality}, text={doc_text_size} chars")

    # Find duplicates
    duplicates = {sha: ids for sha, ids in sha_to_docs.items() if len(ids) > 1}

    # Save index
    index = {
        "version": "1.0.0",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "total_documents": len(documents),
        "total_pages": total_pages,
        "good_pages": good_pages,
        "partial_pages": partial_pages,
        "failed_pages": failed_pages,
        "ocr_required_pages": ocr_required_pages,
        "total_text_size_bytes": total_text_size,
        "duplicate_sha256_count": len(duplicates),
        "documents": [
            {
                "document_id": d.document_id,
                "title": d.title,
                "sha256": d.source.sha256,
                "page_count": d.page_count,
                "extraction_quality": d.extraction_quality,
                "source_filename": d.source.filename,
            }
            for d in documents
        ],
    }
    storage.save_index(index)

    # Save failures
    if failures:
        fail_path = output_dir / "index" / "extraction_failures.json"
        fail_path.parent.mkdir(parents=True, exist_ok=True)
        fail_path.write_text(json.dumps(failures, indent=2), encoding="utf-8")

    return {
        "total_pdfs": len(pdf_files),
        "total_pages": total_pages,
        "good_pages": good_pages,
        "partial_pages": partial_pages,
        "failed_pages": failed_pages,
        "ocr_required_pages": ocr_required_pages,
        "total_text_size": total_text_size,
        "duplicates": duplicates,
        "failures": failures,
        "documents": documents,
    }


if __name__ == "__main__":
    pdfs_dir = Path("/sdcard/Download/aurora-core/research/pdfs")
    output_dir = Path("/sdcard/Download/aurora-core/research/extracted")

    results = ingest_all_pdfs(pdfs_dir, output_dir)

    print("\n" + "=" * 60)
    print("PHASE 3 RESEARCH INGESTION REPORT")
    print("=" * 60)
    print(f"Total PDFs discovered:     {results['total_pdfs']}")
    print(f"Total pages:               {results['total_pages']}")
    print(f"Successful (good) pages:   {results['good_pages']}")
    print(f"Partial pages:             {results['partial_pages']}")
    print(f"Failed pages:              {results['failed_pages']}")
    print(f"OCR-required pages:        {results['ocr_required_pages']}")
    print(f"Total extracted text size: {results['total_text_size']:,} characters")
    print(f"Duplicate documents:       {len(results['duplicates'])}")

    if results["duplicates"]:
        print("\n  Duplicate SHA-256 hashes:")
        for sha, ids in results["duplicates"].items():
            print(f"    {sha[:16]}... -> {len(ids)} copies")

    if results["failures"]:
        print(f"\n  Extraction failures: {len(results['failures'])}")
        for f in results["failures"][:20]:
            print(f"    {f['document']}: {f['error_type']} (page {f['page']})")
        if len(results["failures"]) > 20:
            print(f"    ... and {len(results['failures']) - 20} more")

    print("\n  Per-document summary:")
    for doc in results["documents"]:
        print(f"    {doc.source.filename}: {doc.page_count} pages, quality={doc.extraction_quality}")
