"""Replay VCR cassette for Alchemy JSON-RPC — verifies schema shape without live network.

Cassette recorded with Authorization header filtered. Auth not required for replay.
"""

from __future__ import annotations

from pathlib import Path

import httpx
from vcr import VCR

CASSETTE_DIR = (
    Path(__file__).parent.parent.parent
    / "unified_api_contracts"
    / "unified_api_contracts_external"
    / "alchemy"
    / "mocks"
)

_SUBSCRIBE_BODY = (
    b'{"jsonrpc":"2.0","id":1,"method":"eth_subscribe",'
    b'"params":["logs",{"address":"0x1f9840a85d5aF5bf1D1762F925BDADdC4201F984"}]}'
)


def test_alchemy_ws_subscription_cassette() -> None:
    """Replay VCR cassette for Alchemy eth_subscribe POST."""
    cassette_path = CASSETTE_DIR / "alchemy_ws_eth_subscription.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.post(
            "https://eth-mainnet.g.alchemy.com/v2/demo",
            content=_SUBSCRIBE_BODY,
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data is not None


def test_alchemy_ws_subscription_structure() -> None:
    """Alchemy subscription response has jsonrpc method and params."""
    cassette_path = CASSETTE_DIR / "alchemy_ws_eth_subscription.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.post(
            "https://eth-mainnet.g.alchemy.com/v2/demo",
            content=_SUBSCRIBE_BODY,
            headers={"Content-Type": "application/json"},
        )
        data = response.json()
        assert data.get("method") == "eth_subscription"
        assert "params" in data
        assert "subscription" in data["params"]
        assert "result" in data["params"]


def test_alchemy_ws_log_schema() -> None:
    """Alchemy subscription result validates against AlchemyWsLog schema."""
    from unified_api_contracts.unified_api_contracts_external.alchemy.schemas import AlchemyWsLog

    cassette_path = CASSETTE_DIR / "alchemy_ws_eth_subscription.yaml"
    assert cassette_path.exists(), f"Cassette not found: {cassette_path}"

    with VCR().use_cassette(str(cassette_path)):
        response = httpx.post(
            "https://eth-mainnet.g.alchemy.com/v2/demo",
            content=_SUBSCRIBE_BODY,
            headers={"Content-Type": "application/json"},
        )
        data = response.json()
        result = data["params"]["result"]
        log = AlchemyWsLog.model_validate(result)
        assert log.address is not None
        assert log.transactionHash is not None
        assert log.topics is not None and len(log.topics) > 0
