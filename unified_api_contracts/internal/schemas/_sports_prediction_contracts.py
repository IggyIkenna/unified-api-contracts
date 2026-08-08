"""Sports (odds) + Prediction (Polymarket CLOB) SchemaContracts.

Phase 1.1 + 1.2 of data_pipeline_completion_2026_04_18. Split out of
``contracts.py`` to keep that module under the 900-line codex-compliance
limit. Imported at module load time by ``contracts.py`` via a side-effect
import so the mutations to ``CONTRACT_REGISTRY`` happen before any consumer
performs a lookup.

**Shard dimensions (per availability manifest v4)**

Sports:
    ``(category=sports, venue=BOOKMAKER, source=odds_api|sfi|footystats,
       league_id=EPL|LALIGA|…, instrument_type=odds, data_type=odds)``

    ``venue`` (manifest/path dimension) is the bookmaker (BET365, PINNACLE,
    BETFAIR, MATCHBOOK, UNITY_BETFAIR). ``source`` is the provider.
    ``league_id`` is a first-class shard column — never overload ``venue``.

    **Row-level schema (SPORTS_ODDS_TRADES contract, corrected 2026-07-26 —
    T2.9 of `sports_mtds_odds_trades_index_correctness_followup_2026_07_24.md`):**
    the ROW columns persisted by the native live writer do NOT mirror the
    manifest partition-dimension names 1:1 — `venue_fetch.py`'s per-bookmaker
    shard grouping renames the row-level ``venue`` key to ``bookmaker_key``
    before write, and the writer emits ``bm_time`` / ``source`` / ``market_key``
    / ``outcome_name`` / ``price`` rather than the previously-registered
    ``ts_event`` / ``data_source`` / ``market_type`` / ``outcome`` /
    ``odds_decimal``. There is no ``broker``/``client`` pairing anywhere in
    this ingestion shape (those never existed in the real writer output) —
    verified directly against a live captured
    ``pipeline_mode=batch_odds_api`` object, not inferred.

Prediction:
    ``(category=prediction, venue=POLYMARKET, chain=POLYGON,
       instrument_type=prediction_market, data_type=trades)``

    ``condition_id`` is the on-chain market identifier; ``asset_id`` is the
    per-outcome ERC-1155 token id; ``underlying`` tags the real-world asset
    (BNB, ETH, SPX, fixture id, …) so the row can be joined back to the
    canonical event via prediction_mapping.

Do NOT import this module directly — import from
``unified_api_contracts.internal.schemas.contracts`` which re-exports the
public SchemaContract names.
"""

from __future__ import annotations

from unified_api_contracts.internal.schemas.contracts import (
    CHAIN_COL,
    CONTRACT_REGISTRY,
    INSTRUMENT_ID_COL,
    PRICE_COL,
    TS_EVENT_COL,
    VENUE_COL,
    ColumnSpec,
    SchemaContract,
)

# ---------------------------------------------------------------------------
# Sports (odds) — Phase 1.2
# ---------------------------------------------------------------------------

SPORTS_ODDS_TRADES = SchemaContract(
    asset_group="sports",
    instrument_type="odds",
    data_type="odds",
    columns=[
        INSTRUMENT_ID_COL,
        ColumnSpec(
            name="bookmaker_key",
            dtype="string",
            nullable=False,
            description=(
                "Bookmaker identifier (BET365, PINNACLE, BETFAIR, …). Row-level rename of the "
                "manifest/path 'venue' dimension applied by venue_fetch.py's per-bookmaker shard "
                "grouping before write — the real writer output never carries a 'venue' column."
            ),
        ),
        ColumnSpec(
            name="bm_time",
            dtype="string",
            nullable=False,
            description=(
                "Bookmaker-reported ground-truth event time — ISO8601 string as persisted by the "
                "writer, NOT a parsed datetime64 column (see docs/SPORTS_ODDS.md)."
            ),
        ),
        ColumnSpec(
            name="source",
            dtype="string",
            nullable=False,
            description="Provider: ODDS_API, SFI, FOOTYSTATS. Distinguishes odds_api vs footystats populations.",
        ),
        ColumnSpec(
            name="league_id",
            dtype="string",
            nullable=False,
            description="Canonical league id (EPL, LALIGA, ENG_PREMIER_LEAGUE, …) — v4 shard column.",
        ),
        ColumnSpec(name="fixture_id", dtype="string", nullable=False),
        ColumnSpec(
            name="market_key",
            dtype="string",
            nullable=False,
            description="H2H, OU, BTTS, ASIAN_HANDICAP, CORRECT_SCORE, …",
        ),
        ColumnSpec(name="outcome_name", dtype="string", nullable=False),
        PRICE_COL,
        ColumnSpec(
            name="in_play",
            dtype="bool",
            nullable=True,
            description="True when the bookmaker quote was captured during a live match (bm_minutes_to_kickoff < 0).",
        ),
    ],
    symbol_column="fixture_id",
    required_row_count_min=1,
)

