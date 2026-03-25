"""Polymarket settlement source registry.

Maps each underlying asset/index to its settlement data source.
Polymarket markets resolve via oracle (UMA) using the settlement source
specified in each market's ``resolutionSource`` field.

This registry codifies the known settlement sources for programmatic use
(e.g. verifying resolution, cross-referencing with our own data feeds).
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SettlementSource:
    """Settlement source for a prediction market underlying."""

    underlying: str
    source_name: str
    source_url: str
    resolution_type: str  # chainlink | exchange_candle | official_close | commodity_settle
    chainlink_feed_id: str | None = None
    exchange_pair: str | None = None
    notes: str | None = None


SETTLEMENT_REGISTRY: dict[str, SettlementSource] = {
    # Crypto — Chainlink data streams (primary), Binance candles (secondary)
    "BTC": SettlementSource(
        underlying="BTC",
        source_name="Chainlink BTC/USD",
        source_url="https://data.chain.link/streams/btc-usd",
        resolution_type="chainlink",
        chainlink_feed_id="btc-usd",
        exchange_pair="BTCUSDT",
        notes="Polymarket also uses Binance BTCUSDT 1m candle High for some markets",
    ),
    "ETH": SettlementSource(
        underlying="ETH",
        source_name="Chainlink ETH/USD",
        source_url="https://data.chain.link/streams/eth-usd",
        resolution_type="chainlink",
        chainlink_feed_id="eth-usd",
        exchange_pair="ETHUSDT",
    ),
    "SOL": SettlementSource(
        underlying="SOL",
        source_name="Chainlink SOL/USD",
        source_url="https://data.chain.link/streams/sol-usd",
        resolution_type="chainlink",
        chainlink_feed_id="sol-usd",
    ),
    "XRP": SettlementSource(
        underlying="XRP",
        source_name="Chainlink XRP/USD",
        source_url="https://data.chain.link/streams/xrp-usd",
        resolution_type="chainlink",
        chainlink_feed_id="xrp-usd",
    ),
    "DOGE": SettlementSource(
        underlying="DOGE",
        source_name="Chainlink DOGE/USD",
        source_url="https://data.chain.link/streams/doge-usd",
        resolution_type="chainlink",
        chainlink_feed_id="doge-usd",
    ),
    "BNB": SettlementSource(
        underlying="BNB",
        source_name="Chainlink BNB/USD",
        source_url="https://data.chain.link/streams/bnb-usd",
        resolution_type="chainlink",
        chainlink_feed_id="bnb-usd",
    ),
    "HYPE": SettlementSource(
        underlying="HYPE",
        source_name="Chainlink",
        source_url="https://data.chain.link/streams",
        resolution_type="chainlink",
        notes="Hyperliquid token — check exact Chainlink feed availability",
    ),
    # Equity indices — official close prices
    "SPX": SettlementSource(
        underlying="SPX",
        source_name="S&P 500 Official Close",
        source_url="https://www.spglobal.com/spdji/en/indices/equity/sp-500/",
        resolution_type="official_close",
        notes=(
            "S&P 500: 503 stocks, float-adjusted market cap weighted. "
            "Top 10 (AAPL, MSFT, NVDA, AMZN, GOOGL, META, BRK.B, AVGO, JPM, LLY) ~35%. "
            "Weightings published quarterly on spglobal.com, change intraday by market cap."
        ),
    ),
    "NDX": SettlementSource(
        underlying="NDX",
        source_name="NASDAQ-100 Official Close",
        source_url="https://www.nasdaq.com/market-activity/index/ndx",
        resolution_type="official_close",
        notes="NASDAQ-100: 100 largest non-financial NASDAQ stocks by market cap",
    ),
    "DJIA": SettlementSource(
        underlying="DJIA",
        source_name="Dow Jones Industrial Average Official Close",
        source_url="https://www.spglobal.com/spdji/en/indices/equity/dow-jones-industrial-average/",
        resolution_type="official_close",
        notes="DJIA: 30 blue-chip stocks, price-weighted (not market-cap)",
    ),
    "DAX": SettlementSource(
        underlying="DAX",
        source_name="DAX Official Close",
        source_url="https://www.dax-indices.com/",
        resolution_type="official_close",
        notes="DAX 40: 40 largest German stocks on Frankfurt Stock Exchange",
    ),
    "HANG_SENG": SettlementSource(
        underlying="HANG_SENG",
        source_name="Hang Seng Index Official Close",
        source_url="https://www.hsi.com.hk/",
        resolution_type="official_close",
    ),
    "RUSSELL_2000": SettlementSource(
        underlying="RUSSELL_2000",
        source_name="Russell 2000 Official Close",
        source_url="https://www.ftserussell.com/products/indices/russell-us",
        resolution_type="official_close",
        notes="Russell 2000: smallest 2000 stocks in Russell 3000 by market cap",
    ),
    # Commodities — exchange settlement prices
    "CRUDE_OIL": SettlementSource(
        underlying="CRUDE_OIL",
        source_name="NYMEX WTI Crude Oil (CL) Settlement",
        source_url="https://www.cmegroup.com/markets/energy/crude-oil/light-sweet-crude.html",
        resolution_type="commodity_settle",
        notes="Front-month CL futures settlement price at 14:30 ET",
    ),
    "GOLD": SettlementSource(
        underlying="GOLD",
        source_name="COMEX Gold (GC) Settlement",
        source_url="https://www.cmegroup.com/markets/metals/precious/gold.html",
        resolution_type="commodity_settle",
        notes="Front-month GC futures settlement price",
    ),
    "SILVER": SettlementSource(
        underlying="SILVER",
        source_name="COMEX Silver (SI) Settlement",
        source_url="https://www.cmegroup.com/markets/metals/precious/silver.html",
        resolution_type="commodity_settle",
        notes="Front-month SI futures settlement price",
    ),
    # Forex — daily close
    "GBPUSD": SettlementSource(
        underlying="GBPUSD",
        source_name="GBP/USD Daily Close",
        source_url="",
        resolution_type="official_close",
    ),
    "EURUSD": SettlementSource(
        underlying="EURUSD",
        source_name="EUR/USD Daily Close",
        source_url="",
        resolution_type="official_close",
    ),
    "USDJPY": SettlementSource(
        underlying="USDJPY",
        source_name="USD/JPY Daily Close",
        source_url="",
        resolution_type="official_close",
    ),
    "USDKRW": SettlementSource(
        underlying="USDKRW",
        source_name="USD/KRW Daily Close",
        source_url="",
        resolution_type="official_close",
    ),
}


def get_settlement_source(underlying: str) -> SettlementSource | None:
    """Look up the settlement source for an underlying."""
    return SETTLEMENT_REGISTRY.get(underlying.upper())
