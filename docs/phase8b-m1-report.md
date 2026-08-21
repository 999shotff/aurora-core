# AURORA CORE — Phase 8B Milestone 1 Report: Model Interface Foundation

**Date:** 2026-08-16
**Status:** COMPLETE
**Tests:** 646 passed (588 existing + 58 new)
**Ruff:** All checks passed
**Mypy:** Success: no issues found

---

## 1. Files Created/Modified

| File | Action | Lines |
|------|--------|-------|
| `src/aurora/models/base.py` | Modified | Enhanced with ModelInput, ModelOutput, ModelMetadata, ModelAuditTrail, ModelAdapter |
| `src/aurora/models/registry.py` | Created | ModelRegistry implementation |
| `src/aurora/models/stub.py` | Modified | Updated to use new ModelInput/ModelOutput interface |
| `src/aurora/models/__init__.py` | Modified | Updated exports |
| `src/aurora/evaluation/pipeline.py` | Modified | Added _state_to_input() wrapper for backward compatibility |
| `tests/test_phase8b_m1.py` | Created | 58 comprehensive tests |
| `tests/test_stub_adapter.py` | Modified | Updated to use ModelInput |

---

## 2. Interface Design

### 2.1 ModelInput (Pydantic, frozen)

```python
class ModelInput(BaseModel):
    instrument_id: str
    timeframe: str
    timestamp: datetime
    feature_vector: FeatureVector
    market_state: MarketState
    research_evidence: dict[str, Any]
    regime_label: str
    data_quality: DataQuality
    feature_schema_version: str
    dataset_version: str
    evaluation_context: Literal["train", "validation", "test", "shadow", "live"]
    leakage_flags: dict[str, bool]
```

### 2.2 ModelOutput (Pydantic, frozen)

```python
class ModelOutput(BaseModel):
    model_id: str
    model_version: str
    outcome: Outcome
    probability: float          # [0, 1]
    probability_distribution: dict[str, float]
    confidence: float           # [0, 1]
    uncertainty: float          # [0, 1]
    calibration_status: CalibrationStatus
    calibration_score: float | None
    abstained: bool
    abstention_reason: str | None
    reasoning: str
    raw_output: str | None
    inference_timestamp: datetime | None
    feature_schema_version: str
    metadata: dict[str, str]
```

### 2.3 ModelMetadata (Pydantic, frozen)

```python
class ModelMetadata(BaseModel):
    model_id: str
    model_version: str
    model_type: str
    framework: str
    supported_input_schema: str
    supported_output_schema: str
    training_info: dict[str, Any]
    reproducibility_info: dict[str, Any]
    configuration: dict[str, Any]
```

### 2.4 ModelAuditTrail (dataclass, frozen)

```python
@dataclass(frozen=True)
class ModelAuditTrail:
    model_id: str
    model_version: str
    training_period: tuple[str, str]
    validation_period: tuple[str, str]
    test_period: tuple[str, str]
    dataset_version: str
    feature_schema_version: str
    hyperparameters: dict[str, Any]
    random_seed: int
    calibration_method: CalibrationStatus
    evaluation_metrics: dict[str, float]
    promotion_decision: str
    decision_reason: str
    timestamp: str
```

### 2.5 ModelAdapter (ABC)

```python
class ModelAdapter(ABC):
    @property
    @abstractmethod
    def model_id(self) -> str: ...

    @property
    @abstractmethod
    def model_version(self) -> str: ...

    @abstractmethod
    def predict(self, model_input: ModelInput) -> ModelOutput: ...

    def fit(self, training_inputs, labels) -> None: ...
    def calibrate(self, calibration_inputs, labels) -> None: ...
    def is_ready(self) -> bool: ...
    def feature_requirements(self) -> list[str]: ...
    def metadata(self) -> ModelMetadata: ...
    def validate_input(self, model_input: ModelInput) -> None: ...
```

---