# ---------------------------------------------------------------------------
# Sports (odds) — EXCHANGE_ODDS / FIXED_ODDS fork (contracts-first migration,
# sports_closeout_exchange_fixed_odds_fork_2026_07_25.md todo 3). Same row
# schema as SPORTS_ODDS_TRADES — the fork splits the manifest/GCS
# instrument_type partition by venue class (peer-to-peer exchange vs
# sportsbook), it does not change the captured columns. The legacy ``odds``
# contract above stays registered for the dual-read window (next todo).
# ---------------------------------------------------------------------------

SPORTS_EXCHANGE_ODDS_TRADES = SchemaContract(
    asset_group="sports",
    instrument_type="exchange_odds",
    data_type="odds",
    columns=SPORTS_ODDS_TRADES.columns,
    symbol_column="fixture_id",
    required_row_count_min=1,
)

SPORTS_FIXED_ODDS_TRADES = SchemaContract(
    asset_group="sports",
    instrument_type="fixed_odds",
    data_type="odds",
    columns=SPORTS_ODDS_TRADES.columns,
    symbol_column="fixture_id",
    required_row_count_min=1,
)

# ---------------------------------------------------------------------------
# Prediction markets (Polymarket, Kalshi, …) — Phase 1.1
# ---------------------------------------------------------------------------

PREDICTION_PREDICTION_MARKET_TRADES = SchemaContract(
    asset_group="prediction",
    instrument_type="prediction_market",
    data_type="trades",
    columns=[
        INSTRUMENT_ID_COL,
        VENUE_COL,
        CHAIN_COL,
        TS_EVENT_COL,
        PRICE_COL,
        ColumnSpec(name="size", dtype="float64", nullable=False),
        ColumnSpec(
            name="side",
            dtype="string",
            nullable=False,
            description="BUY / SELL.",
        ),
        ColumnSpec(
            name="outcome",
            dtype="string",
            nullable=False,
            description="Yes/No, Up/Down, or branded outcome label.",
        ),
        ColumnSpec(name="outcome_index", dtype="int64", nullable=False),
        ColumnSpec(
            name="condition_id",
            dtype="string",
            nullable=False,
            description="On-chain market identifier (Polymarket condition id).",
        ),
        ColumnSpec(
            name="asset_id",
            dtype="string",
            nullable=False,
            description="Per-outcome ERC-1155 token id.",
        ),
        ColumnSpec(
            name="underlying",
            dtype="string",
            nullable=False,
            description=(
                "Real-world asset / subject / candidate tag (BNB, SPX, TRUMP, "
                "KAMALA_HARRIS, OSCARS, EPL, …). Written by the canonical "
                "classifier (``classify_polymarket_market``). Required — "
                "promoted from nullable in the 6-dimension resharding."
            ),
        ),
        ColumnSpec(
            name="asset_group",
            dtype="string",
            nullable=False,
            description=(
                "Normalized cross-venue market category: CRYPTO_PRICE | "
                "EQUITY_INDEX | COMMODITY | FX | MACRO | POLITICS_US | "
                "POLITICS_INTL | SPORTS_FOOTBALL | SPORTS_OTHER | CULTURE | "
                "TECH | WEATHER | MISC. Source of truth: "
                "``PredictionMarketCategory`` in "
                "``_prediction_market_taxonomy``."
            ),
        ),
        ColumnSpec(
            name="market_type",
            dtype="string",
            nullable=False,
            description=(
                "Prediction market structure: binary | scalar | categorical | "
                "ranked | range_bracket. SSOT: ``PredictionMarketType``."
            ),
        ),
        ColumnSpec(
            name="resolution_period",
            dtype="string",
            nullable=False,
            description=(
                "Resolution horizon: intraday | hourly | daily | weekly | "
                "monthly | quarterly | yearly | event. SSOT: "
                "``PredictionResolutionPeriod``."
            ),
        ),
    ],
    symbol_column="condition_id",
    required_row_count_min=1,
)


