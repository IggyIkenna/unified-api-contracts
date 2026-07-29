"""M2 source-mode capability registry + M8 cadence + M9 mock — Phase 0.1.

Asserts only the LOAD-BEARING facts (completeness + batch-for-all + the
operator-stated live/replay facts + mock semantics), so the DRAFT live/replay
flags for the uncertain sources can change freely on per-source ratification
without breaking CI. SSOT plan:
``pipeline_mode_source_batch_live_replay_standardisation_2026_06_05.md`` (M2/M8/M9).
"""

from __future__ import annotations

import pytest

from unified_api_contracts import (
    SOURCE_MODE_CAPABILITY,
    Cadence,
    Mode,
    PipelineMode,
    is_live,
    is_replay,
    mode_of,
    modes_for,
    modes_for_source,
    pipeline_mode_for_source,
    source_string_for,
    source_supports,
    sources_supporting,
)
from unified_api_contracts.canonical.crosscutting.source_priority import (
    BATCH_CAPABLE_CEFI_VENUES,
    CEFI_LIVE_VENUES,
    COMPUTED_SOURCES,
    SOURCE_PRIORITY,
)

MOCK = "mock"

# The ratified source-mode capability matrix — row-for-row from
# ``plans/audit/results/source_mode_capability_matrix_2026_06_07.md`` (incl. its
# "CORRECTED MODEL"). This is the test-side SSOT: SOURCE_MODE_CAPABILITY must
# equal it EXACTLY. (CeFi per-venue live/replay sources are added in the next unit.)
_B = frozenset({Mode.BATCH})
_BR = frozenset({Mode.BATCH, Mode.REPLAY})
_BLR = frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY})
EXPECTED_SOURCE_MODE_CAPABILITY: dict[str, frozenset[Mode]] = {
    # CeFi
    "tardis": _B,
    # TradFi
    "databento": _BLR,
    # "massive" (= Polygon.io) removed 2026-07-19 — routing dropped (Databento is the
    # tradfi batch SoT). The PipelineMode.BATCH_/LIVE_/REPLAY_MASSIVE members are kept
    # for historical batch_massive/ object recognition until the gated GCS purge, so
    # massive is now the transitional enum-without-capability case (see
    # test_no_live_or_replay_member_for_a_non_capable_source).
    "yahoo": _B,
    # "barchart" retired 2026-06-24 (VIX 15m → VX futures via databento)
    "eia": _BR,
    # FRED/ECB/OFR — public REST macro/rate/CDS-spread archives, no live/WS leg.
    # Added 2026-07-29 per the round-3 TRADFI
    # gcs_path_resolution_centralization_audit_2026_07_28.md finding.
    "fred": _B,
    "ecb": _B,
    "ofr": _B,
    # DeFi
    # hyperliquid (unified vendor) is in the CeFi-venue block below with _BLR — it is
    # the ONE CeFi venue that is also a DeFi batch source (R4 2026-06-07). The
    # transport-glued ``hyperliquid_rest`` key is retired.
    "onchain_rpc": _BLR,
    "solana_rpc": _BLR,
    "helius_rpc": _BLR,
    "onchain_subgraph": _BLR,
    "chainlink": _BLR,
    "pyth_hermes": _BLR,
    # AAVE on-chain oracle (AaveOracle.getAssetPrice) — added 2026-07-21
    # (lst_rate_honest_coverage plan Phase 1). BATCH-only: only BATCH_AAVE
    # exists in PipelineMode today.
    "aave": _B,
    # DefiLlama historical price-ratio proxy (solana_lst_archival.py Tier-4
    # fallback) — added 2026-07-26 (defi_satellite_ao_dispatch_batch1 lst_rates
    # sub-item (a)). BATCH-only: only BATCH_DEFILLAMA exists in PipelineMode.
    "defillama": _B,
    # Prediction
    "polymarket_clob": _BLR,
    "polymarket_gamma_api": _B,
    "kalshi": _BLR,
    # Sports — odds_api is the first LIVE sports source (polling live-odds stream,
    # the odds_api_ws WSFeedConnector → Live==Batch sports archetype); the rest stay
    # batch+replay until a live source lands for each.
    "api_football": _BR,
    "footystats": _BR,
    "odds_api": _BLR,
    "understat": _BR,
    "transfermarkt": _BR,
    "soccer_football_info": _BR,
    "open_meteo": _BR,
    # Internal service sources
    "instruments_service": _BLR,
    "mdps_odds_horizon_bucket": _BLR,
    "execution_service": _BLR,
    "strategy_service": _BLR,
    "features_onchain_service": _BLR,
    "cross_instrument": _BLR,
    "greeks_service": _BLR,
    "mtds_microstructure": _BLR,
    # CeFi per-venue live/replay sources (NOT batch — Tardis is the CeFi archive),
    # EXCEPT hyperliquid which is ALSO the DeFi perp_funding/solana_defi batch source
    # (REST candleSnapshot) → {BATCH, LIVE, REPLAY} (the unified vendor, R4).
    "binance": frozenset({Mode.LIVE, Mode.REPLAY}),
    "okx": frozenset({Mode.LIVE, Mode.REPLAY}),
    # deribit is ALSO the self-archiving batch source for (cefi, volatility_index)
    # — the public DVOL-history REST endpoint, no creds (vol_dvol_backtestable_
    # engines_2026_07_13.md) — a BATCH_CAPABLE_CEFI_VENUES exception like
    # hyperliquid/aster/extended, even though every OTHER CeFi data_type it
    # serves is still live/replay-only (tardis is those data_types' batch archive).
    "deribit": _BLR,
    "kraken": frozenset({Mode.LIVE, Mode.REPLAY}),
    "hyperliquid": _BLR,
    "bybit": frozenset({Mode.LIVE}),
    # aster self-archives funding/premiumIndex over a historical REST range → _BLR
    # (perp_funding_data_semantics_and_cadence_2026_06_16.md). Like hyperliquid, it is
    # a BATCH_CAPABLE_CEFI_VENUES exception.
    "aster": _BLR,
    # Kalshi-perp (CFTC crypto perps, launched 2026-05-29): public-read REST + WS live.
    # Self-archives trade tape + funding_rates → {BATCH, LIVE, REPLAY}.
    "kalshi_perp": _BLR,
    # Polymarket-perp (CFTC crypto perps, launched 2026-04-21):
    # BLOCKED-UPSTREAM-OUTAGE (DNS NXDOMAIN 2026-06-21). {BATCH, LIVE} until verified.
    "polymarket_perp": frozenset({Mode.BATCH, Mode.LIVE}),
    # Extended (EXTENDED-STARKNET CeFi on-chain perp CLOB, api.starknet.extended.exchange):
    # self-archiving native REST → {BATCH, LIVE, REPLAY}. BATCH_CAPABLE_CEFI_VENUES exception.
    "extended": _BLR,
    # LIGHTER-ZKSYNC native REST /candles (mainnet.zkln.elliot.ai) self-archives ohlcv_1m only
    # → BATCH-only (_B). Its trades/book/derivative_ticker + live capture use the Tardis archive
    # (from 2026-04-17), so no LIVE/REPLAY member.
    "lighter_api": _B,
    # "pacifica" source removed 2026-07-16 (operator ruling: all Solana perp
    # DEXes dropped except Jupiter, not integrated).
}


