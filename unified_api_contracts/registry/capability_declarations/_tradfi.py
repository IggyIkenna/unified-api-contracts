"""TradFi (traditional finance) capability declarations."""

from __future__ import annotations

from ..capability import SourceCapability

# ---------------------------------------------------------------------------
# TradFi (6)
# ---------------------------------------------------------------------------

_IBKR = SourceCapability(
    source="ibkr",
    domains=["market", "execution", "position", "reference"],
    crosscutting=["errors", "rate_limits", "latency", "connectivity"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"test": "paper_account", "prod": "live_account"},
    operations={
        "market": ["market_data", "historical_data", "realtime_bars", "scanner", "ws_market_data"],
        "execution": ["place_order", "cancel_order", "modify_order", "open_orders", "executions"],
        "position": ["portfolio", "positions", "account_summary", "pnl"],
        "reference": ["contract_details", "matching_symbols", "market_rules"],
    },
)

_DATABENTO = SourceCapability(
    source="databento",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits", "latency"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["mbp_1", "mbp_10", "trades", "ohlcv", "tbbo", "imbalance", "statistics"],
        "reference": ["symbology", "datasets", "metadata", "publishers"],
    },
)

_FRED = SourceCapability(
    source="fred",
    domains=["reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=False,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "reference": ["series", "observations", "releases", "categories", "tags", "sources"],
    },
)

_POLYGON = SourceCapability(
    source="polygon",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["aggregates", "trades", "quotes", "last_trade", "last_quote", "snapshot", "ws_trades", "ws_quotes"],
        "reference": ["tickers", "ticker_details", "exchanges", "conditions", "dividends", "splits"],
    },
)

_BARCHART = SourceCapability(
    source="barchart",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["ohlcv", "quotes", "dividends", "earnings"],
        "reference": ["symbols", "sectors", "indices"],
    },
)

_YAHOO_FINANCE = SourceCapability(
    source="yahoo_finance",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "market": ["ohlcv", "options_chain", "streaming_quotes"],
        "reference": ["ticker_info", "balance_sheet", "income_statement", "cash_flow"],
    },
)

_ECB = SourceCapability(
    source="ecb",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=False,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "market": ["yield_curve"],
        "reference": ["exchange_rates", "interest_rates", "monetary_aggregates"],
    },
)

_OPENBB = SourceCapability(
    source="openbb",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=False,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "market": ["bond_data", "yield_curves", "fixed_income"],
        "reference": ["bond_indices", "government_bonds"],
    },
)

_OFR = SourceCapability(
    source="ofr",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=False,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "market": ["cds_spreads", "repo_rates"],
        "reference": ["financial_stability_data"],
    },
)

_REGULATORY = SourceCapability(
    source="regulatory",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=False,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["trade_reports"],
        "reference": ["regulatory_filings", "compliance_data"],
    },
)


# ---------------------------------------------------------------------------
# Ordered list -- TradFi
# ---------------------------------------------------------------------------

TRADFI_CAPABILITIES: list[SourceCapability] = [
    _IBKR,
    _DATABENTO,
    _FRED,
    _POLYGON,
    _BARCHART,
    _YAHOO_FINANCE,
    _ECB,
    _OPENBB,
    _OFR,
    _REGULATORY,
]
