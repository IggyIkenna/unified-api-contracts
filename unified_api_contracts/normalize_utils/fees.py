"""Fee normalizers: raw venue fee schemas → CanonicalFee.

Pure field-mapping functions — no business logic.
One function per venue / fee kind.
"""

from __future__ import annotations

from decimal import Decimal

from ..canonical.domain import CanonicalFee, FeeType
from ..external.binance.account_schemas import BinanceFeeRate
from ..external.bitget.schemas import BitgetFeeDetail
from ..external.bybit.schemas import BybitFeeRate
from ..external.ccxt.schemas import CcxtFee
from ..external.okx.schemas import OKXFeeRate
from ..external.upbit.schemas import UpbitFeeRate

# ---------------------------------------------------------------------------
# Binance
# ---------------------------------------------------------------------------


def normalize_binance_fee_rate(
    raw: BinanceFeeRate,
    fee_type: FeeType = FeeType.MAKER,
    venue: str = "binance",
) -> CanonicalFee:
    """Normalize a BinanceFeeRate to CanonicalFee.

    BinanceFeeRate fields (all strings):
        symbol          — trading pair (e.g. "BTCUSDT")
        makerCommission — maker rate (e.g. "0.001")
        takerCommission — taker rate (e.g. "0.001")

    Pass fee_type=FeeType.MAKER to get the maker rate or
    fee_type=FeeType.TAKER to get the taker rate.
    """
    amount = Decimal(raw.takerCommission) if fee_type is FeeType.TAKER else Decimal(raw.makerCommission)

    return CanonicalFee(
        amount=amount,
        currency=raw.symbol,  # symbol is the trading pair; no separate currency field
        asset=raw.symbol,
        fee_type=fee_type,
        venue=venue,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# CCXT
# ---------------------------------------------------------------------------


def normalize_ccxt_fee(
    raw: CcxtFee,
    venue: str = "ccxt",
    fee_type: FeeType = FeeType.OTHER,
) -> CanonicalFee:
    """Normalize a CcxtFee to CanonicalFee.

    CcxtFee fields:
        cost     — fee amount (float | None)
        currency — fee currency (str | None)

    CcxtFee has no type/rate fields; caller may pass fee_type explicitly.
    """
    amount = Decimal(str(raw.cost)) if raw.cost is not None else Decimal("0")
    currency = raw.currency if raw.currency is not None else ""

    return CanonicalFee(
        amount=amount,
        currency=currency,
        asset=None,
        fee_type=fee_type,
        venue=venue,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# Bybit
# ---------------------------------------------------------------------------


def normalize_bybit_fee_rate(
    raw: BybitFeeRate,
    fee_type: FeeType = FeeType.MAKER,
    venue: str = "bybit",
) -> CanonicalFee:
    """Normalize a BybitFeeRate to CanonicalFee.

    BybitFeeRate fields (all str | None):
        makerFeeRate     — maker fee rate (e.g. "0.0001")
        takerFeeRate     — taker fee rate (e.g. "0.0006")
        baseFeeRate      — base fee rate before discount
        discountFeeRate  — effective discount fee rate
        symbol           — symbol (optional)
        baseCoin         — base coin (optional)

    Pass fee_type=FeeType.TAKER to get the taker rate.
    Falls back to Decimal("0") when the field is None.
    """
    raw_rate = raw.takerFeeRate if fee_type is FeeType.TAKER else raw.makerFeeRate

    amount = Decimal(raw_rate) if raw_rate is not None else Decimal("0")
    currency = raw.baseCoin if raw.baseCoin is not None else (raw.symbol if raw.symbol is not None else "")

    return CanonicalFee(
        amount=amount,
        currency=currency,
        asset=raw.symbol,
        fee_type=fee_type,
        venue=venue,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# OKX
# ---------------------------------------------------------------------------


def normalize_okx_fee_rate(
    raw: OKXFeeRate,
    fee_type: FeeType = FeeType.MAKER,
    venue: str = "okx",
) -> CanonicalFee:
    """Normalize an OKXFeeRate to CanonicalFee.

    OKXFeeRate fields (all str | None):
        maker    — maker fee rate (e.g. "-0.0001", negative = rebate)
        taker    — taker fee rate (e.g. "0.0005")
        tier     — volume tier
        category — instrument category

    Falls back to Decimal("0") when the field is None.
    """
    raw_rate = raw.taker if fee_type is FeeType.TAKER else raw.maker

    amount = Decimal(raw_rate) if raw_rate is not None else Decimal("0")

    return CanonicalFee(
        amount=amount,
        currency="",  # OKXFeeRate has no currency field; caller must enrich if needed
        asset=None,
        fee_type=fee_type,
        venue=venue,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# Deribit
# ---------------------------------------------------------------------------


def normalize_deribit_fee(
    fee: Decimal,
    currency: str,
    fee_type: FeeType = FeeType.TAKER,
    venue: str = "deribit",
) -> CanonicalFee:
    """Normalize a Deribit fill fee to CanonicalFee.

    Deribit embeds fee as a plain float in fill/trade responses.
    The caller must convert it to Decimal before passing.

    Args:
        fee:      Fee amount from the fill (already Decimal).
        currency: Settlement currency of the instrument (e.g. "BTC", "ETH").
        fee_type: Typically FeeType.TAKER for fills; override if known.
        venue:    Venue identifier (default "deribit").
    """
    return CanonicalFee(
        amount=fee,
        currency=currency,
        asset=None,
        fee_type=fee_type,
        venue=venue,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# Hyperliquid
# ---------------------------------------------------------------------------


def normalize_hyperliquid_fee(
    fee: Decimal,
    fee_token: str,
    venue: str = "hyperliquid",
) -> CanonicalFee:
    """Normalize a Hyperliquid fill fee to CanonicalFee.

    Hyperliquid fills expose `fee` (amount) and `feeToken` (currency).
    Fee type is always TAKER for Hyperliquid fills.

    Args:
        fee:       Fee amount from the fill (Decimal).
        fee_token: Token used to pay the fee (e.g. "USDC").
        venue:     Venue identifier (default "hyperliquid").
    """
    return CanonicalFee(
        amount=fee,
        currency=fee_token,
        asset=None,
        fee_type=FeeType.TAKER,
        venue=venue,
        timestamp=None,
    )


# ---------------------------------------------------------------------------
# Coinbase
# ---------------------------------------------------------------------------


def normalize_coinbase_fee(
    fee: Decimal,
    currency: str = "USD",
    venue: str = "coinbase",
) -> CanonicalFee:
    """Normalize a Coinbase fill fee to CanonicalFee.

    Coinbase Advanced Trade fills expose a `fee` field (amount).
    Fee type defaults to TAKER; override via the domain layer if maker detection
    is available from the fill's `liquidity_indicator` field.

    Args:
        fee:      Fee amount from the fill (Decimal).
        currency: Fee currency (default "USD").
        venue:    Venue identifier (default "coinbase").
    """
    return CanonicalFee(
        amount=fee,
        currency=currency,
        asset=None,
        fee_type=FeeType.TAKER,
        venue=venue,
        timestamp=None,
    )


def normalize_bitget_fee(
    raw: BitgetFeeDetail,
    fee_type: FeeType = FeeType.TAKER,
    venue: str = "bitget",
) -> CanonicalFee:
    """Normalize a BitgetFeeDetail to CanonicalFee."""
    amount = Decimal(raw.totalDeductionFee) if raw.totalDeductionFee is not None else Decimal("0")
    return CanonicalFee(
        amount=amount,
        currency=raw.feeCoin or "",
        asset=None,
        fee_type=fee_type,
        venue=venue,
        timestamp=None,
    )


def normalize_upbit_fee_rate(
    raw: UpbitFeeRate,
    fee_type: FeeType = FeeType.TAKER,
    venue: str = "upbit",
) -> CanonicalFee:
    """Normalize an UpbitFeeRate to CanonicalFee.

    Upbit applies a flat 0.25% fee for both maker and taker.
    """
    raw_rate = raw.taker_fee_rate if fee_type is FeeType.TAKER else raw.maker_fee_rate
    amount = Decimal(str(raw_rate)) if raw_rate is not None else Decimal("0")
    return CanonicalFee(
        amount=amount,
        currency=raw.currency or "",
        asset=raw.market,
        fee_type=fee_type,
        venue=venue,
        timestamp=None,
    )


__all__ = [
    "normalize_binance_fee_rate",
    "normalize_bitget_fee",
    "normalize_bybit_fee_rate",
    "normalize_ccxt_fee",
    "normalize_coinbase_fee",
    "normalize_deribit_fee",
    "normalize_hyperliquid_fee",
    "normalize_okx_fee_rate",
    "normalize_upbit_fee_rate",
]
