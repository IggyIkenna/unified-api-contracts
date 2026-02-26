"""Per-venue HTTP endpoint config for VCR recording and replay.

Each entry: url, method, optional headers builder key (env var name), response_path to extract
body for schema validation (e.g. '' = whole JSON, 'data.0' = first data element), schema class name.
Used by scripts/record_vcr_cassettes.py and tests/test_vcr_replay.py.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict


class VCREndpoint(TypedDict):
    """Single request to record/replay and validate."""

    url: str
    method: str
    cassette_name: str
    response_path: str
    schema_class: str
    key_env: str
    header_name: str
    json_body: NotRequired[dict]


def _get(
    url: str,
    cassette: str,
    response_path: str,
    schema_class: str,
    key_env: str = "",
    header_name: str = "Authorization",
) -> VCREndpoint:
    return {
        "url": url,
        "method": "GET",
        "cassette_name": cassette,
        "response_path": response_path,
        "schema_class": schema_class,
        "key_env": key_env,
        "header_name": header_name,
    }


def _post(
    url: str,
    cassette: str,
    response_path: str,
    schema_class: str,
    json_body: dict[str, object] | None = None,
    key_env: str = "",
    header_name: str = "Authorization",
) -> VCREndpoint:
    out: VCREndpoint = {
        "url": url,
        "method": "POST",
        "cassette_name": cassette,
        "response_path": response_path,
        "schema_class": schema_class,
        "key_env": key_env,
        "header_name": header_name,
    }
    if json_body is not None:
        out["json_body"] = json_body
    return out


# Public or optional-auth endpoints only. Key-required venues: set key_env so recorder adds header when env set.
VCR_ENDPOINTS: dict[str, list[VCREndpoint]] = {
    "binance": [
        _get(
            "https://fapi.binance.com/fapi/v1/ticker/24hr?symbol=BTCUSDT",
            "ticker_24hr.yaml",
            "",
            "BinanceTicker",
        ),
    ],
    "okx": [
        _get(
            "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT-SWAP",
            "ticker.yaml",
            "data.0",
            "OKXTicker",
        ),
    ],
    "bybit": [
        _get(
            "https://api.bybit.com/v5/market/tickers?category=linear&symbol=BTCUSDT",
            "ticker.yaml",
            "result.list.0",
            "BybitTicker",
        ),
    ],
    "upbit": [
        _get(
            "https://api.upbit.com/v1/ticker?markets=KRW-BTC",
            "ticker.yaml",
            "0",
            "UpbitTicker",
        ),
    ],
    "hyperliquid": [
        _post(
            "https://api.hyperliquid.xyz/info",
            "meta.yaml",
            "",
            "HyperliquidMeta",
            json_body={"type": "meta"},
        ),
    ],
    "yahoo_finance": [],  # Chart endpoint rate-limits; use examples/ for schema validation
    "databento": [],  # No public endpoint; use DATABENTO_API_KEY + timeseries/symbology when recording
    "tardis": [
        _get(
            "https://api.tardis.dev/v1/exchanges",
            "exchanges.yaml",
            "0",
            "TardisExchange",
            key_env="TARDIS_API_KEY",
            header_name="Authorization",
        ),
    ],
    "thegraph": [],
    "alchemy": [],
    "ccxt": [],
    "aster": [],
    "ibkr": [],
}