## 3. Data Contracts

### 3.1 Input Contract

- `ModelInput` is immutable (frozen Pydantic model)
- `evaluation_context` enforces temporal split awareness
- `leakage_flags` carries explicit leakage detection results
- `feature_schema_version` enables version compatibility checks
- `dataset_version` tracks data provenance

### 3.2 Output Contract

- `ModelOutput` is immutable (frozen Pydantic model)
- `probability` is bounded [0, 1] by Pydantic validation
- `confidence` and `uncertainty` are bounded [0, 1]
- `calibration_status` distinguishes "none" from "platt"/"isotonic"
- `abstained` flag with optional `abstention_reason`
- `inference_timestamp` records when prediction was made

### 3.3 Audit Contract

- `ModelAuditTrail` is immutable (frozen dataclass)
- Records training/validation/test periods as date tuples
- Stores hyperparameters, random seed, calibration method
- Tracks promotion/rejection decision with reason
- Auto-populates timestamp on creation

---

## 4. Registry Behavior

### 4.1 Registration

```python
registry = ModelRegistry()
registry.register(adapter, tags=["experimental"])
```

- Prevents duplicate (model_id, version) combinations
- Returns ModelMetadata on success
- Stores adapter, metadata, tags, status

### 4.2 Lookup

```python
adapter = registry.get("my_model")           # latest version
adapter = registry.get("my_model", "1.0.0")  # specific version
metadata = registry.get_metadata("my_model")
```

- Raises KeyError for missing models
- `get()` defaults to latest version if not specified

### 4.3 Listing

```python
all_models = registry.list_models()
active = registry.list_models(status="active")
experimental = registry.list_models(tag="experimental")
versions = registry.list_versions("my_model")
```

### 4.4 Lifecycle

```python
registry.deactivate("my_model")           # deprecate all versions
registry.deactivate("my_model", "1.0.0")  # deprecate specific version
```

### 4.5 Audit Trail Integration

```python
trail = ModelAuditTrail(model_id="m", model_version="1.0", ...)
registry.add_audit_trail("m", "1.0", trail)
trails = registry.get_audit_trails("m", "1.0")
```

### 4.6 Schema Compatibility

```python
compatible = registry.validate_compatibility("my_model", "0.1.0")
```

---

## 5. Leakage Protections

### 5.1 Input Validation

The `ModelAdapter.validate_input()` method checks:

1. **Test context leakage:** If `evaluation_context == "test"` and any `leakage_flags` are True, raises ValueError
2. **Schema version mismatch:** If `feature_schema_version` doesn't match model's `supported_input_schema`, raises ValueError

### 5.2 Design Rationale

- Leakage flags are carried explicitly, not inferred
- Only the test context enforces strict leakage checks
- Train/validation contexts allow flags for flexibility (e.g., forward-looking features in training)
- Schema version mismatch prevents silent incompatibility

### 5.3 What's NOT Protected (by design)

- The interface does NOT prevent a model from memorizing test data (that's the temporal validation layer's job)
- The interface does NOT prevent a model from using future features (that's the feature engineering layer's job)
- The interface carries leakage flags as a communication channel, not an enforcement mechanism

---

## 6. Calibration Representation

### 6.1 CalibrationStatus

```python
CalibrationStatus = Literal["none", "platt", "isotonic", "unknown"]
```

- `"none"`: No calibration performed (default)
- `"platt"`: Platt scaling applied
- `"isotonic"`: Isotonic regression applied
- `"unknown"`: Calibration status unknown

### 6.2 Calibration Score

```python
calibration_score: float | None = None
```

- `None` means no calibration score available
- When set, represents expected calibration error

### 6.3 Design Rationale

- Distinguishes "no calibration" from "calibrated"
- Does NOT fabricate calibration scores
- Models must explicitly opt into calibration

---

## 7. Abstention Representation

### 7.1 Abstention Fields

