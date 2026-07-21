"""Unit tests for is_canonical / canonical_path_violations (failure class C3).

Round-trips against every ``build_*_partition_path`` output (must ACCEPT) and
rejects the documented non-canonical drift shapes:
  1. ``day-YYYY-MM-DD`` hyphen dir instead of ``day=YYYY-MM-DD``
  2. missing ``pipeline_mode={mode}_{source}/`` (only with require_pipeline_mode)
  3. glued ``VENUE-CHAIN`` venue token / glued ``V{N}`` version
  4. ``asset_group=`` value outside {cefi,defi,tradfi,sports,prediction}
Plan: ``data_pipeline_hardening_self_monitoring_2026_06_22.md`` Phase 3.
"""

from __future__ import annotations

from datetime import date

import pytest

from unified_api_contracts import (
    CanonicalViolationClass,
    InstrumentType,
    build_cefi_partition_path,
    build_defi_partition_path,
    build_prediction_partition_path,
    build_tradfi_partition_path,
    canonical_path_violations,
    canonical_path_violations_classified,
    is_canonical,
    is_canonical_instrument_id,
)

_DAY = date(2026, 4, 17)


# ---------------------------------------------------------------------------
# Round-trip: builder output is canonical.
# ---------------------------------------------------------------------------


def test_defi_builder_output_is_canonical() -> None:
    for pipeline_mode in (None, "batch_eigenlayer", "live_hyperliquid"):
        path = build_defi_partition_path(
            venue="AAVE_V3",
            chain="ETHEREUM",
            instrument_type=InstrumentType.A_TOKEN,
            data_type="lending_indices",
            day=_DAY,
            file_name="aUSDC.parquet",
            pipeline_mode=pipeline_mode,
        )
        assert is_canonical(path), canonical_path_violations(path)


def test_cefi_builder_output_is_canonical() -> None:
    # ``file_name`` is the FULL canonical instrument_id — the stem is now part of the
    # canonicality answer (ID_FORM class), so a wire stem like ``BTC-PERPETUAL.parquet``
    # would (correctly) fail this round-trip.
    path = build_cefi_partition_path(
        venue="BINANCE",
        instrument_type=InstrumentType.PERPETUAL,
        data_type="derivative_ticker",
        day=_DAY,
        file_name="BINANCE:PERPETUAL:BTC-USDT.parquet",
    )
    assert is_canonical(path), canonical_path_violations(path)


def test_tradfi_builder_output_is_canonical() -> None:
    # Single-instrument shard: canonical filename is the FULL instrument_id
    # (the v6 tradfi rules reject a bare-symbol / ticks.parquet single).
    for pipeline_mode in (None, "batch_databento"):
        single = build_tradfi_partition_path(
            venue="NYSE",
            instrument_type=InstrumentType.EQUITY,
            data_type="ohlcv_1m",
            day=_DAY,
            file_name="NYSE:EQUITY:ABBV-USD.parquet",
            pipeline_mode=pipeline_mode,
        )
        assert is_canonical(single), canonical_path_violations(single)
    # Chain bundle: canonical tail is underlying=/quote=/margin=/ticks.parquet.
    chain = build_tradfi_partition_path(
        venue="CME",
        instrument_type="futures_chain",
        data_type="trades",
        day=_DAY,
        file_name="ticks.parquet",
        pipeline_mode="batch_databento",
        underlying="SP500",
        quote_asset="USD",
        margin_type="linear",
    )
    assert is_canonical(chain), canonical_path_violations(chain)


def test_prediction_builder_output_is_canonical() -> None:
    path = build_prediction_partition_path(
        venue="POLYMARKET",
        condition_id="0xabc123",
        data_type="trades",
        day=_DAY,
    )
    assert is_canonical(path), canonical_path_violations(path)


# ---------------------------------------------------------------------------
# Reject the 4 documented bad shapes.
# ---------------------------------------------------------------------------

_GOOD = (
    "raw_tick_data/by_date/day=2026-04-17/asset_group=defi/"
    "venue=AAVE_V3/chain=ETHEREUM/instrument_type=a_token/"
    "data_type=lending_indices/aUSDC.parquet"
)


