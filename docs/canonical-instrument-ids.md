# Canonical Instrument IDs & Schema Contracts

<!-- POST_PLAN_SECTION_2026_05_06 -->

## Post-2026-05-06 additions

**Post-2026-05-06 additions** — `MarketLifecycle` dataclass added per market_id for predictions (`market_created_at` / `resolution_time` / `settlement_time`). Polymarket conditionId / Kalshi ticker map to `CanonicalQuestionGroup` enum via `classify_market_to_canonical_group(market_metadata)` in `canonical/domain/predictions/classifiers.py`. Stability hash prevents re-classification churn on classifier-version change.

**Workspace SSOTs**: [POST_PLAN_REALITY](../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md) (10 cross-cutting principles + active plans), [availability-manifest-and-data-status](../../unified-trading-pm/codex/02-data/availability-manifest-and-data-status.md), [deployment-clusters-live-vs-batch](../../unified-trading-pm/codex/05-infrastructure/deployment-clusters-live-vs-batch.md), [shard-level-failure-isolation](../../unified-trading-pm/codex/04-architecture/shard-level-failure-isolation.md), [error-handling](../../unified-trading-pm/codex/06-coding-standards/error-handling.md), [validation-patterns](../../unified-trading-pm/codex/06-coding-standards/validation-patterns.md).

SSOT for the canonical `instrument_id` format used across MTDS,
instruments-service, features-\*, ML, strategy, execution, risk, and position
services. Every row in every parquet / every payload on every bus MUST carry
a canonical `instrument_id`. Services MUST build IDs through
`build_instrument_id(...)` — no local formatters, no string concatenation,
no category-specific variants.

## Canonical Format

```
VENUE:INSTRUMENT_TYPE:SYMBOL
```

DeFi composes the venue with its chain:

```
VENUE-CHAIN:INSTRUMENT_TYPE:SYMBOL
```

- `VENUE` is upper-cased (CeFi/TradFi) or the protocol-only token (DeFi:
  `AAVE_V3`, `UNISWAP_V3`, `LIDO`).
- `CHAIN` (DeFi only) is upper-cased (`ETHEREUM`, `ARBITRUM`, `SOLANA`).
- `INSTRUMENT_TYPE` is the `InstrumentType.value` as emitted by the enum
  (`PERPETUAL`, `OPTION`, `POOL`, `PREDICTION_MARKET`, ...).
- `SYMBOL` is upper-cased for CeFi/TradFi. DeFi preserves the on-chain case
  (e.g. `aUSDC`, `stETH`, `variableDebtUSDC`, `USDC-WETH-500`).

## `build_instrument_id` API

Defined at `unified_api_contracts/internal/reference/canonical_id_builder.py:291`.

```python
from unified_api_contracts import InstrumentType, build_instrument_id

build_instrument_id(
    venue: str,
    instrument_type: InstrumentType,
    symbol: str,
    *,
    expiry_date: datetime.date | None = None,
    strike: decimal.Decimal | None = None,
    option_right: Literal["C", "P"] | None = None,
    underlying: str | None = None,
    chain: str | None = None,
) -> str
```

Missing required kwargs for a given `InstrumentType` raise `ValueError` —
there are no silent defaults (e.g. `OPTION` without `expiry_date` + `strike`

- `option_right` is rejected).

### Per-InstrumentType formats

| `InstrumentType`    | Category (typical) | Format                                        | Example                                                  |
| ------------------- | ------------------ | --------------------------------------------- | -------------------------------------------------------- |
| `SPOT_PAIR`         | cefi               | `V:SPOT_PAIR:S`                               | `BINANCE:SPOT_PAIR:BTCUSDT`                              |
| `PERPETUAL`         | cefi               | `V:PERPETUAL:S`                               | `BINANCE_FUTURES:PERPETUAL:BTCUSDT`                      |
| `FUTURE`            | cefi / tradfi      | `V:FUTURE:S-YYYYMMDD`                         | `CME:FUTURE:ES-20260620`                                 |
| `OPTION`            | cefi / tradfi      | `V:OPTION:S-YYYYMMDD-STRIKE-[C\|P]`           | `DERIBIT:OPTION:BTC-20260328-65000-C`                    |
| `POOL`              | defi               | `V-C:POOL:S`                                  | `UNISWAP_V3-ETHEREUM:POOL:USDC-WETH-500`                 |
| `LENDING`           | defi               | `V-C:LENDING:S`                               | `AAVE_V3-ETHEREUM:LENDING:USDC`                          |
| `A_TOKEN`           | defi               | `V-C:A_TOKEN:S` (case-sensitive)              | `AAVE_V3-ETHEREUM:A_TOKEN:aUSDC`                         |
| `DEBT_TOKEN`        | defi               | `V-C:DEBT_TOKEN:S` (case-sensitive)           | `AAVE_V3-ETHEREUM:DEBT_TOKEN:variableDebtUSDC`           |
| `LST`               | defi               | `V-C:LST:S` (case-sensitive)                  | `LIDO-ETHEREUM:LST:stETH`                                |
| `YIELD_BEARING`     | defi               | `V-C:YIELD_BEARING:S`                         | `ETHENA-ETHEREUM:YIELD_BEARING:sUSDe`                    |
| `STAKING`           | defi               | `V-C:STAKING:S`                               | `LIDO-ETHEREUM:STAKING:stETH`                            |
| `SPOT_ASSET`        | defi               | `V-C:SPOT_ASSET:S`                            | `UNISWAP_V3-ETHEREUM:SPOT_ASSET:WETH`                    |
| `ETF`               | tradfi             | `V:ETF:S`                                     | `NYSE:ETF:SPY`                                           |
| `EQUITY`            | tradfi             | `V:EQUITY:S`                                  | `NASDAQ:EQUITY:AAPL`                                     |
| `COMMODITY`         | tradfi             | `V:COMMODITY:S`                               | `CME:COMMODITY:CL`                                       |
| `CURRENCY`          | tradfi             | `V:CURRENCY:S`                                | `FX:CURRENCY:EURUSD`                                     |
| `INDEX`             | tradfi             | `V:INDEX:S`                                   | `CBOE:INDEX:VIX`                                         |
| `BOND`              | tradfi             | `V:BOND:S`                                    | `CME:BOND:US10Y`                                         |
| `CDS`               | tradfi             | `V:CDS:S`                                     | `ICE:CDS:ITRAXX`                                         |
| `COMBO`             | multi-leg          | `V:COMBO:S` (opaque combo id)                 | `DERIBIT:COMBO:BTC-20260328-CONDOR-A`                    |
| `PREDICTION_MARKET` | prediction         | `V:PREDICTION_MARKET:S` (pre-built domain id) | `POLYMARKET:PREDICTION_MARKET:event-xxx-yes`             |
| `EXCHANGE_ODDS`     | sports             | `V:EXCHANGE_ODDS:S`                           | `BETFAIR_EX:EXCHANGE_ODDS:epl-2026-04-17-match-123-home` |
| `FIXED_ODDS`        | sports             | `V:FIXED_ODDS:S`                              | `PINNACLE:FIXED_ODDS:epl-2026-04-17-match-123-over2_5`   |
| `PROP`              | sports             | `V:PROP:S`                                    | `DRAFTKINGS:PROP:nba-player-points-over-30`              |

