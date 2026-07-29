# Canonical Instrument IDs & Schema Contracts — unified-api-contracts

> **Canonical SSOT for the instrument-id grammar/taxonomy:**
> [cross-asset-canonical-target-ssot.md](../../unified-trading-pm/codex/02-data/cross-asset-canonical-target-ssot.md)
> § 2 "Canonical instrument-id grammar" (the per-asset-group/type grammar, the SPOT_PAIR vs SPOT_ASSET vs POOL decision
> rule, the lending `A_TOKEN`/`DEBT_TOKEN` split, the CLOB-vs-DEX-pool perp classification). This file carries only the
> **unified-api-contracts** builder/validation API surface. **Do not duplicate the grammar tables here; if this file
> disagrees with codex, codex wins.**

Every row in every parquet / every payload on every bus MUST carry a canonical `instrument_id`, built through
`build_instrument_id(...)` — no local formatters, no string concatenation, no category-specific variants.

## `build_instrument_id` API (this repo)

Defined at `unified_api_contracts/internal/reference/canonical_id_builder.py`.

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

- Canonical form `VENUE:INSTRUMENT_TYPE:SYMBOL` (CeFi/TradFi) or `VENUE-CHAIN:INSTRUMENT_TYPE:SYMBOL` (DeFi). DeFi
  preserves on-chain symbol case (`aUSDC`, `stETH`, `USDC-WETH-500`); CeFi/TradFi upper-case the symbol. `INSTRUMENT_TYPE`
  is the `InstrumentType.value` as emitted by the enum. See the codex SSOT above for the authoritative per-type grammar +
  examples.
- Missing required kwargs for a given `InstrumentType` raise `ValueError` — no silent defaults (e.g. `OPTION` without
  `expiry_date` + `strike` + `option_right` is rejected).
- `SUPPORTED_INSTRUMENT_TYPES` asserts every active `InstrumentType` is covered; a unit test blocks enum additions
  without a builder update. Sports/prediction `SYMBOL` is a domain canonical id pre-built by
  `canonical/domain/sports/canonical_ids.py` / `canonical/domain/prediction/prediction_mapping.py`; the dispatcher wraps
  it with the `VENUE:TYPE:` prefix.

## Per-day availability filter (this repo)

Defined at `unified_api_contracts/internal/reference/availability.py`.

```python
from unified_api_contracts.internal import get_instruments_available_on

rows = get_instruments_available_on(
    ref_date, catalogue, category="cefi", venue="BINANCE_FUTURES",
    instrument_type="perpetual", chain=None,
)
```

`available_from_datetime is None` → open-ended left (inception); `available_to_datetime is None` → still active;
boundaries inclusive both ends; filter args AND-combined, `None` = wildcard, case-insensitive. Pure function — UAC does
not load the catalogue; consumers fetch the parquet via UTL and pass it in.

## SchemaContract framework (this repo)

Defined at `unified_api_contracts/internal/schemas/contracts.py`.

```python
from unified_api_contracts import CONTRACT_REGISTRY, SchemaContract, validate_dataframe

contract = CONTRACT_REGISTRY[("cefi", "perpetual", "trades")]
violations = validate_dataframe(df, contract)  # list[Violation]
```

Contracts declare `(category, instrument_type, data_type)` lookup key, `columns: list[ColumnSpec]`,
`required_row_count_min`, and `null_rate_max` per column. Validation order: required columns present → dtype → non-nullable
columns have zero nulls → null-rate caps → row-count floor; an empty `list[Violation]` passes. Registered keys include
`("cefi","perpetual","trades")`, `("cefi","perpetual","book_snapshot_5")`, `("cefi","options_chain","trades")`,
`("tradfi","future","trades")`, `("tradfi","equity","trades")`, `("defi","dex_pool","dex_pool_swaps")`,
`("defi","lst","lst_rates")`, .... Add triples by appending a `SchemaContract` constant and registering it — never define
contracts inside services (UAC is the single source of truth).

## Downstream consumers

- MTDS passes the matching contract to `StreamingParquetWriter(schema_contract=..., partition_path=...)`.
- `ManifestWriter.write_with_zero_fill(...)` uses `get_instruments_available_on` to compute the day's expected universe.
- instruments-service reference-data adapters populate `instrument_key` via `build_instrument_id(...)` on every record;
  `build_instrument_catalogue.py` walks those per-date snapshots into the daily `prod/catalog.parquet` rollup (the SSOT
  MTDS + data-status read).
