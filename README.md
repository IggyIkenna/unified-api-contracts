# api-contracts

Pydantic schemas, example JSON, and VCR cassette directories for external APIs used by the unified-trading system (UMI, UOI, and services). Contracts cover the full venue surface: public market data, private order feed, position feed, errors, WebSockets, FIX, and corner cases for CeFi, DeFi, and TradFi.

**✅ Schema Validation**: All schemas validated against real API responses using Context7 for accurate type definitions and Decimal precision for financial data.

## Purpose

- **Single source of truth** for external API request/response shapes (Databento, Tardis, CCXT, The Graph, OKX, Bybit, Upbit, Yahoo Finance, Alchemy, Hyperliquid, Aster, IBKR, etc.).
- **Type safety**: UMI and UOI validate or parse raw responses through these schemas before mapping to canonical types.
- **Testability**: VCR cassettes under each `mocks/` directory allow tests to run without live API calls.
- **Contract-vs-reality**: Examples and optional live verification keep schemas aligned with provider behavior.

## Structure

Per-API directories contain:

- `schemas.py` — Pydantic models for request/response shapes.
- `examples/` — Captured JSON (or CSV) from real or trial API calls.
- `mocks/` — VCR cassettes for replay in tests.

See [CONTRIBUTING.md](CONTRIBUTING.md) for how to add a venue, capture examples, and record VCR.

## Venues covered

| Category | Venues |
|----------|--------|
| **High-Priority CeFi exchanges** | **✅ Binance, ✅ Coinbase, ✅ Kraken** (validated schemas) |
| Other CeFi exchanges | OKX, Bybit, Upbit (CCXT and/or REST) |
| CeFi / TradFi data | Databento, Tardis, Yahoo Finance |
| DeFi | The Graph, Alchemy, Hyperliquid, Aster |
| TradFi execution | Interactive Brokers (IBKR, TWS/ib_insync) |

See per-venue README or index under each directory for market data, order feed, position feed, errors, WebSocket, and FIX coverage.

## Consuming from UMI / UOI

Consumers use path dependency `../api-contracts` (see path-dependency-ci.mdc). Example:

```python
from api_contracts.databento.schemas import DatabentoTrade
# validate raw response then map to canonical types
```

## Self-test: schemas and coverage

Quality gates run tests that ensure:

- **Per-venue schema coverage**: Each venue’s `schemas.py` exports the response and error classes declared in `api_contracts/venue_manifest.py` (REST, WebSocket, FIX, and error types per venue).
- **Example validation**: Every `examples/*.json` file validates against the correct Pydantic schema.
- **Manifest consistency**: Venues declare `has_rest`, `has_websocket`, `has_fix`; at least one venue has REST and one has WebSocket.

See `tests/test_venue_contract_coverage.py` and `tests/test_contracts_vs_reality.py`.

## Schema Validation & Collection

### Automated Response Collection

Collect real API responses for schema validation:

```bash
# Collect all high-priority venues
uv run python scripts/collect_responses.py

# Collect specific venue 
uv run python scripts/collect_responses.py --venue binance

# List supported venues
uv run python scripts/collect_responses.py --list
```

**Context7 Integration**: Uses `unified-config-interface` for secure API key management via Secret Manager.

### Schema Validation

Validate schemas against real API responses:

```bash
# Validate all venues
uv run python scripts/validate_schemas.py

# Validate specific venue
uv run python scripts/validate_schemas.py --venue coinbase

# Generate new schemas from responses
uv run python scripts/validate_schemas.py --generate-schemas --venue kraken
```

**Features**:
- **Type Safety**: Uses `Decimal` for financial precision instead of `float`
- **Missing Field Detection**: Identifies fields missing from schemas
- **Type Mismatch Analysis**: Reports incorrect field types
- **Schema Generation**: Auto-generates schemas from real API responses

### Quality Gates Integration

Schema validation is integrated into quality gates:

```bash
# Run all quality checks including schema validation
bash scripts/quality-gates.sh

# Run only schema validation tests
bash scripts/quality-gates.sh --test
```

