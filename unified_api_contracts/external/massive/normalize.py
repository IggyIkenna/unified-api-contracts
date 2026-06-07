"""Massive raw reference data → canonical :class:`InstrumentRecord` normalisers.

This is the single canonicalisation surface for Massive instrument definitions.
The output :class:`InstrumentRecord` is field-for-field equivalent to the records
the Databento path produces (same ``instrument_key`` shape
``{venue}:{TYPE}:{raw_symbol}``, same canonical venue names, same
``instrument_type`` / ``asset_class`` / lifecycle fields) so downstream
consumers (the ``by_date`` writer, the lifecycle catalogue roll-up, the v2
expected-universe enumerator, MTDS) see an identical canonical schema regardless
of which vendor produced it.

Session metadata (trading hours / holidays / early closes) is intentionally
*not* set here — it is date-dependent and enriched service-side by
instruments-service (which owns ``exchange_calendars``), exactly as the Databento
path does.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal, InvalidOperation

from ...internal import AssetClass, InstrumentRecord, InstrumentType, OptionType
from .schemas import (
    MassiveFuturesContract,
    MassiveFuturesProduct,
    MassiveOptionContract,
    MassiveTicker,
)

#: Equity / ETF MIC (ISO-10383 ``primary_exchange``) → canonical venue.
#: NASDAQ family vs NYSE family (NYSE / Arca / American / CBOE-operated equity
#: books). The curated TradFi equity universe (S&P 500 + ETFs) lists only on
#: these two canonical venues, so the default is NYSE (Arca lists most ETFs).
MASSIVE_EQUITY_MIC_TO_VENUE: dict[str, str] = {
    "XNAS": "NASDAQ",
    "XNGS": "NASDAQ",
    "XNMS": "NASDAQ",
    "XNCM": "NASDAQ",
    "XNYS": "NYSE",
    "ARCX": "NYSE",
    "XASE": "NYSE",
    "XCIS": "NYSE",
    "BATS": "NYSE",
    "BATY": "NYSE",
    "BATO": "NYSE",
    "EDGX": "NYSE",
    "EDGA": "NYSE",
    "IEXG": "NYSE",
}

#: Futures MIC (``trading_venue``) → canonical venue.
MASSIVE_FUTURES_MIC_TO_VENUE: dict[str, str] = {
    "XCME": "CME",
    "XCBT": "CME",
    "XNYM": "CME",
    "XCEC": "CME",
    "GLBX": "CME",
    "IFUS": "ICE",
    "IFEU": "ICE",
    "IFLL": "ICE",
    "IFLX": "ICE",
    "NDEX": "ICE",
}

#: Massive futures ``asset_sub_class`` → canonical :class:`AssetClass`.
_FUTURES_SUBCLASS_TO_ASSET_CLASS: dict[str, AssetClass] = {
    "equity": AssetClass.EQUITY,
    "energy": AssetClass.COMMODITY,
    "metal": AssetClass.COMMODITY,
    "metals": AssetClass.COMMODITY,
    "agriculture": AssetClass.COMMODITY,
    "agricultural": AssetClass.COMMODITY,
    "commodity": AssetClass.COMMODITY,
    "fx": AssetClass.FX,
    "currency": AssetClass.FX,
    "interest_rate": AssetClass.FIXED_INCOME,
    "interest rate": AssetClass.FIXED_INCOME,
    "rates": AssetClass.FIXED_INCOME,
    "fixed_income": AssetClass.FIXED_INCOME,
    "crypto": AssetClass.CRYPTO,
    "cryptocurrency": AssetClass.CRYPTO,
}

#: Massive equity ``type`` codes that denote a fund/ETF rather than a common
#: stock. Everything else maps to ``EQUITY``.
_ETF_TYPE_CODES: frozenset[str] = frozenset({"ETF", "ETV", "ETN", "ETS", "FUND"})


def venue_for_equity_mic(mic: str | None) -> str:
    """Resolve the canonical equity venue for a Massive ``primary_exchange`` MIC."""
    if not mic:
        return "NYSE"
    return MASSIVE_EQUITY_MIC_TO_VENUE.get(mic.upper(), "NYSE")


def venue_for_futures_mic(mic: str | None) -> str:
    """Resolve the canonical futures venue for a Massive ``trading_venue`` MIC."""
    if not mic:
        return "CME"
    return MASSIVE_FUTURES_MIC_TO_VENUE.get(mic.upper(), "CME")


def _parse_iso_date(value: str | None) -> datetime | None:
    """Parse a ``YYYY-MM-DD`` (or ISO) date string to a UTC midnight datetime."""
    if not value:
        return None
    try:
        d = date.fromisoformat(value[:10])
    except ValueError:
        return None
    return datetime(d.year, d.month, d.day, tzinfo=UTC)


def _to_decimal(value: float | int | None) -> Decimal | None:
    """Convert a numeric value to ``Decimal`` (via str to avoid float artefacts)."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None


def normalize_massive_equity(raw: MassiveTicker) -> InstrumentRecord | None:
    """Normalise a Massive stocks-market ticker → canonical equity/ETF record.

    Returns ``None`` (honest skip — never a placeholder) when the row carries no
    ticker.
    """
    ticker = (raw.ticker or "").strip()
    if not ticker:
        return None
    venue = venue_for_equity_mic(raw.primary_exchange)
    itype = InstrumentType.ETF if (raw.type or "").upper() in _ETF_TYPE_CODES else InstrumentType.EQUITY
    return InstrumentRecord(
        instrument_key=f"{venue}:{itype.value}:{ticker}",
        venue=venue,
        raw_symbol=ticker,
        instrument_type=itype,
        asset_class=AssetClass.EQUITY,
        base_asset=ticker,
        quote_asset="USD",
        tick_size=Decimal("0.01"),
        min_size=Decimal("1"),
        contract_size=Decimal("1"),
        underlying=raw.name or ticker,
    )


