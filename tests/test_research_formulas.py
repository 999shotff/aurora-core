from aurora.research.formulas import FormulaVariable, ResearchFormula


def test_formula_basic():
    f = ResearchFormula(
        formula_id="form_001",
        source_claim_id="claim_001",
        document_id="doc_001",
        expression="SMA(close, 20)",
        page=1,
    )
    assert f.implementation_status == "not_implemented"
    assert f.expression == "SMA(close, 20)"


def test_formula_with_variables():
    f = ResearchFormula(
        formula_id="form_001",
        source_claim_id="claim_001",
        document_id="doc_001",
        expression="RSI(close, period)",
        variables=[
            FormulaVariable(name="close", description="closing price", units="USD"),
            FormulaVariable(name="period", description="lookback period", units="bars", default_value=14),
        ],
        units="ratio",
        page=1,
    )
    assert len(f.variables) == 2
    assert f.variables[1].default_value == 14


def test_formula_assumptions():
    f = ResearchFormula(
        formula_id="form_001",
        source_claim_id="claim_001",
        document_id="doc_001",
        expression="ATR(high, low, close, 14)",
        assumptions=["market is open", "data is clean"],
        page=1,
    )
    assert "market is open" in f.assumptions


def test_formula_serialization_round_trip():
    f = ResearchFormula(
        formula_id="form_001",
        source_claim_id="claim_001",
        document_id="doc_001",
        expression="EMA(close, 20)",
        page=1,
    )
    data = f.model_dump()
    restored = ResearchFormula.model_validate(data)
    assert restored.formula_id == f.formula_id
    assert restored.expression == f.expression
