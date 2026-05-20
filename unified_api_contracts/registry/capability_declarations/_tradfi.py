"""TradFi (traditional finance) capability declarations."""

from __future__ import annotations

from ..capability import OperationDetail, OperationEnvDetail, SourceCapability

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
    base_urls={"mainnet": "localhost:4001", "testnet": "localhost:4002"},
    margin_model={"mainnet": "portfolio", "testnet": "portfolio"},
    operation_details={
        "place_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="ib_gateway",
                    required_credential="session_token",
                    notes="TWS/Gateway connection; port 4001 live, 4002 paper",
                ),
                "testnet": OperationEnvDetail(
                    signing_scheme="ib_gateway",
                    required_credential="session_token",
                    data_fidelity="production",
                    notes="Paper trading uses real market data with simulated execution",
                ),
            }
        ),
        "market_data": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="ib_gateway", required_credential="session_token"),
                "testnet": OperationEnvDetail(
                    signing_scheme="ib_gateway", required_credential="session_token", data_fidelity="production"
                ),
            }
        ),
    },
    chain=None,
    kind=None,
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
    base_urls={"mainnet": "https://hist.databento.com"},
    operation_details={
        "mbp_1": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
            }
        ),
    },
    chain=None,
    kind=None,
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
    base_urls={"mainnet": "https://api.stlouisfed.org"},
    operation_details={
        "observations": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
            }
        ),
    },
    chain=None,
    kind=None,
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
    base_urls={"mainnet": "https://api.polygon.io"},
    operation_details={
        "aggregates": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
            }
        ),
    },
    chain=None,
    kind=None,
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
    base_urls={"mainnet": "https://ondemand.websol.barchart.com"},
    operation_details={
        "ohlcv": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
            }
        ),
    },
    chain=None,
    kind=None,
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
    base_urls={"mainnet": "https://query1.finance.yahoo.com"},
    operation_details={
        "ohlcv": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
            }
        ),
    },
    chain=None,
    kind=None,
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
    base_urls={"mainnet": "https://data-api.ecb.europa.eu"},
    operation_details={},
    chain=None,
    kind=None,
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
    base_urls={},
    operation_details={},
    chain=None,
    kind=None,
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
    base_urls={"mainnet": "https://data.financialresearch.gov"},
    operation_details={},
    chain=None,
    kind=None,
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
]
