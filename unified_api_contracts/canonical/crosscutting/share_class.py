"""Share class types — base currency denomination for client portfolios.

Operator-ruled 2026-07-29 (pnl_interest_accrual_wrong_engine_and_banned_formula_2026_07_21.md, "converge to one
enum"): this was previously a narrower 3-value duplicate of
``unified_api_contracts.internal.architecture_v2.enums.ShareClass`` (9 values) — two structurally-different
``ShareClass`` classes sharing one name, zero interop, a live wrong-import risk. THIS module is now the SSOT (the
canonical/crosscutting layer other internal types already build on, e.g. ``archetype_config.py``/``cost_capacity.py``
import canonical crosscutting types — the natural dependency direction, canonical -> internal, not the reverse);
``internal.architecture_v2.enums.ShareClass`` re-exports this exact class object (see that module) rather than
defining its own, so every existing import site (``unified_api_contracts.internal.ShareClass``,
``unified_api_contracts.internal.architecture_v2.ShareClass``, the top-level ``unified_api_contracts.ShareClass``)
keeps working unchanged, now all pointing at the SAME 9-value class.
"""

from __future__ import annotations

from enum import StrEnum


class ShareClass(StrEnum):
    """Base currency denomination for a client portfolio / strategy instance.

    9 values (expanded 2026-07-30 from the prior 3-value USDT/ETH/BTC-only set, per the enum-convergence ruling
    above) — stablecoins (USDT/USDC/FDUSD), fiat (USD/GBP/EUR), and native-asset share classes (ETH/BTC/SOL).
    """

    USDT = "USDT"
    USDC = "USDC"
    FDUSD = "FDUSD"
    USD = "USD"
    GBP = "GBP"
    EUR = "EUR"
    ETH = "ETH"
    BTC = "BTC"
    SOL = "SOL"


SHARE_CLASS_BASE_ASSETS: dict[str, list[str]] = {
    "USDT": ["USDT", "USDC", "DAI"],
    "USDC": ["USDC", "USDT", "DAI"],
    "FDUSD": ["FDUSD", "USDT", "USDC"],
    "USD": ["USD"],
    "GBP": ["GBP"],
    "EUR": ["EUR"],
    "ETH": ["ETH", "WETH"],
    "BTC": ["BTC", "WBTC", "CBBTC"],
    "SOL": ["SOL", "WSOL"],
}
