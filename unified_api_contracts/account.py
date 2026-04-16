"""Domain facade — unified trading account identity.

Consumer repos import from here:
    from unified_api_contracts.account import TradingAccount, AccountRegistry, ...
"""

from unified_api_contracts.internal.domain.account import (
    AccountRegistry,
    AccountType,
    TradingAccount,
)

__all__ = [
    "AccountRegistry",
    "AccountType",
    "TradingAccount",
]