```python
abstained: bool = False
abstention_reason: str | None = None
```

### 7.2 Abstention Behavior

- `abstained=True` with `outcome="unknown"` signals the model declined
- `abstention_reason` provides human-readable explanation
- `confidence=0.0` and `uncertainty=1.0` when abstaining
- `probability=0.5` when abstaining (neutral)

### 7.3 Design Rationale

- Explicit abstention prevents forced predictions
- Reason field enables debugging and improvement
- Confidence/uncertainty signals model self-assessment

---

## 8. Tests

### 8.1 Test Categories (58 tests)

| Category | Count | Coverage |
|----------|-------|----------|
| ModelInput validation | 6 | Construction, frozen, extras, context, leakage |
| ModelOutput validation | 10 | Construction, frozen, bounds, calibration, abstention |
| ModelMetadata validation | 3 | Construction, frozen, defaults |
| ModelAuditTrail validation | 5 | Construction, frozen, timestamp, decision, metrics |
| ModelAdapter tests | 8 | Ready, requirements, metadata, validate, predict |
| ModelRegistry tests | 12 | Register, get, list, deactivate, versions, count, compatibility |
| Audit trail integration | 2 | Add/get trails, nonexistent model |
| Leakage protection | 4 | Test context, train context, all contexts, multiple flags |
| Probability validity | 5 | Zero, one, half, negative, above one |
| StubAdapter integration | 3 | Deterministic, abstains, metadata type |

### 8.2 Key Test Scenarios

- **Frozen immutability:** All data classes reject post-construction modification
- **Extra field rejection:** Pydantic models forbid unknown fields
- **Probability bounds:** 0.0 and 1.0 accepted, -0.01 and 1.01 rejected
- **Leakage in test context:** Flags with any True value raise ValueError
- **Leakage in train context:** Flags are allowed (for flexibility)
- **Schema mismatch:** Wrong version raises ValueError
- **Duplicate registration:** Same (id, version) raises ValueError
- **Missing model lookup:** KeyError raised
- **Audit trail storage:** Trails persist and retrieve correctly

---

## 9. Verification Results

### 9.1 Pytest

```
646 passed, 1 warning in 29.89s
```

- 588 existing tests: all pass
- 58 new tests: all pass
- No regressions

### 9.2 Ruff

```
All checks passed!
```

- No lint errors in new code
- Pre-existing errors in research module (not in scope)

### 9.3 Mypy

```
Success: no issues found in 4 source files
```

- Type checking passes for models/ directory

---

## 10. Remaining Limitations

| Limitation | Severity | Mitigation |
|-----------|----------|------------|
| No actual model implementations | MEDIUM | Milestone 2+ will add adapters |
| No temporal validation integration | MEDIUM | Phase 8B later milestones |
| No calibration implementation | LOW | Models can opt into calibration later |
| No benchmark harness | MEDIUM | Phase 8B later milestones |
| Research module has pre-existing ruff errors | LOW | Not in scope for Phase 8B |
| Leakage protection is flag-based, not enforced | LOW | Temporal validation layer handles enforcement |

---

## 11. Architecture Summary

```
ModelInput (Pydantic, frozen)
    ↓
ModelAdapter.validate_input()  →  leakage check, schema check
    ↓
ModelAdapter.predict()         →  model-specific logic
    ↓
ModelOutput (Pydantic, frozen) →  probability, confidence, uncertainty, abstention
    ↓
ModelAuditTrail (dataclass)    →  evaluation lifecycle record
    ↓
ModelRegistry                  →  versioned storage, compatibility check
```

---

## 12. What's NOT in Scope

- No model training
- No PyTorch installation
- No Transformers installation
- No model weight downloads
- No LLM building
- No website
- No live trading
- No benchmark harness (Milestone 2+)
- No calibration implementation (Milestone 2+)

---

**STOP. Milestone 1 complete. Do not implement Milestone 2.**
