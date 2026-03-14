"""Arkham Intelligence entity labeling and on-chain flow analytics.

Auth: arkham-api-key header.
Provides entity identification (exchange, whale, fund) for blockchain addresses.
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from enum import StrEnum

from pydantic import BaseModel

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction


class ArkhamEntityType(StrEnum):
    """Entity type classification."""

    EXCHANGE = "exchange"
    CEX = "cex"
    DEX = "dex"
    WHALE = "whale"
    FUND = "fund"
    PROTOCOL = "protocol"
    BRIDGE = "bridge"
    MINER = "miner"
    TREASURY = "treasury"
    UNKNOWN = "unknown"


class ArkhamEntity(BaseModel):
    """GET /intelligence/addresses/{address}."""

    address: str | None = None
    chain: str | None = None
    arkham_entity: str | None = None
    arkham_label: str | None = None
    entity_type: ArkhamEntityType | None = None
    is_contract: bool | None = None
    token_balances: list[dict[str, str]] | None = None


class ArkhamTokenFlow(BaseModel):
    """GET /intelligence/transactions."""

    tx_hash: str | None = None
    block_number: int | None = None
    timestamp: int | None = None
    chain: str | None = None
    from_address: str | None = None
    from_entity: str | None = None
    from_entity_type: ArkhamEntityType | None = None
    to_address: str | None = None
    to_entity: str | None = None
    to_entity_type: ArkhamEntityType | None = None
    token_symbol: str | None = None
    token_address: str | None = None
    amount: float | None = None
    usd_value: float | None = None


class ArkhamNetFlow(BaseModel):
    """GET /intelligence/addresses/{address}/flows.

    Negative net_flow_usd = net outflow = bullish (coins leaving exchanges).
    """

    entity: str | None = None
    chain: str | None = None
    token_symbol: str | None = None
    time_window: str | None = None  # 1h/4h/24h/7d
    inflow_usd: float | None = None
    outflow_usd: float | None = None
    net_flow_usd: float | None = None
    tx_count_in: int | None = None
    tx_count_out: int | None = None


class ArkhamAlertEvent(BaseModel):
    """Alert event: large_transfer, new_whale_accumulation, etc."""

    alert_id: str | None = None
    timestamp: int | None = None
    chain: str | None = None
    token_symbol: str | None = None
    usd_value: float | None = None
    from_entity: str | None = None
    to_entity: str | None = None
    is_exchange_inflow: bool | None = None
    is_exchange_outflow: bool | None = None
    alert_type: str | None = None


class ArkhamError(BaseModel):
    """Arkham API error."""

    message: str | None = None
    status_code: int | None = None

    @classmethod
    def classify(cls, status_code: int | None) -> ErrorAction:
        """429->RETRY, 401/403->FAIL."""
        if status_code == 429:
            return ErrorAction.RETRY
        if status_code in (401, 403):
            return ErrorAction.FAIL
        return ErrorAction.FAIL
