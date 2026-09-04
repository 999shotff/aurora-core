"""GeoEvidence integration with M26 evidence pipeline.

Provides a function to inject geospatial evidence into the M26
evidence aggregation system without duplicating scoring logic.
"""

from __future__ import annotations

from collections.abc import Sequence

from aurora.features.evidence import (
    EvidenceAggregation,
    EvidencePolarity,
    aggregate_evidence,
)
from aurora.geo.analysis.evidence import (
    aggregate_geo_evidence,
)
from aurora.geo.domain import GeoChange, GeoObservation, GeoTimeSeries


def aggregate_evidence_with_geo(
    market_context: object,
    geo_observations: Sequence[GeoObservation] = (),
    geo_changes: Sequence[GeoChange] = (),
    geo_time_series: Sequence[GeoTimeSeries] = (),
) -> EvidenceAggregation:
    """Aggregate M26 market evidence plus geospatial evidence.

    This function:
    1. Runs the standard M26 evidence aggregation on MarketContext
    2. Converts geospatial data to EvidenceItems
    3. Merges both sets into a single EvidenceAggregation

    The M26 engine remains responsible for scoring/confluence.
    Geo evidence is added as additional OBSERVATION-level items.
    """
    market_agg = aggregate_evidence(market_context)

    geo_items = aggregate_geo_evidence(
        list(geo_observations),
        list(geo_changes),
        list(geo_time_series),
    )

    if not geo_items:
        return market_agg

    all_items = list(market_agg.items) + geo_items

    bull = sum(1 for i in all_items if i.polarity == EvidencePolarity.BULLISH)
    bear = sum(1 for i in all_items if i.polarity == EvidencePolarity.BEARISH)
    neut = sum(1 for i in all_items if i.polarity == EvidencePolarity.NEUTRAL)
    unavail = sum(1 for i in all_items if i.polarity == EvidencePolarity.UNAVAILABLE)
    total = len(all_items)

    return EvidenceAggregation(
        items=all_items,
        bullish_count=bull,
        bearish_count=bear,
        neutral_count=neut,
        unavailable_count=unavail,
        total_evidence=total,
        bullish_pct=round(bull / total, 2) if total > 0 else 0.0,
        bearish_pct=round(bear / total, 2) if total > 0 else 0.0,
    )
