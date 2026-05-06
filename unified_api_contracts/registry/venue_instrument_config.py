"""Per-exchange instrument-type / quote-currency / symbol-format SSOT.

Extracted from ``venue_mapping.py`` 2026-05-06 to keep that module under the
900-line QG ceiling as venue coverage grows. ``ExchangeInstrumentConfig`` is
the single source of truth for:

  * Which instrument types each exchange supports (``exchange_instrument_types``)
  * The valid quote currencies per exchange (``valid_quote_currencies``)
  * Which exchanges are derivatives venues (``derivative_exchanges``)
  * Per-exchange exclusion rules (``excluded_base_currencies`` /
    ``excluded_symbol_patterns``)
  * Symbol-format quirks (``symbol_format`` — Upbit's QUOTE-BASE vs the
    BASE-QUOTE default).

Re-exported from ``unified_api_contracts.registry`` and the top-level
``unified_api_contracts`` package so existing consumers (UTL, MTDS) need no
import changes.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class ExchangeInstrumentConfig:
    """Valid instrument types and quote currencies per exchange (CORRECTED canonical venues)"""

    exchange_instrument_types: dict[str, list[str]] = field(
        default_factory=lambda: {
            # CeFi - Tardis exchanges
            "BINANCE-SPOT": ["SPOT_PAIR"],  # Spot only
            "BINANCE-FUTURES": ["PERPETUAL", "FUTURE"],  # Derivatives only
            "DERIBIT": ["PERPETUAL", "FUTURE", "OPTION"],  # Full derivatives exchange
            "BYBIT": ["SPOT_PAIR", "PERPETUAL"],  # Combined
            "OKX": ["SPOT_PAIR", "PERPETUAL", "FUTURE"],  # Combined
            "UPBIT": ["SPOT_PAIR"],  # Spot only (Korean exchange for kimchi premium)
            "COINBASE": ["SPOT_PAIR"],  # Spot only (for coinbase premium)
            # CeFi - On-chain CLOBs
            "HYPERLIQUID": ["PERPETUAL"],
            "ASTER": ["PERPETUAL"],
            "PACIFICA-SOLANA": ["PERPETUAL"],
            "EXTENDED-STARKNET": ["PERPETUAL"],
            "LIGHTER-ZKSYNC": ["PERPETUAL"],
            # DeFi - DEX protocols (canonical PROTOCOL-CHAIN format)
            "UNISWAPV2-ETHEREUM": ["POOL"],
            "UNISWAPV3-ETHEREUM": ["POOL"],
            "UNISWAPV4-ETHEREUM": ["POOL"],
            "CURVE-ETHEREUM": ["POOL"],
            "BALANCER-ETHEREUM": ["POOL"],
            # DeFi - Lending protocols
            "AAVEV3-ETHEREUM": ["A_TOKEN", "DEBT_TOKEN"],
            "MORPHO-ETHEREUM": ["A_TOKEN", "DEBT_TOKEN"],
            "FLUID-ETHEREUM": ["A_TOKEN", "DEBT_TOKEN"],
            # DeFi - LST/Yield protocols
            "LIDO-ETHEREUM": ["LST"],
            "ETHERFI-ETHEREUM": ["LST"],
            "ETHENA-ETHEREUM": ["YIELD_BEARING"],
        }
    )

    valid_quote_currencies: dict[str, list[str]] = field(
        default_factory=lambda: {
            "BINANCE-SPOT": ["USDT"],  # STRICT: Only USDT
            "BINANCE-FUTURES": ["USDT"],  # STRICT: Only USDT
            "DERIBIT": ["USD", "USDC"],  # Options exchange
            "BYBIT": ["USDT"],  # STRICT: Only USDT
            "OKX": ["USDT"],  # STRICT: Only USDT
            "UPBIT": ["KRW"],  # Korean Won (for kimchi premium calculations)
            "COINBASE": ["USD"],  # US Dollar (for coinbase premium calculations)
        }
    )

    derivative_exchanges: list[str] = field(
        default_factory=lambda: [
            "DERIBIT",
            "BINANCE-FUTURES",
            "OKX",
            "BYBIT",
        ]
    )

    # Excluded base currencies per exchange (e.g., deprecated tokens, leveraged products)
    excluded_base_currencies: dict[str, list[str]] = field(
        default_factory=lambda: {
            "OKX": ["USTC"],  # USTC (Terra Classic) deprecated
            "BYBIT": [],  # No base currency exclusions
        }
    )

    # Excluded symbol patterns per exchange (e.g., leveraged products)
    excluded_symbol_patterns: dict[str, list[str]] = field(
        default_factory=lambda: {
            "BYBIT": [
                "3L",  # 3x leveraged LONG products
                "2L",  # 2x leveraged LONG products
                "3S",  # 3x leveraged SHORT products
                "2S",  # 2x leveraged SHORT products
            ],
            "OKX": [],  # No symbol pattern exclusions
        }
    )

    # Symbol format per exchange
    # Most exchanges use BASE-QUOTE (e.g., BTC-USD, SOL-USDT)
    # Some exchanges like Upbit use QUOTE-BASE (e.g., KRW-BTC, KRW-SOL)
    symbol_format: dict[str, str] = field(
        default_factory=lambda: {
            "UPBIT": "QUOTE-BASE",  # Upbit uses KRW-SOL format (quote first)
            # All other exchanges use BASE-QUOTE by default
        }
    )

    def get_symbol_format(self, venue: str) -> str:
        """Get symbol format for a venue. Returns 'BASE-QUOTE' if not specified."""
        return self.symbol_format.get(venue, "BASE-QUOTE")


__all__ = ["ExchangeInstrumentConfig"]
