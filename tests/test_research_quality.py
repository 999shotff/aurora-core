from aurora.research.quality import assess_extraction_quality


def test_assess_all_good():
    report = assess_extraction_quality(["good", "good", "good"], "doc_001")
    assert report.overall_quality == "good"
    assert report.can_extract_claims is True
    assert report.good_pages == 3


def test_assess_majority_failed():
    report = assess_extraction_quality(["failed", "failed", "failed", "good"], "doc_001")
    assert report.overall_quality == "failed"
    assert report.can_extract_claims is False


def test_assess_ocr_required():
    report = assess_extraction_quality(
        ["ocr_required", "ocr_required", "ocr_required", "good"],
        "doc_001",
    )
    assert report.overall_quality == "ocr_required"
    assert report.can_extract_claims is False


def test_assess_manual_review():
    report = assess_extraction_quality(
        ["manual_review", "manual_review", "manual_review", "good"],
        "doc_001",
    )
    assert report.overall_quality == "manual_review"
    assert report.can_extract_claims is False


def test_assess_partial():
    report = assess_extraction_quality(["good", "partial", "good"], "doc_001")
    assert report.overall_quality == "partial"
    assert report.can_extract_claims is True


def test_assess_empty():
    report = assess_extraction_quality([], "doc_001")
    assert report.total_pages == 0


def test_quality_report_dict():
    report = assess_extraction_quality(["good", "failed"], "doc_001")
    d = report.to_dict()
    assert d["document_id"] == "doc_001"
    assert d["good_pages"] == 1
    assert d["failed_pages"] == 1