def _all_external_sources() -> set[str]:
    srcs: set[str] = set()
    for priority_list in SOURCE_PRIORITY.values():
        srcs.update(priority_list)
    return srcs - set(COMPUTED_SOURCES)


# ---------------------------------------------------------------------------
# Completeness + the certain fact: every external source is batch-capable
# ---------------------------------------------------------------------------


def test_every_external_source_has_a_capability_entry() -> None:
    """No external SOURCE_PRIORITY source may be unclassified (closed-set)."""
    missing = _all_external_sources() - set(SOURCE_MODE_CAPABILITY)
    assert not missing, f"sources missing a capability entry: {sorted(missing)}"


def test_every_non_venue_capability_source_is_batch_capable() -> None:
    """BATCH is the round-trip-derivable floor for every ARCHIVE source. CeFi venue
    sources are the exception — they serve only live/replay (CeFi batch = tardis)."""
    for src, modes in SOURCE_MODE_CAPABILITY.items():
        if src in CEFI_LIVE_VENUES:
            continue
        assert Mode.BATCH in modes, f"{src} must be batch-capable"


def test_cefi_venues_are_not_batch_capable() -> None:
    """CeFi venue sources serve live/replay only — Tardis is the CeFi batch source.
    Exception: hyperliquid (BATCH_CAPABLE_CEFI_VENUES) is ALSO the DeFi batch source."""
    for venue in CEFI_LIVE_VENUES:
        assert venue in SOURCE_MODE_CAPABILITY, f"{venue} must have a capability entry"
        if venue in BATCH_CAPABLE_CEFI_VENUES:
            assert source_supports(venue, Mode.BATCH), f"{venue} is the batch-capable venue exception"
            continue
        assert not source_supports(venue, Mode.BATCH), f"{venue} must NOT be batch (batch = tardis)"


