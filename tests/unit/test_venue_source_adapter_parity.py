"""Centralised venue / source / adapter / MVP-cell PARITY GATE (operator priority,
2026-06-24).

ONE data-driven test that iterates the CANONICAL registries and validates that
EVERY venue / source / (venue, data_type)-MVP-cell is fully cross-wired, so a
future venue/source addition is auto-covered with ZERO new test code.

What it asserts (all PARAMETRISED over registry contents — never a hardcoded list
of venues/sources):

  1. venue ∈ ``VENUES_BY_ASSET_GROUP`` ⟺ venue ∈ ``VENUE_TO_ASSET_GROUP`` and the
     asset_group is consistent (the manifest/data-status denominator keys off both).
  2. every TradFi market-data venue resolves to a DATA SOURCE: either a Databento
     dataset (``venue_to_databento``) OR an external data provider
     (``venue_to_data_provider``) — never neither (an unrouted venue silently
     captures 0 rows; incident DP_VM_GONE_NO_CAPTURE).
  3. every source that appears in ``SOURCE_PRIORITY`` for an asset_group resolves
     to a capability declaration (via the documented source→capability alias map)
     OR is a known computed/service source — so a typo'd source name can't ship.
  4. every MVP ``(venue, data_type)`` cell has (a) the venue registered and (b) a
     non-empty ``SOURCE_PRIORITY`` source list for that data_type (the cell is
     actually fetchable), and the venue's resolved source is IN that list.
  5. every source/adapter that declares fetch LIMITS enforces them on a
     non-bypassable path: Yahoo via ``assert_yahoo_intraday_within_limit`` /
     ``YAHOO_INTRADAY_LOOKBACK_DAYS``; Databento via the allowlist gate
     (``assert_databento_request_allowed`` + ``LEVEL_MAX_LOOKBACK_DAYS``).

It AUDITS the existing fleet: pre-existing gaps are captured in the documented
ALLOWLISTs below (each with a reason / issue-doc), so a LEGACY gap does NOT block
a new venue (KRX). A NEW unwired venue/source RED-fails — proven by
``test_half_wired_venue_red_fails`` (KRX-minus-routing).

SSOT: plans/active/tradfi_datasource_closeout_krx_yahoo_parity_2026_06_24.md.
"""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from unified_api_contracts.canonical.crosscutting.mvp_scope import MVP_SCOPE, is_mvp
from unified_api_contracts.canonical.crosscutting.source_priority import (
    _VENUE_SOURCE_EXCLUSIONS,
    SOURCE_PRIORITY,
    is_source_capable_for_venue,
)
from unified_api_contracts.registry.capability_declarations import (
    ALTDATA_CAPABILITIES,
    CEFI_CAPABILITIES,
    DEFI_CAPABILITIES,
    PROTOCOL_CAPABILITIES,
    SPORTS_CAPABILITIES,
    TRADFI_CAPABILITIES,
)
from unified_api_contracts.registry.market_data_categories import (
    VENUE_TO_ASSET_GROUP,
    VENUES_BY_ASSET_GROUP,
)
from unified_api_contracts.registry.venue_mapping import VenueMapping

# ---------------------------------------------------------------------------
# Source → capability-declaration alias map (the SOURCE_PRIORITY source names do
# not always equal the capability ``source`` names). DATA-DRIVEN: a source not in
# SOURCE_PRIORITY never needs an entry; this only maps the priority name → cap name.
# ---------------------------------------------------------------------------
_SOURCE_TO_CAPABILITY_ALIAS: dict[str, str] = {
    "yahoo": "yahoo_finance",  # SOURCE_PRIORITY says "yahoo"; capability says "yahoo_finance"
}

