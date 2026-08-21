from aurora.research.page_quality import (
    PageQualityPolicy,
    classify_page_quality,
    should_ocr,
)


def test_classify_good():
    assert classify_page_quality("x" * 100, True) == "good"


def test_classify_partial():
    assert classify_page_quality("x" * 30, True) == "partial"


def test_classify_ocr_required_empty():
    assert classify_page_quality("", True) == "ocr_required"


def test_classify_failed():
    assert classify_page_quality("", False) == "failed"


def test_classify_custom_policy():
    policy = PageQualityPolicy(min_text_length_good=200, min_text_length_partial=50)
    assert classify_page_quality("x" * 250, True, policy) == "good"
    assert classify_page_quality("x" * 100, True, policy) == "partial"
    assert classify_page_quality("x" * 10, True, policy) == "partial"
    assert classify_page_quality("", True, policy) == "ocr_required"


def test_should_ocr_ocr_required():
    assert should_ocr("ocr_required", 0) is True


def test_should_ocr_good():
    assert should_ocr("good", 100) is False


def test_should_ocr_disabled():
    policy = PageQualityPolicy(enable_ocr=False)
    assert should_ocr("ocr_required", 0, policy) is False


def test_should_ocr_partial_below_threshold():
    policy = PageQualityPolicy(auto_ocr_threshold=100)
    assert should_ocr("partial", 50, policy) is True


def test_should_ocr_partial_above_threshold():
    policy = PageQualityPolicy(auto_ocr_threshold=100)
    assert should_ocr("partial", 150, policy) is False
