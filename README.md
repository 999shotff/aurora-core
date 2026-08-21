# AURORA CORE

AI-first research and market-reasoning system.

## Current milestone: Phase 0 / Foundation

This repository starts small. It does not attempt to train or deploy a trading model yet.

Current components:
- typed market-state schema
- deterministic feature interfaces
- model adapter interface
- evaluation record schema
- research-library indexing
- experiment manifest
- baseline local-model configuration
- tests

Principles:
1. Research claims are hypotheses until validated.
2. No look-ahead leakage.
3. No fake live data.
4. Numerical calculations belong in deterministic code, not the LLM.
5. A model may abstain when evidence is insufficient.
6. New models are challengers until they beat the champion on predefined tests.
7. OpenMythos/Kimi/other architectures are research references, not assumed solutions.
