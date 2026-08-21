from unittest.mock import patch

from aurora.research.ocr import OCRProvider, TesseractProvider, get_ocr_provider


def test_tesseract_provider_is_available():
    provider = TesseractProvider()
    assert isinstance(provider.is_available(), bool)


def test_tesseract_engine_name():
    provider = TesseractProvider()
    assert provider.engine_name() == "tesseract"


def test_get_ocr_provider_default():
    provider = get_ocr_provider()
    assert isinstance(provider, OCRProvider)


def test_get_ocr_provider_tesseract():
    provider = get_ocr_provider("tesseract")
    assert isinstance(provider, TesseractProvider)


def test_get_ocr_provider_unknown():
    try:
        get_ocr_provider("nonexistent")
        assert False, "should raise"
    except ValueError:
        pass


def test_ocr_provider_interface():
    provider = TesseractProvider()
    assert hasattr(provider, "is_available")
    assert hasattr(provider, "ocr_image")
    assert hasattr(provider, "engine_name")
    assert hasattr(provider, "engine_version")


def test_tesseract_unavailable_graceful():
    provider = TesseractProvider()
    with patch("aurora.research.ocr.TesseractProvider.is_available", return_value=False):
        assert provider.is_available() is False