# ---------------------------------------------------------------------------
# Sports — odds snapshot / movement / arbitrage (DataType enum coverage)
# ---------------------------------------------------------------------------
# ``sports_odds_snapshot`` / ``sports_odds_movement`` / ``sports_arbitrage``
# live under the canonical ``sports`` category + ``odds`` instrument_type.
# Snapshot = point-in-time odds across venues. Movement = deltas between
# snapshots. Arbitrage = cross-venue mispricings. Venue-specific columns
# (``traded_volume`` on Betfair, ``max_bet`` on Pinnacle) carry
# ``provided_by_venues``.

_SNAPSHOT_VENUES = frozenset({"BETFAIR", "MATCHBOOK", "ODDS_API", "PINNACLE_AS_LINE"})

SPORTS_ODDS_SNAPSHOT = SchemaContract(
    asset_group="sports",
    instrument_type="odds",
    data_type="sports_odds_snapshot",
    columns=[
        INSTRUMENT_ID_COL,
        VENUE_COL,
        TS_EVENT_COL,
        ColumnSpec(name="league_id", dtype="string", nullable=False),
        ColumnSpec(name="fixture_id", dtype="string", nullable=False),
        ColumnSpec(name="market_type", dtype="string", nullable=False),
        ColumnSpec(name="outcome", dtype="string", nullable=False),
        ColumnSpec(name="odds_decimal", dtype="float64", nullable=False),
        ColumnSpec(
            name="bookmaker",
            dtype="string",
            nullable=True,
            description="Provider-side bookmaker label (e.g. pinnacle, draftkings).",
        ),
        # Betfair exchange publishes traded volume per outcome; other books do not.
        ColumnSpec(
            name="traded_volume",
            dtype="float64",
            nullable=True,
            required=False,
            provided_by_venues=frozenset({"BETFAIR"}),
        ),
        # Pinnacle publishes max stake per market; other venues do not.
        ColumnSpec(
            name="max_bet",
            dtype="float64",
            nullable=True,
            required=False,
            provided_by_venues=frozenset({"PINNACLE_AS_LINE"}),
        ),
    ],
    symbol_column="fixture_id",
    required_row_count_min=0,
)

SPORTS_ODDS_MOVEMENT = SchemaContract(
    asset_group="sports",
    instrument_type="odds",
    data_type="sports_odds_movement",
    columns=[
        INSTRUMENT_ID_COL,
        VENUE_COL,
        TS_EVENT_COL,
        ColumnSpec(name="league_id", dtype="string", nullable=False),
        ColumnSpec(name="fixture_id", dtype="string", nullable=False),
        ColumnSpec(name="market_type", dtype="string", nullable=False),
        ColumnSpec(name="outcome", dtype="string", nullable=False),
        ColumnSpec(name="odds_before", dtype="float64", nullable=False),
        ColumnSpec(name="odds_after", dtype="float64", nullable=False),
        ColumnSpec(name="odds_delta", dtype="float64", nullable=False),
        ColumnSpec(name="ts_before", dtype="datetime64[ns, UTC]", nullable=False),
        ColumnSpec(name="bookmaker", dtype="string", nullable=True),
    ],
    symbol_column="fixture_id",
    required_row_count_min=0,
)

