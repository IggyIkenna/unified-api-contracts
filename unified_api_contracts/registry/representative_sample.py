"""Representative instrument sample — SSOT for mock/test instrument selection.

This registry defines WHICH specific instruments are generated in mock mode.
The InstrumentGenerator reads this instead of hardcoding its own lists.
Updating the sample is a registry change, not a generator code change.

3-Layer Architecture:
  Layer 1: This registry — deterministic default sample, always the same
  Layer 2: ScenarioConfig.instrument_overrides — inject/expire/delist per scenario
  Layer 3: Runtime API — create/delete/expire instruments ad-hoc during a session

The sample covers every venue x instrument_type combination in VENUE_CATEGORY_MAP.
For derivatives (futures, options), strike/expiry generation is config-driven so
users can create arbitrary new strikes and terms for scenario testing without
waiting for real time to pass.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# CeFi Spot — venue, symbol, base, quote, ccxt_symbol, ccxt_exchange
# ---------------------------------------------------------------------------

CEFI_SPOT_SPECS: list[dict[str, str]] = [
    {
        "venue": "BINANCE-SPOT",
        "symbol": "BTC-USDT",
        "base": "BTC",
        "quote": "USDT",
        "ccxt_symbol": "BTC/USDT",
        "ccxt_exchange": "binance",
        "available_from": "2017-01-01",
    },
    {
        "venue": "BINANCE-SPOT",
        "symbol": "ETH-USDT",
        "base": "ETH",
        "quote": "USDT",
        "ccxt_symbol": "ETH/USDT",
        "ccxt_exchange": "binance",
        "available_from": "2015-07-30",
    },
    {
        "venue": "BINANCE-SPOT",
        "symbol": "SOL-USDT",
        "base": "SOL",
        "quote": "USDT",
        "ccxt_symbol": "SOL/USDT",
        "ccxt_exchange": "binance",
        "available_from": "2020-04-10",
    },
    {
        "venue": "COINBASE",
        "symbol": "BTC-USD",
        "base": "BTC",
        "quote": "USD",
        "ccxt_symbol": "BTC/USD",
        "ccxt_exchange": "coinbase",
        "available_from": "2017-01-01",
    },
    {
        "venue": "BYBIT",
        "symbol": "ETH-USDT",
        "base": "ETH",
        "quote": "USDT",
        "ccxt_symbol": "ETH/USDT",
        "ccxt_exchange": "bybit",
        "available_from": "2015-07-30",
    },
    {
        "venue": "OKX",
        "symbol": "BTC-USDT",
        "base": "BTC",
        "quote": "USDT",
        "ccxt_symbol": "BTC/USDT",
        "ccxt_exchange": "okx",
        "available_from": "2017-01-01",
    },
    {
        "venue": "UPBIT",
        "symbol": "BTC-KRW",
        "base": "BTC",
        "quote": "KRW",
        "ccxt_symbol": "BTC/KRW",
        "ccxt_exchange": "upbit",
        "available_from": "2017-01-01",
    },
]

# ---------------------------------------------------------------------------
# CeFi Perpetuals — venue, symbol, base, quote, raw_symbol
# ---------------------------------------------------------------------------

CEFI_PERPETUAL_SPECS: list[dict[str, str | float]] = [
    {
        "venue": "BINANCE-FUTURES",
        "symbol": "BTC-USDT",
        "base": "BTC",
        "quote": "USDT",
        "raw_symbol": "BTC-USDT-PERP",
        "available_from": "2020-01-01",
    },
    {
        "venue": "DERIBIT",
        "symbol": "BTC-USDC",
        "base": "BTC",
        "quote": "USDC",
        "raw_symbol": "BTC-PERPETUAL",
        "available_from": "2020-01-01",
    },
    {
        "venue": "HYPERLIQUID",
        "symbol": "ETH",
        "base": "ETH",
        "quote": "USD",
        "raw_symbol": "ETH-PERP",
        "available_from": "2023-01-01",
    },
    {
        "venue": "OKX",
        "symbol": "SOL-USDT-SWAP",
        "base": "SOL",
        "quote": "USDT",
        "raw_symbol": "SOL-USDT-SWAP",
        "available_from": "2020-01-01",
    },
    {
        "venue": "BYBIT",
        "symbol": "BTC-USDT",
        "base": "BTC",
        "quote": "USDT",
        "raw_symbol": "BTCUSDT",
        "available_from": "2020-01-01",
    },
    {
        "venue": "ASTER",
        "symbol": "BTC",
        "base": "BTC",
        "quote": "USD",
        "raw_symbol": "BTC-PERP",
        "available_from": "2024-01-01",
    },
]

# ---------------------------------------------------------------------------
# CeFi Futures — venue + underlying for dated futures generation
# Expiries are computed at generation time from ref_date.
# ---------------------------------------------------------------------------

CEFI_FUTURES_SPECS: list[dict[str, str]] = [
    {"venue": "DERIBIT", "underlying": "BTC", "quote": "USD"},
]

# ---------------------------------------------------------------------------
# TradFi Equities — full spec with trading hours and holiday calendar
# ---------------------------------------------------------------------------

TRADFI_EQUITY_SPECS: list[dict[str, str]] = [
    {
        "venue": "NASDAQ",
        "symbol": "AAPL",
        "type": "EQUITY",
        "asset_class": "tradfi_equity",
        "trading_hours_open": "09:30",
        "trading_hours_close": "16:00",
        "regular_open_utc": "14:30",
        "regular_close_utc": "21:00",
        "holiday_calendar": "NYSE",
        "available_from": "1980-12-12",
    },
    {
        "venue": "NASDAQ",
        "symbol": "QQQ",
        "type": "ETF",
        "asset_class": "tradfi_etf",
        "trading_hours_open": "09:30",
        "trading_hours_close": "16:00",
        "regular_open_utc": "14:30",
        "regular_close_utc": "21:00",
        "holiday_calendar": "NYSE",
        "available_from": "1999-03-10",
    },
    {
        "venue": "NYSE",
        "symbol": "GLD",
        "type": "ETF",
        "asset_class": "tradfi_etf",
        "trading_hours_open": "09:30",
        "trading_hours_close": "16:00",
        "regular_open_utc": "14:30",
        "regular_close_utc": "21:00",
        "holiday_calendar": "NYSE",
        "available_from": "2004-11-18",
    },
    {
        "venue": "CBOE",
        "symbol": "VIX",
        "type": "INDEX",
        "asset_class": "tradfi_index",
        "trading_hours_open": "09:30",
        "trading_hours_close": "16:15",
        "regular_open_utc": "14:30",
        "regular_close_utc": "21:15",
        "holiday_calendar": "CBOE",
        "available_from": "1993-01-19",
    },
]

# ---------------------------------------------------------------------------
# TradFi Futures — root symbols + contract specs per venue
# Format: (root_symbol, description, base_asset, contract_size, tick_size)
# Expiries computed from ref_date using CME_MONTH_CODES.
# ---------------------------------------------------------------------------

TRADFI_FUTURES_SPECS: list[dict[str, str | float]] = [
    {
        "venue": "CME",
        "root": "ES",
        "description": "E-mini S&P 500",
        "base": "ES",
        "contract_size": 50.0,
        "tick_size": 0.25,
    },
    {
        "venue": "ICE",
        "root": "ZB",
        "description": "US Treasury Bond Future",
        "base": "ZB",
        "contract_size": 1000.0,
        "tick_size": 0.03125,
    },
    {
        "venue": "ICE",
        "root": "ZN",
        "description": "10-Year T-Note Future",
        "base": "ZN",
        "contract_size": 1000.0,
        "tick_size": 0.015625,
    },
]

# ---------------------------------------------------------------------------
# DeFi instruments — complete spec per instrument
# ---------------------------------------------------------------------------

DEFI_INSTRUMENT_SPECS: list[dict[str, str | float | int]] = [
    # Aave V3 ETH — aTokens
    {
        "venue": "AAVEV3-ETHEREUM",
        "symbol": "aWETH",
        "underlying": "WETH",
        "type": "A_TOKEN",
        "ltv": 0.82,
        "liq_threshold": 0.85,
        "available_from": "2023-01-27",
    },
    {
        "venue": "AAVEV3-ETHEREUM",
        "symbol": "aUSDC",
        "underlying": "USDC",
        "type": "A_TOKEN",
        "ltv": 0.86,
        "liq_threshold": 0.89,
        "available_from": "2023-01-27",
    },
    {
        "venue": "AAVEV3-ETHEREUM",
        "symbol": "aUSDT",
        "underlying": "USDT",
        "type": "A_TOKEN",
        "ltv": 0.75,
        "liq_threshold": 0.80,
        "available_from": "2023-01-27",
    },
    # Aave V3 ETH — Debt tokens
    {
        "venue": "AAVEV3-ETHEREUM",
        "symbol": "variableDebtWETH",
        "underlying": "WETH",
        "type": "DEBT_TOKEN",
        "available_from": "2023-01-27",
    },
    {
        "venue": "AAVEV3-ETHEREUM",
        "symbol": "variableDebtUSDC",
        "underlying": "USDC",
        "type": "DEBT_TOKEN",
        "available_from": "2023-01-27",
    },
    {
        "venue": "AAVEV3-ETHEREUM",
        "symbol": "variableDebtUSDT",
        "underlying": "USDT",
        "type": "DEBT_TOKEN",
        "available_from": "2023-01-27",
    },
    # Compound V3
    {
        "venue": "COMPOUND_V3_ETH",
        "symbol": "cETHv3",
        "underlying": "ETH",
        "type": "POOL",
        "available_from": "2023-06-01",
    },
    # Uniswap V3
    {
        "venue": "UNISWAPV3-ETHEREUM",
        "symbol": "USDT-ETH-3000",
        "underlying": "ETH",
        "type": "POOL",
        "base": "USDT",
        "quote": "ETH",
        "fee_tier": 3000,
        "display": "USDT/ETH",
        "available_from": "2021-05-05",
    },
    # Uniswap V2
    {
        "venue": "UNISWAPV2-ETHEREUM",
        "symbol": "USDT-ETH",
        "underlying": "ETH",
        "type": "POOL",
        "base": "USDT",
        "quote": "ETH",
        "display": "USDT/ETH",
        "available_from": "2020-09-17",
    },
    # Uniswap V4
    {
        "venue": "UNISWAPV4-ETHEREUM",
        "symbol": "USDT-ETH",
        "underlying": "ETH",
        "type": "POOL",
        "base": "USDT",
        "quote": "ETH",
        "display": "USDT/ETH",
        "available_from": "2025-01-15",
    },
    # Lido
    {"venue": "LIDO", "symbol": "stETH", "underlying": "ETH", "type": "LST", "available_from": "2020-12-18"},
    {"venue": "LIDO", "symbol": "wstETH", "underlying": "ETH", "type": "LST", "available_from": "2021-02-11"},
    # EtherFi
    {"venue": "ETHERFI", "symbol": "eETH", "underlying": "ETH", "type": "LST", "available_from": "2023-06-15"},
    {"venue": "ETHERFI", "symbol": "weETH", "underlying": "ETH", "type": "LST", "available_from": "2023-11-01"},
    # Morpho
    {
        "venue": "MORPHO-ETHEREUM",
        "symbol": "wstETH-USDC",
        "underlying": "wstETH",
        "type": "POOL",
        "base": "wstETH",
        "quote": "USDC",
        "display": "wstETH/USDC",
        "available_from": "2024-01-10",
    },
    # Curve
    {
        "venue": "CURVE-ETHEREUM",
        "symbol": "3pool",
        "underlying": "DAI",
        "type": "POOL",
        "base": "DAI",
        "quote": "USDC",
        "display": "3pool",
        "available_from": "2020-09-15",
    },
    # Ethena
    {
        "venue": "ETHENA",
        "symbol": "USDe",
        "underlying": "USDe",
        "type": "YIELD_BEARING",
        "available_from": "2024-02-19",
    },
    {
        "venue": "ETHENA",
        "symbol": "sUSDe",
        "underlying": "USDe",
        "type": "YIELD_BEARING",
        "staked_underlying": "USDe",
        "available_from": "2024-04-02",
    },
    # Euler
    {
        "venue": "EULER-ETHEREUM",
        "symbol": "eUSDC",
        "underlying": "USDC",
        "type": "POOL",
        "available_from": "2024-03-04",
    },
]

# ---------------------------------------------------------------------------
# Sports instruments — complete spec per instrument
# condition_id/clob_token_id are real values from VCR cassettes
# ---------------------------------------------------------------------------

SPORTS_INSTRUMENT_SPECS: list[dict[str, str]] = [
    {
        "venue": "POLYMARKET",
        "symbol": "NBA-DAL-MEM-SPREAD-5.5",
        "type": "PREDICTION_MARKET",
        "asset_class": "prediction",
        "condition_id": "0x064d33e3f5703792aafa92bfb0ee10e08f461b1b34c02c1f02671892ede1609a",
        "clob_yes": "28182404005967940652495463228537840901055649726248190462854914416579180110833",
        "clob_no": "47044845753450022047436429968808601130811164131571549682541703866165095016290",
        "available_from": "2021-12-04",
        "available_to": "2021-12-11",
    },
    {
        "venue": "POLYMARKET",
        "symbol": "NFL-ATL-CAR-SPREAD-3.5",
        "type": "PREDICTION_MARKET",
        "asset_class": "prediction",
        "condition_id": "0x8e0c65676f129764a604fcf618b4f92c34e5dfd2ce4a4cbf7a6bcdfa942241af",
        "clob_yes": "56511259653855886659936827966786013545784841144903847037967986812745595430432",
        "clob_no": "14941478295244605382100055235924143559218628579320890713621951655794746924521",
        "available_from": "2021-10-31",
        "available_to": "2021-11-07",
    },
    {
        "venue": "BETFAIR",
        "symbol": "EPL-MCI-ARS",
        "type": "EXCHANGE_ODDS",
        "asset_class": "sports",
        "venue_type": "football",
        "available_from": "2024-08-01",
    },
    {
        "venue": "PINNACLE",
        "symbol": "NBA-LAL-BOS",
        "type": "FIXED_ODDS",
        "asset_class": "sports",
        "venue_type": "basketball",
        "available_from": "2024-10-01",
    },
]

# ---------------------------------------------------------------------------
# Options chain config — drives strike/expiry generation for Deribit BTC
# Users can override these to generate custom strikes/terms for scenario testing
# ---------------------------------------------------------------------------

OPTIONS_CHAIN_CONFIG: dict[str, str | float | int] = {
    "underlying": "BTC",
    "venue": "DERIBIT",
    "strike_interval_usd": 500,
    "atm_price_usd": 60000,
    "strike_range_pct": 0.30,
    "weekly_expiries": 4,
    "monthly_expiries": 3,
    "quarterly_expiries": 3,
}

# ---------------------------------------------------------------------------
# Futures chain config — CME month codes and quarterly schedule
# ---------------------------------------------------------------------------

CME_MONTH_CODES: dict[int, str] = {3: "H", 6: "M", 9: "U", 12: "Z"}
QUARTERLY_MONTHS: list[int] = [3, 6, 9, 12]

# ---------------------------------------------------------------------------
# Backwards-compatible aliases (used by downstream consumers)
# ---------------------------------------------------------------------------

CEFI_BASE_ASSETS: list[str] = sorted({s["base"] for s in CEFI_SPOT_SPECS})
TRADFI_EQUITIES: dict[str, list[tuple[str, str]]] = {}
for _spec in TRADFI_EQUITY_SPECS:
    TRADFI_EQUITIES.setdefault(_spec["venue"], []).append((_spec["symbol"], _spec["asset_class"]))
TRADFI_FUTURES: dict[str, list[tuple[str, str, float, float]]] = {}
for _spec in TRADFI_FUTURES_SPECS:
    TRADFI_FUTURES.setdefault(str(_spec["venue"]), []).append(
        (str(_spec["root"]), str(_spec["base"]), float(_spec["contract_size"]), float(_spec["tick_size"]))
    )
DEFI_INSTRUMENTS: dict[str, list[dict[str, str | float | int]]] = {}
for _spec in DEFI_INSTRUMENT_SPECS:
    DEFI_INSTRUMENTS.setdefault(str(_spec["venue"]), []).append(_spec)
DEFI_LENDING_ASSETS: list[str] = ["WETH", "USDC", "USDT"]
DEFI_POOL_PAIRS: list[tuple[str, str]] = [("USDT", "ETH"), ("USDC", "ETH"), ("DAI", "USDC")]
SPORTS_LEAGUES: list[str] = ["premier_league", "nba", "la_liga", "nfl"]
