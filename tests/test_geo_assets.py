"""Multi-source Geo Observatory asset/observation tests.

Covers: asset type validation, observation validation, timestamp ordering,
source provenance, unavailable data, stale data, satellite/balloon/UAV/
ground-sensor/subsurface handling, cross-source conflict, evidence
conversion, and — the hard requirement — no fabricated values anywhere.
"""

from __future__ import annotations

import pytest
from datetime import datetime, timedelta, timezone

from aurora.geo.assets import (
    Asset,
    AssetAvailability,
    AssetLocation,
    AssetObservation,
    AssetType,
    ObservationType,
    SourceConflict,
    detect_conflict,
    observation_to_evidence_dict,
    sort_observations_chronologically,
)
from aurora.geo import assets_service


def _obs(
    obs_id: str,
    asset_id: str = "a1",
    asset_type: AssetType = AssetType.GROUND_SENSOR,
    ts: datetime | None = None,
    availability: AssetAvailability = AssetAvailability.DEMO,
    value: float | str | None = 1.0,
    source: str = "test-source",
    confidence: float = 0.5,
) -> AssetObservation:
    return AssetObservation(
        observation_id=obs_id,
        asset_id=asset_id,
        asset_type=asset_type,
        observation_type=ObservationType.TEMPERATURE,
        timestamp=ts or datetime.now(timezone.utc),
        availability=availability,
        source=source,
        value=value,
        confidence=confidence,
    )


# ── Asset type validation ──

class TestAssetTypeValidation:
    def test_all_five_asset_types_exist(self):
        expected = {"satellite", "balloon", "uav", "ground_sensor", "subsurface"}
        assert {t.value for t in AssetType} == expected

    def test_asset_requires_real_source_when_claiming_live(self):
        with pytest.raises(ValueError):
            Asset(
                asset_id="x1", asset_type=AssetType.UAV, name="Ghost UAV",
                source="", availability=AssetAvailability.LIVE,
            )

    def test_asset_can_be_registered_without_source_data(self):
        # REGISTERED means "known platform, no live feed" — must not require a value.
        asset = Asset(
            asset_id="sat_test", asset_type=AssetType.SATELLITE, name="Test Sat",
            source="Test Provider", availability=AssetAvailability.REGISTERED,
        )
        assert asset.availability == AssetAvailability.REGISTERED


# ── Observation validation ──

class TestObservationValidation:
    def test_live_observation_requires_a_value(self):
        with pytest.raises(ValueError):
            _obs("o1", availability=AssetAvailability.LIVE, value=None)

    def test_derived_observation_requires_a_value(self):
        with pytest.raises(ValueError):
            _obs("o2", availability=AssetAvailability.DERIVED, value=None)

    def test_demo_observation_may_omit_value(self):
        obs = _obs("o3", availability=AssetAvailability.DEMO, value=None)
        assert obs.value is None

    def test_unavailable_observation_may_omit_value(self):
        obs = _obs("o4", availability=AssetAvailability.UNAVAILABLE, value=None)
        assert obs.value is None

    def test_naive_timestamp_rejected(self):
        with pytest.raises(ValueError):
            _obs("o5", ts=datetime.now())  # no tzinfo

    def test_future_timestamp_rejected(self):
        with pytest.raises(ValueError):
            _obs("o6", ts=datetime.now(timezone.utc) + timedelta(days=1))


# ── Timestamp ordering ──

class TestTimestampOrdering:
    def test_sorts_strictly_by_timestamp_value(self):
        now = datetime.now(timezone.utc)
        o_late = _obs("late", ts=now)
        o_early = _obs("early", ts=now - timedelta(hours=2))
        o_mid = _obs("mid", ts=now - timedelta(hours=1))
        ordered = sort_observations_chronologically([o_late, o_early, o_mid])
        assert [o.observation_id for o in ordered] == ["early", "mid", "late"]

    def test_does_not_sort_by_display_string(self):
        # "02:00" vs "10:00" would sort wrong as strings; must sort as real timestamps.
        # Use safely-past relative deltas rather than wall-clock hours (which can be
        # in the future depending on current UTC time and broke this test once).
        now = datetime.now(timezone.utc)
        o_2am = _obs("two", ts=now - timedelta(hours=10))
        o_10am = _obs("ten", ts=now - timedelta(hours=2))
        ordered = sort_observations_chronologically([o_10am, o_2am])
        assert [o.observation_id for o in ordered] == ["two", "ten"]


# ── Source provenance ──

class TestSourceProvenance:
    def test_observation_carries_its_source(self):
        obs = _obs("o7", source="Ground Station Alpha")
        assert obs.source == "Ground Station Alpha"

    def test_evidence_conversion_preserves_source(self):
        obs = _obs("o8", source="Ground Station Alpha", availability=AssetAvailability.DEMO)
        ev = observation_to_evidence_dict(obs)
        assert ev["source"] == "Ground Station Alpha"
        assert ev["availability"] == "DEMO"


# ── Unavailable / stale data ──

