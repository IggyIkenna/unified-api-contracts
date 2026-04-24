"""Sports (odds) + Prediction (Polymarket CLOB) SchemaContracts.

Phase 1.1 + 1.2 of data_pipeline_completion_2026_04_18. Split out of
``contracts.py`` to keep that module under the 900-line codex-compliance
limit. Imported at module load time by ``contracts.py`` via a side-effect
import so the mutations to ``CONTRACT_REGISTRY`` happen before any consumer
performs a lookup.

**Shard dimensions (per availability manifest v4)**

Sports:
    ``(category=sports, venue=BOOKMAKER, data_source=ODDS_API|SFI|FOOTYSTATS,
       league_id=EPL|LALIGA|…, instrument_type=odds, data_type=trades)``

    ``venue`` is the bookmaker (BET365, PINNACLE, BETFAIR, MATCHBOOK,
    UNITY_BETFAIR). ``data_source`` is the provider. ``league_id`` is a
    first-class shard column — never overload ``venue``. ``broker`` and
    ``client`` are execution-side row columns, NOT partition dimensions.

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
    category="sports",
    instrument_type="odds",
    data_type="trades",
    columns=[
        INSTRUMENT_ID_COL,
        VENUE_COL,
        TS_EVENT_COL,
        ColumnSpec(
            name="data_source",
            dtype="string",
            nullable=False,
            description="Provider: ODDS_API, SFI, FOOTYSTATS.",
        ),
        ColumnSpec(
            name="league_id",
            dtype="string",
            nullable=False,
            description="Canonical league id (EPL, LALIGA, ENG_PREMIER_LEAGUE, …) — v4 shard column.",
        ),
        ColumnSpec(name="fixture_id", dtype="string", nullable=False),
        ColumnSpec(
            name="market_type",
            dtype="string",
            nullable=False,
            description="H2H, OU, BTTS, ASIAN_HANDICAP, CORRECT_SCORE, …",
        ),
        ColumnSpec(name="outcome", dtype="string", nullable=False),
        ColumnSpec(name="odds_decimal", dtype="float64", nullable=False),
        ColumnSpec(
            name="broker",
            dtype="string",
            nullable=True,
            description="Execution-side broker (e.g. UNITY). Row-level, not a partition dim.",
        ),
        ColumnSpec(
            name="client",
            dtype="string",
            nullable=True,
            description="Allocation-side client id. Row-level, not a partition dim.",
        ),
    ],
    symbol_column="fixture_id",
    required_row_count_min=1,
)

# ---------------------------------------------------------------------------
# Prediction markets (Polymarket, Kalshi, …) — Phase 1.1
# ---------------------------------------------------------------------------

PREDICTION_PREDICTION_MARKET_TRADES = SchemaContract(
    category="prediction",
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
            name="market_category",
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
    category="sports",
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
    category="sports",
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
    category="sports",
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
# Registry side-effects
# ---------------------------------------------------------------------------

CONTRACT_REGISTRY[("sports", "odds", "trades")] = SPORTS_ODDS_TRADES
CONTRACT_REGISTRY[("prediction", "prediction_market", "trades")] = PREDICTION_PREDICTION_MARKET_TRADES
CONTRACT_REGISTRY[("sports", "odds", "sports_odds_snapshot")] = SPORTS_ODDS_SNAPSHOT
CONTRACT_REGISTRY[("sports", "odds", "sports_odds_movement")] = SPORTS_ODDS_MOVEMENT
CONTRACT_REGISTRY[("sports", "odds", "sports_arbitrage")] = SPORTS_ODDS_ARBITRAGE


__all__ = [
    "PREDICTION_PREDICTION_MARKET_TRADES",
    "SPORTS_ODDS_ARBITRAGE",
    "SPORTS_ODDS_MOVEMENT",
    "SPORTS_ODDS_SNAPSHOT",
    "SPORTS_ODDS_TRADES",
]
