"""MVP scope config + ``is_mvp()`` predicate — Phase 1.

This module is the UAC SSOT that defines which catalogue cells belong to
the **MVP scope** (a strict, rules-derived SUBSET of the could-exist
universe). No manifest column is ever written: membership is evaluated
on-the-fly by consumers (instruments-service catalogue view,
deployment-api data-status endpoint) via the :func:`is_mvp` predicate.

Hierarchy (from largest to smallest):
    ALL instrument types  ⊇  could-exist universe  ⊇  MVP scope

Grain of the rule (everything-or-nothing):
    ``(asset_group, venue, instrument_type, data_type[, base_ccy])``

    For sports: ``+ league``
    For prediction: ``+ market_group``

A cell is MVP iff its ``(venue, instrument_type)`` pair is declared in
the rule for its ``asset_group`` AND every other declared axis matches.
A ``(venue, instrument_type)`` absent from the rule → could-exist but
NOT MVP → ``is_mvp()`` returns ``False``.

Per-instrument-type grain note:
    If ``(venue, instrument_type)`` is declared as MVP, ALL of that
    venue's catalogued expiries/strikes/markets for that instrument_type
    are in-scope. The grain is NOT per-expiry, per-strike, or per-turn.
    (See the grain test in ``tests/unit/test_mvp_scope.py``.)

Phase-1 scope:
    Config + predicate + exports + tests.
    IS catalogue view (Phase 2) and deployment-api endpoint (Phase 3)
    are NOT part of this phase.

TODO(mvp-scope): operator sign-off on final membership before Phase 2
    integration. Items marked ``# TODO(mvp-scope)`` below need explicit
    operator confirmation. Conservative defaults are used until sign-off.

SSOT: ``plans/active/mvp_scope_catalogue_tagging_2026_06_08.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from unified_api_contracts.canonical.crosscutting.config_versioning import (
    ConfigDescriptor,
    canonical_config_repr,
    compute_config_content_hash,
)

# The CeFi base-currency universe is the curated capture SSOT
# ``CEFI_BASE_ASSET_UNIVERSE`` (operator-confirmed 2026-06-23 — no longer the
# 44-coin MVP cap; now the survivorship-bias-free union of legacy-44 +
# top-100-mcap-aggregated-since-2019 + HL/ASTER perp bases, ~490 assets).
# ``CEFI_OPTIONS_UNDERLYINGS`` is the
# narrower options carve-out (BTC + ETH only — Deribit is the only CeFi venue
# with OPTION instruments). Imported from the leaf module (NOT the registry
# package ``__init__``) to avoid any import-chain timing surprise; the
# registry → crosscutting direction is acyclic (cefi_instrument_universe.py
# imports nothing from crosscutting).
from unified_api_contracts.registry.cefi_instrument_universe import (
    CEFI_BASE_ASSET_UNIVERSE,
    CEFI_EQUITY_PERP_BASE_UNIVERSE,
    CEFI_OPTIONS_UNDERLYINGS,
    STAKING_SPOT_EXCEPTION,
)

# DeFi MVP venue/data_type derivation source (operator 2026-07-09 — see
# ``_mvp_defi_venues()`` below). Imported from the leaf module (NOT the
# registry package ``__init__``), same acyclic-import discipline as the
# CeFi imports above: the registry → crosscutting direction is acyclic.
from unified_api_contracts.registry.market_data_categories import (
    DATA_TYPES_BY_ASSET_GROUP as _MDC_DATA_TYPES_BY_ASSET_GROUP,
)
from unified_api_contracts.registry.market_data_categories import (
    VENUES_BY_ASSET_GROUP as _MDC_VENUES_BY_ASSET_GROUP,
)

# The TradFi equity/ETF MVP basis universe — the DBEQ.BASIC cash-equity twins of
# the Binance tradfi-perp underlyings (the basis-reference leg of the equity-basis
# arb archetype). Used by the tradfi MVP rule's equity carve-out below so those
# cash equities/ETFs are MVP-scoped alongside the CME futures complex.
from unified_api_contracts.registry.tradfi_ticker_universe import (
    TRADFI_EQUITY_PERP_BASIS_UNIVERSE,
)

# Re-exported (the generic descriptor type now lives in ``config_versioning``;
# kept importable here + at the package root for backwards compatibility).
_canonical_repr = canonical_config_repr


# Venues whose canonical pipeline form is the bare base token but whose MVP rule
# declares SUB-VENUES (so an unsuffixed caller still resolves). OKX is the only
# one today: the catalogue + manifest carry ``OKX-SPOT`` / ``OKX-SWAP`` /
# ``OKX-FUTURES`` but legacy callers (+ some registries) pass the bare ``OKX``.
# A bare token that base-normalises to a key here matches ANY of that key's
# sub-venues for the (instrument_type) axis. (mvp_instrument_universe_gap_audit
# P2 #1, 2026-06-17.)
_CEFI_SUB_VENUE_BASES: Final[frozenset[str]] = frozenset({"OKX"})


def _cefi_venue_data_type_set(venue: str, rule: CeFiMvpRule) -> frozenset[str] | None:
    """Return the per-venue data_type override set for *venue*, or ``None``.

    Checks the ``venue_data_types`` map first with the exact venue string, then
    with the bare base token (``COINBASE-SPOT`` → ``COINBASE``).  Returns ``None``
    when the venue has no override (caller should use ``instrument_type_data_types``
    / flat ``data_types`` instead).

    Introduced in v11 (operator 2026-06-28) to support the COINBASE={trades}
    venue-wide override (COINBASE-SPOT / COINBASE-FUTURES drop book_snapshot_5).
    NOTE: Deribit has NO venue override — its OPTION->{options_chain} cut stays
    in ``instrument_type_data_types`` (v10), and Deribit perp/future keep
    trades + book_snapshot_5.
    """
    if not rule.venue_data_types:
        return None
    v = (venue or "").strip().upper()
    # Exact match first (COINBASE-SPOT, COINBASE-FUTURES, …).
    if v in rule.venue_data_types:
        return rule.venue_data_types[v]
    # Base-token fallback (COINBASE → matches COINBASE-SPOT / COINBASE-FUTURES
    # if the map carries the bare token; not used today but future-safe).
    base = v.split("-", 1)[0]
    if base in rule.venue_data_types:
        return rule.venue_data_types[base]
    return None


def _cefi_venue_in_rule(venue: str, rule_venues: frozenset[str]) -> bool:
    """Match a CeFi ``venue`` against the rule's venue set, OKX-aware.

    Direct membership first (``OKX-SPOT`` ∈ rule). Then, when the caller passes a
    BARE base token (``OKX``) whose base is in :data:`_CEFI_SUB_VENUE_BASES`, it
    matches iff the rule declares ANY sub-venue with that base (``OKX-SPOT`` /
    ``OKX-SWAP`` / ``OKX-FUTURES``) — so ``is_mvp("cefi", "OKX", …)`` resolves the
    instrument-grain question "is this OKX instrument in scope" without the caller
    knowing the exact sub-venue. (mvp_instrument_universe_gap_audit P2 #1.)
    """
    if venue in rule_venues:
        return True
    base = venue.strip().upper().split("-", 1)[0] if venue else ""
    if base not in _CEFI_SUB_VENUE_BASES:
        return False
    return any(rv.split("-", 1)[0] == base for rv in rule_venues)


# ---------------------------------------------------------------------------
# Typed, immutable rule structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CeFiMvpRule:
    """MVP rule for the ``cefi`` asset group.

    Attributes:
        venues: Frozenset of canonical venue identifiers.
            Names match the keys in ``VENUES_BY_ASSET_GROUP["cefi"]`` in
            ``unified_api_contracts.registry.market_data_categories``.
        instrument_types: Frozenset of canonical instrument type strings
            (:class:`~unified_api_contracts.InstrumentType` str values).
        data_types: Frozenset of data_type strings.
        base_ccys: Optional frozenset of base-currency strings. When not
            empty, only cells whose ``base_ccy`` appears here are MVP.
            Empty → all base currencies are in scope for the pair.
        options_base_ccys: Optional frozenset of base-currency strings that
            applies ONLY to ``instrument_type == "OPTION"`` cells (the
            CeFi options expected-universe carve-out). The options universe
            is intentionally narrower than the spot/perp ``base_ccys`` —
            Deribit is the only CeFi venue with OPTION instruments and it
            lists BTC + ETH options only, so expecting the full base-asset
            universe as options would yield false-missing. When non-empty, an OPTION
            cell is MVP iff ``base_ccy`` is in this set (``base_ccys`` is NOT
            applied to OPTION cells). Empty → fall back to ``base_ccys``.
        instrument_type_data_types: Optional per-instrument_type data_type
            OVERRIDE of the flat ``data_types`` set (operator 2026-06-27,
            decision #2). When an instrument_type key is present, ONLY those
            data_types are MVP for that instrument_type — the flat ``data_types``
            set does NOT apply to it. Today the only entry is ``OPTION ->
            {options_chain}``: a Deribit option's MVP MTDS data_type is the
            options_chain bundle ONLY (it carries marks + IVs — sufficient);
            per-strike ``trades`` + ``book_snapshot_5`` are EXCLUDED for options
            (too heavy / ~12k API calls/day vs 1). An instrument_type ABSENT
            from this map uses the flat ``data_types`` set unchanged
            (perps/spot/dated-futures = trades + book_snapshot_5 + funding).
        venue_data_types: Optional per-venue data_type OVERRIDE of the flat
            ``data_types`` set (operator 2026-06-28, decision A). When a
            venue key is present, ONLY those data_types are MVP for that venue
            — the flat ``data_types`` set does NOT apply to it. Takes
            PRECEDENCE over ``instrument_type_data_types`` (the two overrides
            are currently exclusive: a venue in this map must define its own
            complete data_type set, not compose with the per-instrument_type
            map). Key may be a canonical sub-venue (``COINBASE-SPOT``) or the
            bare base token (``COINBASE``) — the predicate checks the EXACT
            venue string first, then falls back to the base token. Current
            overrides (v11):
              COINBASE-SPOT  → {trades} (no book_snapshot_5 — too heavy, no
              COINBASE-FUTURES   depth features derived)
            NOTE: Deribit is intentionally ABSENT from this map. Its
            OPTION->{options_chain} cut lives in ``instrument_type_data_types``
            (v10), and Deribit perp/future keep trades + book_snapshot_5.
            A venue ABSENT from this map uses ``instrument_type_data_types``
            (if present) or the flat ``data_types`` set.
        sources: Optional frozenset of source strings. When not empty,
            only cells from one of these sources are MVP.
    """

    venues: frozenset[str]
    instrument_types: frozenset[str]
    data_types: frozenset[str]
    base_ccys: frozenset[str] = field(default_factory=frozenset)
    options_base_ccys: frozenset[str] = field(default_factory=frozenset)
    instrument_type_data_types: dict[str, frozenset[str]] = field(default_factory=dict)
    venue_data_types: dict[str, frozenset[str]] = field(default_factory=dict)
    sources: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class DeFiMvpRule:
    """MVP rule for the ``defi`` asset group.

    Attributes:
        venues: Frozenset of canonical PROTOCOL-CHAIN venue IDs.
            Names match the entries in ``defi_venues.ALL_DEFI_VENUES``.
        instrument_types: Frozenset of canonical instrument type strings.
        data_types: Frozenset of data_type strings.
        sources: Optional frozenset of source strings.
    """

    venues: frozenset[str]
    instrument_types: frozenset[str]
    data_types: frozenset[str]
    sources: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class TradFiMvpRule:
    """MVP rule for the ``tradfi`` asset group.

    Attributes:
        venues: Frozenset of canonical venue identifiers.
        instrument_types: Frozenset of canonical instrument type strings.
        data_types: Frozenset of data_type strings.
        underliers: Optional frozenset of underlier codes (e.g. ``ES``,
            ``NQ``, ``VX``). When not empty, only cells with one of these
            underlier codes are MVP.
        sources: Optional frozenset of source strings.
    """

    venues: frozenset[str]
    instrument_types: frozenset[str]
    data_types: frozenset[str]
    underliers: frozenset[str] = field(default_factory=frozenset)
    sources: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class SportsMvpRule:
    """MVP rule for the ``sports`` asset group.

    Attributes:
        leagues: Frozenset of canonical league_id strings.
            Names match the keys of
            :data:`unified_api_contracts.canonical.domain.sports.league_data.LEAGUE_REGISTRY`.
        data_types: Frozenset of data_type strings.
    """

    leagues: frozenset[str]
    data_types: frozenset[str]


@dataclass(frozen=True)
class PredictionMvpRule:
    """MVP rule for the ``prediction`` asset group.

    Attributes:
        venues: Frozenset of canonical venue identifiers.
        market_groups: Optional frozenset of
            :class:`~unified_api_contracts.canonical.domain.prediction.prediction_mapping.PredictionMarketCategory`
            string values. When not empty, only cells in these groups are
            MVP.
        data_types: Frozenset of data_type strings.
        sources: Optional frozenset of source strings.
    """

    venues: frozenset[str]
    market_groups: frozenset[str] = field(default_factory=frozenset)
    data_types: frozenset[str] = field(default_factory=frozenset)
    sources: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class FeaturesModelsMvpStub:
    """Stub placeholder for features/strategy/models MVP scope (Phase 2+).

    These sections are declared as named keys in :data:`MVP_SCOPE` so
    that Phase 2 implementations can populate them without a structural
    change to the config. Consumers MUST NOT read these stubs as
    actual config — they are empty by design until the corresponding
    phase ships.

    TODO(mvp-scope): populate in Phase 2 (features-scope) and Phase 3
        (strategy/model-scope) plans.
    """

    description: str = "stub — Phase 2+ scope; not yet populated"


# ---------------------------------------------------------------------------
# Sports MVP league universe — the canonical 94-league football set.
# ---------------------------------------------------------------------------
# operator 2026-06-27 decision #1 (BUG FIX): the sports MVP universe is the
# **94-league football universe** — EVERY league in ``LEAGUE_REGISTRY`` whose
# ``sport == "FOOTBALL"`` (33 Prediction + 22 Features + 39 Reference football
# = 94; the 7 non-football leagues NFL/NBA/MLB/NHL/ATP/WTA/EUROLEAGUE are
# EXCLUDED). The previous rule MVP-tagged only 2 leagues (EPL + LA_LIGA) — a
# drift the audit caught. Derived (not a hand-written literal) from the league
# registry so a future football-league addition is automatically MVP.
#
# Import is LOCAL (inside the helper) to avoid an import cycle: ``mvp_scope`` is
# loaded by the package ``__init__``/crosscutting ``__init__`` chain BEFORE the
# sports domain, and ``league_data`` transitively re-enters that chain — a
# top-level import here would deadlock partial init. The helper is invoked ONCE
# at MVP_SCOPE construction (verified safe: the package __init__ is mid-flight
# but the sports leaf modules import only stdlib/pydantic + config_versioning).
def _mvp_football_league_ids() -> frozenset[str]:
    """Return the canonical 94 football league_ids (``sport == "FOOTBALL"``)."""
    from unified_api_contracts.canonical.domain.sports.league_data import (
        LEAGUE_REGISTRY,
    )

    return frozenset(league.league_id for league in LEAGUE_REGISTRY.values() if league.sport == "FOOTBALL")


# ---------------------------------------------------------------------------
# DeFi MVP venue/data_type universe — "everything we capture" (operator
# 2026-07-09 ruling on `defi_perp_funding_mvp_scope_contradiction_2026_06_29.md`
# §E5: "DeFi MVP framing — define for now, just keep all as MVP though").
# ---------------------------------------------------------------------------
# Prior to this, DeFi had NO dedicated MVP set distinct from the factory
# registry (curated to an 11-venue Ethereum/3-Solana-DEX subset, unlike
# CeFi/TradFi/Sports/Prediction which each have a real, deliberately-scoped
# MVP rule). The operator's ruling: DeFi MVP == the full current, real
# capture universe -- every IS-producible venue -- rather than a curated
# narrower subset, "for now" (a deliberate, simple starting point; a future
# ruling may narrow it the way CeFi/TradFi are narrowed).
#
# Derived (not a hand-written literal) from ``VENUES_BY_ASSET_GROUP["defi"]``
# so a newly-onboarded DeFi venue is automatically MVP the moment it goes
# live -- mirrors ``_mvp_football_league_ids()``'s derivation pattern above.
#
# IMPORTANT: this is intentionally == P (the IS-producible venue set;
# ``VENUES_BY_ASSET_GROUP["defi"]``, phase=="live" per
# ``defi_venues.DEFI_VENUE_PHASE``), NOT the broader ``ALL_DEFI_VENUES``
# declarative registry (which also carries "pipeline"-phase venues that
# UAC has declared but instruments-service does not yet actually produce).
# Instrument_universe_registry_consolidation_2026_06_29.md Decision D
# established "every DeFi-MVP venue is IS-producible" as a data-correctness
# invariant -- MVP membership feeds the honest-coverage reachable
# denominator, so tagging a not-yet-producible venue MVP=true would mint a
# phantom expected-but-never-captured cell. That is why e.g.
# ROCKETPOOL-ETHEREUM (a real, wired adapter -- rocket_pool.py -- but
# deliberately NOT in P; see ``TestDeFiMvpExclusionV12``) stays excluded
# here too: "keep all as MVP" means all of P, not all of the factory's
# adapter classes regardless of pipeline-wiring state.
def _mvp_defi_venues() -> frozenset[str]:
    """Return the full current DeFi venue capture universe (== P, IS-producible)."""
    return frozenset(_MDC_VENUES_BY_ASSET_GROUP["defi"])


def _mvp_defi_data_types() -> frozenset[str]:
    """Return every DeFi data_type instruments-service/MTDS currently produce."""
    return frozenset(_MDC_DATA_TYPES_BY_ASSET_GROUP["defi"])


# ---------------------------------------------------------------------------
# MVP_SCOPE — the single global config
# ---------------------------------------------------------------------------

MVP_SCOPE: Final[dict[str, object]] = {
    # ------------------------------------------------------------------
    # cefi
    #
    # Venues: the 7 primary CeFi venues from the MVP archetype matrix.
    #   carry_staked_basis: Binance/Bybit/OKX/Deribit/Hyperliquid/Aster/Kraken
    #   arbitrage_price_dispersion: same venues (CEX spot + perp marks)
    #
    # Canonical venue names match VENUES_BY_ASSET_GROUP["cefi"]:
    #   BINANCE-SPOT, BINANCE-FUTURES → carry both (spot + perp legs)
    #   BYBIT, OKX, DERIBIT, HYPERLIQUID, ASTER, KRAKEN-SPOT, KRAKEN-FUTURES
    #
    # instrument_types: SPOT_PAIR (spot leg) + PERPETUAL (funding/perp leg)
    #
    # data_types: trades + book_snapshot_5 + funding_rate
    #   (funding_rate maps to the canonical "derivative_ticker" + per-venue
    #    funding rate columns — use "funding_rate" as the MVP label because
    #    that is the logical axis; actual data_type=derivative_ticker in MTDS)
    #   TODO(mvp-scope): confirm whether "funding_rate" should alias
    #   "derivative_ticker" here or remain a separate axis.
    #
    # base_ccys: the curated ``CEFI_BASE_ASSET_UNIVERSE`` (operator-confirmed
    #   2026-06-23 as the CeFi capture SSOT — legacy-44 + top-100-mcap-since-2019
    #   + HL/ASTER perp bases, ~490 assets, survivorship-bias-free; no longer the
    #   44-coin MVP cap). Spot + perp legs span the full universe.
    #
    # options_base_ccys: BTC + ETH ONLY (``CEFI_OPTIONS_UNDERLYINGS``). The
    #   options expected universe is the Deribit-options carve-out — Deribit is
    #   the only CeFi venue with OPTION instruments and it lists BTC + ETH
    #   options only. Expecting the full base-asset universe as options on Deribit
    #   would yield false-missing, so OPTION cells gate on this narrower set.
    #
    # sources: tardis (canonical CeFi archive source per SOURCE_PRIORITY)
    #   + per-venue live source (each venue name is also its live source key
    #   for the live-pipeline REST/WS leg). Empty frozenset = all sources in
    #   scope (conservative default per the task spec).
    # ------------------------------------------------------------------
    "cefi": CeFiMvpRule(
        venues=frozenset(
            {
                "BINANCE-SPOT",
                "BINANCE-FUTURES",
                "BYBIT",
                # OKX is captured under canonical SUB-VENUE names in the
                # instruments-store catalogue + the rest of the pipeline
                # (OKX-SPOT / OKX-SWAP / OKX-FUTURES — like BINANCE-SPOT /
                # BINANCE-FUTURES), NOT the bare ``OKX`` token. Declaring the
                # sub-venues here makes ``is_mvp("cefi", "OKX-SPOT", …)`` etc.
                # match; the predicate also base-venue-token-normalises so a
                # bare ``OKX`` caller still resolves (mvp_instrument_universe_gap_audit
                # P2 #1, 2026-06-17).
                "OKX-SPOT",
                "OKX-SWAP",
                "OKX-FUTURES",
                "DERIBIT",
                "HYPERLIQUID",
                "ASTER",
                "KRAKEN-SPOT",
                "KRAKEN-FUTURES",
                # Additional Tardis CEX venues (cefi_universe_capture_rule
                # 2026-06-23). Previously ABSENT from the rule → their spot/perp
                # cells were mvp=0 regardless of the perp-gate. Each spot venue
                # pairs with its sibling perp venue on the shared entity prefix
                # (BYBIT-SPOT↔BYBIT, COINBASE-SPOT↔COINBASE-FUTURES,
                # BITFINEX-SPOT↔BITFINEX-FUTURES, BITGET-SPOT↔BITGET-FUTURES).
                "BYBIT-SPOT",
                "COINBASE-SPOT",
                "COINBASE-FUTURES",
                "BITFINEX-SPOT",
                "BITFINEX-FUTURES",
                "BITGET-SPOT",
                "BITGET-FUTURES",
                # UPBIT — spot-only Korean venue (kimchi premium). The ONLY
                # perp-gate exception (see is_in_mvp_capture_universe): its SPOT
                # is mvp=true despite no perp on the venue.
                "UPBIT",
                # On-chain CLOB perp venues (LIGHTER / EXTENDED / PACIFICA) —
                # classified as CEFI everywhere (venue_mapping
                # all_cefi_onchain_clob_venues + VENUES_BY_ASSET_GROUP["cefi"] +
                # is_cefi_venue), but previously ABSENT from this MVP rule so their
                # PERPETUAL cells tagged mvp=0 (instruments-vs-MTDS drift). Added
                # cefi here for BOTH instruments + MTDS (operator 2026-06-27
                # decision #4). All three are CLOB-based perp DEXs (confirmed: same
                # CLOB capture surface as HL/ASTER — trades + book_snapshot_5 +
                # derivative_ticker). PACIFICA is forward-poll-only for tick (no
                # historical book/trades backfill — see DataTypeCapability notes).
                "LIGHTER-ZKSYNC",
                "EXTENDED-STARKNET",
                "PACIFICA-SOLANA",
                # NOTE (operator 2026-06-27 decision #3): BINANCE-DELIVERY (Binance
                # COIN-M inverse/delivery futures) was REMOVED from the cefi MVP
                # set — the operator accepts COIN-M delivery is NOT MVP. Other
                # venues' dated/quarterly fixed-delivery futures STAY MVP (the
                # FUTURE instrument_type below + the dated-future capture path).
            }
        ),
        instrument_types=frozenset(
            {
                "SPOT_PAIR",  # InstrumentType.SPOT_PAIR
                "PERPETUAL",  # InstrumentType.PERPETUAL
                "OPTION",  # InstrumentType.OPTION (Deribit BTC/ETH options)
                # Dated/quarterly delivery futures sharing a universe base
                # (e.g. BTC-27JUN25). Part of the futures complex — gated on
                # base-membership + the perp-gate (cefi_universe_capture_rule
                # 2026-06-23). Only in-scope via is_in_mvp_capture_universe's
                # perp-gate; a bare is_mvp("FUTURE") with no perp-sibling is
                # still excluded by the capture predicate.
                "FUTURE",  # InstrumentType.FUTURE
                # Crypto-venue equity instruments (2026-06-20):
                "EQUITY_PERP",  # InstrumentType.EQUITY_PERP — single-stock perps (Binance/OKX/Bybit)
                "TOKENIZED_EQUITY",  # InstrumentType.TOKENIZED_EQUITY — tokenized stocks (e.g. Bybit AAPLX)
            }
        ),
        # FLAT data_types — apply to SPOT_PAIR / PERPETUAL / FUTURE / EQUITY_PERP
        # / TOKENIZED_EQUITY (everything EXCEPT the OPTION override below):
        #   trades + book_snapshot_5 (the spot/perp microstructure pair) +
        #   derivative_ticker / funding_rate (the perp funding axis).
        data_types=frozenset(
            {
                "trades",
                "book_snapshot_5",
                # Perpetual funding: canonical data_type is derivative_ticker
                # (contains funding_rate field) in most venues;
                # some venues expose a separate funding_rate data_type.
                "derivative_ticker",
                "funding_rate",
            }
        ),
        # OPTION data_type override (operator 2026-06-27 decision #2 — cost cut):
        # a Deribit OPTION's MVP MTDS data_type is the ``options_chain`` bundle
        # ONLY (it carries marks + IVs — sufficient for the VOL_* strategy/ML
        # family). Per-strike ``trades`` + ``book_snapshot_5`` are EXCLUDED for
        # options (~12k API calls/day per-strike vs 1 bulk chain call/day; full
        # per-option tick is only needed for execution-quality analysis). This
        # OVERRIDES the flat ``data_types`` set for OPTION cells.
        instrument_type_data_types={
            "OPTION": frozenset({"options_chain"}),
        },
        # PER-VENUE data_type overrides (operator 2026-06-28 decision A):
        #   COINBASE-SPOT/COINBASE-FUTURES → {trades} only. book_snapshot_5 is
        #     excluded: Coinbase depth backfill VMs are the heaviest (BTC-USD
        #     book5 days hit ~30 GB pandas peak) and we derive no depth features
        #     from Coinbase specifically. trades-only is sufficient for price /
        #     execution-quality signals. This applies to BOTH COINBASE-SPOT and
        #     COINBASE-FUTURES. All other cefi venues (Binance, Bybit, OKX, …)
        #     keep trades + book_snapshot_5 unchanged.
        #   Note: Deribit PERP/FUTURE/SPOT tick (trades + book5) is UNCHANGED
        #     (wanted). The OPTION → {options_chain} override above remains. No
        #     Deribit venue_data_types entry — Deribit stays v10-behavior.
        venue_data_types={
            # COINBASE sub-venues: trades-only (no book5).
            "COINBASE-SPOT": frozenset({"trades"}),
            "COINBASE-FUTURES": frozenset({"trades"}),
        },
        # Curated CeFi capture universe (operator-confirmed SSOT, ~490 base assets,
        # survivorship-bias-free). Spot + perp legs.
        # EQUITY_PERP/TOKENIZED_EQUITY cells use CEFI_EQUITY_PERP_BASE_UNIVERSE as
        # their base_ccys (equity tickers like META, NVDA, AAPL — not crypto coins).
        # The combined union covers both crypto-perp and equity-perp families.
        base_ccys=CEFI_BASE_ASSET_UNIVERSE | CEFI_EQUITY_PERP_BASE_UNIVERSE,
        # Deribit-options carve-out: BTC + ETH only (the OPTION expected universe).
        options_base_ccys=CEFI_OPTIONS_UNDERLYINGS,
        # sources: empty → all sources in scope (tardis + per-venue live)
        sources=frozenset(),
    ),
    # ------------------------------------------------------------------
    # defi — "everything we capture" (operator 2026-07-09, see
    # ``_mvp_defi_venues()`` / ``_mvp_defi_data_types()`` above for the full
    # ruling + rationale). Unlike cefi/tradfi/sports/prediction, this is NOT
    # a curated narrower subset — it is every IS-producible DeFi venue (P),
    # every real instrument_type any P-venue adapter emits, and every DeFi
    # data_type the pipeline produces. All three axes are DERIVED (venues +
    # data_types from the UAC market-data-categories SSOT; instrument_types
    # hand-verified against live adapter code, see below) so this rule can
    # never silently drift stale the way the prior 11-venue hand list did.
    #
    # instrument_types (verified 2026-07-09 via
    # `grep -rhoE "InstrumentType\.[A-Z_]+" instruments-service/.../adapters/defi/*.py`
    # — every value at least one live P-venue adapter actually emits):
    #   POOL        — EVM + Solana AMM/CLMM pool snapshots (Uniswap, Curve, Balancer, Orca, Raydium, Kamino, …)
    #   LENDING     — flat-record lending markets (Aave V3, Compound V3, Spark)
    #   A_TOKEN     — supply-side lending leg (Morpho, Fluid, MarginFi, Solend)
    #   DEBT_TOKEN  — borrow-side lending leg (Morpho, Fluid, MarginFi, Solend)
    #   LST         — liquid staking tokens (Lido, EtherFi)
    #   YIELD_BEARING — yield-bearing wrapped assets (Ethena sUSDe, EtherFi)
    #   PERPETUAL   — on-chain perp markets (Drift)
    #   SPOT_PAIR   — on-chain spot markets (Drift, EigenLayer governance token)
    #   STAKING     — native/protocol staking (Jito, Marinade)
    #
    # data_types: the full DATA_TYPES_BY_ASSET_GROUP["defi"] list (dex pool
    # state/swaps, lending/utilization indices, LST rates, perp funding,
    # oracle prices, gas fees, rewards/risk params, liquidation/flash-loan/
    # bridge/mev/governance events, vault share price/APY/TVL, native
    # staking rates, …) — not the prior curated 6-entry subset.
    # ------------------------------------------------------------------
    "defi": DeFiMvpRule(
        venues=_mvp_defi_venues(),
        instrument_types=frozenset(
            {
                "POOL",  # InstrumentType.POOL
                "LENDING",  # InstrumentType.LENDING
                "A_TOKEN",  # InstrumentType.A_TOKEN
                "DEBT_TOKEN",  # InstrumentType.DEBT_TOKEN
                "LST",  # InstrumentType.LST
                "YIELD_BEARING",  # InstrumentType.YIELD_BEARING
                "PERPETUAL",  # InstrumentType.PERPETUAL
                "SPOT_PAIR",  # InstrumentType.SPOT_PAIR
                "STAKING",  # InstrumentType.STAKING
            }
        ),
        data_types=_mvp_defi_data_types(),
        # sources: empty → all on-chain sources in scope (onchain_subgraph, onchain_rpc,
        # pyth_hermes, chainlink, hyperliquid, defillama, …)
        sources=frozenset(),
    ),
    # ------------------------------------------------------------------
    # tradfi
    #
    # Venues: CME only (Databento CME tick data is the primary TradFi MVP
    #   data source per the MVP matrix — ES, NQ, VX futures + options).
    #
    # instrument_types: FUTURE, OPTION
    #   NOTE: TradFi "option" in InstrumentType is ``OPTION`` (the legacy name was
    #   ``OPTIONS_CHAIN``). CME OPTION rows are MVP at ohlcv_1m (operator
    #   2026-06-27 decision #7) — but the catalogue today has 0 CME OPTION
    #   instrument rows (only futures legs); the actual ingestion of CME option
    #   instrument-definitions into instruments-service is a SEPARATE agent's job.
    #   This rule ensures CME options are correctly MVP-tagged ONCE present.
    #
    # data_types: ohlcv_1m ONLY (operator 2026-06-27 decision #7 — NO ohlcv_1s,
    #   NO trades/tbbo in tradfi MVP). 1-minute bars are the tradfi MVP grain.
    #
    # underliers: ES (S&P 500 e-mini), NQ (Nasdaq 100 e-mini), VX (VIX futures)
    #   + the CME commodity roots backing a Binance tradfi-perp. CME OPTIONS on
    #   these roots are MVP (decision #7: "S&P/ES, and the other CME roots that
    #   have Binance perps"). These are the exchange_code / underlier values.
    #
    # sources: databento (primary per SOURCE_PRIORITY)
    # ------------------------------------------------------------------
    "tradfi": TradFiMvpRule(
        venues=frozenset({"CME"}),
        instrument_types=frozenset(
            {
                "FUTURE",  # InstrumentType.FUTURE
                "OPTION",  # InstrumentType.OPTION — CME options, MVP at ohlcv_1m
            }
        ),
        # ohlcv_1m ONLY (operator 2026-06-27 decision #7): tradfi MVP is 1-minute
        # bars — NO ohlcv_1s, NO trades. CME options ride the same ohlcv_1m grain.
        data_types=frozenset(
            {
                "ohlcv_1m",
            }
        ),
        underliers=frozenset(
            {
                "ES",  # S&P 500 e-mini futures/options
                "NQ",  # Nasdaq 100 e-mini futures/options
                "VX",  # CBOE VIX futures
                # Commodity roots backing a Binance tradfi-perp (2026-06-24):
                # XAU→GC, XAG→SI, XPT→PL, XPD→PA, NATGAS→NG, CL→CL, COPPER→HG.
                # The cash-commodity twin (CME future) is the basis-reference
                # leg of the commodity-perp basis arb → MVP-scoped.
                "GC",  # gold (XAU)
                "SI",  # silver (XAG)
                "PL",  # platinum (XPT)
                "PA",  # palladium (XPD)
                "NG",  # natural gas (NATGAS)
                "CL",  # WTI crude (CL)
                "HG",  # copper (COPPER)
            }
        ),
        # sources: empty → all sources in scope (databento primary + massive secondary)
        # TODO(mvp-scope): narrow to {"databento", "massive"} once live-source tagging confirmed.
        sources=frozenset(),
    ),
    # ------------------------------------------------------------------
    # sports
    #
    # The MVP sports coverage targets odds arbitrage (arbitrage_price_dispersion)
    # and fixture results (reference data for prediction-market settlement).
    #
    # Leagues: the canonical 94-league FOOTBALL universe (operator 2026-06-27
    #   decision #1 — BUG FIX). EVERY ``LEAGUE_REGISTRY`` league with
    #   ``sport == "FOOTBALL"`` (33 Prediction + 22 Features + 39 Reference = 94);
    #   the 7 non-football leagues (NFL/NBA/MLB/NHL/ATP/WTA/EUROLEAGUE) are
    #   EXCLUDED. Derived via ``_mvp_football_league_ids()`` so a future
    #   football-league addition is automatically MVP — never a hand-written 2-
    #   league literal (the prior EPL+LA_LIGA drift).
    #
    #   Structural honest-absence (decision #6) is a SEPARATE axis from MVP
    #   membership: a league is MVP for the asset_group, but specific (league x
    #   source) combos the source structurally does not carry are expected-absent
    #   — see ``sports_structural_gaps.py`` (SPORTS_STRUCTURAL_GAPS), which the
    #   coverage SSOT + the IS sports adapters honor (skip-not-attempt).
    #
    # data_types: odds (raw bookmaker odds), markets/outcomes (fixture lifecycle)
    # ------------------------------------------------------------------
    "sports": SportsMvpRule(
        leagues=_mvp_football_league_ids(),
        data_types=frozenset(
            {
                "odds",  # Raw bookmaker odds (from ODDS_API)
                "ODDS",  # Canonical uppercase alias (instruments-service)
                "odds_snapshot",  # Point-in-time bookmaker odds (LOCF sampled)
                "markets",  # Market metadata (event/market listings)
                "outcomes",  # Outcome results (settled markets)
                "settlements",  # Settlement records
            }
        ),
    ),
    # ------------------------------------------------------------------
    # prediction
    #
    # Venues: POLYMARKET + KALSHI (operator 2026-06-27 decision #5 — TODO
    #   resolved). The prediction MVP is the **Kalshi ↔ Polymarket arbitrage
    #   overlap** (``arbitrage_price_dispersion``), which REQUIRES BOTH venues —
    #   a cross-venue same-market spread cannot be quoted with only one leg. The
    #   tradeable MVP universe is the cross-venue arb-overlap built by
    #   ``cross_venue_mapping.build_cross_venue_mapping`` (per-instrument
    #   same-settlement join). Kalshi was previously a "post-MVP TODO"; flipped
    #   in. (The venue-membership rule here is the necessary condition; the
    #   arb-overlap join is the per-instrument refinement applied downstream by
    #   the strategy/coverage consumers.)
    #
    # market_groups: the PredictionMarketCategory values in scope.
    #   crypto, politics, sports — the categories the arb-overlap spans.
    #
    # data_types: trades (CLOB fills), prediction_canonical_question_group
    #   (cluster-grain), market_lifecycle (market lifecycle events).
    # ------------------------------------------------------------------
    "prediction": PredictionMvpRule(
        venues=frozenset({"POLYMARKET", "KALSHI"}),
        market_groups=frozenset(
            {
                "crypto",  # PredictionMarketCategory.CRYPTO
                "politics",  # PredictionMarketCategory.POLITICS
                "sports",  # PredictionMarketCategory.SPORTS
                # "financial" excluded — the arb-overlap MVP is crypto/politics/
                # sports cross-venue same-market pairs.
            }
        ),
        data_types=frozenset(
            {
                "trades",
                "prediction_canonical_question_group",
                "market_lifecycle",
                "MARKET_LIFECYCLE",  # uppercase alias (instruments-service)
            }
        ),
        # sources: empty → all prediction sources in scope (polymarket_clob + polymarket_gamma_api)
        # TODO(mvp-scope): narrow to {"polymarket_clob", "polymarket_gamma_api"} once
        # source tagging is confirmed in the prediction pipeline.
        sources=frozenset(),
    ),
    # ------------------------------------------------------------------
    # Stub sections for future phases (Phase 2+)
    # These are named keys so Phase 2 implementors can replace them with
    # typed rule objects without structural changes.
    # ------------------------------------------------------------------
    "features": FeaturesModelsMvpStub(
        description="MVP features scope — Phase 2; not yet populated. "
        "TODO(mvp-scope): define per-asset_group feature-group x "
        "instrument_type membership."
    ),
    "strategy": FeaturesModelsMvpStub(
        description="MVP strategy scope — Phase 3; not yet populated. "
        "TODO(mvp-scope): define per-archetype strategy scope."
    ),
    "models": FeaturesModelsMvpStub(
        description="MVP model scope — Phase 3; not yet populated. "
        "TODO(mvp-scope): define per-archetype model membership."
    ),
}


# ---------------------------------------------------------------------------
# Config versioning — monotonic version + deterministic content hash.
#
# Per the audit (mvp_scope_catalogue_tagging § "Config versioning"): so a
# coverage delta in data-status attributes to a SCOPE change vs a DATA change,
# carry a (config_version, config_content_hash) descriptor. Bump
# MVP_SCOPE_CONFIG_VERSION whenever MVP_SCOPE content changes; the hash is
# computed at module load and flips IFF the content flips. NOT a GCS key.
# ---------------------------------------------------------------------------


MVP_SCOPE_CONFIG_VERSION: Final[int] = 13
"""Monotonic version of :data:`MVP_SCOPE`. Bump on any content change.

v13 (2026-07-09): DeFi MVP framing defined — "everything we capture" (operator
ruling on ``defi_perp_funding_mvp_scope_contradiction_2026_06_29.md`` §E5).
Previously DeFi had no dedicated MVP set distinct from the factory registry;
the prior ``DeFiMvpRule`` (v10-v12) was a curated 11-venue Ethereum/3-Solana-DEX
subset, unlike cefi/tradfi/sports/prediction which each have a real,
deliberately-narrowed MVP rule. New ruling: DeFi MVP == the full current
capture universe — every IS-producible venue (``_mvp_defi_venues()`` ==
``VENUES_BY_ASSET_GROUP["defi"]``, 57 venues, up from 11), every real
instrument_type a live venue adapter emits (9 values, up from 4 — adds
A_TOKEN/DEBT_TOKEN/YIELD_BEARING/PERPETUAL/STAKING; drops the never-real
``DEX_POOL`` placeholder), and every DeFi data_type
(``_mvp_defi_data_types()`` == the full ``DATA_TYPES_BY_ASSET_GROUP["defi"]``
list, up from a curated 6-entry subset). The Decision-D invariant "every
DeFi-MVP venue is IS-producible" is preserved (venues derive from P, not the
broader ``ALL_DEFI_VENUES`` declarative registry) — ROCKETPOOL-ETHEREUM stays
excluded. Same pass wired 2 new real Solana lending adapters (MarginFi,
Solend) into instruments-service + flipped their ``DEFI_VENUE_PHASE`` to
"live", growing P from 55 to 57.

v12 (2026-06-29): DeFi MVP-exclusion (Decision D —
instrument_universe_registry_consolidation_2026_06_29.md): remove
``ROCKETPOOL-ETHEREUM`` from ``DeFiMvpRule.venues``. ROCKETPOOL-ETHEREUM is
NOT in the IS-producible set P (as confirmed by running ``_build_defi_venues()``
in the IS venv). All other ``DeFiMvpRule.venues`` ARE in P.

v11 (2026-06-28): operator per-venue data_type cut (decision A — cost
reduction, no depth features derived from Coinbase):
  A. COINBASE-SPOT + COINBASE-FUTURES → **trades ONLY** (no book_snapshot_5).
     Coinbase depth backfill VMs are extremely heavy (~30 GB pandas peak for
     BTC-USD book5 days). No depth features are derived from Coinbase
     specifically. Implemented via new ``CeFiMvpRule.venue_data_types`` field
     (the first per-venue override; analogous to the existing per-instrument_type
     override for OPTIONs). All other cefi venues unchanged — they keep
     trades + book_snapshot_5. Deribit is UNCHANGED from v10: OPTION remains
     options_chain-only (``instrument_type_data_types``); PERP/FUTURE/SPOT remain
     trades + book_snapshot_5 (wanted for Deribit perp/future tick capture).

v10 (2026-06-27): operator's CANONICAL MVP definition (7 decisions reconciling
the prior audit's drifts):
  1. SPORTS 94-league FIX — sports MVP leagues = the 94 ``sport == "FOOTBALL"``
     leagues (``_mvp_football_league_ids()``), not the 2-league EPL+LA_LIGA
     literal. The 7 non-football leagues (NFL/NBA/MLB/NHL/ATP/WTA/EUROLEAGUE)
     are no longer MVP.
  2. CEFI Deribit OPTION → ``options_chain`` ONLY (cost cut) — new
     ``CeFiMvpRule.instrument_type_data_types`` override (OPTION ->
     {options_chain}); per-strike trades + book_snapshot_5 EXCLUDED for options.
     Perps/spot/dated-futures unchanged (trades + book_snapshot_5 + funding).
  3. DROP ``BINANCE-DELIVERY`` from the cefi MVP venues (COIN-M delivery not
     MVP). Other venues' dated/quarterly futures STAY MVP (FUTURE type).
  4. LIGHTER-ZKSYNC / EXTENDED-STARKNET / PACIFICA-SOLANA added to the cefi MVP
     venues (CLOB perp DEXs, classified cefi everywhere — reconciled vs the
     instruments-side which already had them cefi).
  5. PREDICTION KALSHI flipped in-MVP — prediction MVP = the Kalshi↔Polymarket
     arb-overlap (needs BOTH venues). TODO resolved.
  7. TRADFI data_types narrowed to ``ohlcv_1m`` ONLY (no ohlcv_1s/trades); CME
     OPTION stays an MVP instrument_type so CME options tag MVP at ohlcv_1m once
     ingested.
(Decision #6 — sports structural honest-absence — is encoded in the sibling
``sports_structural_gaps.py`` registry, not in MVP_SCOPE membership.)

v9 (2026-06-24): added ``BINANCE-DELIVERY`` (Binance COIN-M inverse/delivery
perps + dated futures) to the CeFi MVP scope venues. Inverse perps (e.g.
BTCUSD_PERP) captured on base-membership via PERPETUAL + FUTURE paths, same
CEFI_BASE_ASSET_UNIVERSE as linear venues. cefi_universe_capture_rule 2026-06-24.

v8 (2026-06-23): added 8 CeFi venues to the cefi rule ``venues`` set
(BYBIT-SPOT, COINBASE-SPOT, COINBASE-FUTURES, BITFINEX-SPOT, BITFINEX-FUTURES,
BITGET-SPOT, BITGET-FUTURES, UPBIT) — previously ABSENT so their cells were mvp=0
regardless of the perp-gate (cefi_universe_capture_rule 2026-06-23). Added the
**UPBIT venue carve-out** to :func:`is_in_mvp_capture_universe`
(``_CEFI_SPOT_PERP_GATE_EXEMPT_VENUES``): UPBIT spot is mvp=true REGARDLESS of
perp existence (the ONE spot-only venue exception — kimchi premium). KRW quote
acceptance for UPBIT is handled at the IS ``_passes_asset_filter`` gate via the UAC
``accepted_quotes_for_venue`` SSOT (registry/cefi_instrument_universe.py).

v7 (2026-06-23): expanded ``STAKING_SPOT_EXCEPTION`` from 13 → 28 members to
cover ALL wrapped + unwrapped LST/LRT equivalents (operator 2026-06-23,
cefi_universe_capture_rule — forward-looking allow-list, harmless extras). Added
ETH LSTs/LRTs FRXETH/SFRXETH (Frax), ANKRETH (Ankr), OSETH (StakeWise),
SWETH/RSWETH (Swell), ETHX (Stader), METH (Mantle), RSETH (Kelp), EZETH (Renzo),
PUFETH (Puffer), RSTETH; + SOL LSTs JSOL, SCNSOL, INF (Sanctum). Each is ALSO
added to ``CEFI_BASE_ASSET_UNIVERSE`` (subset invariant holds) so the cefi
``base_ccys`` content-hash flips with the constant.

v6 (2026-06-23): added the **staking-spot exception** to
:func:`is_in_mvp_capture_universe` — a base in ``STAKING_SPOT_EXCEPTION``
(EIGEN/KING/ETHFI restaking + STETH/WSTETH/RETH/WEETH/EETH/CBETH ETH-LSTs +
MSOL/JITOSOL/JTO/BSOL SOL-LSTs) has its SPOT captured on ANY venue that lists it
REGARDLESS of perp existence (the ONLY spot-without-perp carve-out; operator
2026-06-23, cefi_universe_capture_rule). Also expanded ``CEFI_BASE_ASSET_UNIVERSE``
by the 7 previously-absent LSTs (WSTETH/RETH/WEETH/EETH/MSOL/JITOSOL/BSOL) so the
base-membership leg passes for them — the cefi ``base_ccys`` content-hash flips
with the constant.

v5 (2026-06-23): added :func:`is_in_mvp_capture_universe` — the perp-gated CeFi
capture predicate (operator 2026-06-23). It composes the base-membership /
instrument-type / Deribit-options / TradFi-perp rules of :func:`is_mvp` with the
HARD perp-gate (a spot/dated-future cell is in-universe ONLY IF the venue also
lists a perp for the same base). ``MVP_SCOPE`` rule *content* is unchanged, but
the predicate surface (what "MVP capture universe" means) changed, so the
version bumps. ``cefi_universe_capture_rule_2026_06_23``.

v4 (2026-06-23): ``CEFI_BASE_ASSET_UNIVERSE`` expanded from the 44-coin MVP cap
to the curated, survivorship-bias-free capture set (legacy-44 +
top-100-mcap-aggregated-since-2019 + HL/ASTER perp bases, ~490 assets). CeFi
``base_ccys`` therefore now spans that wider universe; the content hash flips
automatically with the constant. ``options_base_ccys`` unchanged (BTC+ETH).

v3 (2026-06-17): CeFi venue set reconciled from the bare ``OKX`` token to the
canonical sub-venues ``OKX-SPOT`` / ``OKX-SWAP`` / ``OKX-FUTURES`` (the form the
instruments-store catalogue + the rest of the pipeline use), so OKX instruments
tag MVP. A bare ``OKX`` caller still resolves via the predicate's base-venue-token
normalisation (``_cefi_venue_in_rule``). Also introduced the unbound-data_type
convention in ``is_mvp`` (``data_type`` blank → "any MVP data_type") — predicate
behaviour, not config content, but versioned together. (mvp_instrument_universe_gap_audit
P2 #1 + #2.)

v2 (2026-06-17): CeFi ``base_ccys`` reconciled from the 4-base BTC/ETH/SOL/USDT
set to the (then) 44-base ``CEFI_BASE_ASSET_UNIVERSE`` (operator-confirmed SSOT),
added ``OPTION`` to CeFi ``instrument_types``, and added the Deribit-options
carve-out (``options_base_ccys = CEFI_OPTIONS_UNDERLYINGS`` = BTC+ETH only). The
content hash flips automatically with the version + content change.
"""


def _compute_mvp_scope_content_hash() -> str:
    """SHA-256 (16-hex prefix) of the canonical MVP_SCOPE content + version."""
    return compute_config_content_hash(
        MVP_SCOPE_CONFIG_VERSION,
        [(asset_group, MVP_SCOPE[asset_group]) for asset_group in sorted(MVP_SCOPE)],
    )


MVP_SCOPE_CONFIG_HASH: Final[str] = _compute_mvp_scope_content_hash()
"""Content hash of :data:`MVP_SCOPE` — flips IFF the scope content changes."""


def mvp_scope_config_descriptor() -> ConfigDescriptor:
    """Return the :data:`MVP_SCOPE` ``(version, content-hash)`` descriptor."""
    return ConfigDescriptor(MVP_SCOPE_CONFIG_VERSION, MVP_SCOPE_CONFIG_HASH)


def get_mvp_data_types_for_cefi_venue(venue: str) -> frozenset[str]:
    """Return the MVP data_type set for a CeFi *venue* (instrument-grain aware).

    Convenience helper for capture-time enforcement (backfill launchers, the
    MTDS orchestrator, live-VM data_type selection): given a canonical CeFi
    venue string, return the data_types that are MVP for that venue.  Callers
    can then REJECT any ``(venue, data_type)`` shard where ``data_type`` is NOT
    in the returned set — this is the code-level block so no VM ever spins for
    a non-MVP (venue x data_type) combination.

    Resolution order (mirrors :func:`is_mvp` for cefi):
      1. Per-venue override (``venue_data_types``) — highest priority.
      2. The union of all per-instrument_type overrides when ALL instrument_types
         for this venue have an ``instrument_type_data_types`` entry.  In
         practice today only OPTION → {options_chain} is declared, so the union
         for a typical cefi venue includes the flat set + options_chain.
      3. Flat ``data_types`` — default (trades + book_snapshot_5 + funding).

    For enforcement: if a launcher has ``data_type in {"book_snapshot_5"}`` and
    ``venue in {"COINBASE-SPOT", "COINBASE-FUTURES"}``, it should skip/reject
    the shard because ``book_snapshot_5 ∉ get_mvp_data_types_for_cefi_venue(venue)``.

    Args:
        venue: Canonical CeFi venue identifier (e.g. ``COINBASE-SPOT``,
            ``BINANCE-FUTURES``, ``DERIBIT``).

    Returns:
        Frozenset of MVP data_type strings for the venue.  An empty frozenset
        is returned only when the venue is not in the CeFi MVP rule (which
        means the venue is not MVP at all).

    Example::

        from unified_api_contracts import get_mvp_data_types_for_cefi_venue

        # COINBASE venues: trades only (no book5)
        assert "trades" in get_mvp_data_types_for_cefi_venue("COINBASE-SPOT")
        assert "book_snapshot_5" not in get_mvp_data_types_for_cefi_venue("COINBASE-SPOT")

        # Standard venue: trades + book5 + funding
        assert "book_snapshot_5" in get_mvp_data_types_for_cefi_venue("BINANCE-FUTURES")
    """
    rule = MVP_SCOPE.get("cefi")
    if not isinstance(rule, CeFiMvpRule):
        return frozenset()
    # Venue must be in the rule at all.
    if not _cefi_venue_in_rule(venue, rule.venues):
        return frozenset()
    # Per-venue override is the highest-priority gate.
    venue_override = _cefi_venue_data_type_set(venue, rule)
    if venue_override is not None:
        return venue_override
    # No per-venue override: return the flat set (the per-instrument_type
    # overrides are instrument_type-scoped so cannot be collapsed here without
    # knowing the instrument_type; callers that know the instrument_type should
    # call ``is_mvp`` directly for an exact gate).
    return rule.data_types


# ---------------------------------------------------------------------------
# Public predicate
# ---------------------------------------------------------------------------


def _data_type_in_rule(data_type: str | None, rule_data_types: frozenset[str]) -> bool:
    """Match a ``data_type`` against a rule's declared data_types — UNBOUND-aware.

    Convention (mvp_instrument_universe_gap_audit P2 #2, 2026-06-17): a blank
    ``data_type`` (``""`` / ``None``) means **"any MVP data_type"** — an
    instrument-grain caller carries no data_type axis (the instrument exists
    across ALL the AG's data_types), so the membership question is "is this
    (venue, instrument_type, base) MVP for ANY of the rule's data_types". A blank
    data_type therefore matches iff the rule declares at least one data_type
    (always true today). A NON-blank data_type must be an explicit member. This
    lets every single-grain consumer call ``is_mvp`` cleanly without inventing a
    fake "representative" data_type locally.
    """
    if not data_type:
        return bool(rule_data_types)
    return data_type in rule_data_types


def is_mvp(
    asset_group: str,
    venue: str,
    instrument_type: str,
    data_type: str | None = None,
    *,
    base_ccy: str | None = None,
    league: str | None = None,
    market_group: str | None = None,
    source: str | None = None,
) -> bool:
    """Return ``True`` iff the catalogue cell is within the MVP scope.

    A cell is MVP iff ALL of the following hold:

    1. ``asset_group`` is declared in :data:`MVP_SCOPE`.
    2. ``(venue, instrument_type)`` is declared in the rule for that
       ``asset_group``. For CeFi, a BARE ``OKX`` caller resolves to the
       canonical ``OKX-SPOT`` / ``OKX-SWAP`` / ``OKX-FUTURES`` sub-venues
       (:func:`_cefi_venue_in_rule`).
    3. ``data_type`` is declared in the rule, OR ``data_type`` is blank
       (``""`` / ``None``) — the **unbound / any-MVP-data_type** convention for
       instrument-grain callers (:func:`_data_type_in_rule`). A blank data_type
       matches when the rule declares at least one data_type.
    4. If the rule declares ``base_ccys`` (non-empty), ``base_ccy`` must
       be in that set.
    5. If the rule declares ``underliers`` (non-empty, TradFi only), the
       caller's ``venue`` maps to an underlier in that set. (The
       ``instrument_type`` already gates the venue; the underlier check is
       advisory — see the NOTE below.)
    6. If the rule declares ``sources`` (non-empty), ``source`` must be in
       that set.
    7. For sports: ``league`` must be in the rule's ``leagues`` set.
    8. For prediction: if the rule declares ``market_groups`` (non-empty),
       ``market_group`` must be in that set.

    NOTE on TradFi underlier filtering:
        The ``underlier`` axis in :class:`TradFiMvpRule` gates which
        underlying indices are in scope (ES/NQ/VX). This is checked by
        looking for ``base_ccy`` (which carries the underlier code for
        TradFi futures — e.g. ``"ES"`` for an ES future). If ``base_ccy``
        is provided AND the rule has ``underliers``, it must be in the set.

    Args:
        asset_group: Lowercase asset-group key
            (``cefi`` / ``defi`` / ``tradfi`` / ``sports`` / ``prediction``).
        venue: Canonical venue identifier.
        instrument_type: Canonical instrument type string
            (a :class:`~unified_api_contracts.InstrumentType` string value).
        data_type: Canonical data_type string.
        base_ccy: Optional base currency or underlier code. Used for CeFi
            base_ccy filtering and TradFi underlier filtering.
        league: Sports league ID (e.g. ``"EPL"``, ``"NFL"``).
        market_group: Prediction market category (e.g. ``"crypto"``,
            ``"politics"``).
        source: Source key (e.g. ``"tardis"``, ``"databento"``).

    Returns:
        ``True`` if the cell is within the MVP scope; ``False`` otherwise.

    Example::

        from unified_api_contracts import is_mvp

        # CeFi BTC perpetual trade on Binance — in MVP scope
        assert is_mvp("cefi", "BINANCE-FUTURES", "PERPETUAL", "trades",
                      base_ccy="BTC")

        # A non-MVP venue — not in scope
        assert not is_mvp("cefi", "UPBIT", "SPOT_PAIR", "trades")

        # TradFi ES future — in MVP scope
        assert is_mvp("tradfi", "CME", "FUTURE", "trades",
                      base_ccy="ES")

        # Same venue/instrument_type, different expiry — ALSO in MVP scope
        # (grain is everything-or-nothing per venue/instrument_type)
        assert is_mvp("tradfi", "CME", "FUTURE", "trades",
                      base_ccy="ES")  # ESH26 and ESM26 both → True
    """
    rule = MVP_SCOPE.get(asset_group)
    if rule is None or isinstance(rule, FeaturesModelsMvpStub):
        return False

    if isinstance(rule, CeFiMvpRule):
        # Axis 1+2: venue + instrument_type (OKX bare → sub-venue aware)
        if not _cefi_venue_in_rule(venue, rule.venues):
            return False
        if instrument_type not in rule.instrument_types:
            return False
        # Axis 3: data_type (blank → any MVP data_type, unbound-grain convention).
        # Resolution order for the effective data_type set (v11):
        #   1. PER-VENUE OVERRIDE (``venue_data_types``) — highest priority.
        #      When the venue has a declared data_type set (e.g. COINBASE →
        #      {trades}, DERIBIT → {options_chain}), that set is final for ALL
        #      instrument_types at that venue.  The per-instrument_type override
        #      below does NOT apply when the venue override is set.
        #   2. PER-INSTRUMENT_TYPE OVERRIDE (``instrument_type_data_types``) —
        #      applies when the venue has NO override. Today OPTION →
        #      {options_chain} only (Deribit BTC/ETH options; this is now
        #      redundant for DERIBIT but kept for any other OPTION rows).
        #   3. FLAT ``data_types`` set — default when no override applies.
        _venue_dt_set = _cefi_venue_data_type_set(venue, rule)
        if _venue_dt_set is not None:
            _dt_set: frozenset[str] = _venue_dt_set
        else:
            _it_norm = (instrument_type or "").strip().upper()
            _dt_set = rule.instrument_type_data_types.get(_it_norm, rule.data_types)
        if not _data_type_in_rule(data_type, _dt_set):
            return False
        # Axis 4: base_ccy (optional — if rule has a non-empty set, must match).
        # OPTION cells use the narrower options carve-out (Deribit-options =
        # BTC+ETH only) when ``options_base_ccys`` is declared; spot/perp legs
        # use the full ``base_ccys`` universe.
        if instrument_type == "OPTION" and rule.options_base_ccys:
            if base_ccy not in rule.options_base_ccys:
                return False
        elif rule.base_ccys and base_ccy not in rule.base_ccys:
            return False
        # Axis 5: source (optional)
        return not (rule.sources and source not in rule.sources)

    if isinstance(rule, DeFiMvpRule):
        if venue not in rule.venues:
            return False
        if instrument_type not in rule.instrument_types:
            return False
        if not _data_type_in_rule(data_type, rule.data_types):
            return False
        return not (rule.sources and source not in rule.sources)

    if isinstance(rule, TradFiMvpRule):
        # Equity-basis carve-out (2026-06-24): the DBEQ.BASIC cash equities/ETFs
        # that BACK a Binance tradfi-perp are the basis-reference leg of the
        # equity-basis arb archetype → MVP-scoped, gated to the basis universe.
        # This is a SEPARATE gate from the CME futures complex (a flat AND across
        # venues+types+underliers cannot express "(CME x FUTURE x {ES,NQ,VX}) OR
        # (NASDAQ/NYSE/ARCA/KRX x EQUITY/ETF x basis-universe)" — mirrors the cefi
        # OPTION venue carve-out pattern). data_type is still gated by the rule.
        # KRX (2026-06-24): the Korean single-stock underliers of the Binance
        # tradfi-perps are venue=KRX / source=yahoo (no US-listed twin) — added to
        # the equity-venue set so their basis cells are MVP. ``rule.sources`` is
        # empty so source=yahoo passes (US equities are databento; both in scope).
        _itype = (instrument_type or "").strip().upper()
        _venue_root = (venue or "").strip().upper().split("-", 1)[0]
        if _itype in ("EQUITY", "ETF") and _venue_root in ("NASDAQ", "NYSE", "ARCA", "AMEX", "BATS", "KRX"):
            if not _data_type_in_rule(data_type, rule.data_types):
                return False
            if (base_ccy or "").strip().upper() not in {t.upper() for t in TRADFI_EQUITY_PERP_BASIS_UNIVERSE}:
                return False
            return not (rule.sources and source not in rule.sources)
        # CME futures complex (ES/NQ/VX) — the original flat-AND rule.
        if venue not in rule.venues:
            return False
        if instrument_type not in rule.instrument_types:
            return False
        if not _data_type_in_rule(data_type, rule.data_types):
            return False
        # Axis: underlier — base_ccy carries the underlier code for TradFi
        if rule.underliers and base_ccy not in rule.underliers:
            return False
        return not (rule.sources and source not in rule.sources)

    if isinstance(rule, SportsMvpRule):
        # Sports cells are keyed by (league, data_type); venue/instrument_type
        # are not axes in the sports MVP rule (the venues are data-source
        # providers, not instrument classification axes for sports).
        if league not in rule.leagues:
            return False
        return _data_type_in_rule(data_type, rule.data_types)

    if isinstance(rule, PredictionMvpRule):
        if venue not in rule.venues:
            return False
        if not _data_type_in_rule(data_type, rule.data_types):
            return False
        # market_group is the UNBOUND axis (mirrors the data_type convention): a
        # blank/None market_group means "any MVP market_group" — an
        # instrument-grain catalogue row carries no market_group axis, so the
        # venue/data_type axes decide membership. Without this, every prediction
        # catalogue row (the IS rollup never passes market_group) tagged mvp=0
        # despite POLYMARKET/KALSHI being in-MVP (decision #5). A NON-blank
        # market_group is still gated against the rule set.
        if rule.market_groups and market_group and market_group not in rule.market_groups:
            return False
        return not (rule.sources and source not in rule.sources)

    # Unknown rule type — conservative default: not MVP
    return False  # pragma: no cover


# ---------------------------------------------------------------------------
# CeFi MVP CAPTURE universe — the perp-gated capture predicate (the SSOT the
# three capture consumers MUST agree on).
#
# ``is_mvp`` above answers "is this (asset_group, venue, instrument_type, base,
# data_type) cell in the MVP scope rule" — base-membership + instrument-type +
# the Deribit-options/TradFi-perp carve-outs. It does NOT enforce the
# **HARD perp-gate** (operator 2026-06-23): a SPOT instrument is captured ONLY
# IF that venue also lists a PERP for the same base at that time. That gate
# needs an extra fact — ``has_perp_for_base`` — that ``is_mvp`` cannot derive
# from a single cell, so it lives in a dedicated capture predicate that the
# catalogue rollup (which sees ALL instruments per venue/day and so can compute
# ``has_perp_for_base``), the MTDS capture-universe derivation, and the
# expected_unattempted enumerator + manifest reclassifier all call. ONE
# implementation → no drift (shard-granularity SSOT).
#
# Rule (per (venue, base, instrument_type), keyed on a per-(venue,base,day)
# ``has_perp_for_base`` flag the caller computes from the full catalogue):
#   - base ∈ the CeFi capture universe (``is_mvp`` base-membership). NECESSARY
#     but NOT sufficient.
#   - PERPETUAL / EQUITY_PERP  ⇒ MVP on base-membership (the perp IS the gate;
#     a TradFi-linked equity perp rides ``CEFI_EQUITY_PERP_BASE_UNIVERSE``).
#   - SPOT_PAIR / SPOT_ASSET   ⇒ MVP ONLY IF ``has_perp_for_base`` (the venue
#     also lists a perp for that base). spot-and-no-perp ⇒ DROP (even top-100).
#   - FUTURE (dated/quarterly, shares a universe base) ⇒ MVP on base-membership
#     + venue, NOT perp-gated (operator 2026-06-23: dated futures are part of the
#     futures complex sharing the base and are included for any universe base the
#     venue lists). ``has_perp_for_base`` is irrelevant for a dated future.
#   - OPTION                   ⇒ MVP ONLY for venue==DERIBIT AND base∈{BTC,ETH}
#     (the Deribit-options carve-out, via ``is_mvp``); ``has_perp_for_base`` is
#     NOT required for options (Deribit options are the carve-out, not perp-gated).
#   - anything else / base not in universe / venue not in rule ⇒ NOT MVP.
# ---------------------------------------------------------------------------

#: CeFi instrument types whose MVP membership is gated on the venue also listing
#: a PERP for the same base — SPOT legs ONLY. (operator 2026-06-23: spot-and-no-perp
#: ⇒ drop. Dated FUTURES are NOT perp-gated — they ride base-membership + venue,
#: as part of the futures complex sharing the base.)
_CEFI_PERP_GATED_TYPES: Final[frozenset[str]] = frozenset(
    {
        "SPOT_PAIR",  # InstrumentType.SPOT_PAIR
        "SPOT_ASSET",  # InstrumentType.SPOT_ASSET
    }
)

#: CeFi DATED-FUTURES types — MVP on base-membership + venue (NOT perp-gated).
#: Dated/quarterly futures sharing a universe base (e.g. BTC-27JUN25) are part of
#: the futures complex; per the operator spec they're included for any universe
#: base the venue lists, independent of a sibling perp.
_CEFI_DATED_FUTURE_TYPES: Final[frozenset[str]] = frozenset(
    {
        "FUTURE",  # InstrumentType.FUTURE
    }
)

#: CeFi instrument types that ARE perps (self-qualify the perp-gate on base-membership).
_CEFI_PERP_TYPES: Final[frozenset[str]] = frozenset(
    {
        "PERPETUAL",  # InstrumentType.PERPETUAL
        "EQUITY_PERP",  # InstrumentType.EQUITY_PERP — TradFi-linked single-stock perps
    }
)

#: Venue ENTITY prefixes (split on '-') that are exempt from the SPOT perp-gate —
#: their SPOT is mvp=true REGARDLESS of perp existence (operator 2026-06-23,
#: cefi_universe_capture_rule). UPBIT is the ONE such venue: it lists NO perps
#: (Korean spot-only exchange) but we capture all its spot pairs for the kimchi
#: premium + cross-currency dispersion. This is a VENUE-scoped exception, distinct
#: from the BASE-scoped ``STAKING_SPOT_EXCEPTION`` (LSTs on any venue).
_CEFI_SPOT_PERP_GATE_EXEMPT_VENUES: Final[frozenset[str]] = frozenset({"UPBIT"})


def is_in_mvp_capture_universe(
    venue: str,
    base: str,
    instrument_type: str,
    *,
    has_perp_for_base: bool,
    source: str | None = None,
) -> bool:
    """Return ``True`` iff the CeFi cell is in the **MVP capture universe**.

    The shared SSOT predicate (operator 2026-06-23) consumed by the THREE
    capture consumers that MUST agree (drift = silent correctness bug):

    1. the IS catalogue rollup ``_add_mvp_column`` (tags the ``mvp`` column);
    2. the MTDS cefi capture-universe derivation (what tick data we download);
    3. the ``expected_unattempted`` enumerator + manifest reclassifier
       (honest-coverage denominator).

    It composes the base-membership / instrument-type / Deribit-options /
    TradFi-perp rules from :func:`is_mvp` (cefi asset group, unbound data_type)
    with the **HARD perp-gate**: a spot/dated-future cell is in-universe ONLY
    IF the venue also lists a perp for the same base at that time
    (``has_perp_for_base``). A PERP/EQUITY_PERP self-qualifies on
    base-membership; an OPTION rides the Deribit BTC/ETH carve-out (not
    perp-gated).

    Args:
        venue: Canonical CeFi venue id (``BINANCE-SPOT`` / ``OKX-SWAP`` / …; a
            bare ``OKX`` resolves to its sub-venues via :func:`is_mvp`).
        base: Base asset / underlying (``BTC``, ``ETH``, ``AAPL`` for an equity
            perp, …) — the axis the universe-membership rule gates on.
        instrument_type: Canonical :class:`InstrumentType` string value.
        has_perp_for_base: Whether the SAME venue lists a PERPETUAL (or
            EQUITY_PERP) for ``base`` at the relevant time. The caller computes
            this from the full catalogue (per venue/day). Ignored for
            PERP/EQUITY_PERP/OPTION cells (they don't need a sibling perp).
        source: Optional source key (passed through to :func:`is_mvp`).

    Returns:
        ``True`` iff the cell is in the MVP capture universe.
    """
    itype = (instrument_type or "").strip().upper()

    # OPTION: Deribit BTC/ETH carve-out ONLY — NOT perp-gated. The venue MUST be
    # DERIBIT (the is_mvp options carve-out only narrows base_ccy to BTC/ETH, but
    # the cefi venue set also contains BINANCE/OKX/… so a bare is_mvp("OPTION")
    # would wrongly pass a Binance BTC option — operator: options mvp ONLY for
    # venue==deribit). Gate the venue explicitly here.
    if itype == "OPTION":
        if venue.strip().upper().split("-", 1)[0] != "DERIBIT":
            return False
        return is_mvp(
            "cefi",
            venue=venue,
            instrument_type="OPTION",
            base_ccy=base,
            source=source,
        )

    # PERP / EQUITY_PERP: in-universe on base-membership (the perp IS the gate).
    if itype in _CEFI_PERP_TYPES:
        return is_mvp(
            "cefi",
            venue=venue,
            instrument_type=itype,
            base_ccy=base,
            source=source,
        )

    # SPOT: base-membership AND the venue lists a perp for the base (HARD perp-gate)
    # — EXCEPT the staking/restaking/LST allow-list (STAKING_SPOT_EXCEPTION,
    # operator 2026-06-23): a base in that set has its SPOT captured on ANY venue
    # that lists it, REGARDLESS of perp existence (the carry_staked_basis legs).
    # This is the ONLY spot-without-perp carve-out.
    if itype in _CEFI_PERP_GATED_TYPES:
        base_in_staking_exception = (base or "").strip().upper() in STAKING_SPOT_EXCEPTION
        venue_exempt = (venue or "").strip().upper().split("-", 1)[0] in _CEFI_SPOT_PERP_GATE_EXEMPT_VENUES
        if not has_perp_for_base and not base_in_staking_exception and not venue_exempt:
            return False
        return is_mvp(
            "cefi",
            venue=venue,
            instrument_type=itype,
            base_ccy=base,
            source=source,
        )

    # DATED FUTURE: base-membership + venue only (NOT perp-gated — part of the
    # futures complex sharing the base; operator 2026-06-23).
    if itype in _CEFI_DATED_FUTURE_TYPES:
        return is_mvp(
            "cefi",
            venue=venue,
            instrument_type=itype,
            base_ccy=base,
            source=source,
        )

    # TOKENIZED_EQUITY and any other type: defer to the base rule (no extra
    # perp-gate — tokenized equities are an explicit allow-listed type, not a
    # spot-needs-perp case). Out-of-rule types fall through to is_mvp → False.
    return is_mvp(
        "cefi",
        venue=venue,
        instrument_type=itype,
        base_ccy=base,
        source=source,
    )


# ---------------------------------------------------------------------------
# MVP-for-MDPS  =  MVP-for-MDS  (Concept 1 — same venue/instrument set)
#
# Plan: ``plans/active/mvp_for_mdps_and_features_universe_uac_2026_06_28.md``.
#
# MDPS does NOT maintain its own processing screen — it processes exactly the
# instruments-catalogue cells MDS (market-tick-data-service) captures for the
# asset group.  ``mdps_mvp_universe`` exposes that derived set so the "what
# must MDPS cover" question is COMPUTED from ``MVP_SCOPE``, never coordinated
# by hand — a separate hand-maintained list is the drift surface this helper
# eliminates.
#
# Grain: ``frozenset[tuple[venue, instrument_type]]``.  This is the axis pair
# every market-data AG's MVP rule declares.  The per-(venue, base, day)
# capture predicate (:func:`is_in_mvp_capture_universe`) decides per-instrument
# membership at a finer grain (with the perp-gate, base-membership, the
# Deribit-options carve-out, etc.) — the MDPS universe at the (venue,
# instrument_type) grain is the REACHABLE projection of that predicate, which
# for cefi/defi equals the rule's ``venues x instrument_types`` Cartesian
# product, and for tradfi adds the equity-basis carve-out cells the predicate's
# tradfi branch hardcodes.
#
# Sports / prediction MVP rules have NO ``instrument_types`` axis (sports keys
# on league + data_type; prediction on venue + market_group) — MDPS handles
# market-data AGs only (CLAUDE.md "MTDS is market-data only"), so the helper
# raises ``ValueError`` for those AGs rather than returning a misleading empty
# set.
# ---------------------------------------------------------------------------


#: TradFi equity-basis venues — the cash equity twin of every Binance tradfi
#: perp underlier (NASDAQ/NYSE/ARCA/AMEX/BATS for US equities; KRX for the Korean
#: single-stock twins).  The ``is_mvp`` tradfi branch hardcodes this venue set
#: as the equity-basis carve-out (separate from the CME futures complex);
#: mirrored here so the MDPS universe derivation matches the predicate's
#: reachable ``(venue, instrument_type)`` set.  Keep in lockstep with the tuple
#: in :func:`is_mvp`.
_TRADFI_EQUITY_BASIS_VENUES: Final[frozenset[str]] = frozenset({"NASDAQ", "NYSE", "ARCA", "AMEX", "BATS", "KRX"})

#: TradFi equity-basis instrument types — single-name equities + ETFs that back
#: a Binance tradfi-perp.  Mirrors the ``is_mvp`` tradfi branch's instrument-type
#: gate for the equity-basis carve-out.
_TRADFI_EQUITY_BASIS_TYPES: Final[frozenset[str]] = frozenset({"EQUITY", "ETF"})


def mdps_mvp_universe(asset_group: str) -> frozenset[tuple[str, str]]:
    """Return the ``(venue, instrument_type)`` cells MDPS processes for *asset_group*.

    MVP-for-MDPS == MVP-for-MDS: MDPS processes exactly the catalogue cells
    MDS captures for the asset group (Concept 1, plan
    ``mvp_for_mdps_and_features_universe_uac_2026_06_28.md``).  The returned
    set is DERIVED from :data:`MVP_SCOPE` so identity with the MDS capture
    universe is structural — there is no separate hand-maintained MDPS list.

    Per-AG composition (matches the reachable projection of
    :func:`is_in_mvp_capture_universe` / :func:`is_mvp` at the
    ``(venue, instrument_type)`` grain):

    * **cefi / defi** — ``rule.venues x rule.instrument_types``.  The Deribit-
      options carve-out, perp-gate, base-membership, and the per-venue /
      per-instrument_type data_type overrides all apply at the INSTRUMENT grain
      (per-base, per-cell) downstream of this set — at the AG/axis grain every
      declared ``(venue, instrument_type)`` pair is reachable.
    * **tradfi** — ``rule.venues x rule.instrument_types`` PLUS the equity-basis
      carve-out cells :data:`_TRADFI_EQUITY_BASIS_VENUES` x
      :data:`_TRADFI_EQUITY_BASIS_TYPES` (the cash equity twins of Binance
      tradfi-perp underliers, hardcoded in :func:`is_mvp`'s tradfi branch).
    * **sports / prediction** — no ``instrument_type`` axis at the MDPS grain
      (sports keys on ``league``; prediction on ``venue x market_group``); MDPS
      handles market-data AGs only.  Raises :class:`ValueError`.

    Args:
        asset_group: Lowercase asset-group key.  Must be one of
            ``cefi`` / ``defi`` / ``tradfi`` (the market-data AGs MDPS processes).

    Returns:
        Frozenset of canonical ``(venue, instrument_type)`` pairs.  Empty
        frozenset only if *asset_group* names a Phase-2+ stub
        (``features`` / ``strategy`` / ``models``) that has no rule yet.

    Raises:
        ValueError: *asset_group* is unknown, or is ``sports`` / ``prediction``
            (no ``instrument_type`` axis — MDPS handles market-data AGs only).

    Example::

        from unified_api_contracts import mdps_mvp_universe

        cefi_cells = mdps_mvp_universe("cefi")
        assert ("BINANCE-FUTURES", "PERPETUAL") in cefi_cells
        assert ("DERIBIT", "OPTION") in cefi_cells
        assert ("CME", "FUTURE") in mdps_mvp_universe("tradfi")
        assert ("NASDAQ", "EQUITY") in mdps_mvp_universe("tradfi")
    """
    rule = MVP_SCOPE.get(asset_group)
    if rule is None:
        raise ValueError(f"mdps_mvp_universe: unknown asset_group {asset_group!r} (not declared in MVP_SCOPE)")
    if isinstance(rule, FeaturesModelsMvpStub):
        return frozenset()
    if isinstance(rule, CeFiMvpRule | DeFiMvpRule):
        return frozenset((v, it) for v in rule.venues for it in rule.instrument_types)
    if isinstance(rule, TradFiMvpRule):
        cells: set[tuple[str, str]] = {(v, it) for v in rule.venues for it in rule.instrument_types}
        cells.update((v, it) for v in _TRADFI_EQUITY_BASIS_VENUES for it in _TRADFI_EQUITY_BASIS_TYPES)
        return frozenset(cells)
    # SportsMvpRule / PredictionMvpRule — no (venue, instrument_type) axis at
    # the MDPS grain. MDPS handles market-data AGs only.
    raise ValueError(
        f"mdps_mvp_universe: asset_group {asset_group!r} has no (venue, instrument_type) axis — "
        "MDPS handles market-data AGs (cefi/defi/tradfi) only."
    )