# Cross-venue arbitrage opportunities — ``venue`` and ``instrument_id`` carry
# a composite ``<LEG_A_VENUE>_VS_<LEG_B_VENUE>`` label. Not venue-scoped.
SPORTS_ODDS_ARBITRAGE = SchemaContract(
    asset_group="sports",
    instrument_type="odds",
    data_type="sports_arbitrage",
    columns=[
        INSTRUMENT_ID_COL,
        TS_EVENT_COL,
        ColumnSpec(name="league_id", dtype="string", nullable=False),
        ColumnSpec(name="fixture_id", dtype="string", nullable=False),
        ColumnSpec(name="market_type", dtype="string", nullable=False),
        ColumnSpec(name="leg_a_venue", dtype="string", nullable=False),
        ColumnSpec(name="leg_b_venue", dtype="string", nullable=False),
        ColumnSpec(name="leg_a_outcome", dtype="string", nullable=False),
        ColumnSpec(name="leg_b_outcome", dtype="string", nullable=False),
        ColumnSpec(name="leg_a_odds", dtype="float64", nullable=False),
        ColumnSpec(name="leg_b_odds", dtype="float64", nullable=False),
        ColumnSpec(
            name="arbitrage_margin_bps",
            dtype="float64",
            nullable=False,
            description="Positive margin in basis points when the 1/a + 1/b book < 1.",
        ),
    ],
    symbol_column="fixture_id",
    required_row_count_min=0,
)


# ---------------------------------------------------------------------------
# PREDICTION — additional contracts (Gap 1 of cross-category audit, 2026-04-25).
#
# Polymarket has three production APIs surfaced by the MTDS PolymarketAdapter:
# - **Gamma API** (gamma-api.polymarket.com): market metadata + tag taxonomy.
#   Source for ``market_metadata`` contract.
# - **CLOB API** (clob.polymarket.com): orderbook + trades + orders.
#   Source for ``book_snapshot``; ``trades`` already registered above.
# - **Data API** (data-api.polymarket.com): historical fills + position
#   snapshots. Source for ``fills`` contract.
#
# Column lists drawn from PolymarketAdapter writer source + Polymarket public
# docs (https://docs.polymarket.com/developers/CLOB | gamma-markets-api |
# data-api). All three contracts use ``condition_id`` as the canonical row
# identifier (matches PREDICTION_PREDICTION_MARKET_TRADES) — the on-chain
# market id is the only identifier guaranteed stable across endpoints.
# ---------------------------------------------------------------------------


PREDICTION_PREDICTION_MARKET_BOOK_SNAPSHOT = SchemaContract(
    asset_group="prediction",
    instrument_type="prediction_market",
    data_type="book_snapshot_5",
    columns=[
        INSTRUMENT_ID_COL,
        TS_EVENT_COL,
        ColumnSpec(
            name="condition_id",
            dtype="string",
            nullable=False,
            description=(
                "Polymarket on-chain market id (0x-prefixed bytes32). One condition "
                "produces N outcome tokens (binary=2, scalar=2, categorical=N>2)."
            ),
        ),
        ColumnSpec(
            name="asset_id",
            dtype="string",
            nullable=False,
            description=(
                "ERC-1155 outcome-token id within the condition. Each condition has "
                "one asset_id per outcome (binary YES + NO). The L2 book is "
                "asset-id-scoped: bids/asks are quoted per outcome, not per market."
            ),
        ),
        ColumnSpec(
            name="bids",
            dtype="string",
            nullable=False,
            description=(
                "Top-N bid levels serialised as JSON array of [price, size] pairs. "
                "Polymarket CLOB returns up to 50 levels per side; we serialise "
                "rather than flatten to keep the schema rectangular across markets "
                "with varying depth."
            ),
        ),
        ColumnSpec(
            name="asks",
            dtype="string",
            nullable=False,
            description="Top-N ask levels as JSON array of [price, size] pairs.",
        ),
        ColumnSpec(
            name="venue",
            dtype="string",
            nullable=False,
            description="POLYMARKET (or KALSHI for the Kalshi adapter on the same shape).",
        ),
        ColumnSpec(
            name="chain",
            dtype="string",
            nullable=False,
            description="Settlement chain — POLYGON for Polymarket, ETHEREUM for Kalshi.",
        ),
        ColumnSpec(
            name="market_category",
            dtype="string",
            nullable=False,
            description=(
                "UAC market taxonomy: CRYPTO_PRICE, EQUITY_INDEX, COMMODITY, "
                "POLITICS_US, SPORTS_*, EVENT, etc. SSOT: ``PredictionMarketCategory``."
            ),
        ),
    ],
    symbol_column="condition_id",
    required_row_count_min=0,
)