def test_good_baseline_is_canonical() -> None:
    assert is_canonical(_GOOD)


def test_reject_hyphen_day_dir() -> None:
    bad = _GOOD.replace("day=2026-04-17", "day-2026-04-17")
    assert not is_canonical(bad)
    assert any("hyphen day" in v for v in canonical_path_violations(bad))


def test_reject_glued_venue_chain() -> None:
    bad = _GOOD.replace("venue=AAVE_V3/chain=ETHEREUM", "venue=AAVE_V3-ETHEREUM")
    assert not is_canonical(bad)
    assert any("VENUE-CHAIN" in v for v in canonical_path_violations(bad))


def test_cefi_hyphenated_venue_is_canonical() -> None:
    # Regression (2026-06-23): a hyphen in a CEFI venue is a legitimate venue-name
    # token (BINANCE-FUTURES / OKX-FUTURES / BYBIT-FUTURES / KRAKEN-FUTURES — the
    # canonical cefi venue tokens), NOT the defi PROTOCOL-CHAIN glue. The VENUE-CHAIN
    # guard is defi-gated, so these MUST pass. The un-gated guard crashed every cefi
    # LIVE producer at the writer boundary (live_tick_blob_path) and silently froze the
    # deribit/hyperliquid/binance live VMs for hours.
    for venue in ("BINANCE-FUTURES", "OKX-FUTURES", "BYBIT-FUTURES", "KRAKEN-FUTURES"):
        path = build_cefi_partition_path(
            venue=venue,
            instrument_type=InstrumentType.PERPETUAL,
            data_type="trades",
            day=_DAY,
            file_name=f"{venue}:PERPETUAL:BTC-USDT.parquet",
        )
        violations = canonical_path_violations(path)
        assert is_canonical(path), violations
        assert not any("VENUE-CHAIN" in v for v in violations)


def test_reject_glued_version() -> None:
    bad = _GOOD.replace("venue=AAVE_V3", "venue=AAVEV3")
    assert not is_canonical(bad)
    assert any("V{N}" in v for v in canonical_path_violations(bad))


def test_underscore_version_is_canonical() -> None:
    # AAVE_V3 (canonical) must NOT trip the glued-version detector.
    assert is_canonical(_GOOD)
    assert canonical_path_violations(_GOOD) == []


@pytest.mark.parametrize("bad_ag", ["crypto", "equities", "DeFi", "options"])
def test_reject_out_of_set_asset_group(bad_ag: str) -> None:
    bad = _GOOD.replace("asset_group=defi", f"asset_group={bad_ag}")
    assert not is_canonical(bad)
    assert any("outside the canonical set" in v for v in canonical_path_violations(bad))


def test_reject_missing_prefix() -> None:
    assert not is_canonical("day=2026-04-17/asset_group=defi/venue=X/data_type=y/f.parquet")


# ---------------------------------------------------------------------------
# pipeline_mode: bare accepted by default; required-but-missing opt-in rejects.
# ---------------------------------------------------------------------------


def test_bare_path_accepted_by_default() -> None:
    assert is_canonical(_GOOD)


def test_missing_pipeline_mode_rejected_when_required() -> None:
    assert not is_canonical(_GOOD, require_pipeline_mode=True)
    viols = canonical_path_violations(_GOOD, require_pipeline_mode=True)
    assert any("pipeline_mode=" in v for v in viols)


def test_pipeline_mode_present_satisfies_requirement() -> None:
    with_pm = _GOOD.replace("day=2026-04-17/asset_group=", "day=2026-04-17/pipeline_mode=batch_eigenlayer/asset_group=")
    assert is_canonical(with_pm, require_pipeline_mode=True)


def test_malformed_pipeline_mode_rejected() -> None:
    # pipeline_mode present but not the canonical {mode}_{source} form.
    bad = _GOOD.replace("day=2026-04-17/asset_group=", "day=2026-04-17/pipeline_mode=batch/asset_group=")
    assert not is_canonical(bad)
    assert any("pipeline_mode value" in v for v in canonical_path_violations(bad))


