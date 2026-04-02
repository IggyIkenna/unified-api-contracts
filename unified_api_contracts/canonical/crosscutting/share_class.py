"""Share class types — base currency denomination for client portfolios."""

from __future__ import annotations

from enum import StrEnum


class ShareClass(StrEnum):
    """Base currency denomination for a client portfolio / strategy instance."""

    USDT = "USDT"
    ETH = "ETH"
    BTC = "BTC"


SHARE_CLASS_BASE_ASSETS: dict[str, list[str]] = {
    "USDT": ["USDT", "USDC", "DAI"],
    "ETH": ["ETH", "WETH"],
    "BTC": ["BTC", "WBTC", "CBBTC"],
}