PREDICTION_PREDICTION_MARKET_METADATA = SchemaContract(
    asset_group="prediction",
    instrument_type="prediction_market",
    data_type="market_metadata",
    columns=[
        INSTRUMENT_ID_COL,
        ColumnSpec(
            name="condition_id",
            dtype="string",
            nullable=False,
            description="On-chain market id — primary key for the row.",
        ),
        ColumnSpec(
            name="question",
            dtype="string",
            nullable=False,
            description=(
                "Free-text market question as published by Polymarket Gamma API. "
                "Example: 'Will Bitcoin reach $150,000 by end of 2026?'"
            ),
        ),
        ColumnSpec(
            name="market_slug",
            dtype="string",
            nullable=True,
            description="URL-safe slug of the question; used in market URLs.",
        ),
        ColumnSpec(
            name="event_slug",
            dtype="string",
            nullable=True,
            description=(
                "Parent event slug — events group multiple related markets "
                "(e.g. an election event carries markets per candidate)."
            ),
        ),
        ColumnSpec(
            name="end_date_iso",
            dtype="string",
            nullable=True,
            description=("Expected resolution date (ISO 8601 string). Null when the market has open-ended resolution."),
        ),
        ColumnSpec(
            name="active",
            dtype="bool",
            nullable=False,
            description="True while the market accepts trades; False once paused or resolved.",
        ),
        ColumnSpec(
            name="closed",
            dtype="bool",
            nullable=False,
            description="True once resolution is finalised on-chain.",
        ),
        ColumnSpec(
            name="volume",
            dtype="float64",
            nullable=True,
            description="Total USDC traded across all outcomes (lifetime).",
        ),
        ColumnSpec(
            name="liquidity",
            dtype="float64",
            nullable=True,
            description="Aggregate USDC liquidity quoted across the orderbook (instantaneous).",
        ),
        ColumnSpec(
            name="tokens",
            dtype="string",
            nullable=False,
            description=(
                "JSON array of outcome tokens: [{token_id, outcome, price, winner}]. "
                "Length = number of outcomes (2 for binary/scalar, N for categorical)."
            ),
        ),
        TS_EVENT_COL,
    ],
    symbol_column="condition_id",
    required_row_count_min=0,
)


