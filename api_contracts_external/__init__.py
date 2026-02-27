"""Top-level alias for api_contracts.api_contracts_external.

Import raw venue schemas directly:
    from api_contracts_external.databento import DatabentoOhlcvBar
    from api_contracts_external.binance.schemas import BinanceOrderBook
    from api_contracts_external import *

All schemas live in api_contracts.api_contracts_external; this package is a
backward-forward shim so consumers can use the shorter top-level path.
"""

import contextlib
import importlib
import sys

_VENUES = [
    "alchemy",
    "api_football",
    "arkham",
    "aster",
    "barchart",
    "betdaq",
    "ecb",
    "betfair",
    "binance",
    "bloxroute",
    "bybit",
    "ccxt",
    "chainlink",
    "cloud_sdks",
    "coinbase",
    "databento",
    "defi",
    "defillama",
    "deribit",
    "fred",
    "fear_greed",
    "footystats",
    "github",
    "glassnode",
    "hyperliquid",
    "ibkr",
    "kalshi",
    "manifold",
    "matchbook",
    "mev",
    "odds_api",
    "ofr",
    "okx",
    "open_meteo",
    "openbb",
    "pinnacle",
    "polymarket",
    "predictit",
    "pyth",
    "smarkets",
    "soccer_football_info",
    "tardis",
    "thegraph",
    "transfermarkt",
    "understat",
    "upbit",
    "yahoo_finance",
]

_SUBMODULES = ["schemas", "request", "response", "errors", "mocks", "data_schemas"]

# Pre-register all venue submodules in sys.modules so submodule imports work.
for _v in _VENUES:
    _src_prefix = f"api_contracts.api_contracts_external.{_v}"
    _dst_prefix = f"api_contracts_external.{_v}"
    try:
        _mod = importlib.import_module(_src_prefix)
        sys.modules[_dst_prefix] = _mod
        for _sub in _SUBMODULES:
            with contextlib.suppress(ImportError):
                sys.modules[f"{_dst_prefix}.{_sub}"] = importlib.import_module(f"{_src_prefix}.{_sub}")
    except ImportError:
        pass

# Replace this module with the real one so attribute access works naturally.
sys.modules["api_contracts_external"] = importlib.import_module("api_contracts.api_contracts_external")