class TestUnavailableAndStaleData:
    def test_balloon_category_reports_not_connected(self):
        summary = assets_service.get_category_summary(AssetType.BALLOON)
        assert summary.connected is False
        assert summary.asset_count == 0
        assert summary.note == "DATA SOURCE NOT CONNECTED"

    def test_uav_category_reports_not_connected(self):
        summary = assets_service.get_category_summary(AssetType.UAV)
        assert summary.connected is False
        assert summary.note == "DATA SOURCE NOT CONNECTED"

    def test_ground_sensor_category_reports_not_connected(self):
        summary = assets_service.get_category_summary(AssetType.GROUND_SENSOR)
        assert summary.connected is False
        assert summary.note == "DATA SOURCE NOT CONNECTED"

    def test_subsurface_category_reports_not_connected(self):
        summary = assets_service.get_category_summary(AssetType.SUBSURFACE)
        assert summary.connected is False
        assert summary.note == "DATA SOURCE NOT CONNECTED"

    def test_unconnected_categories_return_empty_asset_lists(self):
        assert assets_service.list_balloon_assets() == []
        assert assets_service.list_uav_assets() == []
        assert assets_service.list_ground_sensor_assets() == []
        assert assets_service.list_subsurface_assets() == []

    def test_stale_availability_is_a_valid_distinct_state(self):
        obs = _obs("o9", availability=AssetAvailability.STALE, value=2.0)
        assert obs.availability == AssetAvailability.STALE
        assert obs.availability != AssetAvailability.LIVE


# ── Satellite (real provider-backed) ──

class TestSatelliteAssets:
    def test_satellite_assets_come_from_real_registry(self):
        assets = assets_service.list_satellite_assets()
        # Whatever the registry has, every asset must reference a real, named provider.
        for a in assets:
            assert a.asset_type == AssetType.SATELLITE
            assert a.source.strip() != ""
            assert a.availability == AssetAvailability.REGISTERED

    def test_satellite_observations_not_fabricated_without_a_search(self):
        # No scene search has run, so there must be zero fabricated observations.
        assert assets_service.list_satellite_observations() == []

    def test_satellite_category_summary_reflects_registry_state(self):
        summary = assets_service.get_category_summary(AssetType.SATELLITE)
        assets = assets_service.list_satellite_assets()
        assert summary.asset_count == len(assets)
        assert summary.connected == (len(assets) > 0)


# ── Balloon / UAV / Ground sensor / Subsurface (no fabrication) ──

class TestNoFabricationAcrossCategories:
    @pytest.mark.parametrize("asset_type", [
        AssetType.BALLOON, AssetType.UAV, AssetType.GROUND_SENSOR, AssetType.SUBSURFACE,
    ])
    def test_category_has_no_assets_or_observations(self, asset_type):
        assert assets_service.list_all_assets(asset_type) == []
        assert assets_service.list_all_observations(asset_type) == []

    def test_all_assets_combined_only_contains_real_satellites(self):
        all_assets = assets_service.list_all_assets()
        for a in all_assets:
            assert a.asset_type == AssetType.SATELLITE


# ── Cross-source conflict ──

class TestCrossSourceConflict:
    def test_detects_numeric_disagreement(self):
        a = _obs("c1", value=20.0, source="Sensor A")
        b = _obs("c2", value=28.0, source="Sensor B")
        conflict = detect_conflict(a, b, field_name="temperature")
        assert isinstance(conflict, SourceConflict)
        assert conflict.observation_ids == ("c1", "c2")

    def test_no_conflict_within_tolerance(self):
        a = _obs("c3", value=20.0, source="Sensor A")
        b = _obs("c4", value=20.05, source="Sensor B")
        conflict = detect_conflict(a, b, field_name="temperature", tolerance=0.1)
        assert conflict is None

    def test_does_not_average_conflicting_values(self):
        a = _obs("c5", value=10.0)
        b = _obs("c6", value=30.0)
        conflict = detect_conflict(a, b)
        # The conflict preserves both raw values — it must never compute/report an average.
        assert "20" not in conflict.values[0] and "20" not in conflict.values[1]
        assert conflict.values == ("10.0", "30.0")

    def test_conflict_none_when_either_value_missing(self):
        a = _obs("c7", value=None, availability=AssetAvailability.UNAVAILABLE)
        b = _obs("c8", value=5.0)
        assert detect_conflict(a, b) is None


# ── Evidence conversion ──

class TestEvidenceConversion:
    def test_converts_observation_to_evidence_shape(self):
        obs = _obs("e1", asset_type=AssetType.GROUND_SENSOR, value=42.0, confidence=0.9)
        ev = observation_to_evidence_dict(obs, investigation_id="inv_test")
        assert ev["id"] == "ev_e1"
        assert ev["investigationId"] == "inv_test"
        assert ev["confidence"] == "high"
        assert ev["metadata"]["assetId"] == "a1"

    def test_confidence_bands_map_correctly(self):
        low = observation_to_evidence_dict(_obs("e2", confidence=0.1))
        med = observation_to_evidence_dict(_obs("e3", confidence=0.5))
        high = observation_to_evidence_dict(_obs("e4", confidence=0.9))
        assert (low["confidence"], med["confidence"], high["confidence"]) == ("low", "medium", "high")

    def test_satellite_maps_to_satellite_source_type(self):
        obs = _obs("e5", asset_type=AssetType.SATELLITE, value=1.0)
        ev = observation_to_evidence_dict(obs)
        assert ev["sourceType"] == "satellite"

    def test_preserves_limitations_in_metadata(self):
        obs = AssetObservation(
            observation_id="e6", asset_id="a1", asset_type=AssetType.GROUND_SENSOR,
            observation_type=ObservationType.HUMIDITY, timestamp=datetime.now(timezone.utc),
            availability=AssetAvailability.DEMO, source="test", value=None,
            limitations=("Sensor calibration overdue",),
        )
        ev = observation_to_evidence_dict(obs)
        assert "calibration" in ev["metadata"]["limitations"]
