from __future__ import annotations

from dataclasses import dataclass, field

from pydantic import BaseModel, ConfigDict, Field


class MultipleTestingResult(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    family_id: str = ""
    total_tests: int = 0
    significant_before_correction: int = 0
    significant_after_bonferroni: int = 0
    significant_after_bh_fdr: int = 0
    bonferroni_threshold: float = 0.0
    bh_fdr_threshold: float = 0.0
    raw_pvalues: list[float] = Field(default_factory=list)
    adjusted_pvalues: list[float] = Field(default_factory=list)


@dataclass(frozen=True)
class MultipleTestingRecorder:
    records: dict[str, list[float]] = field(default_factory=dict)

    def record_pvalue(self, family_id: str, experiment_id: str, pvalue: float) -> None:
        if family_id not in self.records:
            self.records[family_id] = []
        self.records[family_id].append(pvalue)

    def get_pvalues(self, family_id: str) -> list[float]:
        return self.records.get(family_id, [])

    def family_count(self) -> int:
        return len(self.records)

    def total_tests(self, family_id: str | None = None) -> int:
        if family_id:
            return len(self.records.get(family_id, []))
        return sum(len(v) for v in self.records.values())

    def bonferroni_correction(
        self, family_id: str, alpha: float = 0.05
    ) -> MultipleTestingResult:
        pvalues = self.get_pvalues(family_id)
        n = len(pvalues)
        if n == 0:
            return MultipleTestingResult(family_id=family_id, total_tests=0)
        threshold = alpha / n
        sig_before = sum(1 for p in pvalues if p < alpha)
        sig_after = sum(1 for p in pvalues if p < threshold)
        return MultipleTestingResult(
            family_id=family_id,
            total_tests=n,
            significant_before_correction=sig_before,
            significant_after_bonferroni=sig_after,
            bonferroni_threshold=threshold,
            raw_pvalues=pvalues,
        )

    def benjamini_hochberg_fdr(
        self, family_id: str, alpha: float = 0.05
    ) -> MultipleTestingResult:
        pvalues = self.get_pvalues(family_id)
        n = len(pvalues)
        if n == 0:
            return MultipleTestingResult(family_id=family_id, total_tests=0)
        sorted_pvals = sorted(enumerate(pvalues), key=lambda x: x[1])
        adjusted = [0.0] * n
        for rank, (orig_idx, pval) in enumerate(sorted_pvals, 1):
            adjusted[orig_idx] = pval * n / rank
        for i in range(n - 2, -1, -1):
            idx = sorted_pvals[i + 1][0]
            curr = sorted_pvals[i][0]
            adjusted[curr] = min(adjusted[curr], adjusted[idx])
        adjusted = [min(p, 1.0) for p in adjusted]
        sig_before = sum(1 for p in pvalues if p < alpha)
        sig_after = sum(1 for p in adjusted if p < alpha)
        bh_threshold = alpha * n / max(1, sig_after) if sig_after > 0 else 0.0
        return MultipleTestingResult(
            family_id=family_id,
            total_tests=n,
            significant_before_correction=sig_before,
            significant_after_bh_fdr=sig_after,
            bh_fdr_threshold=bh_threshold,
            raw_pvalues=pvalues,
            adjusted_pvalues=adjusted,
        )

    def reset(self, family_id: str | None = None) -> None:
        if family_id:
            self.records.pop(family_id, None)
        else:
            self.records.clear()
