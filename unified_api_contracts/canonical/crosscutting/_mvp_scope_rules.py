"""MVP scope typed rule dataclasses + the ``MVP_SCOPE`` config itself.

Split out of ``mvp_scope.py`` (900-line file-size QG, 2026-07-09) — pure
file-organization move, no behavior change. ``mvp_scope.py`` re-exports
everything here so the public import path
(``unified_api_contracts.canonical.crosscutting.mvp_scope``) is unchanged.

See ``mvp_scope.py`` for the full module-level doc (hierarchy, grain,
phase-1 scope). This module owns:
    * The 6 typed, immutable rule dataclasses (one per asset_group + the
      Phase-2+ stub).
    * The 3 config-build helper functions (``_mvp_football_league_ids`` /
      ``_mvp_defi_venues`` / ``_mvp_defi_data_types``).
    * The ``MVP_SCOPE`` dict itself — the single global config.

SSOT: ``plans/active/mvp_scope_catalogue_tagging_2026_06_08.md``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

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
            data_types are MVP for that instrument_type (a FULL REPLACEMENT) —
            the flat ``data_types`` set does NOT apply to it. Entries:
              * ``OPTION -> {options_chain}``: a Deribit option's MVP MTDS
                data_type is the options_chain bundle ONLY (it carries marks +
                IVs — sufficient); per-strike ``trades`` + ``book_snapshot_5``
                are EXCLUDED for options (too heavy / ~12k API calls/day vs 1).
              * ``PERPETUAL -> {trades, book_snapshot_5, derivative_ticker,
                funding_rate, liquidations}`` (2026-07-15): the flat tick set
                PLUS ``liquidations`` — a PERPETUAL-leg CeFi MVP data_type. It is
                declared on PERPETUAL ONLY (not the flat set, which would
                over-claim SPOT_PAIR; not FUTURE, where captured liq
                is negligible). The venue axis is gated separately by
                ``VENUE_DATA_TYPE_CAPABILITIES`` to the 6 perp venues that carry
                a real liquidations feed.
            An instrument_type ABSENT from this map uses the flat ``data_types``
            set unchanged (spot/dated-futures = trades + book_snapshot_5 +
            funding).
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
            underlier codes are MVP. Applies to non-OPTION instrument_types
            (FUTURE); OPTION cells use ``option_underliers`` instead when it
            is declared (mirrors the CeFi ``options_base_ccys`` narrower
            options carve-out pattern).
        option_underliers: Optional frozenset of underlier ROOT codes that
            applies ONLY to ``instrument_type == "OPTION"`` cells (operator
            2026-07-14 ruling: "tradfi MVP options scope = the S&P 500
            complex ONLY" — options on non-ES underliers, e.g. GC/CL/NG/NQ,
            are explicitly OUT of tradfi MVP even though those roots remain
            MVP for FUTURE/equity-basis cells). When non-empty, an OPTION
            cell is MVP iff its resolved underlying future ROOT is in this
            set (``underliers`` is NOT applied to OPTION cells). Empty →
            fall back to ``underliers`` (pre-2026-07-14 behavior: every
            underlier root's options were MVP, same as its futures).
        sources: Optional frozenset of source strings.
    """

    venues: frozenset[str]
    instrument_types: frozenset[str]
    data_types: frozenset[str]
    underliers: frozenset[str] = field(default_factory=frozenset)
    option_underliers: frozenset[str] = field(default_factory=frozenset)
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
# TradFi MVP OPTION underlying-root narrowing (operator ruling, 2026-07-14,
# tradfi_eu_not_draining_source_axis_drift_2026_06_24.md).
# ---------------------------------------------------------------------------
# Verbatim operator intent: "We DO want tradfi options for S&P 500 — options
# and futures — but NO other options in tradfi MVP; just the single stocks,
# ETFs and futures already in MVP." I.e. tradfi MVP OPTION scope narrows to
# the S&P 500 complex ONLY (options on the ES root, the S&P 500 future that
# is already MVP) — GC/CL/NG/SI/PL/PA/HG/NQ/VX options are explicitly OUT of
# MVP even though those roots stay MVP for FUTURE cells (unchanged) and for
# the equity-basis carve-out (unchanged).
#
# Root only, not a Databento sub-code list: ``build_instrument_catalogue.py``
# ``_tradfi_contract_code_to_root`` already resolves an OPTION row's specific
# underlying future contract code (e.g. ``ESZ5``) down to its canonical root
# (``ES``) before calling ``is_mvp`` — so every S&P 500 options sub-series
# (quarterly ES.OPT, weekly EW/EW1/EW2/EW4.OPT, daily E1A-E5A.OPT, EOM.OPT)
# resolves to the SAME root "ES" and is covered by this one-element set. No
# separate "MES" entry is needed today: there is no declared MES.OPT product
# in ``TRADFI_DATABENTO_INSTRUMENTS`` (micros only exist as FUTURE contracts),
# so a micro-options root can never actually appear at the catalogue-tagging
# layer; if a MES options product is added in the future, "MES" would need to
# be added here explicitly (deliberately not derived/implicit) — MES is not
# itself a member of ``TradFiMvpRule.underliers`` (only "ES" is), so it would
# not silently inherit MVP status without an explicit addition. Registry-idiom
# name mirrors the `MVP_CME_EXCHANGE_CODES` derivation style in
# `registry/tradfi_instrument_universe.py`.
TRADFI_MVP_OPTION_UNDERLYING_ROOTS: Final[frozenset[str]] = frozenset({"ES"})


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
                # On-chain CLOB perp venues (LIGHTER / EXTENDED) — classified as
                # CEFI everywhere (venue_mapping all_cefi_onchain_clob_venues +
                # VENUES_BY_ASSET_GROUP["cefi"] + is_cefi_venue), but previously
                # ABSENT from this MVP rule so their PERPETUAL cells tagged mvp=0
                # (instruments-vs-MTDS drift). Added cefi here for BOTH
                # instruments + MTDS (operator 2026-06-27 decision #4). Both are
                # CLOB-based perp DEXs (confirmed: same CLOB capture surface as
                # HL/ASTER — trades + book_snapshot_5 + derivative_ticker).
                # (PACIFICA (Solana) was a third venue here, forward-poll-only
                # for tick, until removed entirely 2026-07-16 — operator ruling:
                # all Solana perp DEXes dropped except Jupiter, not integrated.)
                "LIGHTER-ZKSYNC",
                "EXTENDED-STARKNET",
                # NOTE (operator 2026-06-27 decision #3): BINANCE-DELIVERY (Binance
                # COIN-M inverse/delivery futures) was REMOVED from the cefi MVP
                # set — the operator accepts COIN-M delivery is NOT MVP. Other
                # venues' dated/quarterly fixed-delivery futures STAY MVP (the
                # FUTURE instrument_type below + the dated-future capture path).
                # DERIBIT-COMBO (operator 2026-07-10, decision #6 on
                # cefi_layer1_denominator_gaps_2026_07_03.md's
                # BLOCKED-OPERATOR-DECISION): a declared cefi venue
                # (VENUES_BY_ASSET_GROUP["cefi"]) with real captured data but
                # previously ABSENT from this rule's ``venues`` set, so
                # ``get_mvp_data_types_for_cefi_venue()`` silently returned
                # frozenset() and its Layer-1 EXPECTED was always 0 — the exact
                # "entire venue absent from the denominator" dishonesty class
                # honest-coverage v2 exists to kill. Operator decision: keep it
                # declared (add it), not confirm out-of-MVP. See the
                # ``venue_data_types`` override below for its per-venue
                # data_type scoping.
                #
                # NOTE: the same decision #6 also named bare "COINBASE" for this
                # treatment. NOT added here — `coinbase_bare_name_migration_
                # 2026_07_06.md` (operator decision #3, same 12-decision batch)
                # is an ACTIVE, dispatched 7-step plan whose explicit goal is to
                # retire bare "COINBASE" workspace-wide in favor of the sole
                # canonical "COINBASE-SPOT" key (already declared here, already
                # trades-only scoped below) — adding a new dependency on the
                # bare key here would work directly against that migration.
                # COINBASE-SPOT already satisfies decision #6's real intent
                # (denominator correctness + trades-only cost control for the
                # Coinbase spot product).
                "DERIBIT-COMBO",
                # Coinbase Derivatives Exchange (CDE) — 2026-07-10,
                # COINBASE-FUTURES/#3-vs-#8 resolution (instruments_remaining_work_audit_
                # 2026_07_10.md Progress Log). FUTURE-only venue (real dated futures +
                # far-dated "nano perpetual" contracts, 99 live products confirmed via
                # api.coinbase.com Advanced Trade REST); rides base-membership + venue
                # via the dated-future rule (NOT perp-gated — no PERPETUAL sibling
                # needed, see _mvp_scope_capture.py _CEFI_DATED_FUTURE_TYPES). A
                # SEPARATE venue from COINBASE-FUTURES (Coinbase INTX) — zero Tardis
                # coverage under any name.
                "COINBASE-CDE",
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
                # Crypto-venue equity instruments (operator 2026-07-16): NO longer a
                # distinct EQUITY_PERP/TOKENIZED_EQUITY type — instrument_type is the
                # BROAD mechanics type only. A single-stock perp gates here as
                # ``PERPETUAL`` and a tokenized stock as ``SPOT_PAIR``; their equity
                # bases (META/NVDA/AAPL/…) ride ``CEFI_EQUITY_PERP_BASE_UNIVERSE``,
                # already unioned into ``base_ccys`` below, so they stay MVP. The
                # equity identity is carried by the catalogue ``is_equity_perp`` /
                # ``tracks_equity`` tags (IS rollup), NOT by a scoped instrument_type.
                # InstrumentType.COMBO — Deribit multi-leg combo/spread instruments
                # (operator decision, cefi_deribit_combo_and_okx_bare_venue_gaps_
                # 2026_07_12.md, 2026-07-16): the instruments-service catalogue tags
                # DERIBIT-COMBO rows with instrument_type "COMBO" (a distinct
                # InstrumentType from "OPTION" — see _instrument_enums.py), so
                # without this entry is_mvp() unconditionally returned False for
                # every one of the 68,847 now-fully-backfilled DERIBIT-COMBO
                # catalogue rows regardless of base_ccy/available_from — the exact
                # "entire venue silently excluded from the denominator" dishonesty
                # class honest-coverage v2 exists to kill (same precedent as the
                # DERIBIT-COMBO venues-set addition above, operator decision #6,
                # 2026-07-10). The DERIBIT-COMBO ``venue_data_types`` override below
                # already scopes its effective data_type set to {trades,
                # book_snapshot_5} (NOT options_chain) independent of
                # instrument_type, so adding "COMBO" here does not risk minting a
                # phantom options_chain cell. "COMBO" is ALSO used by TradFi
                # Databento spread/bag instruments (external/databento/
                # databento_classifier.py) — but those route through the SEPARATE
                # ``TradFiMvpRule`` instance, so this CeFi-scoped addition cannot
                # leak into TradFi's MVP predicate.
                "COMBO",  # InstrumentType.COMBO (Deribit multi-leg combo/spread)
            }
        ),
        # FLAT data_types — apply to SPOT_PAIR / PERPETUAL / FUTURE (everything
        # EXCEPT the OPTION override below):
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
        # PER-INSTRUMENT_TYPE data_type overrides (each a FULL REPLACEMENT of the
        # flat ``data_types`` set for that instrument_type):
        #   OPTION → {options_chain} (operator 2026-06-27 decision #2 — cost cut):
        #     a Deribit OPTION's MVP MTDS data_type is the ``options_chain`` bundle
        #     ONLY (marks + IVs — sufficient for the VOL_* strategy/ML family).
        #     Per-strike ``trades`` + ``book_snapshot_5`` are EXCLUDED for options
        #     (~12k API calls/day per-strike vs 1 bulk chain call/day; full
        #     per-option tick is only needed for execution-quality analysis).
        #   PERPETUAL → the flat tick set + ``liquidations`` (2026-07-15, workstream
        #     E of cefi_completion_program_2026_07_15.md): ``liquidations`` is a
        #     PERPETUAL-leg CeFi MVP data_type — densely captured (732,751 captured
        #     PERPETUAL manifest rows; 99.95% of all captured cefi liquidations) on
        #     the perp venues that carry a real liquidations feed. The VENUE axis is
        #     gated SEPARATELY by ``VENUE_DATA_TYPE_CAPABILITIES`` (market_data_
        #     categories.py) to exactly the 6 real-feed venues: BINANCE-FUTURES /
        #     OKX-SWAP / BYBIT / KRAKEN-FUTURES / BITFINEX-FUTURES / BITGET-FUTURES.
        #     Declared on PERPETUAL ONLY — NOT the flat ``data_types`` set (would
        #     over-claim SPOT_PAIR), NOT FUTURE (dated-futures liq is
        #     negligible — 221 captured FUTURE rows / 0.03%). Reconciles the
        #     un-superseded ``mvp-universe.yaml`` ("liquidations P1-critical for
        #     CEFI") vs the prior CeFiMvpRule omission (liquidations pulled
        #     2026-06-29, never restored). CeFiMvpRule is the live SSOT.
        #     NOTE: the enumerator applies this per-itype set via the itype-aware
        #     ``get_mvp_data_types_for_cefi_venue_itype`` helper so the venue
        #     ``venue_data_types`` overrides (e.g. COINBASE-FUTURES → {trades}) are
        #     STILL respected for PERPETUAL cells (no over-seed).
        instrument_type_data_types={
            "OPTION": frozenset({"options_chain"}),
            "PERPETUAL": frozenset({"trades", "book_snapshot_5", "derivative_ticker", "funding_rate", "liquidations"}),
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
            # DERIBIT-COMBO (operator 2026-07-10, decision #6): a DISTINCT venue
            # from bare DERIBIT (multi-leg combo/spread instruments — see
            # VENUES_BY_ASSET_GROUP["cefi"] comment). Its real declared capture
            # capability (data_type_capability.py DataTypeCapability entries,
            # VENUE_DATA_TYPE_CAPABILITIES["DERIBIT-COMBO"]) is trades +
            # book_snapshot_5 — NOT options_chain. An explicit override is
            # REQUIRED here: without one, DERIBIT-COMBO would inherit the
            # instrument_type_data_types["OPTION"] -> {options_chain} override
            # from the flat DERIBIT-shaped rule above (DERIBIT-COMBO's only
            # valid instrument_type is OPTION per INSTRUMENT_TYPES_BY_VENUE),
            # minting a phantom options_chain EXPECTED cell DERIBIT-COMBO can
            # never actually produce. Verified dynamically: DERIBIT-COMBO's
            # base venue token "DERIBIT" IS a FUTURE_BUNDLE_VENUES member, so
            # its leaf OPTION itype rolls up to the options_chain bundle grain
            # at the itype-gate stage (same as bare DERIBIT); with this
            # override + the matching VENUE_DATA_TYPE_CAPABILITIES entry,
            # build_expected("cefi") yields (DERIBIT-COMBO, options_chain,
            # trades) — no longer silently zero. book_snapshot_5 is declared
            # here too (matches its real DataTypeCapability entries) but never
            # surfaces as an EXPECTED cell at this bundle grain (the bundle's
            # only valid data_type is trades) — harmless, honest superset.
            "DERIBIT-COMBO": frozenset({"trades", "book_snapshot_5"}),
            # COINBASE-CDE (2026-07-10) — trades-only: the only real capture surface
            # today is the re-keyed live connector (Advanced Trade WS market_trades
            # channel); no book-depth channel is wired and there is no Tardis/batch
            # source at all for this venue (see VENUE_DATA_TYPE_CAPABILITIES
            # ["COINBASE-CDE"] in market_data_categories.py).
            "COINBASE-CDE": frozenset({"trades"}),
        },
        # Curated CeFi capture universe (operator-confirmed SSOT, ~490 base assets,
        # survivorship-bias-free). Spot + perp legs.
        # Crypto-venue equity instruments (operator 2026-07-16): typed PERPETUAL
        # (single-stock perp) / SPOT_PAIR (tokenized stock), NOT a distinct type.
        # Their equity bases (META, NVDA, AAPL — not crypto coins) ride
        # CEFI_EQUITY_PERP_BASE_UNIVERSE, unioned in below so those PERPETUAL /
        # SPOT_PAIR cells stay MVP; the equity identity is carried by the catalogue
        # is_equity_perp / tracks_equity tags, not by the instrument_type.
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
    #   PERPETUAL   — on-chain perp markets (Drift adapter removed 2026-07-16,
    #                 operator ruling — no current IS-adapter example)
    #   SPOT_PAIR   — on-chain spot markets (EigenLayer governance token)
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
    #   UPDATE (operator 2026-07-14, tradfi_eu_not_draining_source_axis_drift_
    #   2026_06_24.md): once CME OPTION rows actually populated the catalogue
    #   (739,278 rows, 2026-07-14 regen), the operator narrowed the OPTION
    #   scope further — see ``option_underliers`` below / ``TRADFI_MVP_OPTION_
    #   UNDERLYING_ROOTS`` (the S&P 500 / ES complex ONLY, not every underlier
    #   root that has a future).
    #
    # data_types: ohlcv_1m ONLY (operator 2026-06-27 decision #7 — NO ohlcv_1s,
    #   NO trades/tbbo in tradfi MVP). 1-minute bars are the tradfi MVP grain.
    #
    # underliers: ES (S&P 500 e-mini), NQ (Nasdaq 100 e-mini), VX (VIX futures)
    #   + the CME commodity roots backing a Binance tradfi-perp. Applies to
    #   FUTURE cells (decision #7: "S&P/ES, and the other CME roots that have
    #   Binance perps"). These are the exchange_code / underlier values.
    #
    # option_underliers: ES ONLY (operator 2026-07-14 ruling — see
    #   TRADFI_MVP_OPTION_UNDERLYING_ROOTS above). OPTION cells no longer
    #   inherit the full ``underliers`` set: GC/SI/PL/PA/NG/CL/HG/NQ/VX options
    #   are explicitly OUT of tradfi MVP even though those roots stay MVP for
    #   FUTURE cells. The prior (pre-2026-07-14) behavior tagged ALL 739,278
    #   real CME OPTION catalogue rows mvp=True because every one of those
    #   roots was already in ``underliers`` with no OPTION-specific narrowing.
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
        # OPTION-only narrowing (operator 2026-07-14): the S&P 500 / ES complex
        # ONLY. See TRADFI_MVP_OPTION_UNDERLYING_ROOTS above for full rationale.
        option_underliers=TRADFI_MVP_OPTION_UNDERLYING_ROOTS,
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
    # data_types: trades (CLOB fills), book_snapshot_5 (top-5 CLOB depth ladder),
    #   prediction_canonical_question_group (cluster-grain), market_lifecycle
    #   (market lifecycle events).
    #
    #   book_snapshot_5 (added 2026-07-18, prediction_consolidated_closeout_
    #   2026_07_18.md P1 reconcile): this ALIGNS the prediction MVP rule with the
    #   OTHER two registries that already carry it — DATA_TYPES_BY_ASSET_GROUP
    #   ["prediction"] + VENUE_DATA_TYPE_CAPABILITIES["POLYMARKET"/"KALSHI"] +
    #   expected_coverage._PREDICTION (all three re-added it 2026-06-23 when BOTH
    #   venues began genuinely emitting it: LIVE via polymarket_clob_ws/
    #   kalshi_clob_ws top-5 ladder, BATCH via the REST /book path, mtds@7c849d7)
    #   — AND with the captured data (live A0 measured 399,713 book_snapshot_5
    #   prediction rows). Before this, book_snapshot_5 sat in 2 of the 3
    #   registries but not here, so a plain MTDS shard matrix yielded 4 shards
    #   ({POLYMARKET,KALSHI} x {trades,book_snapshot_5}) while an ``--mvp-only`` run
    #   silently tested only ``trades`` (2 shards) — the CLOB-depth shard that
    #   actually flows and is a real prediction arb-dispersion (price-dispersion)
    #   input went untested. The outlier was THIS rule; reconciled by adding it.
    #   NOTE (operator): to narrow the prediction MVP back to trades-only (drop
    #   the depth shard from --mvp-only), remove "book_snapshot_5" here — but keep
    #   it in the capability/expected_coverage registries so the plain matrix +
    #   honest-coverage denominator still count the captured depth data.
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
                # Top-5 CLOB depth ladder — instrument-day grain (same grain as
                # trades), in scope for BOTH POLYMARKET + KALSHI. See the
                # data_types note above for the 3-registry reconcile rationale.
                "book_snapshot_5",
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
