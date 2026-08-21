"""Phase 3.5 — OCR the three zero-text documents."""
from __future__ import annotations

import json
from pathlib import Path

from aurora.research.ocr import get_ocr_provider
from aurora.research.page_quality import ocr_page

ZERO_TEXT_DOCS = [
    "The Law of Vibration- The Revelation of William D. Gann -- Tony Plummer -- ( WeLib.org ).pdf",
    "fibonacci-lucas (1).pdf",
    "varahmihirHorasastram (1).pdf",
]


def run_ocr_on_zero_text():
    pdfs_dir = Path("/sdcard/Download/aurora-core/research/pdfs")
    extracted_dir = Path("/sdcard/Download/aurora-core/research/extracted")
    pages_dir = extracted_dir / "pages"

    provider = get_ocr_provider()
    if not provider.is_available():
        print("OCR unavailable — cannot process zero-text documents")
        print("Required: tesseract-ocr, pytesseract, Pillow, pdf2image")
        return

    print(f"OCR engine: {provider.engine_name()} {provider.engine_version()}")

    total_attempted = 0
    total_success = 0
    total_failed = 0
    confidences: list[float] = []

    for pdf_name in ZERO_TEXT_DOCS:
        pdf_path = pdfs_dir / pdf_name
        if not pdf_path.exists():
            print(f"  SKIP: {pdf_name} not found")
            continue

        print(f"\n  Processing: {pdf_name}")

        # Find document_id from index
        doc_json = None
        for f in (extracted_dir / "documents").glob("*.json"):
            data = json.loads(f.read_text())
            if data.get("source", {}).get("filename") == pdf_name:
                doc_json = data
                break

        if not doc_json:
            print(f"    ERROR: no document record found for {pdf_name}")
            continue

        doc_id = doc_json["document_id"]
        page_count = doc_json["page_count"]
        print(f"    document_id={doc_id}, pages={page_count}")

        doc_success = 0
        doc_failed = 0

        for page_num in range(1, page_count + 1):
            total_attempted += 1

            # Load original page
            page_id = f"{doc_id}_p{page_num}"
            page_path = pages_dir / f"{page_id}.json"

            original_text = ""
            original_quality = "ocr_required"
            if page_path.exists():
                page_data = json.loads(page_path.read_text())
                original_text = page_data.get("text", "")
                original_quality = page_data.get("extraction_quality", "ocr_required")

            result = ocr_page(
                pdf_path=pdf_path,
                page_number=page_num,
                document_id=doc_id,
                original_text=original_text,
                original_quality=original_quality,
                provider=provider,
                output_dir=extracted_dir,
            )

            if result.ocr_result and result.ocr_result.ocr_status == "success":
                total_success += 1
                doc_success += 1
                confidences.append(result.ocr_result.confidence)

                # Update the original page with OCR text alongside (DO NOT overwrite)
                if page_path.exists():
                    page_data = json.loads(page_path.read_text())
                    page_data["ocr_available"] = True
                    page_data["ocr_text_length"] = result.ocr_result.char_count
                    page_data["ocr_confidence"] = result.ocr_result.confidence
                    page_data["ocr_engine"] = result.ocr_result.ocr_engine
                    page_path.write_text(json.dumps(page_data, indent=2), encoding="utf-8")
            else:
                total_failed += 1
                doc_failed += 1
                action = result.action_taken
                if page_num <= 3 or doc_failed <= 3:
                    print(f"    page {page_num}: {action}")

        print(f"    -> {doc_success}/{page_count} pages OCR'd, {doc_failed} failed")

    avg_conf = sum(confidences) / len(confidences) if confidences else 0.0

    print(f"\n{'=' * 60}")
    print("OCR RESULTS")
    print(f"{'=' * 60}")
    print(f"Documents processed:   {len(ZERO_TEXT_DOCS)}")
    print(f"Pages attempted:       {total_attempted}")
    print(f"Pages successfully OCR'd: {total_success}")
    print(f"Pages failed:          {total_failed}")
    if confidences:
        print(f"Average confidence:    {avg_conf:.1f}%")
        print(f"Min confidence:        {min(confidences):.1f}%")
        print(f"Max confidence:        {max(confidences):.1f}%")
    print(f"Remaining OCR_REQUIRED: {total_failed}")


if __name__ == "__main__":
    run_ocr_on_zero_text()