All 24 `InstrumentType` values are covered — `SUPPORTED_INSTRUMENT_TYPES`
in the module asserts this and a unit test blocks accidental enum
additions without a corresponding builder update.

Sports / prediction `SYMBOL` is the domain canonical id pre-built by
`canonical/domain/sports/canonical_ids.py` or
`canonical/domain/prediction/prediction_mapping.py`; the dispatcher simply
wraps it with the `VENUE:TYPE:` prefix.

## Per-Day Availability Filter

Defined at `unified_api_contracts/internal/reference/availability.py:89`.

```python
from unified_api_contracts.internal import get_instruments_available_on

rows = get_instruments_available_on(
    ref_date,                  # datetime.date
    catalogue,                 # Iterable[InstrumentRecord] — caller loads
    category="cefi",           # optional
    venue="BINANCE_FUTURES",   # optional
    instrument_type="perpetual",  # optional
    chain=None,                # optional (DeFi)
)
```

- `available_from_datetime is None` → open-ended on the left (inception).
- `available_to_datetime is None` → still active.
- Boundaries are inclusive on both ends (`from.date() <= ref_date <= to.date()`).
- Filter args are AND-combined; `None` is wildcard; matching is case-
  insensitive.
- Pure function: UAC does not load the catalogue. Consumers (instruments-
  service, MTDS, features-\*, strategy, execution, risk, position) fetch the
  parquet via UTL, pass it in.

## SchemaContract Framework

Defined at `unified_api_contracts/internal/schemas/contracts.py`.

```python
from unified_api_contracts import (
    CONTRACT_REGISTRY,
    SchemaContract,
    validate_dataframe,
)

contract = CONTRACT_REGISTRY[("cefi", "perpetual", "trades")]
violations = validate_dataframe(df, contract)  # list[Violation]
```

Contracts declare:

- `category`, `instrument_type`, `data_type` — lookup key in `CONTRACT_REGISTRY`.
- `columns: list[ColumnSpec]` — name, dtype, nullable flag, description.
- `required_row_count_min` — basic floor; zero means "empty frames allowed".
- `null_rate_max: dict[str, float]` — per-column cap for noisy sources.

Validation checks (in order): required columns present, dtype per column,
non-nullable columns contain zero nulls, null-rate caps, row-count floor.
An empty `list[Violation]` means the frame passes.

### Built-in registry keys

All entries below are exposed through `CONTRACT_REGISTRY`:

| Key                                               |
| ------------------------------------------------- |
| `("cefi", "perpetual", "trades")`                 |
| `("cefi", "perpetual", "book_snapshot_5")`        |
| `("cefi", "options_chain", "trades")`             |
| `("cefi", "futures_chain", "trades")`             |
| `("tradfi", "future", "trades")`                  |
| `("tradfi", "options_chain", "trades")`           |
| `("tradfi", "equity", "trades")`                  |
| `("defi", "lending_position", "lending_indices")` |
| `("defi", "dex_pool", "dex_pool_swaps")`          |
| `("defi", "lst", "lst_rates")`                    |

Add new (category, instrument_type, data_type) triples by appending a new
`SchemaContract` constant in `contracts.py` and registering it in
`CONTRACT_REGISTRY`. Do NOT define contracts inside services — the module
docstring calls out UAC as the single source of truth.

## Downstream Consumers

- MTDS passes the matching contract to
  `StreamingParquetWriter(schema_contract=..., partition_path=...)` — see
  `market-tick-data-service/docs/canonical-write-conventions.md`.
- `ManifestWriter.write_with_zero_fill(...)` uses
  `get_instruments_available_on` to compute the expected universe for the
  day — see `unified-trading-library/docs/data-sink-validation.md`.
- instruments-service reference-data adapters populate `instrument_key` via
  `unified_api_contracts.build_instrument_id(...)` on every record they emit;
  `build_instrument_catalogue.py` then walks those per-date snapshots into
  the daily `prod/catalog.parquet` rollup (the SSOT MTDS + data-status read).
