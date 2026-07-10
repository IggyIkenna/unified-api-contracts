"""Exchange session times — stateless utility for trading hour detection.

Provides ``is_trading_hours()`` and ``get_session_times()`` for features
services to distinguish expected gaps (market closed) from anomalies (data
outage during trading hours).

Uses ``zoneinfo`` (stdlib) for DST-correct timezone conversions.
No ``exchange_calendars`` dependency — session windows are hardcoded for
the exchanges we trade. Holiday calendars are not handled here; features
services should use instruments-service ``is_trading_day`` field for that.

Usage::

    from unified_api_contracts.registry.session_times import (
        is_trading_hours,
        get_session_times,
    )

    if is_trading_hours("CME", some_datetime):
        ...
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

# --- Session definitions ---

_CT = ZoneInfo("America/Chicago")
_ET = ZoneInfo("America/New_York")
_UTC = ZoneInfo("UTC")


@dataclass(frozen=True)
class SessionWindow:
    """A trading session window for an exchange.

    For exchanges that trade across midnight (e.g. CME electronic),
    ``open_time`` > ``close_time`` means the session wraps midnight.
    ``open_weekday`` is the ISO weekday (1=Mon, 7=Sun) of the session open.
    """

    timezone: ZoneInfo
    open_time: time
    close_time: time
    open_weekday: int  # ISO weekday of session open (1=Mon..7=Sun)
    close_weekday: int  # ISO weekday of session close
    is_24_7: bool = False


# CME Globex: Sunday 5pm CT - Friday 4pm CT (with daily break 4pm-5pm CT)
_CME_SESSION = SessionWindow(
    timezone=_CT,
    open_time=time(17, 0),
    close_time=time(16, 0),
    open_weekday=7,  # Sunday
    close_weekday=5,  # Friday
)

# NYSE / NASDAQ: 9:30am - 4pm ET, Monday - Friday
_NYSE_SESSION = SessionWindow(
    timezone=_ET,
    open_time=time(9, 30),
    close_time=time(16, 0),
    open_weekday=1,
    close_weekday=5,
)

# CBOE: 8:30am - 3:15pm CT for options (SPX)
_CBOE_SESSION = SessionWindow(
    timezone=_CT,
    open_time=time(8, 30),
    close_time=time(15, 15),
    open_weekday=1,
    close_weekday=5,
)

# ICE: Same as NYSE for US contracts
_ICE_SESSION = _NYSE_SESSION

# Crypto / DeFi: 24/7
_CRYPTO_SESSION = SessionWindow(
    timezone=_UTC,
    open_time=time(0, 0),
    close_time=time(23, 59, 59),
    open_weekday=1,
    close_weekday=7,
    is_24_7=True,
)


# Exchange → session mapping
_EXCHANGE_SESSIONS: dict[str, SessionWindow] = {
    "CME": _CME_SESSION,
    "ICE": _ICE_SESSION,
    "NYSE": _NYSE_SESSION,
    "NASDAQ": _NYSE_SESSION,
    "CBOE": _CBOE_SESSION,
    "FX": _CME_SESSION,  # FX trades on CME Globex hours
    # CeFi exchanges are 24/7
    "BINANCE-SPOT": _CRYPTO_SESSION,
    "BINANCE-FUTURES": _CRYPTO_SESSION,
    "BYBIT": _CRYPTO_SESSION,
    "OKX": _CRYPTO_SESSION,
    "DERIBIT": _CRYPTO_SESSION,
    "COINBASE-SPOT": _CRYPTO_SESSION,
    "HYPERLIQUID": _CRYPTO_SESSION,
    "ASTER": _CRYPTO_SESSION,
    # DeFi — all 24/7
    "AAVE_V3-ETHEREUM": _CRYPTO_SESSION,
    "UNISWAP_V2-ETHEREUM": _CRYPTO_SESSION,
    "UNISWAP_V3-ETHEREUM": _CRYPTO_SESSION,
    "UNISWAP_V4-ETHEREUM": _CRYPTO_SESSION,
    "CURVE-ETHEREUM": _CRYPTO_SESSION,
    "BALANCER-ETHEREUM": _CRYPTO_SESSION,
    "MORPHO-ETHEREUM": _CRYPTO_SESSION,
    # Sports / Prediction — event-driven, always "available"
    "ODDS_API": _CRYPTO_SESSION,
    "POLYMARKET": _CRYPTO_SESSION,
    "KALSHI": _CRYPTO_SESSION,
}


@dataclass(frozen=True)
class SessionTimes:
    """Session open/close times in UTC for a given date."""

    exchange: str
    date: str
    open_utc: datetime
    close_utc: datetime
    is_24_7: bool
    timezone_name: str


def get_session_times(exchange: str, target_date: datetime) -> SessionTimes:
    """Get trading session open/close times in UTC for a given date.

    Args:
        exchange: Canonical exchange/venue name (e.g., "CME", "NYSE").
        target_date: The date to get session times for.

    Returns:
        SessionTimes with UTC open/close datetimes.

    Raises:
        ValueError: If exchange is not recognized.
    """
    session = _EXCHANGE_SESSIONS.get(exchange.upper())
    if session is None:
        # Default: treat unknown as 24/7 crypto
        session = _CRYPTO_SESSION

    if session.is_24_7:
        day_start = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
        if day_start.tzinfo is None:
            day_start = day_start.replace(tzinfo=_UTC)
        return SessionTimes(
            exchange=exchange,
            date=target_date.strftime("%Y-%m-%d"),
            open_utc=day_start,
            close_utc=day_start + timedelta(hours=24),
            is_24_7=True,
            timezone_name="UTC",
        )

    # Localize to exchange timezone
    local_dt = (
        target_date.astimezone(session.timezone) if target_date.tzinfo else target_date.replace(tzinfo=session.timezone)
    )
    local_date = local_dt.date()

    open_local = datetime.combine(local_date, session.open_time, tzinfo=session.timezone)
    close_local = datetime.combine(local_date, session.close_time, tzinfo=session.timezone)

    # For sessions that wrap midnight (CME: open 17:00 > close 16:00),
    # the open is previous day
    if session.open_time > session.close_time:
        open_local = open_local - timedelta(days=1)

    return SessionTimes(
        exchange=exchange,
        date=local_date.isoformat(),
        open_utc=open_local.astimezone(_UTC),
        close_utc=close_local.astimezone(_UTC),
        is_24_7=False,
        timezone_name=str(session.timezone),
    )


def is_trading_hours(exchange: str, dt: datetime) -> bool:
    """Check if the given datetime falls within trading hours for an exchange.

    Args:
        exchange: Canonical exchange/venue name.
        dt: Datetime to check (timezone-aware; naive treated as UTC).

    Returns:
        True if the exchange is open at the given time.
    """
    session = _EXCHANGE_SESSIONS.get(exchange.upper())
    if session is None or session.is_24_7:
        return True

    # Convert to exchange local time
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_UTC)
    local_dt = dt.astimezone(session.timezone)

    # Check weekday (ISO: 1=Mon..7=Sun)
    iso_weekday = local_dt.isoweekday()

    # For CME-style sessions (Sun 17:00 - Fri 16:00):
    if session.open_time > session.close_time:
        # Session wraps midnight. Two windows:
        # 1. open_time → midnight (e.g., 17:00-23:59)
        # 2. midnight → close_time (e.g., 00:00-16:00)
        local_time = local_dt.time()

        # Weekend check: closed Sat all day, Sun before open_time
        if iso_weekday == 6:  # Saturday
            return False
        if iso_weekday == 7 and local_time < session.open_time:  # Sunday before open
            return False
        if iso_weekday == 5 and local_time >= session.close_time:  # Friday after close
            return False

        # During the week: open except during daily maintenance (close->open same day)
        return not (session.close_time <= local_time < session.open_time)

    # Standard session (NYSE: 9:30-16:00, same day)
    if iso_weekday > 5:  # Weekend
        return False
    local_time = local_dt.time()
    return session.open_time <= local_time < session.close_time