def test_capability_keys_are_real_sources() -> None:
    """No typo'd / phantom source in the registry — every key is an external
    SOURCE_PRIORITY source, an internal computed/service emitter, or a CeFi venue."""
    stray = set(SOURCE_MODE_CAPABILITY) - _all_external_sources() - set(COMPUTED_SOURCES) - set(CEFI_LIVE_VENUES)
    assert not stray, f"capability registry has unrecognised sources: {sorted(stray)}"


# ---------------------------------------------------------------------------
# Operator-stated facts (load-bearing — these encode real decisions)
# ---------------------------------------------------------------------------


def test_chain_rpcs_are_replay_capable() -> None:
    """DeFi chain RPCs are deterministic ⇒ fully replayable (operator-stated)."""
    for src in ("onchain_rpc", "solana_rpc", "helius_rpc"):
        assert source_supports(src, Mode.REPLAY), f"{src} should be replay-capable"


def test_tardis_is_batch_only() -> None:
    """Ratified 2026-06-07 (matrix R1 + CORRECTED MODEL): Tardis is the CeFi BATCH
    (T+1 archive) source ONLY. The academic licence blocks replay, and CeFi
    live/replay come from the EXCHANGES (the per-venue ``live_<venue>`` sources),
    not Tardis."""
    assert modes_for_source("tardis") == frozenset({Mode.BATCH})
    assert not source_supports("tardis", Mode.LIVE)
    assert not source_supports("tardis", Mode.REPLAY)


def test_databento_is_live_and_replay_capable() -> None:
    """Operator 2026-06-05 + vendor-doc check: databento streams live AND supports
    intraday replay (Live-API 24h intraday replay; Historical API is 24h-embargoed).
    (massive was the other tradfi live/replay vendor — routing removed 2026-07-19, so
    it no longer carries a capability row; see the EXPECTED matrix note.)"""
    assert source_supports("databento", Mode.LIVE)
    assert source_supports("databento", Mode.REPLAY)


def test_odds_api_is_the_first_live_sports_source() -> None:
    """odds_api (The Odds API) is the FIRST live sports source — a polling live-odds
    stream (the ``odds_api_ws`` WSFeedConnector) makes the Live==Batch sports
    archetype real (operator-directed 2026-06-21). The other sports vendors stay
    batch-only-for-live until a live source lands for each."""
    assert source_supports("odds_api", Mode.LIVE)
    for src in ("api_football", "footystats", "understat"):
        assert not source_supports(src, Mode.LIVE)


# ---------------------------------------------------------------------------
# Helpers + mock + enums
# ---------------------------------------------------------------------------


def test_sources_supporting_replay_is_nonempty_and_subset() -> None:
    replayers = sources_supporting(Mode.REPLAY)
    assert "onchain_rpc" in replayers
    assert replayers <= set(SOURCE_MODE_CAPABILITY)


def test_unregistered_source_defaults_to_batch_only() -> None:
    assert modes_for_source("totally_new_vendor") == frozenset({Mode.BATCH})


def test_mock_source_supports_all_modes() -> None:
    """M9 — a mock fixture can stand in for any mode (dev-tier only)."""
    assert modes_for_source(MOCK) == frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY})


def test_mode_of_maps_pipeline_mode_to_reconciliation_class() -> None:
    assert mode_of(PipelineMode.BATCH_DATABENTO) is Mode.BATCH
    assert mode_of(PipelineMode.LIVE_BINANCE) is Mode.LIVE


def test_cadence_values_are_the_agreed_set() -> None:
    assert {c.value for c in Cadence} == {
        "one_off_backfill",
        "t1_daily",
        "scheduled_recurring",
        "continuous_live",
        "recovery_replay",
    }


# ---------------------------------------------------------------------------
# M2 (b) — SOURCE_MODE_CAPABILITY matches the ratified matrix row-for-row
# ---------------------------------------------------------------------------