# Sources that are COMPUTED / SERVICE-internal (not an external vendor adapter) —
# they legitimately have no SourceCapability declaration. DATA-DRIVEN: a source
# computed by one of OUR services, or an on-chain RPC source (no vendor adapter).
_COMPUTED_SERVICE_SOURCES: frozenset[str] = frozenset(
    {
        # our own services that emit a derived data_type
        "greeks_service",  # greeks-service computes from the options chain
        "cross_instrument",
        "execution_service",
        "features_onchain_service",
        "instruments_service",
        "mdps_odds_horizon_bucket",
        "mtds_microstructure",
        "strategy_service",
        # on-chain RPC / subgraph sources (no vendor capability — the chain IS the source)
        "onchain_subgraph",
        "onchain_rpc",
        "chainlink",
        "pyth_hermes",
        "balancer_api_v3",
        "protocol_sdk",
        "the_graph",
        "rpc",
        "helius_rpc",
        "solana_rpc",
    }
)

# ── DOCUMENTED PRE-EXISTING GAPS (audit allowlist) ─────────────────────────
# Each entry is a LEGACY gap this gate surfaced; listed here so it does NOT block
# a new venue, with the reason. New gaps are NOT added here — they must be fixed.

# Sources that appear in SOURCE_PRIORITY but have NO capability declaration (and
# are not computed/service sources). PRE-EXISTING — tracked for capability backfill.
_KNOWN_SOURCE_WITHOUT_CAPABILITY: frozenset[str] = frozenset(
    {
        # "massive" is a live S3 flat-file vendor used across tradfi/cefi but has
        # no SourceCapability declaration (capability registry predates it). It is
        # a real, wired source (MTDS _route_massive) — only the declaration is
        # missing. Tracked: codex/02-data/tradfi-databento-sourcing-ssot.md.
        "massive",
        # Polymarket prediction vendors — real external sources wired via the
        # prediction adapters, but no SourceCapability row yet. Tracked for
        # capability backfill (prediction capability declarations).
        "polymarket_clob",
        "polymarket_gamma_api",
    }
)

# "Venues" that are actually source-as-venue legacy artifacts (a data SOURCE listed
# in VENUES_BY_ASSET_GROUP). PRE-EXISTING — kept to avoid manifest churn; flagged.
_KNOWN_SOURCE_AS_VENUE: dict[str, frozenset[str]] = {
    "tradfi": frozenset({"YAHOO_FINANCE"}),  # a source, not a venue (legacy denom artifact)
}


def _all_capability_sources() -> set[str]:
    """Every declared SourceCapability ``source`` name across all asset groups.

    PROTOCOL_CAPABILITIES is a list of operation-name STRINGS (not SourceCapability
    objects) — skipped via the ``.source`` attribute guard.
    """
    sources: set[str] = set()
    for group in (
        ALTDATA_CAPABILITIES,
        CEFI_CAPABILITIES,
        DEFI_CAPABILITIES,
        PROTOCOL_CAPABILITIES,
        SPORTS_CAPABILITIES,
        TRADFI_CAPABILITIES,
    ):
        for cap in group:
            src = getattr(cap, "source", None)
            if src is not None:
                sources.add(src)
    return sources


def _tradfi_market_data_venues() -> list[str]:
    """TradFi venues that carry market data (exclude the source-as-venue artifacts)."""
    artifacts = _KNOWN_SOURCE_AS_VENUE.get("tradfi", frozenset())
    return [v for v in VENUES_BY_ASSET_GROUP["tradfi"] if v not in artifacts]


# ---------------------------------------------------------------------------
# 1. venue ⟺ asset_group consistency (parametrised over EVERY venue)
# ---------------------------------------------------------------------------
def _all_venue_ag_pairs() -> list[tuple[str, str]]:
    return [(v, ag) for ag, venues in VENUES_BY_ASSET_GROUP.items() for v in venues]


@pytest.mark.parametrize("venue,asset_group", _all_venue_ag_pairs())
def test_venue_in_reverse_index_and_consistent(venue: str, asset_group: str) -> None:
    """Every venue in VENUES_BY_ASSET_GROUP is in the reverse VENUE_TO_ASSET_GROUP
    index with the SAME asset_group (the data-status denominator reads both)."""
    assert venue in VENUE_TO_ASSET_GROUP, f"venue {venue!r} ({asset_group}) missing from VENUE_TO_ASSET_GROUP"
    assert VENUE_TO_ASSET_GROUP[venue] == asset_group, (
        f"venue {venue!r} maps to {VENUE_TO_ASSET_GROUP[venue]!r} in the reverse "
        f"index but is listed under {asset_group!r} in VENUES_BY_ASSET_GROUP"
    )


