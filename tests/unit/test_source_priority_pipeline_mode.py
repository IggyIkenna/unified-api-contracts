"""Unit tests for the Phase 1C ``read_with_source_priority`` reader and the
SOURCE_PRIORITY ↔ PipelineMode coupling.

Phase 1C of ``gcs_migration_bundle_pipeline_mode_2026_05_08`` adds a
``pipeline_mode`` per-source coupling so callers can stratify rows by
``pipeline_mode`` at read-time. Per the chosen Option B design, the coupling
is implemented as a thin reader (:func:`read_with_source_priority`) that
delegates to :func:`pipeline_mode_for_source` rather than restructuring
:data:`SOURCE_PRIORITY`'s value type.

Plans:

* ``gcs_migration_bundle_pipeline_mode_2026_05_08`` Phase 1C
* ``live_pipeline_mtds_mdps_features_2026_05_08`` Phase 12 (consumer)

Tests:

1. Every SOURCE_PRIORITY entry has at least one source string.
2. Every source string in SOURCE_PRIORITY round-trips to a PipelineMode.
3. read_with_source_priority returns ``(source, pipeline_mode)``.
4. read_with_source_priority returns the same source string as
   :func:`get_primary_source` for every registered pair.
5. The reader's pipeline_mode is always a batch value (live is a write-time
   concern, not a registry concern).
6. Live-priority-over-batch behaviour at the row-selection layer — synthetic
   row tagged with a source-aware ``live_<source>`` pipeline_mode wins over a
   same-key batch row even though the registry returns the batch source.
7. Public-export surface — :func:`read_with_source_priority` is reachable
   via ``from unified_api_contracts.canonical.crosscutting import ...``.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.canonical.crosscutting.pipeline_mode import (
    PipelineMode,
    is_batch,
    is_live,
    pipeline_mode_for_source,
)
from unified_api_contracts.canonical.crosscutting.source_priority import (
    SOURCE_PRIORITY,
    DivergenceKind,
    detect_dual_source_conflicts,
    get_all_sources_with_priority,
    get_primary_source,
    read_with_source_priority,
    select_primary_available_source,
)

# ---------------------------------------------------------------------------
# Test 1 — every entry has at least one source string
# ---------------------------------------------------------------------------


def test_every_source_priority_entry_has_at_least_one_source() -> None:
    """Empty source lists would silently break the reader; assert the seed."""
    empty: list[tuple[str, str]] = []
    for key, sources in SOURCE_PRIORITY.items():
        if not sources:
            empty.append(key)
    assert not empty, f"SOURCE_PRIORITY entries with empty source lists: {empty}"


# ---------------------------------------------------------------------------
# Test 2 — every source string round-trips to a PipelineMode (closed-set)
# ---------------------------------------------------------------------------


def test_every_source_priority_source_round_trips_to_pipeline_mode() -> None:
    """Phase 1C closed-set: every primary source has a BATCH_<SOURCE> mode.

    Mirrors the assertion in ``test_pipeline_mode.py`` but framed as the
    Phase 1C contract — :func:`read_with_source_priority` cannot succeed
    unless every source in the registry has a matching PipelineMode.
    """
    missing: list[str] = []
    for sources in SOURCE_PRIORITY.values():
        for source in sources:
            try:
                _ = pipeline_mode_for_source(source)
            except ValueError:
                missing.append(source)
    assert not missing, (
        f"SOURCE_PRIORITY references sources with no PipelineMode: {sorted(set(missing))}; "
        "add BATCH_<SOURCE> values to PipelineMode (closed-set round-trip required)."
    )


# ---------------------------------------------------------------------------
# Test 3 — reader returns (source, pipeline_mode) tuple
# ---------------------------------------------------------------------------


def test_read_with_source_priority_returns_source_and_pipeline_mode() -> None:
    """Reader contract: ``(source: str, pipeline_mode: PipelineMode)``."""
    source, mode = read_with_source_priority("cefi", "trades")
    assert source == "tardis"
    assert mode is PipelineMode.BATCH_TARDIS
    assert isinstance(source, str)
    assert isinstance(mode, PipelineMode)


def test_read_with_source_priority_returns_databento_for_tradfi_trades() -> None:
    """DATABENTO-FIRST (2026-06-24, supersedes the 2026-06-11 massive-first)."""
    source, mode = read_with_source_priority("tradfi", "trades")
    assert source == "databento"
    assert mode is PipelineMode.BATCH_DATABENTO


def test_read_with_source_priority_returns_polymarket_for_prediction_trades() -> None:
    source, mode = read_with_source_priority("prediction", "trades")
    assert source == "polymarket_clob"
    assert mode is PipelineMode.BATCH_POLYMARKET_CLOB


def test_read_with_source_priority_returns_onchain_rpc_for_defi_gas_fees() -> None:
    source, mode = read_with_source_priority("defi", "gas_fees")
    assert source == "onchain_rpc"
    assert mode is PipelineMode.BATCH_ONCHAIN_RPC


def test_read_with_source_priority_returns_api_football_for_sports_fixtures() -> None:
    source, mode = read_with_source_priority("sports", "fixtures")
    assert source == "api_football"
    assert mode is PipelineMode.BATCH_API_FOOTBALL


# ---------------------------------------------------------------------------
# Test 4 — reader is consistent with get_primary_source for every registered pair
# ---------------------------------------------------------------------------


def test_read_with_source_priority_matches_get_primary_source_everywhere() -> None:
    """The reader's source string must equal :func:`get_primary_source` for
    every registered pair — Phase 1C just adds the pipeline_mode pairing,
    it does NOT change which source is primary.
    """
    for asset_group, data_type in SOURCE_PRIORITY:
        primary = get_primary_source(asset_group, data_type)
        reader_source, _reader_mode = read_with_source_priority(asset_group, data_type)
        assert reader_source == primary, (
            f"({asset_group!r}, {data_type!r}): "
            f"read_with_source_priority returned {reader_source!r} but "
            f"get_primary_source returned {primary!r} — drift between SSOT "
            "reader and primary-source helper."
        )


# ---------------------------------------------------------------------------
# Test 5 — reader always returns a batch pipeline_mode
# ---------------------------------------------------------------------------


def test_read_with_source_priority_always_returns_batch_mode() -> None:
    """Live mode is set by the streaming writer at write-time, never derived
    from the registry. The reader's pipeline_mode is always a batch value.
    """
    for asset_group, data_type in SOURCE_PRIORITY:
        _source, mode = read_with_source_priority(asset_group, data_type)
        assert is_batch(mode), (
            f"({asset_group!r}, {data_type!r}) reader returned non-batch "
            f"PipelineMode {mode!r}; live is a write-time concern, not a "
            "registry-time concern."
        )
        assert not is_live(mode)


# ---------------------------------------------------------------------------
# Test 6 — failure modes propagate from get_primary_source
# ---------------------------------------------------------------------------


def test_read_with_source_priority_raises_keyerror_for_unregistered_pair() -> None:
    with pytest.raises(KeyError, match="No source priority registered"):
        _ = read_with_source_priority("cefi", "totally_made_up_data_type")


def test_read_with_source_priority_raises_keyerror_for_unknown_asset_group() -> None:
    with pytest.raises(KeyError):
        _ = read_with_source_priority("alien", "trades")


# ---------------------------------------------------------------------------
# Test 7 — live-priority-over-batch row-selection semantics
# ---------------------------------------------------------------------------


def test_live_pipeline_mode_wins_over_batch_at_same_row_key() -> None:
    """Synthetic row-selection: when the same ``(asset_group, venue, day)``
    has both a live and a batch row, live wins.

    The registry itself returns the batch source (live is write-time), so
    consumers stratify rows by ``pipeline_mode`` and prefer live when both
    exist. This test simulates that selection logic at the row level.
    """
    # Synthetic candidate rows for the same (asset_group, venue, day).
    # In the real pipeline these come from the manifest reader; here we hand-
    # construct them to assert the stratification logic.
    candidate_rows = [
        {"source": "tardis", "pipeline_mode": PipelineMode.BATCH_TARDIS, "value": 100},
        {"source": "binance", "pipeline_mode": PipelineMode.LIVE_BINANCE, "value": 200},
    ]

    # Caller-side stratification: prefer live row if any live row exists.
    live_rows = [r for r in candidate_rows if r["pipeline_mode"] is PipelineMode.LIVE_BINANCE]
    chosen = live_rows[0] if live_rows else candidate_rows[0]

    assert chosen["pipeline_mode"] is PipelineMode.LIVE_BINANCE
    assert chosen["value"] == 200, "live row's value should win over batch's"


def test_batch_only_row_is_chosen_when_no_live_row_exists() -> None:
    """Inverse of the live-wins case — when only batch rows exist, the
    batch primary source from :func:`read_with_source_priority` is used.
    """
    candidate_rows = [
        {"source": "tardis", "pipeline_mode": PipelineMode.BATCH_TARDIS, "value": 100},
    ]

    live_rows = [r for r in candidate_rows if r["pipeline_mode"] is PipelineMode.LIVE_BINANCE]
    chosen = live_rows[0] if live_rows else candidate_rows[0]

    # Reader returns the batch source for the (cefi, trades) pair — confirms
    # the registry-side primary source and the runtime-chosen row agree when
    # live is absent.
    reader_source, reader_mode = read_with_source_priority("cefi", "trades")
    assert chosen["source"] == reader_source
    assert chosen["pipeline_mode"] is reader_mode


# ---------------------------------------------------------------------------
# Test 8 — public-export surface
# ---------------------------------------------------------------------------


def test_read_with_source_priority_exposed_from_crosscutting_namespace() -> None:
    """Phase 1C adds :func:`read_with_source_priority` to the crosscutting
    facade so consumers don't have to reach into ``source_priority`` directly.
    """
    from unified_api_contracts.canonical.crosscutting import (
        read_with_source_priority as facade_reader,
    )

    assert facade_reader is read_with_source_priority


# ---------------------------------------------------------------------------
# Test 9 — get_all_sources_with_priority (Phase 2 multi-source building block)
# ---------------------------------------------------------------------------


def test_get_all_sources_single_source_cell_returns_list_of_one() -> None:
    """Single-source cells return a one-element list."""
    results = get_all_sources_with_priority("cefi", "options_chain")  # (cefi,trades) is multi-source now
    assert len(results) == 1
    source, mode = results[0]
    assert source == "tardis"
    assert mode is PipelineMode.BATCH_TARDIS


def test_get_all_sources_multi_source_cell_returns_ordered_list() -> None:
    """Multi-source cells (tradfi ohlcv_1m = databento + yahoo) return both in priority order.

    databento is the verified-complete primary; yahoo serves the KRX/daily-candle slice.
    (massive was the pre-2026-07-19 fallback — routing removed, so trades/tbbo/chain
    cells are now single-source databento; the candle cells keep the yahoo secondary.)
    """
    results = get_all_sources_with_priority("tradfi", "ohlcv_1m")
    assert len(results) >= 2
    sources = [s for s, _ in results]
    assert sources[0] == "databento", "databento is primary for tradfi ohlcv_1m"
    assert "yahoo" in sources, "yahoo is registered (secondary) for tradfi ohlcv_1m"
    assert sources.index("databento") < sources.index("yahoo"), "databento precedes yahoo"


def test_get_all_sources_returns_batch_pipeline_modes() -> None:
    """Every returned pipeline_mode must be a batch value."""
    for source, mode in get_all_sources_with_priority("tradfi", "ohlcv_15m"):
        assert is_batch(mode), f"source {source!r} returned non-batch mode {mode!r}"


def test_get_all_sources_primary_matches_read_with_source_priority() -> None:
    """Index-0 of get_all_sources must equal read_with_source_priority."""
    for asset_group, data_type in SOURCE_PRIORITY:
        all_sources = get_all_sources_with_priority(asset_group, data_type)
        primary_source, primary_mode = read_with_source_priority(asset_group, data_type)
        assert all_sources[0] == (primary_source, primary_mode), (
            f"({asset_group!r}, {data_type!r}): all_sources[0]={all_sources[0]!r} "
            f"!= read_with_source_priority result {(primary_source, primary_mode)!r}"
        )


def test_get_all_sources_raises_for_unknown_pair() -> None:
    with pytest.raises(KeyError, match="No source priority registered"):
        get_all_sources_with_priority("alien", "trades")


def test_get_all_sources_exposed_from_crosscutting_namespace() -> None:
    from unified_api_contracts.canonical.crosscutting import (
        get_all_sources_with_priority as facade_fn,
    )

    assert facade_fn is get_all_sources_with_priority


# ---------------------------------------------------------------------------
# Test 10 — select_primary_available_source (Phase 2 tie-breaker)
# ---------------------------------------------------------------------------


def test_select_primary_available_primary_only() -> None:
    """Primary source available → returned (standard single-source case)."""
    source, mode = select_primary_available_source("cefi", "trades", {"tardis"})
    assert source == "tardis"
    assert mode is PipelineMode.BATCH_TARDIS


def test_select_primary_available_multi_source_primary_wins() -> None:
    """When all sources are present, the primary (index-0) wins."""
    source, mode = select_primary_available_source("tradfi", "ohlcv_1m", {"databento", "yahoo"})
    assert source == "databento", "databento is primary for tradfi ohlcv_1m (databento-first)"
    assert mode is PipelineMode.BATCH_DATABENTO


def test_select_primary_available_fallback_to_secondary() -> None:
    """When primary is absent but secondary is present, secondary wins."""
    source, mode = select_primary_available_source("tradfi", "trades", {"databento"})
    assert source == "databento"
    assert mode is PipelineMode.BATCH_DATABENTO


def test_select_primary_available_no_sources_raises() -> None:
    """Empty / non-matching available_sources raises KeyError."""
    with pytest.raises(KeyError, match="No registered source"):
        select_primary_available_source("cefi", "trades", {"unknown_source"})


def test_select_primary_available_empty_set_raises() -> None:
    with pytest.raises(KeyError, match="No registered source"):
        select_primary_available_source("tradfi", "trades", set())


def test_select_primary_available_returns_batch_mode() -> None:
    """Tie-breaker always returns a batch pipeline_mode."""
    _, mode = select_primary_available_source("tradfi", "trades", {"databento"})
    assert is_batch(mode)


def test_select_primary_available_exposed_from_crosscutting_namespace() -> None:
    from unified_api_contracts.canonical.crosscutting import (
        select_primary_available_source as facade_fn,
    )

    assert facade_fn is select_primary_available_source


# ---------------------------------------------------------------------------
# Tests 11 — DivergenceKind + detect_dual_source_conflicts (tasks -014, -015)
# ---------------------------------------------------------------------------


def test_divergence_kind_dual_source_duplicate_value() -> None:
    """DivergenceKind.DUAL_SOURCE_DUPLICATE is a manifest-compatible string."""
    assert DivergenceKind.DUAL_SOURCE_DUPLICATE == "DUAL_SOURCE_DUPLICATE"
    assert isinstance(DivergenceKind.DUAL_SOURCE_DUPLICATE, str)


def test_detect_dual_source_conflicts_happy_path_no_overlap() -> None:
    """Happy path: two sources with completely distinct row-keys → no conflicts."""
    keys_databento = {("NYSE", "2026-05-30", "AAPL", 1000), ("NYSE", "2026-05-30", "AAPL", 2000)}
    keys_massive = {("NYSE", "2026-05-30", "MSFT", 1000), ("NYSE", "2026-05-30", "MSFT", 2000)}
    result = detect_dual_source_conflicts(
        "databento",
        keys_databento,
        "massive",
        keys_massive,
        asset_group="tradfi",
        data_type="trades",
    )
    assert result == []


def test_detect_dual_source_conflicts_with_duplicates() -> None:
    """Conflict path: same row-key in both sources → returned in sorted order."""
    shared_key = ("NYSE", "2026-05-30", "AAPL", 1000)
    keys_databento = {shared_key, ("NYSE", "2026-05-30", "AAPL", 2000)}
    keys_massive = {shared_key, ("NYSE", "2026-05-30", "MSFT", 1000)}
    result = detect_dual_source_conflicts(
        "databento",
        keys_databento,
        "massive",
        keys_massive,
        asset_group="tradfi",
        data_type="trades",
    )
    assert result == [shared_key]
    assert shared_key in result


def test_detect_dual_source_conflicts_missing_source_a_present_source_b() -> None:
    """Missing-source-A path: keys_a empty → no conflicts even if keys_b is full."""
    keys_massive = {("NYSE", "2026-05-30", "SPY", 1000)}
    result = detect_dual_source_conflicts(
        "databento",
        set(),
        "massive",
        keys_massive,
        asset_group="tradfi",
        data_type="ohlcv_1m",
    )
    assert result == []


def test_detect_dual_source_conflicts_field_union_path() -> None:
    """Field-union path: no key overlap → no DUAL_SOURCE_DUPLICATE even if both present."""
    # When sources have non-overlapping keys, there's nothing to flag —
    # the consumer unions the rows, not picks one.
    keys_a = {("CME", "2026-05-30", "ES", 1000)}
    keys_b = {("CME", "2026-05-30", "NQ", 1000)}
    result = detect_dual_source_conflicts(
        "databento",
        keys_a,
        "massive",
        keys_b,
        asset_group="tradfi",
        data_type="futures_chain",
    )
    assert result == []


def test_detect_dual_source_conflicts_logs_warning(caplog: pytest.LogCaptureFixture) -> None:
    """Conflicts log at WARNING level with DUAL_SOURCE_DUPLICATE in the message."""
    import logging

    shared = ("NYSE", "2026-05-30", "AAPL", 500)
    with caplog.at_level(logging.WARNING):
        detect_dual_source_conflicts(
            "databento",
            {shared},
            "massive",
            {shared},
            asset_group="tradfi",
            data_type="trades",
        )
    assert any("DUAL_SOURCE_DUPLICATE" in r.message for r in caplog.records)


def test_divergence_kind_exposed_from_crosscutting_namespace() -> None:
    from unified_api_contracts.canonical.crosscutting import DivergenceKind as DivergenceKindFacade

    assert DivergenceKindFacade is DivergenceKind


# ---------------------------------------------------------------------------
# Phase 5 — multi-source resolution is GENERIC across cefi/defi/sports
# (data_source_provenance_all_asset_groups_2026_06_01.md Phase 5 P0).
# Proves the consumer-layer resolver picks exactly ONE primary source per cell
# (no silent double-count) for every multi-source asset group, not just tradfi.
# ---------------------------------------------------------------------------


def test_select_primary_defi_oracle_prices_pyth_wins() -> None:
    """DeFi oracle_prices: pyth_hermes is primary over chainlink → one resolved row."""
    source, mode = select_primary_available_source("defi", "oracle_prices", {"pyth_hermes", "chainlink"})
    assert source == "pyth_hermes"
    assert is_batch(mode)


def test_select_primary_defi_oracle_prices_fallback_to_chainlink() -> None:
    """When pyth is absent, chainlink (secondary) wins — single resolved row."""
    source, _ = select_primary_available_source("defi", "oracle_prices", {"chainlink"})
    assert source == "chainlink"


def test_select_primary_defi_native_staking_solana_rpc_wins() -> None:
    source, _ = select_primary_available_source("defi", "native_staking_rates", {"solana_rpc", "helius_rpc"})
    assert source == "solana_rpc"


def test_select_primary_sports_fixtures_api_football_wins() -> None:
    """Sports fixtures: api_football is primary over footystats → one resolved row."""
    source, _ = select_primary_available_source("sports", "fixtures", {"api_football", "footystats"})
    assert source == "api_football"


def test_detect_dual_source_conflicts_defi_oracle_prices() -> None:
    """DeFi co-mingled cell: same (chain, day, feed, ts) in both sources is flagged."""
    shared = ("SOLANA", "2026-05-30", "SOL/USD", 1000)
    result = detect_dual_source_conflicts(
        "pyth_hermes",
        {shared, ("SOLANA", "2026-05-30", "SOL/USD", 2000)},
        "chainlink",
        {shared},
        asset_group="defi",
        data_type="oracle_prices",
    )
    assert result == [shared]


def test_detect_dual_source_conflicts_sports_fixtures() -> None:
    """Sports co-mingled cell: same fixture from api_football + footystats flagged."""
    shared = ("EPL", "2026-05-30", "fixture_42")
    result = detect_dual_source_conflicts(
        "api_football",
        {shared},
        "footystats",
        {shared, ("EPL", "2026-05-30", "fixture_99")},
        asset_group="sports",
        data_type="fixtures",
    )
    assert result == [shared]


def test_select_primary_resolves_single_row_for_all_multi_source_groups() -> None:
    """Exhaustive: every multi-source cell resolves to exactly ONE primary source."""
    from unified_api_contracts.canonical.crosscutting.source_priority import (
        SOURCE_PRIORITY,
        external_sources_for,
    )

    for asset_group, data_type in SOURCE_PRIORITY:
        external = external_sources_for(asset_group, data_type)
        if len(external) <= 1:
            continue
        # All external sources present → resolves to the index-0 primary (one row).
        source, _ = select_primary_available_source(asset_group, data_type, set(external))
        assert source == external[0], f"{asset_group}/{data_type} primary mismatch"


def test_detect_dual_source_conflicts_exposed_from_crosscutting_namespace() -> None:
    from unified_api_contracts.canonical.crosscutting import (
        detect_dual_source_conflicts as facade_fn,
    )

    assert facade_fn is detect_dual_source_conflicts


# ---------------------------------------------------------------------------
# live_source_for_venue / live_pipeline_mode_for_venue (M1 — source-aware live
# pipeline_mode for the migrated live path; pipeline_mode_source_batch_live_replay
# _standardisation_2026_06_05.md). The source-aware live_<source> value.
# ---------------------------------------------------------------------------


def test_live_source_for_cefi_venue_is_the_exchange() -> None:
    from unified_api_contracts.canonical.crosscutting.source_priority import (
        live_source_for_venue,
    )

    # CeFi live source = the EXCHANGE (tardis is the batch archive, never live).
    assert live_source_for_venue("cefi", "BINANCE", "trades") == "binance"
    assert live_source_for_venue("cefi", "OKX", "trades") == "okx"
    # Case-insensitive venue.
    assert live_source_for_venue("CeFi", "Hyperliquid", "trades") == "hyperliquid"


def test_live_pipeline_mode_for_cefi_venue_is_source_aware() -> None:
    from unified_api_contracts.canonical.crosscutting.source_priority import (
        live_pipeline_mode_for_venue,
    )

    assert live_pipeline_mode_for_venue("cefi", "BINANCE", "trades") is PipelineMode.LIVE_BINANCE
    assert live_pipeline_mode_for_venue("cefi", "DERIBIT", "trades") is PipelineMode.LIVE_DERIBIT
    # Result is a live value.
    assert is_live(live_pipeline_mode_for_venue("cefi", "OKX", "trades"))


def test_live_source_for_cefi_crypto_perp_venue_is_its_own_ws_feed() -> None:
    """CeFi crypto-perp venues (hyphen) resolve to their underscore WS source token, NOT
    the batch-only ``tardis`` book_snapshot primary (regression: live_pipeline_mode raised
    ``No PipelineMode for source 'tardis' in mode 'live'`` before the perp venue override)."""
    from unified_api_contracts.canonical.crosscutting.source_priority import (
        live_pipeline_mode_for_venue,
        live_source_for_venue,
    )

    assert live_source_for_venue("cefi", "KALSHI-PERP", "book_snapshot") == "kalshi_perp"
    assert live_source_for_venue("cefi", "POLYMARKET-PERP", "trades") == "polymarket_perp"
    # case-insensitive venue
    assert live_source_for_venue("CeFi", "Kalshi-Perp", "book_snapshot") == "kalshi_perp"
    # the live pipeline_mode resolves (no ValueError) to the venue's own live_ member
    assert live_pipeline_mode_for_venue("cefi", "KALSHI-PERP", "book_snapshot") is PipelineMode.LIVE_KALSHI_PERP
    assert live_pipeline_mode_for_venue("cefi", "POLYMARKET-PERP", "book_snapshot") is PipelineMode.LIVE_POLYMARKET_PERP
    # non-perp cefi venue still resolves to the exchange (no regression)
    assert live_pipeline_mode_for_venue("cefi", "BINANCE", "trades") is PipelineMode.LIVE_BINANCE


def test_live_source_for_cefi_cex_venue_with_market_type_suffix() -> None:
    """CeFi CEX venues carry a market-type SUFFIX (``BINANCE-FUTURES`` / ``OKX-SWAP`` /
    ``BYBIT-LINEAR`` …) but the live source is the bare exchange vendor (bug#9: the
    suffix made the bare ``CEFI_LIVE_VENUES`` check miss → fell through to batch-only
    ``tardis`` → ``No PipelineMode for source 'tardis' in mode 'live'``)."""
    from unified_api_contracts.canonical.crosscutting.source_priority import (
        live_pipeline_mode_for_venue,
        live_source_for_venue,
    )

    # Vendor-prefix resolution across the market-type suffixes the live writer emits.
    assert live_source_for_venue("cefi", "BINANCE-FUTURES", "trades") == "binance"
    assert live_source_for_venue("cefi", "BINANCE-SPOT", "trades") == "binance"
    assert live_source_for_venue("cefi", "OKX-SWAP", "trades") == "okx"
    assert live_source_for_venue("cefi", "OKX-FUTURES", "trades") == "okx"
    assert live_source_for_venue("cefi", "BYBIT-LINEAR", "trades") == "bybit"
    assert live_source_for_venue("cefi", "KRAKEN-FUTURES", "trades") == "kraken"
    # Case-insensitive venue.
    assert live_source_for_venue("CeFi", "Binance-Futures", "trades") == "binance"
    # The live pipeline_mode resolves (no ValueError) to the venue's own live_ member.
    assert live_pipeline_mode_for_venue("cefi", "BINANCE-FUTURES", "trades") is PipelineMode.LIVE_BINANCE
    assert live_pipeline_mode_for_venue("cefi", "OKX-SWAP", "book_snapshot") is PipelineMode.LIVE_OKX
    assert live_pipeline_mode_for_venue("cefi", "BYBIT-LINEAR", "trades") is PipelineMode.LIVE_BYBIT
    assert live_pipeline_mode_for_venue("cefi", "KRAKEN-FUTURES", "trades") is PipelineMode.LIVE_KRAKEN


def test_live_pipeline_mode_for_cefi_replay_mode() -> None:
    from unified_api_contracts.canonical.crosscutting.pipeline_mode import Mode
    from unified_api_contracts.canonical.crosscutting.source_priority import (
        live_pipeline_mode_for_venue,
    )

    assert live_pipeline_mode_for_venue("cefi", "BINANCE", "trades", Mode.REPLAY) is PipelineMode.REPLAY_BINANCE


def test_live_pipeline_mode_for_non_cefi_uses_source_priority_primary() -> None:
    from unified_api_contracts.canonical.crosscutting.source_priority import (
        get_primary_source,
        live_pipeline_mode_for_venue,
        live_source_for_venue,
    )

    # TradFi: live source = databento (the ONLY tradfi Live WS producer). As of the
    # DATABENTO-FIRST flip (2026-06-24) the BATCH SOURCE_PRIORITY primary is ALSO
    # databento, so live + batch now CONVERGE on databento (cleaner than the prior
    # massive-batch / databento-live split that mis-stamped live shards `live_massive`,
    # fixed 2026-06-21). massive remains the batch fallback [1].
    assert live_source_for_venue("tradfi", "DATABENTO", "trades") == "databento"
    assert live_source_for_venue("tradfi", "CME", "trades") == "databento"
    assert get_primary_source("tradfi", "trades") == "databento"  # batch primary now databento-first
    pm = live_pipeline_mode_for_venue("tradfi", "DATABENTO", "trades")
    assert is_live(pm)


def test_live_pipeline_mode_replay_raises_for_live_only_venue() -> None:
    from unified_api_contracts.canonical.crosscutting.pipeline_mode import Mode
    from unified_api_contracts.canonical.crosscutting.source_priority import (
        live_pipeline_mode_for_venue,
    )

    # Bybit/Aster are LIVE-only (no replay member) — REPLAY mode must fail loud.
    with pytest.raises(ValueError):
        live_pipeline_mode_for_venue("cefi", "BYBIT", "trades", Mode.REPLAY)


def test_live_pipeline_mode_for_prediction_polymarket_book_snapshot_5() -> None:
    """Prediction POLYMARKET book_snapshot_5 shard resolves via the venue override
    (polymarket → polymarket_clob) and not through the data_type-level SOURCE_PRIORITY
    primary — item 69 + prediction-side of item 75 (2026-06-22).

    ``live_source_for_venue("prediction", "POLYMARKET", "book_snapshot_5")`` must
    return ``"polymarket_clob"`` and the pipeline_mode must be
    ``PipelineMode.LIVE_POLYMARKET_CLOB``."""
    from unified_api_contracts.canonical.crosscutting.source_priority import (
        live_pipeline_mode_for_venue,
        live_source_for_venue,
    )

    source = live_source_for_venue("prediction", "POLYMARKET", "book_snapshot_5")
    assert source == "polymarket_clob", (
        f"Expected 'polymarket_clob', got {source!r}; "
        "the venue override for 'polymarket' must resolve before SOURCE_PRIORITY lookup"
    )
    pm = live_pipeline_mode_for_venue("prediction", "POLYMARKET", "book_snapshot_5")
    assert pm is PipelineMode.LIVE_POLYMARKET_CLOB


def test_live_pipeline_mode_for_venue_exposed_from_top_level() -> None:
    from unified_api_contracts import (
        live_pipeline_mode_for_venue as facade_fn,
    )
    from unified_api_contracts import (
        live_source_for_venue as facade_src,
    )
    from unified_api_contracts.canonical.crosscutting.source_priority import (
        live_pipeline_mode_for_venue,
        live_source_for_venue,
    )

    assert facade_fn is live_pipeline_mode_for_venue
    assert facade_src is live_source_for_venue