# ---------------------------------------------------------------------------
# TradFi garbage-``underlying=`` guard (chain + combo bundles).
# tradfi_canonical_path_migration_design_2026_07_19.md categories A/B/C.
# ---------------------------------------------------------------------------


def _tradfi_chain_path(underlying: str, *, instrument_type: str = "futures_chain") -> str:
    return (
        "raw_tick_data/by_date/day=2026-04-17/pipeline_mode=batch_databento/asset_group=tradfi/"
        f"venue=CME/instrument_type={instrument_type}/data_type=trades/"
        f"underlying={underlying}/quote=USD/margin=linear/ticks.parquet"
    )


def _tradfi_combo_path(underlying: str) -> str:
    return (
        "raw_tick_data/by_date/day=2026-04-17/pipeline_mode=batch_databento/asset_group=tradfi/"
        f"venue=CME/instrument_type=combo/data_type=trades/underlying={underlying}/ticks.parquet"
    )


@pytest.mark.parametrize("underlying", ["SP500", "MES", "XAB", "XAU", "WTI-BZ", "NAT-GAS-HH"])
def test_tradfi_chain_real_root_or_named_spread_is_canonical(underlying: str) -> None:
    # C real roots (incl. the newly-resolved MES/XA*) + B named-spreads PASS.
    path = _tradfi_chain_path(underlying)
    assert is_canonical(path, require_pipeline_mode=True), canonical_path_violations(path, require_pipeline_mode=True)


@pytest.mark.parametrize("underlying", ["12", "13", "23"])
def test_tradfi_chain_numeric_underlying_rejected(underlying: str) -> None:
    # A numeric CBOE globex GROUP code — quarantine, never fake-canonicalize.
    path = _tradfi_chain_path(underlying)
    violations = canonical_path_violations(path, require_pipeline_mode=True)
    assert any("is not a real product root" in v for v in violations), violations


@pytest.mark.parametrize("underlying", ["GN", "VT", "IC", "3W"])
def test_tradfi_combo_opaque_ud_underlying_rejected(underlying: str) -> None:
    # A opaque CBOE user-defined leg code (combo bundle) — quarantine.
    path = _tradfi_combo_path(underlying)
    violations = canonical_path_violations(path, require_pipeline_mode=True)
    assert any("is not a real product root" in v for v in violations), violations


def test_tradfi_combo_named_spread_and_recovered_root_pass() -> None:
    # B named-spread + D recovered root-qualified UD (UD:ZN: → UST-10Y) combos PASS.
    for underlying in ("WTI-BZ", "UST-10Y", "SP500-NASDAQ100"):
        path = _tradfi_combo_path(underlying)
        assert is_canonical(path, require_pipeline_mode=True), canonical_path_violations(
            path, require_pipeline_mode=True
        )


@pytest.mark.parametrize("underlying", ["BTC", "ETH", "MBT", "MET"])
def test_tradfi_chain_cme_crypto_futures_root_is_canonical(underlying: str) -> None:
    # CME crypto FUTURES roots (operator 2026-07-21) — BTC/ETH full-size + MBT/MET
    # micro. Added to the MVP tradfi FUTURE download scope but were quarantined
    # write-time because the recognised-root registry did not list them. The
    # write-guard now accepts ``venue=CME/instrument_type=futures_chain/
    # underlying=BTC`` as canonical (canonical id ``CME:FUTURE:BTC-USD@LIN-…``).
    path = _tradfi_chain_path(underlying)
    assert is_canonical(path, require_pipeline_mode=True), canonical_path_violations(path, require_pipeline_mode=True)


