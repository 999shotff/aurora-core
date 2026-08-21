from aurora.research.taxonomy import (
    METHODOLOGY_TAXONOMY,
    classify_methodology,
    list_categories,
)


def test_taxonomy_categories_exist():
    cats = list_categories()
    assert "liquidity" in cats
    assert "gann" in cats
    assert "fibonacci" in cats
    assert "astrology" in cats
    assert "unknown" in cats


def test_taxonomy_all_have_descriptions():
    for info in METHODOLOGY_TAXONOMY.values():
        assert "description" in info
        assert len(info["description"]) > 0


def test_classify_methodology():
    assert classify_methodology("This is about liquidity sweeps") == "liquidity"
    assert classify_methodology("Fibonacci retracement levels") == "fibonacci"
    assert classify_methodology("Gann angle analysis") == "gann"
    assert classify_methodology("Elliott wave impulse") == "elliott_wave"
    assert classify_methodology("VWAP deviation bands") == "vwap"


def test_classify_unknown():
    assert classify_methodology("random text with no keywords") == "unknown"


def test_methodology_tag():
    from aurora.research.taxonomy import MethodologyTag

    tag = MethodologyTag(category="gann", confidence=0.8)
    assert tag.category == "gann"
    assert tag.confidence == 0.8


def test_taxonomy_parent_hierarchy():
    assert METHODOLOGY_TAXONOMY["liquidity"]["parent"] == "market_structure"
    assert METHODOLOGY_TAXONOMY["market_structure"]["parent"] == "technical_analysis"
    assert METHODOLOGY_TAXONOMY["technical_analysis"]["parent"] == ""
