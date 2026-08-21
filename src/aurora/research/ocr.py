from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

OCRStatus = Literal["success", "failed", "unavailable", "skipped"]
ExtractionQuality = Literal["good", "partial", "ocr_required", "failed"]


class OCRResult(BaseModel):
    model_config = ConfigDict(extra="forbid")
    document_id: str
    page_number: int
    original_status: ExtractionQuality
    ocr_text: str
    ocr_status: OCRStatus
    ocr_engine: str = "unknown"
    ocr_version: str = ""
    confidence: float = Field(ge=0.0, le=100.0, default=0.0)
    char_count: int = Field(ge=0, default=0)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error: str | None = None
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


class OCRProvider(ABC):
    @abstractmethod
    def is_available(self) -> bool:
        raise NotImplementedError

    @abstractmethod
    def ocr_image(self, image_path: Path, language: str = "eng") -> tuple[str, float]:
        raise NotImplementedError

    @abstractmethod
    def engine_name(self) -> str:
        raise NotImplementedError

    @abstractmethod
    def engine_version(self) -> str:
        raise NotImplementedError


class TesseractProvider(OCRProvider):
    def __init__(self) -> None:
        self._available: bool | None = None

    def is_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import pytesseract

            pytesseract.get_tesseract_version()
            self._available = True
        except (ImportError, OSError):
            self._available = False
        return self._available

    def ocr_image(self, image_path: Path, language: str = "eng") -> tuple[str, float]:
        if not self.is_available():
            raise RuntimeError("Tesseract OCR is not available")
        import pytesseract
        from PIL import Image

        img = Image.open(str(image_path))
        data = pytesseract.image_to_data(img, lang=language, output_type=pytesseract.Output.DICT)
        text = pytesseract.image_to_string(img, lang=language)
        confidences = [int(c) for c in data["conf"] if int(c) > 0]
        avg_confidence = sum(confidences) / len(confidences) if confidences else 0.0
        return text.strip(), avg_confidence

    def engine_name(self) -> str:
        return "tesseract"

    def engine_version(self) -> str:
        if not self.is_available():
            return ""
        try:
            import pytesseract

            return str(pytesseract.get_tesseract_version())
        except (ImportError, OSError):
            return ""


def get_ocr_provider(name: str = "tesseract") -> OCRProvider:
    if name == "tesseract":
        return TesseractProvider()
    raise ValueError(f"unknown OCR provider: {name}")