@pytest.mark.parametrize("underlying", ["BTCF3-BTCG3", "ETHF3-ETHG3", "MBTF3-MBTG3"])
def test_tradfi_opaque_crypto_calendar_spread_leg_bundle_rejected(underlying: str) -> None:
    # Precision guard: recognising the single crypto roots must NOT whitelist an
    # opaque ``-``-joined dated-leg bundle (``BTCF3-BTCG3``) — those have no
    # resolvable single root and MUST stay quarantined (the crypto root is only a
    # substring of the leg token). Covers both the chain and combo bundle shapes.
    for path in (_tradfi_chain_path(underlying), _tradfi_combo_path(underlying)):
        violations = canonical_path_violations(path, require_pipeline_mode=True)
        assert any("is not a real product root" in v for v in violations), violations


# ---------------------------------------------------------------------------
# ID-FORM oracle — the filename stem (regression: the oracle was BLIND to it).
#
# Before 2026-07-20 ``canonical_path_violations`` dropped the filename
# (``partition_segments = segments[:-1]``) before validating, so a CeFi corpus
# of raw wire stems measured 0 violations == CANONICAL. ~811,200 objects
# carried wire instrument_ids while the machine oracle reported the surface
# clean. SSOT:
# ``plans/active/issues/canonical_path_oracle_blind_to_filename_stem_2026_07_20.md``.
# ---------------------------------------------------------------------------

_CEFI_TPL = (
    "raw_tick_data/by_date/day=2026-05-01/pipeline_mode=batch_tardis/asset_group=cefi/"
    "venue={venue}/instrument_type={itype}/data_type={dtype}/{file_name}"
)


def _cefi_path(file_name: str, *, itype: str = "perpetual", venue: str = "BITFINEX-FUTURES") -> str:
    return _CEFI_TPL.format(venue=venue, itype=itype, dtype="trades", file_name=file_name)


@pytest.mark.parametrize(
    "file_name",
    [
        "ADAF0:USTF0.parquet",  # raw Bitfinex wire symbol
        "AVAX_USDC-PERPETUAL.parquet",  # raw Deribit wire symbol
        "BTCUSD.parquet",  # bare symbol
        "BITFINEX-FUTURES:PERPETUAL:ADAF0:USTF0.parquet",  # DOUBLE-WRAPPED catalogue miss
    ],
)
def test_cefi_non_canonical_stem_is_flagged_by_default(file_name: str) -> None:
    """A wire / double-wrapped stem must NOT come back canonical from the DEFAULT call."""
    path = _cefi_path(file_name)
    violations = canonical_path_violations(path)
    assert any("is not a canonical instrument_id" in v for v in violations), violations
    assert not is_canonical(path)


@pytest.mark.parametrize(
    "file_name",
    [
        "BITFINEX-FUTURES:PERPETUAL:ADA-USDT.parquet",
        "HYPERLIQUID:PERPETUAL:BTC-USD@LIN.parquet",
        "DERIBIT:FUTURE:BTC-USD-20260327.parquet",
        "DERIBIT:OPTION:BTC-USD-20260327-65000-C.parquet",
        "DERIBIT:COMBO:BTC-PERP-CALENDAR.parquet",
        "BINANCE-FUTURES:SPOT_PAIR:BTC-USDT.parquet",
    ],
)
def test_cefi_canonical_stem_is_clean(file_name: str) -> None:
    path = _cefi_path(file_name)
    assert is_canonical(path), canonical_path_violations(path)


@pytest.mark.parametrize("itype", ["options_chain", "futures_chain"])
def test_cefi_chain_ticks_parquet_is_never_flagged(itype: str) -> None:
    """Chain shards legitimately have NO per-instrument stem — must not be flagged."""
    path = _cefi_path("underlying=BTC/ticks.parquet", itype=itype)
    assert is_canonical(path), canonical_path_violations(path)


def test_symbol_less_ticks_parquet_fan_in_is_never_flagged() -> None:
    """The symbol-less ``ticks.parquet`` fan-in (prediction book_snapshot_5) is canonical."""
    path = _cefi_path("ticks.parquet")
    assert is_canonical(path), canonical_path_violations(path)


