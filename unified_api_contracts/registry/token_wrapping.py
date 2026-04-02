"""Token wrapping rules — ETH/WETH, eETH/weETH, stETH/wstETH mappings.

Covers both WRAP (entry) and UNWRAP (exit) directions. Also provides
LST→base-asset price resolution for share class delta and P&L calculations.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class TokenWrappingRule:
    """A single token wrapping rule (unwrapped <-> wrapped)."""

    unwrapped: str
    wrapped: str
    wrapper_contract: str
    chain: str
    is_rebasing: bool
    auto_wrap_supported: bool
    balance_tracking_form: str  # "wrapped" or "unwrapped" — which form positions are tracked in


TOKEN_WRAPPING_RULES: list[TokenWrappingRule] = [
    TokenWrappingRule("ETH", "WETH", "0xC02aaA39b223FE8D0A0e5C4F27eAD9083C756Cc2", "ETHEREUM", False, True, "wrapped"),
    TokenWrappingRule(
        "eETH", "weETH", "0xCd5fE23C85820F7B72D0926FC9b05b43E359b7ee", "ETHEREUM", True, False, "wrapped"
    ),
    TokenWrappingRule(
        "stETH", "wstETH", "0x7f39C581F595B53c5cb19bD0b3f8dA6c935E2Ca0", "ETHEREUM", True, False, "wrapped"
    ),
]

# Lookup: wrapped -> unwrapped (for exit/unwrap flows)
_UNWRAP_MAP: dict[str, str] = {r.wrapped: r.unwrapped for r in TOKEN_WRAPPING_RULES}
# Lookup: unwrapped -> wrapped
_WRAP_MAP: dict[str, str] = {r.unwrapped: r.wrapped for r in TOKEN_WRAPPING_RULES}

# LST tokens that trade at a premium over their base asset due to staking yield
# Key = wrapped LST, value = base asset whose price is the "par" reference
LST_BASE_ASSET: dict[str, str] = {
    "weETH": "ETH",
    "wstETH": "ETH",
    "mSOL": "SOL",
}

PROTOCOL_TOKEN_PREFERENCE: dict[str, dict[str, str]] = {
    "AAVEV3": {
        "ETH": "WETH",
        "eETH": "weETH",
        "stETH": "wstETH",
        "WETH": "WETH",
        "weETH": "weETH",
        "wstETH": "wstETH",
        "USDT": "USDT",
        "USDC": "USDC",
        "DAI": "DAI",
        "WBTC": "WBTC",
    },
    "MORPHO": {
        "ETH": "WETH",
        "eETH": "weETH",
        "stETH": "wstETH",
        "WETH": "WETH",
        "weETH": "weETH",
        "wstETH": "wstETH",
    },
    "ETHERFI": {"ETH": "ETH", "WETH": "WETH"},
    "LIDO": {"ETH": "ETH"},
    "UNISWAPV3": {"ETH": "WETH"},
    "HYPERLIQUID": {"USDC": "USDC"},
}


def get_protocol_token(token: str, protocol: str) -> str:
    """Get the preferred token form for a given protocol."""
    prefs = PROTOCOL_TOKEN_PREFERENCE.get(protocol, {})
    return prefs.get(token, token)


def needs_wrapping(token: str, target_protocol: str) -> tuple[bool, str | None]:
    """Check if a token needs wrapping for a target protocol.

    Returns (needs_wrap, target_token) tuple.
    """
    preferred = get_protocol_token(token, target_protocol)
    if preferred != token:
        return True, preferred
    return False, None


def needs_unwrapping(wrapped_token: str) -> tuple[bool, str | None]:
    """Check if a wrapped token can be unwrapped.

    Returns (needs_unwrap, unwrapped_token) tuple.
    Used in exit flows (e.g. Aave withdrawal returns weETH, may need eETH).
    """
    unwrapped = _UNWRAP_MAP.get(wrapped_token)
    if unwrapped is not None:
        return True, unwrapped
    return False, None


def get_wrapped_form(token: str) -> str:
    """Get the wrapped form of a token, or the token itself if no wrapping rule exists."""
    return _WRAP_MAP.get(token, token)


def get_unwrapped_form(token: str) -> str:
    """Get the unwrapped form of a token, or the token itself if no unwrap rule exists."""
    return _UNWRAP_MAP.get(token, token)


def is_lst(token: str) -> bool:
    """Check if token is a liquid staking token that trades at a premium over its base."""
    return token in LST_BASE_ASSET


def get_lst_base_asset(token: str) -> str | None:
    """Get the base asset for an LST (e.g. weETH -> ETH, wstETH -> ETH).

    Returns None if token is not an LST.
    """
    return LST_BASE_ASSET.get(token)


def lst_adjusted_value(
    quantity: Decimal,
    lst_price_usd: Decimal,
    base_asset_price_usd: Decimal,
    token: str,
) -> tuple[Decimal, Decimal]:
    """Compute the USD value and base-asset-equivalent quantity for an LST position.

    For LSTs (weETH, wstETH), the staking ratio = lst_price / base_price.
    10 weETH at $3165/weETH and $3000/ETH = $31,650 USD = 10.55 ETH-equivalent.

    Returns:
        (usd_value, base_asset_equivalent_quantity)
    """
    usd_value = quantity * lst_price_usd
    if not is_lst(token) or base_asset_price_usd <= 0:
        return usd_value, quantity
    base_equivalent = usd_value / base_asset_price_usd
    return usd_value, base_equivalent


def get_balance_tracking_form(token: str) -> str:
    """Get which form (wrapped or unwrapped) positions should be tracked in.

    Returns "wrapped" or "unwrapped". Defaults to the token itself if no rule exists.
    """
    for rule in TOKEN_WRAPPING_RULES:
        if token in (rule.wrapped, rule.unwrapped):
            return rule.balance_tracking_form
    return "wrapped"