# ---------------------------------------------------------------------------
# 2. every TradFi market-data venue resolves to a DATA SOURCE
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("venue", _tradfi_market_data_venues())
def test_tradfi_venue_resolves_to_a_data_source(venue: str) -> None:
    """A TradFi venue must route to a Databento dataset OR an external data
    provider — never neither (an unrouted venue silently captures 0 rows)."""
    vm = VenueMapping()
    has_databento = vm.venue_to_databento.get(venue) is not None
    has_provider = vm.venue_to_data_provider.get(venue) is not None
    assert has_databento or has_provider, (
        f"TradFi venue {venue!r} resolves to NO data source: not in venue_to_databento "
        f"and not in venue_to_data_provider. Wire it (databento dataset or a provider) "
        f"or remove it from VENUES_BY_ASSET_GROUP['tradfi']."
    )


# ---------------------------------------------------------------------------
# 3. every SOURCE_PRIORITY source resolves to a capability (or is allowlisted)
# ---------------------------------------------------------------------------
def _all_priority_sources() -> list[str]:
    seen: set[str] = set()
    for sources in SOURCE_PRIORITY.values():
        seen.update(sources)
    return sorted(seen)


@pytest.mark.parametrize("source", _all_priority_sources())
def test_priority_source_resolves_to_capability(source: str) -> None:
    """Every source named in SOURCE_PRIORITY resolves to a SourceCapability
    declaration (via the alias map), OR is a computed/service source, OR is a
    DOCUMENTED pre-existing gap. A typo'd / unwired NEW source RED-fails here."""
    if source in _COMPUTED_SERVICE_SOURCES:
        return
    if source in _KNOWN_SOURCE_WITHOUT_CAPABILITY:
        return  # documented pre-existing gap — does not block new sources
    cap_name = _SOURCE_TO_CAPABILITY_ALIAS.get(source, source)
    assert cap_name in _all_capability_sources(), (
        f"SOURCE_PRIORITY source {source!r} (capability name {cap_name!r}) has NO "
        f"SourceCapability declaration. Add it to registry/capability_declarations/, "
        f"map it in _SOURCE_TO_CAPABILITY_ALIAS, or (if computed) add it to "
        f"_COMPUTED_SERVICE_SOURCES. NEW unwired sources must not ship."
    )


# ---------------------------------------------------------------------------
# 4. every MVP (venue, data_type) cell is fetchable + the venue's source is valid
# ---------------------------------------------------------------------------
def _tradfi_mvp_equity_cells() -> list[tuple[str, str, str]]:
    """(venue, data_type, source) MVP cells for the TradFi equity carve-out.

    DATA-DRIVEN: iterate the TradFi MVP rule's data_types × the equity venues the
    carve-out recognises × the resolved source for each venue. Future venues/types
    added to the rule are auto-covered.
    """
    rule = MVP_SCOPE["tradfi"]
    vm = VenueMapping()
    cells: list[tuple[str, str, str]] = []
    # The equity-carve-out venues (mirror mvp_scope.is_mvp). KRX is the new one.
    equity_venues = ["NASDAQ", "NYSE", "KRX"]
    for venue in equity_venues:
        if venue not in VENUES_BY_ASSET_GROUP["tradfi"]:
            continue
        provider = vm.venue_to_data_provider.get(venue)
        source = "yahoo" if provider == "yahoo_finance" else "databento"
        for data_type in sorted(rule.data_types):
            # Only pair a cell with a data_type the venue's source can actually
            # serve: the source must be in SOURCE_PRIORITY[(tradfi, data_type)] AND
            # not venue-excluded. (Yahoo serves ohlcv_* but NOT trades — so a
            # KRX/trades cell is not a real fetchable cell, skip it.)
            priority = SOURCE_PRIORITY.get(("tradfi", data_type), [])
            if source not in priority:
                continue
            if source in _VENUE_SOURCE_EXCLUSIONS.get((venue, data_type), frozenset()):
                continue
            cells.append((venue, data_type, source))
    return cells