PREDICTION_PREDICTION_MARKET_FILLS = SchemaContract(
    asset_group="prediction",
    instrument_type="prediction_market",
    data_type="fills",
    columns=[
        INSTRUMENT_ID_COL,
        TS_EVENT_COL,
        ColumnSpec(
            name="fill_id",
            dtype="string",
            nullable=False,
            description="Unique fill identifier from Polymarket Data API. Primary key.",
        ),
        ColumnSpec(
            name="order_id",
            dtype="string",
            nullable=False,
            description=(
                "Parent order this fill matched against. Multiple fills can stem "
                "from one order (partial fills against multiple counterparties)."
            ),
        ),
        ColumnSpec(
            name="condition_id",
            dtype="string",
            nullable=False,
            description="On-chain market id — join key back to trades / book_snapshot.",
        ),
        ColumnSpec(
            name="asset_id",
            dtype="string",
            nullable=False,
            description="ERC-1155 outcome-token id (which side of the binary/categorical was filled).",
        ),
        ColumnSpec(
            name="price",
            dtype="float64",
            nullable=False,
            description="Fill price in USDC per outcome share (0.0-1.0 for binary).",
        ),
        ColumnSpec(
            name="size",
            dtype="float64",
            nullable=False,
            description="Fill size in outcome shares (1 share = $1 if outcome wins).",
        ),
        ColumnSpec(
            name="side",
            dtype="string",
            nullable=False,
            description="BUY | SELL — taker direction relative to the outcome token.",
        ),
        ColumnSpec(
            name="fee",
            dtype="float64",
            nullable=True,
            description="Polymarket fee charged on this fill (USDC). Null on legacy fills.",
        ),
        ColumnSpec(
            name="maker",
            dtype="string",
            nullable=True,
            description="Maker wallet address (0x-prefixed). Null when the API redacts it.",
        ),
        ColumnSpec(
            name="taker",
            dtype="string",
            nullable=True,
            description="Taker wallet address. Null when redacted.",
        ),
        ColumnSpec(
            name="venue",
            dtype="string",
            nullable=False,
            description="POLYMARKET | KALSHI.",
        ),
        ColumnSpec(
            name="chain",
            dtype="string",
            nullable=False,
            description="Settlement chain.",
        ),
    ],
    symbol_column="condition_id",
    required_row_count_min=0,
)


# ---------------------------------------------------------------------------
# Registry side-effects
# ---------------------------------------------------------------------------

CONTRACT_REGISTRY[("sports", "odds", "odds")] = SPORTS_ODDS_TRADES
CONTRACT_REGISTRY[("sports", "exchange_odds", "odds")] = SPORTS_EXCHANGE_ODDS_TRADES
CONTRACT_REGISTRY[("sports", "fixed_odds", "odds")] = SPORTS_FIXED_ODDS_TRADES
# Backward-compat aliases for the P2 migration window (GCS objects written before
# this P1 rename still carry data_type=trades in their path; remove after P2 re-stamps).
CONTRACT_REGISTRY[("sports", "odds", "trades")] = SPORTS_ODDS_TRADES
CONTRACT_REGISTRY[("sports", "exchange_odds", "trades")] = SPORTS_EXCHANGE_ODDS_TRADES
CONTRACT_REGISTRY[("sports", "fixed_odds", "trades")] = SPORTS_FIXED_ODDS_TRADES
CONTRACT_REGISTRY[("prediction", "prediction_market", "trades")] = PREDICTION_PREDICTION_MARKET_TRADES
CONTRACT_REGISTRY[("prediction", "prediction_market", "book_snapshot_5")] = PREDICTION_PREDICTION_MARKET_BOOK_SNAPSHOT
CONTRACT_REGISTRY[("prediction", "prediction_market", "market_metadata")] = PREDICTION_PREDICTION_MARKET_METADATA
CONTRACT_REGISTRY[("prediction", "prediction_market", "fills")] = PREDICTION_PREDICTION_MARKET_FILLS
CONTRACT_REGISTRY[("sports", "odds", "sports_odds_snapshot")] = SPORTS_ODDS_SNAPSHOT
CONTRACT_REGISTRY[("sports", "odds", "sports_odds_movement")] = SPORTS_ODDS_MOVEMENT
CONTRACT_REGISTRY[("sports", "odds", "sports_arbitrage")] = SPORTS_ODDS_ARBITRAGE


__all__ = [
    "PREDICTION_PREDICTION_MARKET_BOOK_SNAPSHOT",
    "PREDICTION_PREDICTION_MARKET_FILLS",
    "PREDICTION_PREDICTION_MARKET_METADATA",
    "PREDICTION_PREDICTION_MARKET_TRADES",
    "SPORTS_EXCHANGE_ODDS_TRADES",
    "SPORTS_FIXED_ODDS_TRADES",
    "SPORTS_ODDS_ARBITRAGE",
    "SPORTS_ODDS_MOVEMENT",
    "SPORTS_ODDS_SNAPSHOT",
    "SPORTS_ODDS_TRADES",
]
