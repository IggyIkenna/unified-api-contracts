"""Sports, prediction markets, and sports reference data capability declarations."""

from __future__ import annotations

from datetime import date

from ..capability import OperationDetail, OperationEnvDetail, SourceCapability

# ---------------------------------------------------------------------------
# Sports / prediction markets (13)
# ---------------------------------------------------------------------------

_BETFAIR = SourceCapability(
    source="betfair",
    domains=["market", "execution", "reference"],
    crosscutting=["errors", "rate_limits", "latency"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key", "cert"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["list_market_catalogue", "list_market_book", "list_runner_book", "streaming"],
        "execution": ["place_orders", "cancel_orders", "replace_orders", "list_current_orders"],
        "reference": ["list_event_types", "list_competitions", "list_events", "list_countries", "list_venues"],
    },
    base_urls={"mainnet": "https://api.betfair.com/exchange"},
    operation_details={
        "place_orders": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="api_key_header",
                    required_credential="cert",
                    notes="Requires X-Application header + client SSL cert",
                ),
            }
        ),
        "list_market_book": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
            }
        ),
    },
    chain=None,
    kind="sports_book",
)

_PINNACLE = SourceCapability(
    source="pinnacle",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=False,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["odds", "fixtures", "settled_fixtures", "line"],
        "reference": ["sports", "leagues", "periods"],
    },
    base_urls={"mainnet": "https://api.pinnacle.com"},
    operation_details={
        "odds": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="api_key_header", required_credential="api_key"),
            }
        ),
    },
    chain=None,
    kind="sports_book",
)

_KALSHI = SourceCapability(
    source="kalshi",
    domains=["market", "execution", "position", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=True,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"test": "demo_key", "prod": "prod_key"},
    operations={
        "market": ["markets", "market_orderbook", "trades", "series", "ws_orderbook"],
        "execution": ["create_order", "cancel_order", "batch_create_orders"],
        "position": ["portfolio", "positions", "fills", "settlements"],
        "reference": ["events", "series", "categories"],
    },
    base_urls={"mainnet": "https://trading-api.kalshi.com", "testnet": "https://demo-api.kalshi.co"},
    operation_details={
        "create_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="rsa_pkcs1v15_sha256", required_credential="rsa_private_key"
                ),
                "testnet": OperationEnvDetail(
                    signing_scheme="rsa_pkcs1v15_sha256",
                    required_credential="rsa_private_key",
                    data_fidelity="synthetic",
                ),
            }
        ),
        "markets": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
                "testnet": OperationEnvDetail(
                    signing_scheme="none", required_credential="none", data_fidelity="synthetic"
                ),
            }
        ),
    },
    chain=None,
    kind=None,
    coverage_start={"candles": date(2021, 7, 30)},
)

_POLYMARKET = SourceCapability(
    source="polymarket",
    domains=["market", "execution", "position", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["markets", "orderbook", "prices", "trades", "ws_prices"],
        "execution": ["create_order", "cancel_order", "open_orders"],
        "position": ["positions", "balances", "pnl"],
        "reference": ["events", "markets_metadata", "tags"],
    },
    base_urls={"mainnet": "https://clob.polymarket.com"},
    operation_details={
        "create_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(
                    signing_scheme="eip712",
                    required_credential="wallet_private_key",
                    notes="L1 auth: wallet private key → EIP-712 → CLOB credentials; L2 auth: HMAC per request",
                ),
            }
        ),
        "cancel_order": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="eip712", required_credential="wallet_private_key"),
            }
        ),
        "markets": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="none", required_credential="none"),
            }
        ),
    },
    chain="polygon",
    kind="prediction_dex",
    coverage_start={"candles": date(2020, 9, 1)},
)

_ODDS_API = SourceCapability(
    source="odds_api",
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
        "market": ["odds", "scores", "historical_odds"],
        "reference": ["sports", "participants"],
    },
    base_urls={"mainnet": "https://api.the-odds-api.com"},
    operation_details={},
    chain=None,
    kind=None,
)

_ODDS_ENGINE = SourceCapability(
    source="odds_engine",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=False,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["markets", "odds_lines"],
        "reference": ["sports", "leagues"],
    },
    base_urls={"mainnet": "https://api.oddsengine.com"},
    operation_details={},
    chain=None,
    kind=None,
)