def normalize_massive_index(raw: MassiveTicker, venue: str = "CBOE") -> InstrumentRecord | None:
    """Normalise a Massive indices-market ticker → canonical index record.

    Index tickers carry an ``I:`` prefix (``I:VIX``); the canonical ``raw_symbol``
    strips it. ``venue`` defaults to CBOE (where the curated index universe lists).
    """
    ticker = (raw.ticker or "").strip()
    if not ticker:
        return None
    symbol = ticker.removeprefix("I:")
    return InstrumentRecord(
        instrument_key=f"{venue}:{InstrumentType.INDEX.value}:{symbol}",
        venue=venue,
        raw_symbol=ticker,
        instrument_type=InstrumentType.INDEX,
        asset_class=AssetClass.EQUITY,
        base_asset=symbol,
        quote_asset="USD",
        tick_size=Decimal("0.01"),
        min_size=Decimal("1"),
        contract_size=Decimal("1"),
        underlying=raw.name or symbol,
    )


def normalize_massive_fx(raw: MassiveTicker) -> InstrumentRecord | None:
    """Normalise a Massive fx-market ticker (``C:KRWUSD``) → canonical FX record.

    The canonical FX record matches the Databento static FX shape: venue ``FX``,
    ``instrument_key=FX:SPOT_PAIR:{base}-{quote}``.
    """
    base = (raw.base_currency_symbol or "").strip().upper()
    quote = (raw.currency_symbol or "").strip().upper()
    if not base or not quote:
        return None
    pair = f"{base}-{quote}"
    return InstrumentRecord(
        instrument_key=f"FX:{InstrumentType.SPOT_PAIR.value}:{pair}",
        venue="FX",
        raw_symbol=raw.ticker or pair,
        instrument_type=InstrumentType.SPOT_PAIR,
        asset_class=AssetClass.FX,
        base_asset=base,
        quote_asset=quote,
        tick_size=Decimal("0.0001"),
        min_size=Decimal("1"),
        contract_size=Decimal("1"),
        timezone="UTC",
        holiday_calendar="FX",
    )


def normalize_massive_option(raw: MassiveOptionContract, venue: str | None = None) -> InstrumentRecord | None:
    """Normalise a Massive option contract → canonical option record.

    ``venue`` pins the canonical venue (e.g. ``"CBOE"`` for cash-index options
    like SPX/VIX whose OPRA ``primary_exchange`` MIC — XCBO/GMNI — does not map
    cleanly to an equity venue). When omitted, the venue is derived from the
    option's ``primary_exchange`` MIC (equity/ETF options).

    Returns ``None`` when ticker or expiry is missing (honest skip).
    """
    ticker = (raw.ticker or "").strip()
    expiry = _parse_iso_date(raw.expiration_date)
    if not ticker or expiry is None:
        return None
    underlying = (raw.underlying_ticker or "").strip()
    venue = venue or venue_for_equity_mic(raw.primary_exchange)
    opt_type = {"call": OptionType.CALL, "put": OptionType.PUT}.get((raw.contract_type or "").lower())
    return InstrumentRecord(
        instrument_key=f"{venue}:{InstrumentType.OPTION.value}:{ticker}",
        venue=venue,
        raw_symbol=ticker,
        instrument_type=InstrumentType.OPTION,
        asset_class=AssetClass.EQUITY,
        base_asset=underlying or ticker,
        quote_asset="USD",
        tick_size=Decimal("0.01"),
        min_size=Decimal("1"),
        contract_size=_to_decimal(raw.shares_per_contract) or Decimal("100"),
        expiry=expiry,
        strike=_to_decimal(raw.strike_price),
        option_type=opt_type,
        underlying=underlying or None,
    )


def normalize_massive_futures(
    raw: MassiveFuturesContract,
    product: MassiveFuturesProduct | None = None,
) -> InstrumentRecord | None:
    """Normalise a Massive futures contract → canonical future record.

    ``first_trade_date`` → ``available_from_datetime``; ``last_trade_date`` →
    ``expiry``; ``trading_venue`` MIC → canonical venue (CME/ICE);
    ``product.unit_of_measure_qty`` → ``contract_size``;
    ``product.asset_sub_class`` → ``asset_class``.
    """
    ticker = (raw.ticker or "").strip()
    if not ticker:
        return None
    # InstrumentRecord requires a non-null expiry for FUTURE (contract-roll
    # sharding). A contract with no last_trade_date is unusable → honest skip,
    # never an invalid/placeholder record.
    expiry = _parse_iso_date(raw.last_trade_date)
    if expiry is None:
        return None
    venue = venue_for_futures_mic(raw.trading_venue)
    root = (raw.product_code or raw.group_code or "").strip()
    sub_class = (product.asset_sub_class if product else None) or ""
    asset_class = _FUTURES_SUBCLASS_TO_ASSET_CLASS.get(sub_class.lower(), AssetClass.COMMODITY)
    quote = (product.trade_currency_code if product else None) or "USD"
    contract_size = _to_decimal(product.unit_of_measure_qty) if product else None
    return InstrumentRecord(
        instrument_key=f"{venue}:{InstrumentType.FUTURE.value}:{ticker}",
        venue=venue,
        raw_symbol=ticker,
        instrument_type=InstrumentType.FUTURE,
        asset_class=asset_class,
        base_asset=root or ticker,
        quote_asset=quote,
        tick_size=Decimal("0.01"),
        min_size=Decimal("1"),
        contract_size=contract_size or Decimal("1"),
        expiry=expiry,
        underlying=root or None,
        available_from_datetime=_parse_iso_date(raw.first_trade_date),
    )