def test_source_mode_capability_matches_ratified_matrix_exactly() -> None:
    """The registry must equal the ratified matrix row-for-row — incl. tardis={batch}
    (CeFi live/replay from exchanges) and eia/sports={batch,replay}."""
    assert SOURCE_MODE_CAPABILITY == EXPECTED_SOURCE_MODE_CAPABILITY


def test_eia_is_replay_capable_no_live() -> None:
    """EIA weekly series is re-fetchable by date (replay) but has no live stream."""
    assert modes_for_source("eia") == frozenset({Mode.BATCH, Mode.REPLAY})


def test_sports_sources_are_replay_capable() -> None:
    """Sports vendors are replay-capable (historical fetch by date/season)."""
    sports_sources = (
        "api_football",
        "footystats",
        "odds_api",
        "understat",
        "transfermarkt",
        "soccer_football_info",
        "open_meteo",
    )
    for src in sports_sources:
        assert source_supports(src, Mode.REPLAY), f"{src} should be replay-capable"


def test_internal_service_sources_are_full_service_mode() -> None:
    """Internal service emitters run batch=live symmetry; re-run = replay."""
    for src in (
        "instruments_service",
        "mdps_odds_horizon_bucket",
        "execution_service",
        "strategy_service",
        "features_onchain_service",
        "cross_instrument",
        "greeks_service",
    ):
        assert modes_for_source(src) == frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY})


# ---------------------------------------------------------------------------
# M1 (a)/(d) — enum ⟺ capability consistency (a LIVE_/REPLAY_ member exists
# iff the source's capability set contains that mode)
# ---------------------------------------------------------------------------


def test_every_capability_live_or_replay_source_has_its_enum_member() -> None:
    """(a) Every source whose matrix row has LIVE / REPLAY has the matching member."""
    for src, modes in SOURCE_MODE_CAPABILITY.items():
        if Mode.LIVE in modes:
            assert pipeline_mode_for_source(src, Mode.LIVE).value == f"live_{src}"
        if Mode.REPLAY in modes:
            assert pipeline_mode_for_source(src, Mode.REPLAY).value == f"replay_{src}"


# Enum members intentionally RETAINED without a SOURCE_MODE_CAPABILITY row — the
# transitional state until a gated GCS purge removes the historical objects that still
# carry the pipeline_mode value. ``massive`` routing was dropped 2026-07-19 (Databento
# is the tradfi batch SoT) but ``batch_massive/`` / ``live_massive/`` objects still
# exist, so LIVE_/REPLAY_/BATCH_MASSIVE stay for reader/phantom-audit recognition. Drop
# after the purge (tradfi_canonical_path_migration_design_2026_07_19.md § Massive removal).
_LEGACY_ENUM_SOURCES_PENDING_PURGE: frozenset[str] = frozenset({"massive"})


def test_no_live_or_replay_member_for_a_non_capable_source() -> None:
    """(d) No ``live_<source>`` / ``replay_<source>`` member exists for a source whose
    matrix row lacks that mode (e.g. tardis replay, yahoo/barchart live+replay).

    Exemption: the ``_LEGACY_ENUM_SOURCES_PENDING_PURGE`` transitional sources keep
    their enum members (for on-disk object recognition) after their capability row was
    removed — the intended state until the gated GCS purge, not a permanent alias."""
    for member in PipelineMode:
        src = source_string_for(member)
        assert src is not None
        if src in _LEGACY_ENUM_SOURCES_PENDING_PURGE:
            continue  # enum kept for on-disk recognition; capability removed until purge
        if is_live(member):
            assert source_supports(src, Mode.LIVE), f"{member.value} has no LIVE capability for {src!r}"
        elif is_replay(member):
            assert source_supports(src, Mode.REPLAY), f"{member.value} has no REPLAY capability for {src!r}"


# ---------------------------------------------------------------------------
# M1 (c) — source_string_for(pm) == source round-trips for batch + live + replay
# ---------------------------------------------------------------------------


def test_source_string_round_trips_for_every_mode() -> None:
    """(c) For every (source, mode) the capability registry declares, the enum
    member round-trips both ways: pipeline_mode_for_source(src, mode) → member and
    source_string_for(member) → src."""
    for src, modes in SOURCE_MODE_CAPABILITY.items():
        for mode in modes:
            member = pipeline_mode_for_source(src, mode)
            assert member.value == f"{mode.value}_{src}"
            assert source_string_for(member) == src
            assert mode_of(member) is mode


