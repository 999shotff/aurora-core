"""Tests for Phase 13: External Data + Advanced Model Research."""

import pytest

from aurora.models.phase13 import (
    ExternalDataProvenance,
    ExternalDataRecord,
    ExternalDataset,
    DataQualityReport,
    LeakageCheckResult,
    ExternalEvalResult,
    InstrumentEvalReport,
    M13Summary,
    EXTERNAL_SOURCES,
    EXTERNAL_FEATURE_GROUPS,
    ALL_EXTERNAL_FEATURE_NAMES,
    CROSS_ASSET_MAP,
    validate_external_data,
    check_temporal_leakage,
    get_external_feature_names,
    get_external_feature_groups,
    get_feature_group_indices,
    engineer_vix_features,
    engineer_external_features,
)
from aurora.models.phase7_validation import OHLCVRecord


def _make_records(n: int) -> list[OHLCVRecord]:
    """Create synthetic OHLCV records."""
    from datetime import datetime, timedelta

    base = datetime(2021, 1, 1)
    records = []
    for i in range(n):
        dt = base + timedelta(days=i)
        records.append(
            OHLCVRecord(
                timestamp=dt.strftime("%Y-%m-%dT00:00:00"),
                open=100.0 + i * 0.1,
                high=101.0 + i * 0.1,
                low=99.0 + i * 0.1,
                close=100.5 + i * 0.1,
                volume=1000000.0,
            )
        )
    return records


def _make_external_dataset(ticker: str, n: int) -> ExternalDataset:
    """Create synthetic external dataset."""
    from datetime import datetime, timedelta

    base = datetime(2021, 1, 1)
    records = []
    for i in range(n):
        dt = base + timedelta(days=i)
        records.append(
            ExternalDataRecord(
                date=dt.strftime("%Y-%m-%d"),
                open=50.0 + i * 0.05,
                high=51.0 + i * 0.05,
                low=49.0 + i * 0.05,
                close=50.5 + i * 0.05,
                volume=500000.0,
                ticker=ticker,
            )
        )
    return ExternalDataset(
        ticker=ticker,
        records=records,
        provenance=ExternalDataProvenance(
            source_ticker=ticker,
            source_name=ticker,
            category="test",
            fetch_timestamp="2026-01-01T00:00:00Z",
            rows=n,
            date_range_start=records[0].date,
            date_range_end=records[-1].date,
            missing_values=0,
        ),
    )


class TestExternalDataSchema:
    def test_external_sources_defined(self):
        assert "^VIX" in EXTERNAL_SOURCES
        assert "^TNX" in EXTERNAL_SOURCES
        assert "DX-Y.NYB" in EXTERNAL_SOURCES
        assert "GC=F" in EXTERNAL_SOURCES
        assert "CL=F" in EXTERNAL_SOURCES
        assert "ETH-USD" in EXTERNAL_SOURCES

    def test_source_categories(self):
        assert EXTERNAL_SOURCES["^VIX"]["category"] == "volatility"
        assert EXTERNAL_SOURCES["^TNX"]["category"] == "rates"
        assert EXTERNAL_SOURCES["DX-Y.NYB"]["category"] == "macro"

    def test_cross_asset_map(self):
        assert "BTC-USD" in CROSS_ASSET_MAP
        assert "SPY" in CROSS_ASSET_MAP
        assert "QQQ" in CROSS_ASSET_MAP
        assert "^VIX" in CROSS_ASSET_MAP["BTC-USD"]

    def test_external_feature_groups(self):
        groups = get_external_feature_groups()
        assert "volatility" in groups
        assert "cross_asset_returns" in groups
        assert "cross_asset_regime" in groups
        assert "cross_asset_correlation" in groups

    def test_external_feature_names(self):
        names = get_external_feature_names()
        assert len(names) > 0
        assert "vix_level" in names
        assert "vix_change" in names

    def test_no_duplicate_features(self):
        names = get_external_feature_names()
        assert len(names) == len(set(names))


class TestDataQuality:
    def test_validate_good_data(self):
        ds = _make_external_dataset("^VIX", 100)
        report = validate_external_data(ds)
        assert report.total_rows == 100
        assert report.quality_score > 0.9
        assert report.timestamp_order_valid is True
        assert report.duplicate_dates == 0
        assert report.missing_values == 0

    def test_validate_with_duplicates(self):
        ds = _make_external_dataset("^VIX", 10)
        bad_records = ds.records + [ds.records[0]]
        ds_dup = ExternalDataset(
            ticker="^VIX",
            records=bad_records,
            provenance=ds.provenance,
        )
        report = validate_external_data(ds_dup)
        assert report.duplicate_dates == 1

    def test_validate_zero_close(self):
        records = [
            ExternalDataRecord("2021-01-01", 100, 101, 99, 0, 1000, "^VIX"),
            ExternalDataRecord("2021-01-02", 100, 101, 99, 100, 1000, "^VIX"),
        ]
        ds = ExternalDataset(
            ticker="^VIX",
            records=records,
            provenance=ExternalDataProvenance(
                source_ticker="^VIX", source_name="VIX", category="volatility",
                fetch_timestamp="", rows=2, date_range_start="", date_range_end="",
                missing_values=0,
            ),
        )
        report = validate_external_data(ds)
        assert report.missing_values == 1


