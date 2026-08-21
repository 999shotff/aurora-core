from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from aurora.schemas.market_state import MarketState, MarketStateSequence


class FeatureVector(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())
    version: str = "0.1.0"
    extractor_id: str
    asset: str
    timeframe: str
    timestamp: datetime
    numerical: dict[str, float] = Field(default_factory=dict)
    categorical: dict[str, str] = Field(default_factory=dict)
    metadata: dict[str, Any] = Field(default_factory=dict)


class FeatureExtractor(ABC):
    extractor_id: str

    @abstractmethod
    def extract(self, sequence: MarketStateSequence) -> FeatureVector:
        raise NotImplementedError

    def extract_single(self, state: MarketState) -> FeatureVector:
        seq = MarketStateSequence(
            asset=state.asset,
            timeframe=state.timeframe,
            snapshots=[state],
        )
        return self.extract(seq)

    def metadata(self) -> dict[str, Any]:
        return {"extractor_id": self.extractor_id}


@dataclass(frozen=True)
class FeatureRegistry:
    _extractors: dict[str, FeatureExtractor] = field(default_factory=dict)

    def register(self, extractor: FeatureExtractor) -> None:
        if extractor.extractor_id in self._extractors:
            raise ValueError(
                f"Extractor '{extractor.extractor_id}' already registered"
            )
        self._extractors[extractor.extractor_id] = extractor

    def get(self, extractor_id: str) -> FeatureExtractor:
        if extractor_id not in self._extractors:
            raise KeyError(f"Extractor '{extractor_id}' not found")
        return self._extractors[extractor_id]

    def extract_all(self, sequence: MarketStateSequence) -> dict[str, FeatureVector]:
        results = {}
        for eid, extractor in self._extractors.items():
            results[eid] = extractor.extract(sequence)
        return results

    def list_extractors(self) -> list[str]:
        return sorted(self._extractors.keys())