_OPTICODDS = SourceCapability(
    source="opticodds",
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
        "market": ["odds", "fixtures", "player_props"],
        "reference": ["sports", "leagues", "books"],
    },
    base_urls={"mainnet": "https://api.opticodds.com"},
    operation_details={},
    chain=None,
    kind=None,
)

_MATCHBOOK = SourceCapability(
    source="matchbook",
    domains=["market", "execution", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=False,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["events", "markets", "runners", "prices"],
        "execution": ["offer", "cancel_offer", "current_offers"],
        "reference": ["sports", "events_list"],
    },
    base_urls={"mainnet": "https://api.matchbook.com"},
    operation_details={
        "offer": OperationDetail(
            environments={
                "mainnet": OperationEnvDetail(signing_scheme="session_auth", required_credential="username_password"),
            }
        ),
    },
    chain=None,
    kind="sports_book",
)

_ONEXBET = SourceCapability(
    source="onexbet",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=False,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "market": ["prematch_odds", "live_odds"],
        "reference": ["sports", "tournaments"],
    },
    base_urls={"mainnet": "https://1xbet.com/api"},
    operation_details={},
    chain=None,
    kind="sports_book",
)

_METABET = SourceCapability(
    source="metabet",
    domains=["market", "reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=True,
    supports_batch=True,
    supports_historical=False,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["api_key"],
    auth_environments={"prod": "prod_key"},
    operations={
        "market": ["markets", "instruments"],
        "reference": ["sports", "markets_list"],
    },
    base_urls={"mainnet": "https://api.metabet.io"},
    operation_details={},
    chain=None,
    kind="sports_book",
)

# ---------------------------------------------------------------------------
# Sports reference data (5)
# ---------------------------------------------------------------------------

_API_FOOTBALL = SourceCapability(
    source="api_football",
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
        "market": ["fixtures", "odds", "predictions"],
        "reference": ["leagues", "teams", "players", "venues", "standings"],
    },
    base_urls={"mainnet": "https://v3.football.api-sports.io"},
    operation_details={},
    chain=None,
    kind=None,
)

_FOOTYSTATS = SourceCapability(
    source="footystats",
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
        "market": ["matches", "odds"],
        "reference": ["leagues", "teams", "players", "standings"],
    },
    base_urls={"mainnet": "https://api.football-data-api.com"},
    operation_details={},
    chain=None,
    kind=None,
)

_SOCCER_FOOTBALL_INFO = SourceCapability(
    source="soccer_football_info",
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
        "reference": ["fixtures", "teams", "leagues", "players", "referees", "venues"],
    },
    base_urls={"mainnet": "https://api.soccer-football.info"},
    operation_details={},
    chain=None,
    kind=None,
)

_TRANSFERMARKT = SourceCapability(
    source="transfermarkt",
    domains=["reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=False,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "reference": ["players", "teams", "transfers", "market_values"],
    },
    base_urls={"mainnet": "https://www.transfermarkt.com"},
    operation_details={},
    chain=None,
    kind=None,
)

_UNDERSTAT = SourceCapability(
    source="understat",
    domains=["reference"],
    crosscutting=["errors", "rate_limits"],
    supports_live=False,
    supports_batch=True,
    supports_historical=True,
    supports_testnet=False,
    supports_mainnet=True,
    auth_scope=["none"],
    auth_environments={},
    operations={
        "reference": ["fixtures", "teams", "leagues", "players", "xg_stats"],
    },
    base_urls={"mainnet": "https://understat.com"},
    operation_details={},
    chain=None,
    kind=None,
)

# ---------------------------------------------------------------------------
# Ordered list -- Sports
# ---------------------------------------------------------------------------

SPORTS_CAPABILITIES: list[SourceCapability] = [
    # Sports / prediction markets
    _BETFAIR,
    _PINNACLE,
    _KALSHI,
    _POLYMARKET,
    _ODDS_API,
    _ODDS_ENGINE,
    _OPTICODDS,
    _MATCHBOOK,
    _ONEXBET,
    _METABET,
    # Sports reference data
    _API_FOOTBALL,
    _FOOTYSTATS,
    _SOCCER_FOOTBALL_INFO,
    _TRANSFERMARKT,
    _UNDERSTAT,
]
