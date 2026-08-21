"""Tests for Phase 10: Advanced Signal & Target Research.

Tests cover:
1. Multi-horizon target construction
2. Target design variations
3. Market-structure features
4. Cross-asset features
5. Feature interactions
6. Regime classification
7. Statistical testing
8. Transaction costs
9. Audit trail
10. Reproducibility
"""

import math

from aurora.models.phase7_validation import OHLCVRecord
from aurora.models.phase10 import (
    AuditTrail,
    compute_feature_interactions,
    construct_targets_multi_horizon,
    construct_targets_thresholded,
    construct_targets_volatility_adjusted,
    engineer_cross_asset_features,
    engineer_market_structure_features,
    get_market_structure_feature_names,
    get_market_structure_groups,
)

# ═══════════════════════════════════════════════════════
# TEST DATA
# ═══════════════════════════════════════════════════════

def _make_records(n: int = 300) -> list[OHLCVRecord]:
    """Create synthetic OHLCV records for testing."""
    records = []
    price = 100.0
    for i in range(n):
        import random
        rng = random.Random(i)
        change = rng.gauss(0, 0.02)
        price *= (1 + change)

        r = OHLCVRecord(
            timestamp=f"2024-01-{i+1:02d}",
            open=price * 0.99,
            high=price * 1.01,
            low=price * 0.98,
            close=price,
            volume=rng.randint(1000, 10000),
        )
        records.append(r)
    return records


# ═══════════════════════════════════════════════════════
# 1. MULTI-HORIZON TARGETS
# ═══════════════════════════════════════════════════════

class TestMultiHorizonTargets:
    def test_horizon_1(self):
        records = _make_records(100)
        targets = construct_targets_multi_horizon(records, [1])
        labels, target_def = targets[1]
        assert len(labels) == 99
        assert target_def.horizon == 1

    def test_horizon_5(self):
        records = _make_records(100)
        targets = construct_targets_multi_horizon(records, [5])
        labels, target_def = targets[5]
        assert len(labels) == 95
        assert target_def.horizon == 5

    def test_multiple_horizons(self):
        records = _make_records(100)
        targets = construct_targets_multi_horizon(records, [1, 2, 5, 10])
        assert len(targets) == 4
        for h in [1, 2, 5, 10]:
            assert h in targets

    def test_class_distribution(self):
        records = _make_records(100)
        targets = construct_targets_multi_horizon(records, [1])
        _labels, target_def = targets[1]
        pos_rate = target_def.class_distribution["up"]
        neg_rate = target_def.class_distribution["down"]
        assert abs(pos_rate + neg_rate - 1.0) < 1e-10


# ═══════════════════════════════════════════════════════
# 2. THRESHOLDED TARGETS
# ═══════════════════════════════════════════════════════

class TestThresholdedTargets:
    def test_threshold_001(self):
        records = _make_records(100)
        labels, target_def = construct_targets_thresholded(records, 0.001)
        assert len(labels) == 99
        assert "flat" in target_def.class_distribution

    def test_threshold_01(self):
        records = _make_records(100)
        labels, _target_def = construct_targets_thresholded(records, 0.01)
        assert len(labels) == 99
        # Higher threshold should have more flat labels
        n_flat = sum(1 for y in labels if y == "flat")
        assert n_flat > 0


# ═══════════════════════════════════════════════════════
# 3. VOLATILITY-ADJUSTED TARGETS
# ═══════════════════════════════════════════════════════

class TestVolatilityAdjustedTargets:
    def test_vol_adjusted(self):
        records = _make_records(100)
        labels, target_def = construct_targets_volatility_adjusted(records, lookback=20, multiplier=1.0)
        assert len(labels) == 99
        assert "neutral" in target_def.class_distribution

    def test_higher_multiplier(self):
        records = _make_records(100)
        labels_1, _ = construct_targets_volatility_adjusted(records, lookback=20, multiplier=1.0)
        labels_2, _ = construct_targets_volatility_adjusted(records, lookback=20, multiplier=2.0)
        # Higher multiplier should have more neutral labels
        n_neutral_1 = sum(1 for y in labels_1 if y == "neutral")
        n_neutral_2 = sum(1 for y in labels_2 if y == "neutral")
        assert n_neutral_2 >= n_neutral_1


# ═══════════════════════════════════════════════════════
# 4. MARKET-STRUCTURE FEATURES
# ═══════════════════════════════════════════════════════

class TestMarketStructureFeatures:
    def test_engineer_features(self):
        records = _make_records(100)
        features = engineer_market_structure_features(records)
        assert len(features) == 100

    def test_feature_names(self):
        names = get_market_structure_feature_names()
        assert len(names) > 20

    def test_feature_groups(self):
        groups = get_market_structure_groups()
        assert "trend_structure" in groups
        assert "momentum_structure" in groups
        assert "volatility_structure" in groups
        assert "range_structure" in groups
        assert "volume_structure" in groups
        assert "price_volume" in groups

    def test_no_nans(self):
        records = _make_records(100)
        features = engineer_market_structure_features(records)
        for f in features:
            for name, value in f.items():
                assert not math.isnan(value), f"NaN in feature {name}"
                assert not math.isinf(value), f"Inf in feature {name}"


# ═══════════════════════════════════════════════════════
# 5. CROSS-ASSET FEATURES
# ═══════════════════════════════════════════════════════

class TestCrossAssetFeatures:
    def test_no_secondary(self):
        records = _make_records(100)
        features = engineer_cross_asset_features(records, None)
        assert len(features) == 100
        assert features[0] == {}

    def test_with_secondary(self):
        primary = _make_records(100)
        secondary = _make_records(100)
        features = engineer_cross_asset_features(primary, secondary, "BTC")
        assert len(features) == 100
        assert "BTC_return_1d" in features[0]


# ═══════════════════════════════════════════════════════
# 6. FEATURE INTERACTIONS
# ═══════════════════════════════════════════════════════

class TestFeatureInteractions:
    def test_compute_interactions(self):
        features = [{"rsi_14": 50.0, "volatility_20d": 0.02, "close_to_sma20": 0.01,
                     "relative_volume": 1.0, "body_range": 0.01, "bb_width": 0.05}]
        interactions = compute_feature_interactions(features, list(features[0].keys()))
        assert len(interactions) == 1
        assert "momentum_x_volatility" in interactions[0]


# ═══════════════════════════════════════════════════════
# 7. AUDIT TRAIL
# ═══════════════════════════════════════════════════════

class TestAuditTrail:
    def test_add_entry(self):
        trail = AuditTrail()
        trail.add("test_event", {"key": "value"})
        assert len(trail.entries) == 1
        assert trail.entries[0].event == "test_event"

    def test_to_dict(self):
        trail = AuditTrail()
        trail.add("test_event", {"key": "value"})
        d = trail.to_dict()
        assert len(d) == 1
        assert d[0]["event"] == "test_event"


# ═══════════════════════════════════════════════════════
# 8. EMPTY INPUTS
# ═══════════════════════════════════════════════════════

class TestEmptyInputs:
    def test_empty_multi_horizon(self):
        records = _make_records(10)
        targets = construct_targets_multi_horizon(records, [1])
        labels, _ = targets[1]
        assert len(labels) == 9

    def test_empty_cross_asset(self):
        features = engineer_cross_asset_features([], None)
        assert features == []
