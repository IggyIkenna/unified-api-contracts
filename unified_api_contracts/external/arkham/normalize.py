"""Arkham Intelligence normalizers — all normalize_arkham_* functions.

Extracted from normalize_utils/onchain.py and normalize_utils/errors/_normalize_b.py.

Covers entity labeling and on-chain token flows: entity_flow, net_flow, and alert events.
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
    ArkhamAlertEvent,
    ArkhamNetFlow,
    ArkhamTokenFlow,
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
# Arkham Intelligence — entity labeling and token flows
# ---------------------------------------------------------------------------


def normalize_arkham_token_flow(
    raw: ArkhamTokenFlow,
    venue: str = "arkham",
) -> CanonicalOnChainMetric | None:
    """Normalize ArkhamTokenFlow (on-chain transaction) to CanonicalOnChainMetric.

    metric_type = "entity_flow"
    value = usd_value of the transfer
    entity = from_entity -> to_entity direction label
    """
    if raw.usd_value is None and raw.amount is None:
        return None
    ts = _unix_to_utc(raw.timestamp)
    entity_label = f"{raw.from_entity or 'unknown'}->{raw.to_entity or 'unknown'}"
    raw_dict: dict[str, float | int | str | None] = {
        "tx_hash": raw.tx_hash,
        "from_entity": raw.from_entity,
        "to_entity": raw.to_entity,
        "amount": raw.amount,
        "usd_value": raw.usd_value,
    }
    return CanonicalOnChainMetric(
        timestamp=ts,
        venue=venue,
        metric_type="entity_flow",
        asset=raw.token_symbol,
        chain=raw.chain,
        value=_d(raw.usd_value),
        secondary_value=_d(raw.amount),
        entity=entity_label,
        raw=raw_dict,
    )


def normalize_arkham_net_flow(
    raw: ArkhamNetFlow,
    venue: str = "arkham",
) -> CanonicalOnChainMetric | None:
    """Normalize ArkhamNetFlow to CanonicalOnChainMetric.

    metric_type = "net_flow"
    value = net_flow_usd (negative = net outflow = bullish)
    secondary_value = inflow_usd
    """
    if raw.net_flow_usd is None:
        return None
    raw_dict: dict[str, float | int | str | None] = {
        "inflow_usd": raw.inflow_usd,
        "outflow_usd": raw.outflow_usd,
        "net_flow_usd": raw.net_flow_usd,
        "time_window": raw.time_window,
    }
    return CanonicalOnChainMetric(
        timestamp=datetime.now(UTC),
        venue=venue,
        metric_type="net_flow",
        asset=raw.token_symbol,
        chain=raw.chain,
        value=_d(raw.net_flow_usd),
        secondary_value=_d(raw.inflow_usd),
        entity=raw.entity,
        raw=raw_dict,
    )


def normalize_arkham_alert_event(
    raw: ArkhamAlertEvent,
    venue: str = "arkham",
) -> CanonicalOnChainMetric | None:
    """Normalize ArkhamAlertEvent (large transfer / whale activity) to CanonicalOnChainMetric.

    metric_type = alert_type (e.g. "large_transfer", "new_whale_accumulation")
    value = usd_value
    entity = from_entity -> to_entity
    """
    if raw.usd_value is None:
        return None
    ts = _unix_to_utc(raw.timestamp)
    entity_label = f"{raw.from_entity or 'unknown'}->{raw.to_entity or 'unknown'}"
    alert_type = raw.alert_type or "alert"
    raw_dict: dict[str, float | int | str | None] = {
        "alert_id": raw.alert_id,
        "alert_type": raw.alert_type,
        "usd_value": raw.usd_value,
        "from_entity": raw.from_entity,
        "to_entity": raw.to_entity,
    }
    return CanonicalOnChainMetric(
        timestamp=ts,
        venue=venue,
        metric_type=alert_type,
        asset=raw.token_symbol,
        chain=raw.chain,
        value=_d(raw.usd_value),
        entity=entity_label,
        raw=raw_dict,
    )


# ---------------------------------------------------------------------------
# Error normalizer
# ---------------------------------------------------------------------------


def normalize_arkham_error(
    error_code: str | int,
    message: str = "",
    venue: str = "arkham",
) -> CanonicalError:
    """Map an Arkham API error to a CanonicalError subclass."""
    code = str(error_code)
    try:
        return from_http_status(int(code), message, venue)
    except ValueError:
        return CanonicalError(code=code, message=message, action=ErrorAction.FAIL, venue=venue)


__all__ = [
    "normalize_arkham_alert_event",
    "normalize_arkham_error",
    "normalize_arkham_net_flow",
    "normalize_arkham_token_flow",
]