def test_pipeline_mode_for_source_defaults_to_batch() -> None:
    """The default mode keeps existing batch callers unchanged."""
    assert pipeline_mode_for_source("tardis") is PipelineMode.BATCH_TARDIS
    assert pipeline_mode_for_source("databento") is PipelineMode.BATCH_DATABENTO


def test_pipeline_mode_for_source_raises_for_unsupported_mode() -> None:
    """A source that does not support a mode has no member → ValueError."""
    with pytest.raises(ValueError, match="does not support that mode|No PipelineMode"):
        _ = pipeline_mode_for_source("tardis", Mode.LIVE)  # tardis is batch-only
    with pytest.raises(ValueError, match="does not support that mode|No PipelineMode"):
        _ = pipeline_mode_for_source("yahoo", Mode.REPLAY)  # yahoo is batch-only


def test_source_aware_live_member_has_concrete_source() -> None:
    """Every live member maps to a concrete source string."""
    assert source_string_for(PipelineMode.LIVE_BINANCE) == "binance"
    assert is_live(PipelineMode.LIVE_BINANCE)


# ---------------------------------------------------------------------------
# M2/M3 — CeFi per-venue live/replay sources
# ---------------------------------------------------------------------------


def test_cefi_replay_venues_are_live_and_replay() -> None:
    """binance/okx/kraken re-fetch a same-day window via REST (live+replay,
    no batch — CeFi batch = tardis). hyperliquid/deribit are live+replay too but
    ALSO batch (unified-vendor exceptions) → asserted as a superset, not
    exact-equality."""
    for venue in ("binance", "okx", "kraken"):
        assert modes_for_source(venue) == frozenset({Mode.LIVE, Mode.REPLAY})
        assert pipeline_mode_for_source(venue, Mode.LIVE).value == f"live_{venue}"
        assert pipeline_mode_for_source(venue, Mode.REPLAY).value == f"replay_{venue}"
    # hyperliquid: live + replay (+ batch), the unified vendor exception.
    assert {Mode.LIVE, Mode.REPLAY} <= modes_for_source("hyperliquid")
    assert pipeline_mode_for_source("hyperliquid", Mode.LIVE).value == "live_hyperliquid"
    assert pipeline_mode_for_source("hyperliquid", Mode.REPLAY).value == "replay_hyperliquid"
    # deribit: live + replay (+ batch, for volatility_index only) — the
    # vol_dvol_backtestable_engines_2026_07_13.md exception.
    assert {Mode.LIVE, Mode.REPLAY} <= modes_for_source("deribit")
    assert pipeline_mode_for_source("deribit", Mode.LIVE).value == "live_deribit"
    assert pipeline_mode_for_source("deribit", Mode.REPLAY).value == "replay_deribit"


def test_bybit_is_live_only_replay_absent() -> None:
    """(b) Bybit (public REST recent-only) is LIVE-only — replay ABSENT (a fact: its
    live-downtime gaps wait for batch T+1), so no REPLAY_BYBIT member exists."""
    assert modes_for_source("bybit") == frozenset({Mode.LIVE})
    assert source_supports("bybit", Mode.LIVE)
    assert not source_supports("bybit", Mode.REPLAY)
    with pytest.raises(ValueError, match="does not support that mode|No PipelineMode"):
        _ = pipeline_mode_for_source("bybit", Mode.REPLAY)


def test_aster_self_archives_all_three_modes() -> None:
    """Aster (reclassified CeFi on-chain CLOB) is a UNIFIED vendor like hyperliquid:
    its native fapi.asterdex.com funding/premiumIndex REST is a HISTORICAL time-range
    endpoint (verified 2026-06-16, perp_funding_data_semantics_and_cadence_2026_06_16),
    so it SELF-ARCHIVES → {batch, live, replay}, batch_aster/live_aster/replay_aster all
    resolve, and it is a BATCH_CAPABLE_CEFI_VENUES exception (NOT Tardis-archived)."""
    assert modes_for_source("aster") == frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY})
    assert "aster" in BATCH_CAPABLE_CEFI_VENUES
    for mode in (Mode.BATCH, Mode.LIVE, Mode.REPLAY):
        assert pipeline_mode_for_source("aster", mode).value == f"{mode.value}_aster"


