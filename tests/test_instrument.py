from aurora.schemas.instrument import InstrumentIdentity, build_instrument


def test_build_instrument_crypto():
    inst = build_instrument("BTCUSD", asset_class="crypto", exchange="binance")
    assert inst.symbol == "BTCUSD"
    assert inst.asset_class == "crypto"
    assert inst.exchange == "binance"
    assert inst.quote_currency == "USD"


def test_build_instrument_equity():
    inst = build_instrument("AAPL", asset_class="equity", exchange="NASDAQ", quote_currency="USD")
    assert inst.symbol == "AAPL"
    assert inst.asset_class == "equity"


def test_build_instrument_forex():
    inst = build_instrument("EURUSD", asset_class="forex", exchange="forex")
    assert inst.symbol == "EURUSD"
    assert inst.asset_class == "forex"


def test_build_instrument_commodity():
    inst = build_instrument("XAUUSD", asset_class="commodity", exchange="comex")
    assert inst.symbol == "XAUUSD"
    assert inst.asset_class == "commodity"


def test_canonical_name():
    inst = build_instrument("BTCUSD", asset_class="crypto", exchange="binance")
    assert inst.canonical_name() == "BTCUSD:crypto:binance"


def test_matches_same():
    a = build_instrument("BTCUSD", asset_class="crypto")
    b = build_instrument("BTCUSD", asset_class="equity")
    assert a.matches(b)


def test_matches_different():
    a = build_instrument("BTCUSD", asset_class="crypto")
    b = build_instrument("ETHUSD", asset_class="crypto")
    assert not a.matches(b)


def test_base_currency():
    inst = build_instrument("BTCUSD", asset_class="crypto", quote_currency="USD")
    assert inst.base_currency == "BTC"


def test_display_name_default():
    inst = build_instrument("BTCUSD", asset_class="crypto")
    assert inst.display_name == "BTCUSD"


def test_display_name_custom():
    inst = InstrumentIdentity(
        symbol="BTCUSD",
        asset_class="crypto",
        display_name="Bitcoin / US Dollar",
    )
    assert inst.display_name == "Bitcoin / US Dollar"


def test_metadata():
    inst = build_instrument(
        "BTCUSD",
        asset_class="crypto",
        exchange="binance",
        decimals=8,
        min_tick_size=0.01,
        metadata={"max_leverage": "125"},
    )
    assert inst.decimals == 8
    assert inst.min_tick_size == 0.01
    assert inst.metadata["max_leverage"] == "125"


def test_instrument_serialization_round_trip():
    inst = build_instrument("BTCUSD", asset_class="crypto", exchange="binance")
    data = inst.model_dump()
    restored = InstrumentIdentity.model_validate(data)
    assert restored.symbol == inst.symbol
    assert restored.asset_class == inst.asset_class
    assert restored.exchange == inst.exchange
