# AURORA CORE — Agent Rules

Read README.md before modifying the project.

## Mandatory workflow
Inspect -> Plan -> Implement -> Test -> Verify -> Document.

## Rules
- Do not rewrite the repository from scratch.
- Do not create duplicate abstractions.
- Never fabricate market data, news, model results, or backtest results.
- Never use future information in a feature or label.
- Never claim profitability from in-sample performance.
- Mark experimental research as EXPERIMENTAL.
- Keep deterministic calculations outside the language model.
- Use UTC internally.
- Every model experiment must have a reproducible configuration.
- A challenger model cannot replace the champion without passing the evaluation gate.
- Do not add cloud infrastructure until the local core is testable.
- Do not make OpenMythos the production reasoning model; it is only an architecture experiment.
- Do not make Kimi-K3 the deployment model; its architecture may be studied.
- Keep dependencies minimal.
- Run tests after meaningful changes.

## OCR Rules (Phase 3.5)
- Never overwrite original pypdf-extracted text; OCR text stored alongside in separate fields.
- OCR results stored in `research/extracted/ocr/`, originals in `research/extracted/pages/`.
- Page quality classified as GOOD/PARTIAL/OCR_REQUIRED/FAILED by text length thresholds.
- `PageQualityPolicy` controls OCR thresholds; defaults are conservative.
- No research PDFs are auto-claimed as true; OCR enables extraction, not validation.
- All hypotheses remain `untested` until separate evaluation pipeline.

## Claim Extraction Rules (Phase 4)
- All extracted claims start as UNREVIEWED; never auto-validate.
- All hypotheses start as UNTESTED; never auto-support/reject.
- Every claim must be source-attributed: document_id, page, source_file, source_sha256.
- Never paraphrase away original source text; store exact source_text alongside normalized_text.
- Claim types: DEFINITION, OBSERVATION, RULE, HYPOTHESIS, EMPIRICAL_CLAIM, FORMULA, HISTORICAL_CLAIM, OPINION, UNKNOWN.
- If uncertain about classification, use UNKNOWN.
- Methodology uses existing taxonomy; documents may contain multiple methodologies.
- Conflicting claims are valuable; store contradictions without resolving.
- Deterministic/rule-based extraction only in Phase 4; no LLM extraction yet.
- Phase 5 will compare: rule-based vs LLM vs hybrid extraction.

## Context-Aware Classification Rules (Phase 4.5)
- Methodology classification uses weighted keyword evidence with confidence thresholds.
- `classify_methodology_context(text, context)` returns category + confidence + evidence.
- Context from page text and headings improves classification accuracy.
- Classification confidence must be > 0.3 to assign a methodology; otherwise UNKNOWN.
- Claim context (preceding/following sentences) is preserved alongside source_text.
- OCR text is routed through the same extraction pipeline as native text.
- Native text is preferred when quality is GOOD; OCR used when native is FAILED/OCR_REQUIRED.
- All claims remain UNREVIEWED; all hypotheses remain UNTESTED.

## Phase 5 Rules (LLM Extraction Experiment)
- Phase 5 is an EXPERIMENT. Do not replace the deterministic system.
- Do not treat LLM output as truth. Do not backtest claims yet.
- LLM output is untrusted data. Validate: schema, source grounding, allowed enums, confidence ranges.
- Every LLM claim must contain an exact source-text span. No hallucinated content.
- Models are interchangeable candidates. Do not assume largest model is best.
- Report MODEL_UNAVAILABLE rather than failing if a model is unavailable.
- Deterministic rule-based extraction is the baseline. LLM/hybrid are experimental.
- Benchmark on curated gold-standard set first. Do not process all 4,326 pages with an LLM.

## Phase 6 Rules (Hypothesis Engine + Temporal Validation)
- All hypotheses start as UNTESTED. No hypothesis is SUPPORTED merely because a backtest produces positive returns.
- Every hypothesis requires explicit feature requirements and a computable target.
- Never use random train/test splitting for temporal market data.
- Always use chronological, walk-forward, or expanding-window validation.
- Every feature must have a feature_timestamp <= prediction_timestamp.
- Every target must have target_start_timestamp and target_end_timestamp.
- Future target information must NEVER enter the feature set.
- Every feature must have a ProvenanceRecord with exact formula definition.
- All methodologies (Fibonacci, Gann, Astrology, Liquidity, etc.) enter the same hypothesis-testing framework with no special credibility assumptions.
- Run leakage checks before any experiment. A leakage detection failure must fail the experiment.
- Record all experiments in the ExperimentRegistry with full reproducibility metadata.
- Prepare for multiple-testing correction; do not treat the best result among hundreds as automatically significant.
- Do NOT connect trading platforms, brokers, or live data feeds.
- Do NOT make an LLM required for hypothesis testing.
- Mark experimental research as EXPERIMENTAL.

## Phase 7 Rules (First Real Hypothesis Experiment)
- Every experiment must have a predetermined classification rule before running.
- Predetermined criteria: supported (DA > baseline+2%, Sharpe>0.3, mean_return>0), weak (DA > baseline, Sharpe>0 or mean_return>0), rejected (DA < baseline-2%, mean_return<0), inconclusive (all others).
- Never classify a hypothesis as SUPPORTED based on in-sample performance alone.
- Always run robustness checks across parameter variations before classification.
- Always test transaction-cost sensitivity before claiming profitability.
- Always compare against a buy-and-hold baseline.
- Always use chronological splits; never random for temporal data.
- Always run leakage checks before any experiment.
- Always record experiments in the ExperimentRegistry.
- Report all robustness results, not just the best parameter set.
- Do not start Phase 8 automatically after Phase 7. Wait for user review.