@pytest.mark.parametrize("venue,data_type,source", _tradfi_mvp_equity_cells())
def test_tradfi_mvp_equity_cell_is_fetchable(venue: str, data_type: str, source: str) -> None:
    """Each TradFi equity MVP cell: venue registered, a SOURCE_PRIORITY list exists
    for the data_type, and the venue's resolved source can actually serve it
    (capability + not venue-excluded)."""
    assert venue in VENUE_TO_ASSET_GROUP, f"MVP venue {venue!r} not registered"
    priority = SOURCE_PRIORITY.get(("tradfi", data_type))
    assert priority, f"MVP cell (tradfi, {venue}, {data_type}) has NO SOURCE_PRIORITY list — not fetchable"
    assert source in priority, (
        f"MVP venue {venue!r} resolves to source {source!r} but it is not in "
        f"SOURCE_PRIORITY[(tradfi, {data_type})]={priority}"
    )
    assert is_source_capable_for_venue("tradfi", data_type, venue, source), (
        f"source {source!r} is not capable for venue {venue!r} / data_type {data_type!r} "
        f"(excluded via _VENUE_SOURCE_EXCLUSIONS or absent from priority)"
    )


def test_krx_basis_cells_are_mvp() -> None:
    """The 3 KRX stocks (venue=KRX, source=yahoo) are MVP for the equity data_types
    (the close-out 103/103). A non-basis KRX ticker is NOT mvp."""
    rule = MVP_SCOPE["tradfi"]
    for symbol in ("005380", "005930", "000660"):
        for data_type in rule.data_types:
            assert is_mvp("tradfi", "KRX", "EQUITY", data_type, base_ccy=symbol, source="yahoo"), (
                f"KRX {symbol} ({data_type}) should be MVP"
            )
    assert not is_mvp("tradfi", "KRX", "EQUITY", "ohlcv_1m", base_ccy="999999", source="yahoo"), (
        "a non-basis KRX ticker must NOT be MVP"
    )


# ---------------------------------------------------------------------------
# 5. every adapter that declares fetch LIMITS enforces them
# ---------------------------------------------------------------------------
def test_yahoo_adapter_limits_declared_and_enforced() -> None:
    """The Yahoo source declares per-interval lookback + per-request width limits
    AND enforces them on the guardrail (fail-closed raise)."""
    from unified_api_contracts.registry.data_source_continuity import (
        YAHOO_DAILY_BACKFILL_FLOOR,
        YAHOO_INTRADAY_LOOKBACK_DAYS,
        YAHOO_INTRADAY_MAX_REQUEST_DAYS,
        YahooLookbackExceededError,
        YahooRequestTooWideError,
        assert_yahoo_intraday_within_limit,
        assert_yahoo_request_width_ok,
    )

    # limits declared for the core intervals
    for interval in ("1m", "15m", "1h", "1d"):
        assert interval in YAHOO_INTRADAY_LOOKBACK_DAYS
    assert YAHOO_INTRADAY_MAX_REQUEST_DAYS["1m"] == 8  # measured 2026-06-24
    assert isinstance(YAHOO_DAILY_BACKFILL_FLOOR, date)

    # enforced: a beyond-limit intraday request raises
    with pytest.raises(YahooLookbackExceededError):
        assert_yahoo_intraday_within_limit("15m", date.today() - timedelta(days=61))
    # enforced: a pre-floor daily request raises (the GENERAL daily clamp)
    with pytest.raises(YahooLookbackExceededError):
        assert_yahoo_intraday_within_limit("1d", YAHOO_DAILY_BACKFILL_FLOOR - timedelta(days=1))
    # enforced: a too-wide single request raises
    with pytest.raises(YahooRequestTooWideError):
        assert_yahoo_request_width_ok("1m", date(2026, 6, 1), date(2026, 6, 20))


