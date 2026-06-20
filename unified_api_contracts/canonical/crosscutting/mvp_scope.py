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

# The CeFi MVP base-currency universe is the 44-base SSOT
# ``CEFI_BASE_ASSET_UNIVERSE`` (operator-confirmed 2026-06-16; supersedes the
# former 4-base BTC/ETH/SOL/USDT set). ``CEFI_OPTIONS_UNDERLYINGS`` is the
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
            lists BTC + ETH options only, so expecting the full 44-base set
            as options would yield false-missing. When non-empty, an OPTION
            cell is MVP iff ``base_ccy`` is in this set (``base_ccys`` is NOT
            applied to OPTION cells). Empty → fall back to ``base_ccys``.
        sources: Optional frozenset of source strings. When not empty,
            only cells from one of these sources are MVP.
    """

    venues: frozenset[str]
    instrument_types: frozenset[str]
    data_types: frozenset[str]
    base_ccys: frozenset[str] = field(default_factory=frozenset)
    options_base_ccys: frozenset[str] = field(default_factory=frozenset)
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
    # base_ccys: the 44-base ``CEFI_BASE_ASSET_UNIVERSE`` (operator-confirmed
    #   2026-06-16 as the CeFi MVP base-currency SSOT — supersedes the former
    #   4-base BTC/ETH/SOL/USDT set). Spot + perp legs span the full universe.
    #
    # options_base_ccys: BTC + ETH ONLY (``CEFI_OPTIONS_UNDERLYINGS``). The
    #   options expected universe is the Deribit-options carve-out — Deribit is
    #   the only CeFi venue with OPTION instruments and it lists BTC + ETH
    #   options only. Expecting the full 44-base set as options on Deribit would
    #   yield false-missing, so OPTION cells gate on this narrower set.
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
            }
        ),
        instrument_types=frozenset(
            {
                "SPOT_PAIR",  # InstrumentType.SPOT_PAIR
                "PERPETUAL",  # InstrumentType.PERPETUAL
                "OPTION",  # InstrumentType.OPTION (Deribit BTC/ETH options)
                # Crypto-venue equity instruments (2026-06-20):
                "EQUITY_PERP",  # InstrumentType.EQUITY_PERP — single-stock perps (Binance/OKX/Bybit)
                "TOKENIZED_EQUITY",  # InstrumentType.TOKENIZED_EQUITY — tokenized stocks (e.g. Bybit AAPLX)
            }
        ),
        data_types=frozenset(
            {
                "trades",
                "book_snapshot_5",
                # Perpetual funding: canonical data_type is derivative_ticker
                # (contains funding_rate field) in most venues;
                # some venues expose a separate funding_rate data_type.
                # TODO(mvp-scope): confirm canonical MVP data_type for funding axis.
                "derivative_ticker",
                "funding_rate",
            }
        ),
        # 44-base CeFi MVP universe (operator-confirmed SSOT). Spot + perp legs.
        # EQUITY_PERP/TOKENIZED_EQUITY cells use CEFI_EQUITY_PERP_BASE_UNIVERSE as
        # their base_ccys (equity tickers like META, NVDA, AAPL — not crypto coins).
        # The combined union covers both crypto-perp and equity-perp families.
        base_ccys=CEFI_BASE_ASSET_UNIVERSE | CEFI_EQUITY_PERP_BASE_UNIVERSE,
        # Deribit-options carve-out: BTC + ETH only (the OPTION expected universe).
        options_base_ccys=CEFI_OPTIONS_UNDERLYINGS,
        # sources: empty → all sources in scope (tardis + per-venue live)
        # TODO(mvp-scope): narrow to ["tardis"] once live-source tagging confirmed.
        sources=frozenset(),
    ),
    # ------------------------------------------------------------------
    # defi
    #
    # Venues: DEX pools (EVM + Solana), LST protocols, lending protocols
    #   from the MVP archetype matrix (carry_staked_basis + arb_price_dispersion)
    #
    # EVM DEX (arbitrage_price_dispersion leg):
    #   UNISWAP_V3-ETHEREUM, CURVE-ETHEREUM, BALANCER-ETHEREUM,
    #   SUSHISWAP_V3-ETHEREUM, PANCAKESWAP_V3-ETHEREUM
    #
    # Solana DEX (arbitrage_price_dispersion + carry_staked_basis):
    #   PHOENIX-SOLANA (TODO: confirm canonical form — not in ALL_DEFI_VENUES;
    #     see note below), ORCA-SOLANA, RAYDIUM-SOLANA, DRIFT-SOLANA
    #
    # LST protocols (carry_staked_basis leg):
    #   LIDO-ETHEREUM (stETH), ROCKETPOOL-ETHEREUM (rETH),
    #   TODO(mvp-scope): confirm cbETH (Coinbase Base token) — may be
    #     COINBASE-ETHEREUM or another canonical form.
    #   JITO (JitoSOL) + MARINADE (mSOL) are Solana — confirm canonical forms.
    #
    # Lending (carry_staked_basis — Aave/Compound base rates):
    #   AAVE_V3-ETHEREUM, COMPOUND_V3-ETHEREUM
    #
    # NOTE on PHOENIX-SOLANA: The task spec lists "Phoenix" as a DeFi DEX
    # venue. As of the defi_venues.py registry (2026-06-08), the Solana DEX
    # entries include ORCA-SOLANA, RAYDIUM-SOLANA, DRIFT-SOLANA but NOT a
    # PHOENIX-SOLANA entry. Phoenix is the Solana CLOB DEX; it may be listed
    # under a different canonical name or not yet in the registry.
    # TODO(mvp-scope): operator confirmation required on PHOENIX-SOLANA
    # canonical venue ID in ALL_DEFI_VENUES before Phase 2 integration.
    #
    # instrument_types:
    #   POOL       — legacy EVM AMM pool snapshots (Uniswap, Curve, Balancer)
    #   DEX_POOL   — Solana-basis DEX orderbook/quote/trade shards (ORCA, RAYDIUM,
    #                DRIFT, PHOENIX)
    #   LST        — Liquid staking tokens (Lido stETH, RocketPool rETH, JitoSOL, mSOL)
    #   LENDING    — Lending protocol markets (Aave V3, Compound V3)
    #
    # data_types (from DATA_TYPES_BY_ASSET_GROUP["defi"]):
    #   dex_pool_state, dex_pool_swaps — DEX pool metrics + swap events
    #   lst_rates                      — LST exchange rates (stETH/ETH ratio, rETH/ETH, etc.)
    #   lending_indices                — Lending rate indices (supply APY, borrow APY, utilization)
    #   perp_funding                   — Perpetual funding rates (Hyperliquid, Aster, Drift)
    #   oracle_prices                  — Chainlink/Pyth oracle prices
    # ------------------------------------------------------------------
    "defi": DeFiMvpRule(
        venues=frozenset(
            {
                # EVM DEX (arbitrage_price_dispersion)
                "UNISWAP_V3-ETHEREUM",
                "CURVE-ETHEREUM",
                "BALANCER-ETHEREUM",
                "SUSHISWAP_V3-ETHEREUM",
                "PANCAKESWAP_V3-ETHEREUM",
                # Solana DEX (arbitrage_price_dispersion + carry_staked_basis)
                "ORCA-SOLANA",
                "RAYDIUM-SOLANA",
                "DRIFT-SOLANA",
                # TODO(mvp-scope): PHOENIX-SOLANA not found in ALL_DEFI_VENUES (2026-06-08).
                # Add once the canonical entry lands in defi_venues.py.
                # LST protocols (carry_staked_basis)
                "LIDO-ETHEREUM",  # stETH
                "ROCKETPOOL-ETHEREUM",  # rETH
                # TODO(mvp-scope): confirm cbETH canonical venue name.
                # TODO(mvp-scope): confirm JitoSOL (JITO-SOLANA?) and mSOL
                # (MARINADE-SOLANA?) canonical venue names.
                # Lending protocols (carry_staked_basis base rates)
                "AAVE_V3-ETHEREUM",
                "COMPOUND_V3-ETHEREUM",
            }
        ),
        instrument_types=frozenset(
            {
                "POOL",  # InstrumentType.POOL — EVM AMM pools
                "DEX_POOL",  # InstrumentType.DEX_POOL — Solana DEX orderbook/quote
                "LST",  # InstrumentType.LST — Liquid staking tokens
                "LENDING",  # InstrumentType.LENDING — Lending protocol markets
            }
        ),
        data_types=frozenset(
            {
                "dex_pool_state",
                "dex_pool_swaps",
                "lst_rates",
                "lending_indices",
                "perp_funding",
                "oracle_prices",
            }
        ),
        # sources: empty → all on-chain sources in scope (onchain_subgraph, onchain_rpc,
        # pyth_hermes, chainlink, hyperliquid)
        sources=frozenset(),
    ),
    # ------------------------------------------------------------------
    # tradfi
    #
    # Venues: CME only (Databento CME tick data is the primary TradFi MVP
    #   data source per the MVP matrix — ES, NQ, VX futures + options).
    #
    # instrument_types: FUTURE, OPTION
    #   NOTE: TradFi "option" in InstrumentType is ``OPTION``, not
    #   ``OPTIONS_CHAIN`` (which was the legacy name). The task spec says
    #   ``OPTIONS_CHAIN`` but the canonical enum value is ``OPTION``.
    #   TODO(mvp-scope): confirm whether the plan means the OPTION instrument
    #   type (individual option contract) or the futures_chain/options_chain
    #   data_type (the daily chain bundle). Using OPTION for now.
    #
    # data_types: trades, ohlcv_1m (per DATA_TYPES_BY_ASSET_GROUP["tradfi"])
    #
    # underliers: ES (S&P 500 e-mini), NQ (Nasdaq 100 e-mini), VX (VIX futures)
    #   These are the exchange_code values in tradfi_instrument_universe.py.
    #
    # sources: databento (primary per SOURCE_PRIORITY), massive (secondary)
    # ------------------------------------------------------------------
    "tradfi": TradFiMvpRule(
        venues=frozenset({"CME"}),
        instrument_types=frozenset(
            {
                "FUTURE",  # InstrumentType.FUTURE
                "OPTION",  # InstrumentType.OPTION
                # TODO(mvp-scope): confirm whether ETF (e.g. SPY options) is
                # in MVP scope — excluded conservatively for now.
            }
        ),
        data_types=frozenset(
            {
                "trades",
                "ohlcv_1m",
            }
        ),
        underliers=frozenset(
            {
                "ES",  # S&P 500 e-mini futures/options
                "NQ",  # Nasdaq 100 e-mini futures/options
                "VX",  # CBOE VIX futures
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
    # Leagues: the prediction-tier leagues from LEAGUE_REGISTRY.
    #   Core football (soccer): EPL, LA_LIGA, BUNDESLIGA, SERIE_A, LIGUE_1
    #   US sports: NFL, NBA (from NON_FOOTBALL_LEAGUES / FEATURES_LEAGUES).
    #   TODO(mvp-scope): confirm exact league set for MVP; using a conservative
    #   selection of top-tier leagues with full data-source coverage.
    #
    # data_types: odds (raw bookmaker odds), markets/outcomes (fixture lifecycle)
    # ------------------------------------------------------------------
    "sports": SportsMvpRule(
        leagues=frozenset(
            {
                # Top-tier football (soccer) — Prediction classification
                "EPL",  # English Premier League
                "LA_LIGA",  # Spanish La Liga
                # TODO(mvp-scope): confirm BUNDESLIGA canonical league_id
                # (may be BUN or BUNDESLIGA_1 in league_data.py).
                # US sports (Features/Non-football)
                "NFL",  # National Football League
                "NBA",  # National Basketball Association
            }
        ),
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
    # Venues: POLYMARKET only (MVP per the archetype matrix; Kalshi is
    #   post-MVP for data ingestion per the SOURCE_PRIORITY registry).
    #   TODO(mvp-scope): confirm whether Kalshi is in MVP or post-MVP scope.
    #
    # market_groups: the PredictionMarketCategory values in scope.
    #   crypto, politics, sports, financial are the main Polymarket categories.
    #   TODO(mvp-scope): operator sign-off on market_group membership.
    #
    # data_types: trades (CLOB fills), prediction_canonical_question_group
    #   (cluster-grain), market_lifecycle (market lifecycle events).
    # ------------------------------------------------------------------
    "prediction": PredictionMvpRule(
        venues=frozenset({"POLYMARKET"}),
        market_groups=frozenset(
            {
                "crypto",  # PredictionMarketCategory.CRYPTO
                "politics",  # PredictionMarketCategory.POLITICS
                "sports",  # PredictionMarketCategory.SPORTS
                # TODO(mvp-scope): confirm whether "financial" is MVP.
                # Excluded conservatively for now.
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


MVP_SCOPE_CONFIG_VERSION: Final[int] = 3
"""Monotonic version of :data:`MVP_SCOPE`. Bump on any content change.