@pytest.mark.parametrize(
    "path",
    [
        # DeFi ids route through the passthrough builder (pool addresses / aTokens) —
        # the VENUE:ITYPE:BASE-QUOTE grammar does not apply, so no false violations.
        "raw_tick_data/by_date/day=2026-05-01/pipeline_mode=batch_thegraph/asset_group=defi/"
        "venue=AAVE_V3/chain=ETHEREUM/instrument_type=a_token/data_type=lending_indices/aUSDC.parquet",
        # Prediction shards are named for the venue condition_id.
        "raw_tick_data/by_date/day=2026-05-01/asset_group=prediction/venue=POLYMARKET/"
        "instrument_type=binary_option/data_type=trades/0xabc123.parquet",
    ],
)
def test_id_form_check_does_not_apply_to_defi_or_prediction(path: str) -> None:
    assert is_canonical(path), canonical_path_violations(path)


def test_violation_classes_partition_the_default_answer() -> None:
    """STRUCTURAL + ID_FORM must sum to the default (unfiltered) answer."""
    path = _cefi_path("ADAF0:USTF0.parquet").replace("day=2026-05-01", "day-2026-05-01")
    default = canonical_path_violations(path)
    structural = canonical_path_violations(path, violation_classes=frozenset({CanonicalViolationClass.STRUCTURAL}))
    id_form = canonical_path_violations(path, violation_classes=frozenset({CanonicalViolationClass.ID_FORM}))
    assert structural, "legacy day- prefix must be a STRUCTURAL violation"
    assert id_form, "wire stem must be an ID_FORM violation"
    assert sorted(default) == sorted([*structural, *id_form])


def test_structural_only_preserves_pre_change_behaviour_for_cefi() -> None:
    """The STRUCTURAL pin the MTDS write-guards use must accept a wire stem.

    This pins the contract the two raising CeFi callers
    (``live_tick_blob_path`` / ``_microstructure_blob_path``) rely on: turning
    ID_FORM on for them without first fixing ``_sanitize_symbol`` would raise on
    EVERY live cefi write.
    """
    path = _cefi_path("ADAF0:USTF0.parquet")
    assert canonical_path_violations(path, violation_classes=frozenset({CanonicalViolationClass.STRUCTURAL})) == []


def test_classified_view_reports_every_class() -> None:
    result = canonical_path_violations_classified(_cefi_path("ADAF0:USTF0.parquet"))
    assert set(result) == set(CanonicalViolationClass)
    assert result[CanonicalViolationClass.STRUCTURAL] == []
    assert result[CanonicalViolationClass.ID_FORM]


@pytest.mark.parametrize(
    ("candidate", "expected"),
    [
        ("BITFINEX-FUTURES:PERPETUAL:ADA-USDT", True),
        ("HYPERLIQUID:PERPETUAL:BTC-USD@LIN", True),
        ("DERIBIT:COMBO:anything-here", True),
        ("ADAF0:USTF0", False),
        ("BITFINEX-FUTURES:PERPETUAL:ADAF0:USTF0", False),
        ("BTCUSD", False),
        ("", False),
    ],
)
def test_is_canonical_instrument_id(candidate: str, expected: bool) -> None:
    assert is_canonical_instrument_id(candidate) is expected


def test_tradfi_single_instrument_stem_rules_still_fire() -> None:
    """The pre-existing tradfi stem rules must be unchanged (now classed ID_FORM)."""
    base = (
        "raw_tick_data/by_date/day=2026-05-01/pipeline_mode=batch_databento/asset_group=tradfi/"
        "venue=XNAS/instrument_type=equity/data_type=trades/{file_name}"
    )
    bare = canonical_path_violations(base.format(file_name="AAPL.parquet"), require_pipeline_mode=True)
    assert any("got a bare symbol" in v for v in bare), bare
    fan_in = canonical_path_violations(base.format(file_name="ticks.parquet"), require_pipeline_mode=True)
    assert any("ticks.parquet' fan-in" in v for v in fan_in), fan_in
    ok = base.format(file_name="XNAS:EQUITY:AAPL-USD.parquet")
    assert is_canonical(ok, require_pipeline_mode=True), canonical_path_violations(ok, require_pipeline_mode=True)
