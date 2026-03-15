"""Glassnode normalizers — all normalize_glassnode_* functions.

Extracted from normalize_utils/onchain.py and normalize_utils/errors/_normalize_b.py.

Covers on-chain analytics: MVRV, SOPR, NVT, HODL waves, exchange reserves,
realized cap, thermocap, and generic timeseries points.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation

from ...canonical.crosscutting.errors import (
    CanonicalError,
    ErrorAction,
)
from ...canonical.domain import CanonicalOnChainMetric
from ...normalize_utils.errors._utils import from_http_status
from .schemas import (
    ExchangeReserves,
    GlassnodeTimeseriesPoint,
    HodlWave,
    MvrvRatio,
    MvrvZScore,
    NvtRatio,
    NvtSignal,
    RealizedCap,
    SoprMetric,
    ThermoCap,
)

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _d(val: float | int | str | Decimal | None) -> Decimal | None:
    """Convert numeric-ish value to Decimal; return None on failure."""
    if val is None:
        return None
    if isinstance(val, Decimal):
        return val
    try:
        return Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _unix_to_utc(ts: int | None) -> datetime:
    """Convert unix timestamp (seconds) to aware UTC datetime."""
    if ts is None:
        return datetime.now(UTC)
    try:
        return datetime.fromtimestamp(int(ts), tz=UTC)
    except (ValueError, OSError, OverflowError):
        return datetime.now(UTC)


# ---------------------------------------------------------------------------
# Glassnode — on-chain analytics
# ---------------------------------------------------------------------------


def normalize_glassnode_timeseries_point(
    raw: GlassnodeTimeseriesPoint,
    metric_type: str,
    asset: str = "BTC",
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize a GlassnodeTimeseriesPoint to CanonicalOnChainMetric.

    GlassnodeTimeseriesPoint: {t: unix_seconds, v: float}.
    Skips points where v is None.

    Args:
        raw:         GlassnodeTimeseriesPoint from a metric response.
        metric_type: Metric name e.g. "mvrv", "sopr", "nvt".
        asset:       Asset symbol (e.g. "BTC", "ETH").
        venue:       Provider tag, defaults to "glassnode".
    """
    if raw.v is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.t),
        venue=venue,
        metric_type=metric_type,
        asset=asset,
        value=_d(raw.v),
        raw={"t": raw.t, "v": raw.v},
    )


def normalize_glassnode_mvrv(
    raw: MvrvRatio,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize a MvrvRatio to CanonicalOnChainMetric (metric_type="mvrv")."""
    if raw.mvrv is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="mvrv",
        asset="BTC",
        value=_d(raw.mvrv),
        raw={"mvrv": raw.mvrv},
    )


def normalize_glassnode_mvrv_z_score(
    raw: MvrvZScore,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize a MvrvZScore to CanonicalOnChainMetric (metric_type="mvrv_z_score")."""
    if raw.mvrv_z_score is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="mvrv_z_score",
        asset="BTC",
        value=_d(raw.mvrv_z_score),
        raw={"mvrv_z_score": raw.mvrv_z_score},
    )


def normalize_glassnode_sopr(
    raw: SoprMetric,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize a SoprMetric to CanonicalOnChainMetric (metric_type="sopr")."""
    if raw.sopr is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="sopr",
        asset="BTC",
        value=_d(raw.sopr),
        raw={"sopr": raw.sopr},
    )


def normalize_glassnode_nvt(
    raw: NvtRatio,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize a NvtRatio to CanonicalOnChainMetric (metric_type="nvt")."""
    if raw.nvt is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="nvt",
        asset="BTC",
        value=_d(raw.nvt),
        raw={"nvt": raw.nvt},
    )


def normalize_glassnode_nvt_signal(
    raw: NvtSignal,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize a NvtSignal to CanonicalOnChainMetric (metric_type="nvt_signal")."""
    if raw.nvt_signal is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="nvt_signal",
        asset="BTC",
        value=_d(raw.nvt_signal),
        raw={"nvt_signal": raw.nvt_signal},
    )


def normalize_glassnode_exchange_reserves(
    raw: ExchangeReserves,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize ExchangeReserves to CanonicalOnChainMetric (metric_type="exchange_reserves").

    value = balance_sum, secondary_value = net_flow_24h.
    """
    if raw.balance_sum is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="exchange_reserves",
        asset=raw.asset or "BTC",
        value=_d(raw.balance_sum),
        secondary_value=_d(raw.net_flow_24h),
        raw={"balance_sum": raw.balance_sum, "net_flow_24h": raw.net_flow_24h},
    )


def normalize_glassnode_realized_cap(
    raw: RealizedCap,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize RealizedCap to CanonicalOnChainMetric (metric_type="realized_cap")."""
    if raw.realized_cap_usd is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="realized_cap",
        asset="BTC",
        value=_d(raw.realized_cap_usd),
        raw={"realized_cap_usd": raw.realized_cap_usd},
    )


def normalize_glassnode_thermocap(
    raw: ThermoCap,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize ThermoCap to CanonicalOnChainMetric (metric_type="thermocap")."""
    if raw.thermocap_usd is None:
        return None
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="thermocap",
        asset="BTC",
        value=_d(raw.thermocap_usd),
        raw={"thermocap_usd": raw.thermocap_usd},
    )


def normalize_glassnode_hodl_wave(
    raw: HodlWave,
    venue: str = "glassnode",
) -> CanonicalOnChainMetric | None:
    """Normalize HodlWave to CanonicalOnChainMetric (metric_type="hodl_wave").

    value = 1d band (most short-term); secondary_value = 10y+ band (most long-term).
    Full band data stored in raw dict.
    """
    if raw.timestamp is None:
        return None
    raw_dict: dict[str, float | int | str | None] = {
        "band_1d": raw.band_1d,
        "band_1d_1w": raw.band_1d_1w,
        "band_1w_1m": raw.band_1w_1m,
        "band_1m_3m": raw.band_1m_3m,
        "band_3m_6m": raw.band_3m_6m,
        "band_6m_12m": raw.band_6m_12m,
        "band_1y_2y": raw.band_1y_2y,
        "band_2y_3y": raw.band_2y_3y,
        "band_3y_5y": raw.band_3y_5y,
        "band_5y_7y": raw.band_5y_7y,
        "band_7y_10y": raw.band_7y_10y,
        "band_10y_plus": raw.band_10y_plus,
    }
    return CanonicalOnChainMetric(
        timestamp=_unix_to_utc(raw.timestamp),
        venue=venue,
        metric_type="hodl_wave",
        asset="BTC",
        value=_d(raw.band_1d),
        secondary_value=_d(raw.band_10y_plus),
        raw=raw_dict,
    )


# ---------------------------------------------------------------------------
# Error normalizer
# ---------------------------------------------------------------------------


def normalize_glassnode_error(
    error_code: str | int,
    message: str = "",
    venue: str = "glassnode",
) -> CanonicalError:
    """Map a Glassnode HTTP error code to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_glassnode_error",
    "normalize_glassnode_exchange_reserves",
    "normalize_glassnode_hodl_wave",
    "normalize_glassnode_mvrv",
    "normalize_glassnode_mvrv_z_score",
    "normalize_glassnode_nvt",
    "normalize_glassnode_nvt_signal",
    "normalize_glassnode_realized_cap",
    "normalize_glassnode_sopr",
    "normalize_glassnode_thermocap",
    "normalize_glassnode_timeseries_point",
]
