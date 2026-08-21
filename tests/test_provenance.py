from aurora.features.provenance import (
    FEATURE_REGISTRY,
    FeatureProvenance,
    get_provenance,
    register_provenance,
)


def test_provenance_known_features():
    for name in ["sma", "ema", "rsi", "atr", "momentum", "volatility"]:
        p = get_provenance(name)
        assert p is not None
        assert p.feature_name == name


def test_provenance_unknown():
    assert get_provenance("nonexistent") is None


def test_provenance_to_dict():
    p = get_provenance("rsi")
    assert p is not None
    d = p.to_dict()
    assert d["feature_name"] == "rsi"
    assert "close" in d["source_columns"]
    assert d["lookback"] == 14


def test_provenance_custom_register():
    custom = FeatureProvenance(
        feature_name="custom_feature",
        source_columns=["close", "volume"],
        lookback=5,
        method="custom_method",
    )
    register_provenance(custom)
    assert get_provenance("custom_feature") is custom


def test_provenance_registry_size():
    assert len(FEATURE_REGISTRY) >= 10