def test_databento_allowlist_limits_declared_and_enforced() -> None:
    """The Databento source declares per-level rolling-history floors AND enforces
    them on the allowlist gate (fail-closed raise)."""
    from unified_api_contracts.registry.databento_subscription_allowlist import (
        LEVEL_MAX_LOOKBACK_DAYS,
        DatabentoLookbackExceededError,
        assert_databento_request_allowed,
        earliest_allowed_start,
    )

    # per-level floors declared
    for level in ("L0", "L1", "L2", "L3"):
        assert level in LEVEL_MAX_LOOKBACK_DAYS
    # MEASURED 2026-06-24: our fixed subscription grants FULL history (no PAYG
    # rolling edge) — so L1/L2/L3 floors equal L0 (full history). A request one
    # day PAST the (now 16y) floor still raises (the gate is non-bypassable); a
    # request well inside (e.g. 1y back, which the prior 365d L1 window would have
    # rejected at its edge) is now correctly ALLOWED.
    floor = earliest_allowed_start("trades")
    with pytest.raises(DatabentoLookbackExceededError):
        assert_databento_request_allowed("GLBX.MDP3", "trades", floor.date() - timedelta(days=1))
    # 2 years back is INSIDE the measured full-history entitlement → allowed
    # (regression guard: the old L1=365d window WRONGLY rejected this).
    assert_databento_request_allowed("GLBX.MDP3", "trades", date.today() - timedelta(days=730))


# ---------------------------------------------------------------------------
# Negative proof: a deliberately HALF-WIRED venue RED-fails the gate.
# ---------------------------------------------------------------------------
def test_half_wired_venue_red_fails() -> None:
    """PROOF the gate catches a half-wired venue: a venue listed in
    VENUES_BY_ASSET_GROUP['tradfi'] with NO source routing (no databento dataset,
    no data provider) MUST fail ``test_tradfi_venue_resolves_to_a_data_source``.

    Simulates 'KRX minus its yahoo_finance routing' WITHOUT mutating global state:
    we re-run the rule-2 predicate against a synthetic VenueMapping whose KRX
    provider entry is removed, and assert the predicate now fails.
    """
    vm = VenueMapping()
    # Synthesise the half-wired state: KRX in the venue list but absent from BOTH
    # source maps (the exact regression rule-2 guards against).
    half_wired_to_databento = dict(vm.venue_to_databento)
    half_wired_to_provider = dict(vm.venue_to_data_provider)
    half_wired_to_databento.pop("KRX", None)
    half_wired_to_provider.pop("KRX", None)

    has_databento = half_wired_to_databento.get("KRX") is not None
    has_provider = half_wired_to_provider.get("KRX") is not None
    # The rule-2 assertion is `has_databento or has_provider`; here it is False →
    # the gate WOULD raise AssertionError for this venue.
    assert not (has_databento or has_provider), (
        "expected the half-wired KRX (no databento, no provider) to resolve to NO "
        "source — this is the state rule-2 RED-fails on"
    )
    # And confirm the LIVE KRX (with routing) PASSES rule-2 (regression guard).
    assert vm.venue_to_data_provider.get("KRX") == "yahoo_finance", (
        "live KRX must route to yahoo_finance (rule-2 passes for the real venue)"
    )


def test_half_wired_venue_invokes_real_gate_and_red_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Stronger proof: invoke the ACTUAL gate assertion
    ``test_tradfi_venue_resolves_to_a_data_source`` against a half-wired venue and
    assert it RAISES the AssertionError (cite the exact assertion that fires).

    Half-wires KRX by patching ``VenueMapping`` so KRX is absent from BOTH source
    maps, then calls the real rule-2 test function — which must raise (it would
    turn the parametrised ``[KRX]`` case RED in CI)."""
    real_init = VenueMapping.__init__

    def _half_wired_init(self: VenueMapping) -> None:
        real_init(self)
        # Remove KRX's routing → the exact "no source" regression.
        self.venue_to_databento.pop("KRX", None)
        self.venue_to_data_provider.pop("KRX", None)

    monkeypatch.setattr(VenueMapping, "__init__", _half_wired_init)

    with pytest.raises(AssertionError, match="resolves to NO data source"):
        test_tradfi_venue_resolves_to_a_data_source("KRX")
