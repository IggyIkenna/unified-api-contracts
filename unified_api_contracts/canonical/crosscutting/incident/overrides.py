"""Immediate-SEV0 overrides — closed-set 7-trigger predicates.

Pre-evaluated by the alerting-service Incident Gateway BEFORE severity-hint
routing. Any override = True forces SEV0 routing (PagerDuty + Twilio voice +
physical pager) regardless of severity_hint or recovery_confirmed.

Codified per `disaster_recovery.md` §7.5 + operator HARD RULE 2026-05-23.
Codex SSOT: ``codex/04-architecture/incident-gateway-state-machine.md``.
"""

from __future__ import annotations

from enum import StrEnum


class ImmediateSev0Override(StrEnum):
    """Closed set of 7 predicates that force SEV0 regardless of severity_hint.

    These map to the 7 wake-up-immediately conditions from the target
    operating model:

    - **UNKNOWN_NET_EXPOSURE**: venue total ≠ internal total + no
      transfer/funding/fill row explains the delta.
    - **OPEN_ORDERS_UNCONFIRMABLE**: venue REST is returning 5xx + internal
      records N open orders for the venue. We don't know if they're live.
    - **KILL_SWITCH_CANNOT_CONFIRM_CANCEL**: kill_switch.activate ran but
      cancel-all-orders for the venue returned a partial-success or unknown
      result. Some orders may still be live.
    - **VENUE_INTERNAL_BALANCE_MISMATCH**: abs(venue_total - internal_total)
      exceeds a USD threshold (default $1000; per-asset configurable).
    - **POSITION_EXISTS_EXTERNALLY_UNKNOWN_INTERNALLY**: venue REST reports a
      non-zero position for an instrument our internal ledger has no record of.
    - **MATERIAL_BALANCE_MOVEMENT_UNEXPLAINED**: balance moved > USD threshold
      between consecutive snapshots and no transfer/fill/funding row in our
      ledger explains it.
    - **MARGIN_COLLATERAL_SAFETY_UNCERTAIN**: venue API cannot confirm margin
      state for an active perp position OR ADL/insurance-fund risk signal
      from venue.
    """

    UNKNOWN_NET_EXPOSURE = "UNKNOWN_NET_EXPOSURE"
    OPEN_ORDERS_UNCONFIRMABLE = "OPEN_ORDERS_UNCONFIRMABLE"
    KILL_SWITCH_CANNOT_CONFIRM_CANCEL = "KILL_SWITCH_CANNOT_CONFIRM_CANCEL"
    VENUE_INTERNAL_BALANCE_MISMATCH = "VENUE_INTERNAL_BALANCE_MISMATCH"
    POSITION_EXISTS_EXTERNALLY_UNKNOWN_INTERNALLY = (
        "POSITION_EXISTS_EXTERNALLY_UNKNOWN_INTERNALLY"
    )
    MATERIAL_BALANCE_MOVEMENT_UNEXPLAINED = "MATERIAL_BALANCE_MOVEMENT_UNEXPLAINED"
    MARGIN_COLLATERAL_SAFETY_UNCERTAIN = "MARGIN_COLLATERAL_SAFETY_UNCERTAIN"