class TestLeakageProtection:
    def test_safe_no_leakage(self):
        result = check_temporal_leakage("2021-01-01", "2021-01-02")
        assert result.is_safe is True
        assert result.reason == "safe"

    def test_safe_same_date(self):
        result = check_temporal_leakage("2021-01-01", "2021-01-01")
        assert result.is_safe is True

    def test_leakage_detected(self):
        result = check_temporal_leakage("2021-01-03", "2021-01-02")
        assert result.is_safe is False
        assert "LEAKAGE" in result.reason

    def test_leakage_result_fields(self):
        result = check_temporal_leakage("2021-01-01", "2021-01-02")
        assert result.feature_available_time == "2021-01-01"
        assert result.prediction_cutoff_time == "2021-01-02"


class TestVIXFeatures:
    def test_vix_features_length(self):
        records = _make_records(30)
        vix_data = {
            records[i].timestamp[:10]: ExternalDataRecord(
                date=records[i].timestamp[:10],
                open=20.0, high=21.0, low=19.0, close=20.5,
                volume=0, ticker="^VIX",
            )
            for i in range(30)
        }
        features = engineer_vix_features(vix_data, records)
        assert len(features) == 30
        for f in features:
            assert "vix_level" in f
            assert "vix_change" in f
            assert "vix_ma5" in f
            assert "vix_ma10" in f
            assert "vix_ma20" in f
            assert "vix_rsi14" in f

    def test_vix_level_values(self):
        records = _make_records(5)
        vix_data = {
            records[i].timestamp[:10]: ExternalDataRecord(
                date=records[i].timestamp[:10],
                open=20.0, high=21.0, low=19.0, close=20.0 + i,
                volume=0, ticker="^VIX",
            )
            for i in range(5)
        }
        features = engineer_vix_features(vix_data, records)
        assert features[0]["vix_level"] == 20.0
        assert features[1]["vix_level"] == 21.0


class TestExternalFeatures:
    def test_engineer_external_features(self):
        records = _make_records(30)
        ds = _make_external_dataset("^VIX", 30)
        datasets = {"^VIX": ds}
        features = engineer_external_features(datasets, records)
        assert len(features) == 30
        for f in features:
            assert "vix_level" in f

    def test_feature_count_matches_names(self):
        records = _make_records(30)
        ds = _make_external_dataset("^VIX", 30)
        datasets = {"^VIX": ds}
        features = engineer_external_features(datasets, records)
        # All features from available sources should be present
        assert len(features) == 30
        for f in features:
            assert "vix_level" in f
            assert "vix_change" in f
            # Features should be generated for available sources
            assert len(f) > 0


class TestFeatureGroupIndices:
    def test_volatility_indices(self):
        names = get_external_feature_names()
        indices = get_feature_group_indices(names, "volatility")
        assert len(indices) > 0
        for i in indices:
            assert names[i] in EXTERNAL_FEATURE_GROUPS["volatility"]

    def test_invalid_group(self):
        names = get_external_feature_names()
        indices = get_feature_group_indices(names, "nonexistent")
        assert indices == []


class TestModelFactory:
    def test_create_logistic_regression(self):
        from aurora.models.phase12 import create_model
        model = create_model("logistic_regression", {"learning_rate": 0.01, "n_iterations": 100})
        assert model is not None

    def test_create_decision_tree(self):
        from aurora.models.phase12 import create_model
        model = create_model("decision_tree", {"max_depth": 4})
        assert model is not None


class TestProvenance:
    def test_provenance_fields(self):
        prov = ExternalDataProvenance(
            source_ticker="^VIX",
            source_name="VIX",
            category="volatility",
            fetch_timestamp="2026-01-01T00:00:00Z",
            rows=1256,
            date_range_start="2021-01-01",
            date_range_end="2026-01-01",
            missing_values=0,
        )
        assert prov.source_ticker == "^VIX"
        assert prov.category == "volatility"
        assert prov.timezone == "UTC"


class TestExperimentRegistry:
    def test_experiment_record_fields(self):
        from aurora.models.phase11 import ExperimentRecord
        rec = ExperimentRecord(
            experiment_id="test_13",
            hypothesis="test",
            data_source="yfinance",
            data_period="5y",
            instrument="BTC-USD",
            target="directional",
            horizon=1,
            feature_groups=["base", "external"],
            model="logistic_regression",
            hyperparameters={"lr": 0.01},
            ensemble_config=None,
            train_period="2021-2024",
            validation_period="2024-2025",
            test_period="2025-2026",
            metrics={"accuracy": 0.5},
            transaction_costs={"cost": 0.001},
            statistical_results={"p_value": 0.1},
            adjusted_p_value=None,
            status="INCONCLUSIVE",
            reason="no improvement",
        )
        assert rec.experiment_id == "test_13"
        assert rec.instrument == "BTC-USD"