def test_cefi_venues_have_no_batch_member() -> None:
    """No ``batch_<venue>`` member — the venue is not a batch/archive source. Exception:
    hyperliquid IS batch-capable (the unified DeFi+CeFi vendor) → BATCH_HYPERLIQUID."""
    for venue in CEFI_LIVE_VENUES:
        if venue in BATCH_CAPABLE_CEFI_VENUES:
            assert pipeline_mode_for_source(venue, Mode.BATCH).value == f"batch_{venue}"
            continue
        with pytest.raises(ValueError, match="does not support that mode|No PipelineMode"):
            _ = pipeline_mode_for_source(venue, Mode.BATCH)


def test_cefi_venue_pipeline_modes_round_trip() -> None:
    """source_string_for(live_<venue>) → venue, for every CeFi venue."""
    assert source_string_for(PipelineMode.LIVE_BINANCE) == "binance"
    assert source_string_for(PipelineMode.REPLAY_HYPERLIQUID) == "hyperliquid"
    assert source_string_for(PipelineMode.LIVE_BYBIT) == "bybit"
    assert source_string_for(PipelineMode.LIVE_ASTER) == "aster"


# ---------------------------------------------------------------------------
# M2-REFINEMENT — modes_for(source, data_type): per-(source, data_type) keying
# derived from SourceCapability.operations (ws ⇒ LIVE, REST ⇒ BATCH; REPLAY = the
# live-gap-fill tier, drops with LIVE). SSOT plan § M2-REFINEMENT.
# ---------------------------------------------------------------------------


def test_modes_for_hyperliquid_trades_includes_live() -> None:
    """hyperliquid STREAMS trades (``ws_trades`` op) → LIVE is reachable."""
    assert Mode.LIVE in modes_for("hyperliquid", "trades")


def test_modes_for_hyperliquid_funding_rates_is_batch_only() -> None:
    """hyperliquid only REST-archives funding (no ``ws_funding*`` op) → exactly {BATCH}.

    The over-approximation fix: the coarse per-source set is {BATCH, LIVE, REPLAY},
    but funding_rates has no live (ws) path, so LIVE and its REPLAY gap-fill tier
    drop — leaving the BATCH floor only.
    """
    assert modes_for("hyperliquid", "funding_rates") == frozenset({Mode.BATCH})
    assert modes_for("hyperliquid", "funding_rates") != modes_for_source("hyperliquid")


def test_modes_for_hyperliquid_l2_book_includes_live() -> None:
    """hyperliquid STREAMS the order book (``ws_l2_book`` op) → LIVE reachable."""
    assert Mode.LIVE in modes_for("hyperliquid", "l2_book")


def test_modes_for_live_replay_only_venue_collapses_on_batch_only_data_type() -> None:
    """A live/replay-only venue (binance) serves NO mode for a data_type it doesn't
    declare (funding) — it is not a CeFi batch source (tardis is) and has no ws
    funding op, so it collapses to ``frozenset()`` (honest absence)."""
    assert modes_for("binance", "funding_rates") == frozenset()
    # …but it DOES stream trades (ws_trades) → its full live/replay set survives.
    assert modes_for("binance", "trades") == modes_for_source("binance")


def test_modes_for_never_widens_beyond_coarse() -> None:
    """The refinement only ever NARROWS: modes_for(s, dt) ⊆ modes_for_source(s)."""
    for source in ("hyperliquid", "binance", "deribit", "bybit", "kraken", "tardis", "databento"):
        for data_type in ("trades", "funding_rates", "l2_book", "candles", "no_such_data_type"):
            assert modes_for(source, data_type) <= modes_for_source(source)


def test_modes_for_batch_only_source_is_coarse_unchanged() -> None:
    """A source with no LIVE (tardis) is never refined — its coarse set IS the answer
    for every data_type (no ohlcv-style regression from incomplete op declarations)."""
    for data_type in ("trades", "ohlcv_1m", "funding_rate", "no_such_data_type"):
        assert modes_for("tardis", data_type) == modes_for_source("tardis")


def test_modes_for_non_ws_live_source_is_coarse_unchanged() -> None:
    """A live source that does NOT use the ws/REST op convention (databento vendor
    feed) can't be refined → its coarse {BATCH, LIVE, REPLAY} survives per data_type."""
    assert modes_for("databento", "trades") == modes_for_source("databento")
    assert Mode.REPLAY in modes_for("databento", "trades")


def test_modes_for_mock_is_all_modes() -> None:
    """The mock fixture source stands in for any (source, data_type)."""
    assert modes_for(MOCK, "anything") == frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY})