**Validation Tests**: Located in `tests/test_schema_validation.py`, covering:
- Real API response validation against schemas
- Decimal precision for financial fields
- Error handling for invalid data
- Schema coverage across venues

## Usage Patterns

### Financial Precision

Always use `Decimal` for financial data to avoid floating-point precision errors:

```python
from decimal import Decimal
from api_contracts.binance.schemas import BinanceTicker

# ✅ Correct - preserves precision
ticker = BinanceTicker(
    symbol="BTCUSDT",
    lastPrice=Decimal("50000.12345678"),  # 8 decimal places preserved
    volume=Decimal("1234.56789"),
    # ...
)

# ❌ Wrong - loses precision  
ticker = BinanceTicker(
    symbol="BTCUSDT", 
    lastPrice=50000.12345678,  # May lose precision
    # ...
)
```

### List-Based API Responses

Handle APIs that return arrays (klines, candles, trades):

```python
from api_contracts.binance.schemas import BinanceKline

# Binance klines return [timestamp, open, high, low, close, volume, ...]
kline_data = [1771898400000, "64160.26", "64500.00", "64000.00", "64109.81", "599.63527", ...]

# Use from_list classmethod for conversion
kline = BinanceKline.from_list(kline_data)
print(kline.open_price)  # Decimal('64160.26')
```

### Error Response Handling

Standard error handling across venues:

```python
from api_contracts.binance.schemas import BinanceError
from api_contracts.coinbase.schemas import CoinbaseError

try:
    # API call
    response_data = api_call()
except APIError as e:
    # Parse venue-specific error format
    if venue == "binance":
        error = BinanceError(**e.response)
        print(f"Binance error {error.code}: {error.msg}")
    elif venue == "coinbase":
        error = CoinbaseError(**e.response)  
        print(f"Coinbase error: {error.message}")
```

### WebSocket Schema Reuse

REST and WebSocket schemas are often compatible:

```python
from api_contracts.binance.schemas import BinanceTicker

# Same schema works for both REST and WebSocket
rest_ticker = BinanceTicker(**rest_api_response)
ws_ticker = BinanceTicker(**websocket_message_data)
```

## Development Setup

### Installation

```bash
# Install dependencies
uv pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install
```

### Pre-commit Hooks

Install and run pre-commit hooks:

```bash
# Install hooks (one-time setup)
pre-commit install

# Run hooks on all files
pre-commit run --all-files

# Hooks run automatically on commit
git commit -m "your message"
```

### Quality Gates

```bash
bash scripts/quality-gates.sh        # Auto-fix
bash scripts/quality-gates.sh --no-fix  # Verify
```

## Contract-vs-reality

- **CI**: Validate all `examples/*.json` against the corresponding Pydantic models (no live calls).
- **Optional live verification**: When `LIVE_API_VERIFICATION=1`, use the same config and Secret Manager as UMI/UOI (no duplication). Install from workspace: `uv pip install -e ../unified-cloud-services -e ../unified-config-interface`, then run `scripts/verify_contracts_vs_reality_live.py`. API keys are resolved via `config.get_secret(secret_field)` (unified-config-interface), which uses unified-cloud-services under the hood.

## Permissions and collaborators

GitHub usernames **CosmicTrader** and **datadodo** have Write/Maintain (or Admin per org policy) access for maintaining contracts and running contract-vs-reality checks. Documented in this README and optionally in a PERMISSIONS or COLLABORATORS file.

## Creating this repo on GitHub

If you are setting up the repo for the first time:

1. Create a new GitHub repository (e.g. `unified-trading-api-contracts` or `api-contracts`) under the same org/owner as other unified-trading repos.
2. Add collaborators **CosmicTrader** and **datadodo** with Write or Admin access (Settings → Collaborators).
3. Push this directory: `git remote add origin <repo-url> && git push -u origin main`.

Quality gates and optional contract-vs-reality can be added to GitHub Actions once the repo exists.
