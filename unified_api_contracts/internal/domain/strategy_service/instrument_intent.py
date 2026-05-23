"""Strategy instrument intent — strategy declares what it needs, instruments-service resolves."""

from pydantic import BaseModel


class StrategyInstrumentIntent(BaseModel):
    """What a strategy needs — NOT specific instrument IDs.

    Strategy says: "I need ETH lending on AAVE, Ethereum chain"
    instruments-service resolves to: AAVE_V3-ETHEREUM:A_TOKEN:AETH@ETHEREUM
    """

    protocol: str  # e.g. "AAVE_V3", "UNISWAP_V3", "HYPERLIQUID"
    chain: str  # e.g. "ETHEREUM", "ARBITRUM"
    base_currencies: list[str]  # e.g. ["USDC", "USDT", "ETH"]
    instrument_types: list[str] = []  # e.g. ["A_TOKEN", "PERPETUAL", "SPOT"]
    venue_filter: list[str] = []  # e.g. ["AAVE_V3-ETHEREUM"] — empty = all matching


class ResolvedInstruments(BaseModel):
    """Result of resolving a StrategyInstrumentIntent."""

    intent: StrategyInstrumentIntent
    instrument_ids: list[str]  # resolved canonical instrument IDs
    date: str  # date for which instruments were resolved
    missing_currencies: list[str] = []  # currencies with no matching instruments