v3 (2026-06-17): CeFi venue set reconciled from the bare ``OKX`` token to the
canonical sub-venues ``OKX-SPOT`` / ``OKX-SWAP`` / ``OKX-FUTURES`` (the form the
instruments-store catalogue + the rest of the pipeline use), so OKX instruments
tag MVP. A bare ``OKX`` caller still resolves via the predicate's base-venue-token
normalisation (``_cefi_venue_in_rule``). Also introduced the unbound-data_type
convention in ``is_mvp`` (``data_type`` blank → "any MVP data_type") — predicate
behaviour, not config content, but versioned together. (mvp_instrument_universe_gap_audit
P2 #1 + #2.)

v2 (2026-06-17): CeFi ``base_ccys`` reconciled from the 4-base BTC/ETH/SOL/USDT
set to the 44-base ``CEFI_BASE_ASSET_UNIVERSE`` (operator-confirmed SSOT), added
``OPTION`` to CeFi ``instrument_types``, and added the Deribit-options carve-out
(``options_base_ccys = CEFI_OPTIONS_UNDERLYINGS`` = BTC+ETH only). The content
hash flips automatically with the version + content change.
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
        # Axis 3: data_type (blank → any MVP data_type, unbound-grain convention)
        if not _data_type_in_rule(data_type, rule.data_types):
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
        if rule.market_groups and market_group not in rule.market_groups:
            return False
        return not (rule.sources and source not in rule.sources)

    # Unknown rule type — conservative default: not MVP
    return False  # pragma: no cover
