"""Unit tests for CME options instrument-definition universe (2026-06-27).

Verifies that:
1. All CME option roots for MVP underliers are present in TRADFI_DATABENTO_INSTRUMENTS.
2. MVP_CME_EXCHANGE_CODES covers the full commodity + index option surface.
3. EXCHANGE_CODE_TO_NAME covers commodity option root codes so the adapter can
   resolve product roots for OG, LO, ON, HXE, SO, PO, PAO, OH, OB, etc.
4. get_mvp_databento_symbols_for_venue("CME") returns the expected option defs.
5. Option defs have instrument_type="OPTION", dataset="GLBX.MDP3", stype_in="parent".

Root cause: the tradfi catalogue had 0 CME OPTION rows because the option
exchange codes (OG, LO, etc.) were missing from MVP_CME_EXCHANGE_CODES and
EXCHANGE_CODE_TO_NAME, causing the adapter's resolve-product-root path to
return None for commodity options (→ reclassified as COMBO → dropped).
Fixed 2026-06-27: expanded both constants.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.tradfi_instrument_universe import (
    EXCHANGE_CODE_TO_NAME,
    MVP_CME_EXCHANGE_CODES,
    TRADFI_DATABENTO_INSTRUMENTS,
    DatabentoInstrumentDef,
    get_databento_symbols_for_venue,
    get_mvp_databento_symbols_for_venue,
)

# ---------------------------------------------------------------------------
# Expected MVP CME option roots — grouped by underlying
# ---------------------------------------------------------------------------

# ES (SP500) option surfaces — all exchange codes that map to ES options
_ES_OPTION_CODES: frozenset[str] = frozenset(
    {
        "ES",  # ES.OPT — quarterly
        "EW",  # EW.OPT  — weekly Friday
        "EW1",  # EW1.OPT — Monday weekly
        "EW2",  # EW2.OPT — Wednesday weekly
        "EW4",  # EW4.OPT — Tuesday weekly
        "E1A",  # E1A.OPT — Monday 0DTE
        "E2A",  # E2A.OPT — Tuesday 0DTE
        "E3A",  # E3A.OPT — Wednesday 0DTE
        "E4A",  # E4A.OPT — Thursday 0DTE
        "E5A",  # E5A.OPT — Friday 0DTE
        "EOM",  # EOM.OPT — end-of-month
    }
)

# NQ (Nasdaq 100) option surface
_NQ_OPTION_CODES: frozenset[str] = frozenset({"NQ"})

# Commodity options-on-futures (MVP roots only — Binance perp basis)
_COMMODITY_OPTION_CODES: frozenset[str] = frozenset(
    {
        "OG",  # gold options on GC futures
        "LO",  # crude oil options on CL futures
        "ON",  # natural gas options on NG futures
        "HXE",  # copper options on HG futures
        "SO",  # silver options on SI futures
        "PO",  # platinum options on PL futures
        "PAO",  # palladium options on PA futures
    }
)

# CME event contracts for MVP underliers
_EVENT_CONTRACT_CODES: frozenset[str] = frozenset({"ECES", "ECNQ", "ECGC", "ECCL", "ECNG", "ECBTC"})

_ALL_MVP_OPTION_CODES: frozenset[str] = (
    _ES_OPTION_CODES | _NQ_OPTION_CODES | _COMMODITY_OPTION_CODES | _EVENT_CONTRACT_CODES
)

# ---------------------------------------------------------------------------
# Expected commodity option → underlying name mapping (EXCHANGE_CODE_TO_NAME)
# ---------------------------------------------------------------------------
_EXPECTED_COMMODITY_OPT_NAMES: dict[str, str] = {
    "OG": "GOLD",
    "LO": "CRUDE",
    "ON": "NATGAS",
    "HXE": "COPPER",
    "SO": "SILVER",
    "PO": "PLATINUM",
    "PAO": "PALLADIUM",
    "OH": "HEATING_OIL",
    "OB": "GASOLINE",
}


# ---------------------------------------------------------------------------
# Helper: get all CME option defs from the registry
# ---------------------------------------------------------------------------
def _cme_option_defs() -> list[DatabentoInstrumentDef]:
    """Return all CME OPTION defs from TRADFI_DATABENTO_INSTRUMENTS."""
    return [d for d in TRADFI_DATABENTO_INSTRUMENTS if d.venue == "CME" and d.instrument_type == "OPTION"]


# ---------------------------------------------------------------------------
# 1. TRADFI_DATABENTO_INSTRUMENTS contains the expected CME option roots
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_es_options_present_in_universe() -> None:
    """All 11 ES/SP500 option surface roots are in TRADFI_DATABENTO_INSTRUMENTS."""
    cme_opts = _cme_option_defs()
    cme_opt_codes = frozenset(d.exchange_code for d in cme_opts)
    for code in _ES_OPTION_CODES:
        assert code in cme_opt_codes, f"ES option exchange_code '{code}' missing from TRADFI_DATABENTO_INSTRUMENTS"


@pytest.mark.unit
def test_nq_option_present_in_universe() -> None:
    """NQ.OPT (Nasdaq 100 options-on-futures) is in TRADFI_DATABENTO_INSTRUMENTS."""
    cme_opts = _cme_option_defs()
    cme_opt_symbols = frozenset(d.symbol for d in cme_opts)
    assert "NQ.OPT" in cme_opt_symbols, "NQ.OPT missing from TRADFI_DATABENTO_INSTRUMENTS"


@pytest.mark.unit
def test_commodity_options_present_in_universe() -> None:
    """Gold, crude, natgas, copper, silver, platinum, palladium options-on-futures are present."""
    cme_opts = _cme_option_defs()
    cme_opt_codes = frozenset(d.exchange_code for d in cme_opts)
    for code in _COMMODITY_OPTION_CODES:
        assert code in cme_opt_codes, (
            f"Commodity option exchange_code '{code}' missing from TRADFI_DATABENTO_INSTRUMENTS"
        )


@pytest.mark.unit
def test_cme_options_total_count() -> None:
    """CME OPTION defs: ES(11) + NQ(1) + commodity(9) + event_contracts(9) = 30 minimum."""
    cme_opts = _cme_option_defs()
    # 11 ES options + 1 NQ.OPT + 9 commodity + 9 event contracts = 30
    assert len(cme_opts) >= 30, f"Expected >= 30 CME OPTION defs, got {len(cme_opts)}"


@pytest.mark.unit
def test_cme_options_all_glbx_mdp3() -> None:
    """All CME options use GLBX.MDP3 dataset and stype_in='parent'."""
    for d in _cme_option_defs():
        assert d.dataset == "GLBX.MDP3", f"CME option {d.symbol} has wrong dataset: {d.dataset}"
        assert d.stype_in == "parent", f"CME option {d.symbol} has wrong stype_in: {d.stype_in}"


@pytest.mark.unit
def test_cme_options_instrument_type_is_option() -> None:
    """All CME option defs have instrument_type='OPTION'."""
    for d in _cme_option_defs():
        assert d.instrument_type == "OPTION", f"CME option {d.symbol} has wrong instrument_type: {d.instrument_type}"


# ---------------------------------------------------------------------------
# 2. MVP_CME_EXCHANGE_CODES covers the full option surface
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_mvp_cme_exchange_codes_contains_es_options() -> None:
    """MVP_CME_EXCHANGE_CODES includes all ES option surface codes."""
    for code in _ES_OPTION_CODES:
        assert code in MVP_CME_EXCHANGE_CODES, f"ES option code '{code}' missing from MVP_CME_EXCHANGE_CODES"


@pytest.mark.unit
def test_mvp_cme_exchange_codes_contains_nq() -> None:
    """MVP_CME_EXCHANGE_CODES includes NQ (for NQ.FUT + NQ.OPT)."""
    assert "NQ" in MVP_CME_EXCHANGE_CODES


@pytest.mark.unit
def test_mvp_cme_exchange_codes_contains_commodity_options() -> None:
    """MVP_CME_EXCHANGE_CODES includes commodity option-on-futures codes."""
    for code in _COMMODITY_OPTION_CODES:
        assert code in MVP_CME_EXCHANGE_CODES, f"Commodity option code '{code}' missing from MVP_CME_EXCHANGE_CODES"


@pytest.mark.unit
def test_mvp_cme_exchange_codes_contains_commodity_futures() -> None:
    """MVP_CME_EXCHANGE_CODES includes the commodity futures codes (GC, CL, NG, HG, SI, PL, PA)."""
    expected_futures = {"GC", "CL", "NG", "HG", "SI", "PL", "PA"}
    for code in expected_futures:
        assert code in MVP_CME_EXCHANGE_CODES, f"Commodity future code '{code}' missing from MVP_CME_EXCHANGE_CODES"


@pytest.mark.unit
def test_mvp_cme_exchange_codes_contains_event_contracts() -> None:
    """MVP_CME_EXCHANGE_CODES includes MVP CME event contract roots."""
    for code in _EVENT_CONTRACT_CODES:
        assert code in MVP_CME_EXCHANGE_CODES, f"Event contract code '{code}' missing from MVP_CME_EXCHANGE_CODES"


# ---------------------------------------------------------------------------
# 3. EXCHANGE_CODE_TO_NAME covers commodity option roots for product-root resolution
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("code,expected_name", list(_EXPECTED_COMMODITY_OPT_NAMES.items()))
def test_exchange_code_to_name_commodity_options(code: str, expected_name: str) -> None:
    """EXCHANGE_CODE_TO_NAME maps each commodity option root to the correct name."""
    assert code in EXCHANGE_CODE_TO_NAME, f"Commodity option code '{code}' missing from EXCHANGE_CODE_TO_NAME"
    assert EXCHANGE_CODE_TO_NAME[code] == expected_name, (
        f"EXCHANGE_CODE_TO_NAME['{code}'] = {EXCHANGE_CODE_TO_NAME[code]!r}, expected {expected_name!r}"
    )


@pytest.mark.unit
def test_exchange_code_to_name_es_option_roots() -> None:
    """EXCHANGE_CODE_TO_NAME covers EW, E1A–E5A, EOM (ES option weekly/daily roots)."""
    es_option_weekly_codes = {"EW", "EW1", "EW2", "EW4", "E1A", "E2A", "E3A", "E4A", "E5A", "EOM"}
    for code in es_option_weekly_codes:
        assert code in EXCHANGE_CODE_TO_NAME, f"ES option weekly/daily code '{code}' missing from EXCHANGE_CODE_TO_NAME"
        assert EXCHANGE_CODE_TO_NAME[code] == "SP500", (
            f"EXCHANGE_CODE_TO_NAME['{code}'] = {EXCHANGE_CODE_TO_NAME[code]!r}, expected 'SP500'"
        )


# ---------------------------------------------------------------------------
# 4. get_mvp_databento_symbols_for_venue returns option defs
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_get_mvp_databento_symbols_for_cme_includes_es_options() -> None:
    """get_mvp_databento_symbols_for_venue('CME') includes ES option surface defs."""
    mvp_defs = get_mvp_databento_symbols_for_venue("CME")
    mvp_opt_codes = frozenset(d.exchange_code for d in mvp_defs if d.instrument_type == "OPTION")
    for code in _ES_OPTION_CODES:
        assert code in mvp_opt_codes, f"ES option code '{code}' missing from get_mvp_databento_symbols_for_venue('CME')"


@pytest.mark.unit
def test_get_mvp_databento_symbols_for_cme_includes_commodity_options() -> None:
    """get_mvp_databento_symbols_for_venue('CME') includes commodity option-on-futures defs."""
    mvp_defs = get_mvp_databento_symbols_for_venue("CME")
    mvp_opt_codes = frozenset(d.exchange_code for d in mvp_defs if d.instrument_type == "OPTION")
    for code in _COMMODITY_OPTION_CODES:
        assert code in mvp_opt_codes, (
            f"Commodity option code '{code}' missing from get_mvp_databento_symbols_for_venue('CME')"
        )


@pytest.mark.unit
def test_get_mvp_databento_symbols_for_cme_option_count() -> None:
    """get_mvp_databento_symbols_for_venue('CME') returns >=20 OPTION defs.

    Minimum: 11 ES options + 1 NQ + 7 commodity + partial event contracts = >20.
    """
    mvp_defs = get_mvp_databento_symbols_for_venue("CME")
    mvp_options = [d for d in mvp_defs if d.instrument_type == "OPTION"]
    assert len(mvp_options) >= 20, (
        f"Expected >= 20 MVP CME OPTION defs, got {len(mvp_options)}: {sorted(d.symbol for d in mvp_options)}"
    )


@pytest.mark.unit
def test_get_databento_symbols_for_cme_includes_all_options() -> None:
    """get_databento_symbols_for_venue('CME') (no MVP filter) includes all 30+ option defs."""
    all_cme = get_databento_symbols_for_venue("CME")
    all_opts = [d for d in all_cme if d.instrument_type == "OPTION"]
    assert len(all_opts) >= 30, f"Expected >= 30 CME OPTION defs, got {len(all_opts)}"


# ---------------------------------------------------------------------------
# 5. Per-root spot-checks: symbol/venue/asset_group correctness
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "symbol,expected_base_asset,expected_asset_group",
    [
        ("OG.OPT", "GOLD", "commodity"),
        ("LO.OPT", "CRUDE", "commodity"),
        ("ON.OPT", "NATGAS", "commodity"),
        ("HXE.OPT", "COPPER", "commodity"),
        ("SO.OPT", "SILVER", "commodity"),
        ("PO.OPT", "PLATINUM", "commodity"),
        ("PAO.OPT", "PALLADIUM", "commodity"),
        ("NQ.OPT", "NASDAQ100", "equity"),
        ("ES.OPT", "SP500", "equity"),
        ("EW.OPT", "SP500", "equity"),
        ("E1A.OPT", "SP500", "equity"),
        ("EOM.OPT", "SP500", "equity"),
    ],
)
def test_cme_option_def_fields(symbol: str, expected_base_asset: str, expected_asset_group: str) -> None:
    """Each CME option def has correct venue, base_asset, asset_group."""
    matching = [d for d in TRADFI_DATABENTO_INSTRUMENTS if d.symbol == symbol]
    assert len(matching) == 1, f"Expected exactly 1 def for symbol '{symbol}', found {len(matching)}"
    d = matching[0]
    assert d.venue == "CME", f"{symbol}: wrong venue {d.venue!r}"
    assert d.instrument_type == "OPTION", f"{symbol}: wrong instrument_type {d.instrument_type!r}"
    assert d.dataset == "GLBX.MDP3", f"{symbol}: wrong dataset {d.dataset!r}"
    assert d.stype_in == "parent", f"{symbol}: wrong stype_in {d.stype_in!r}"
    assert d.base_asset == expected_base_asset, (
        f"{symbol}: wrong base_asset {d.base_asset!r}, expected {expected_base_asset!r}"
    )
    assert d.asset_group == expected_asset_group, (
        f"{symbol}: wrong asset_group {d.asset_group!r}, expected {expected_asset_group!r}"
    )
