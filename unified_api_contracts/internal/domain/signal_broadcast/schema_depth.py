"""Schema depth enum for signal-leasing emissions.

Each counterparty is onboarded at one ``SchemaDepth`` — the payload shape
they receive when a strategy-service strategy emits a
``STRATEGY_SIGNAL_GENERATED`` event internally. Commercial tier +
counterparty preference drive the choice; higher depth = richer
attribution + higher lease price.

Mirrors the schema-depth dimension of rule-10 block-5 of the
signal-leasing commercial model. SSOT:
``unified-trading-pm/plans/active/signal_leasing_broadcast_architecture_2026_04_20.plan.md``.
"""

from __future__ import annotations

from enum import StrEnum

__all__ = ["SchemaDepth"]


class SchemaDepth(StrEnum):
    """Payload shape served to a counterparty per-emission.

    * ``MINIMAL`` — direction + weight + optional confidence. Cheapest tier,
      lowest leakage of Odum alpha internals.
    * ``STANDARD`` — ``MINIMAL`` + horizon + stop/take-profit hints. Enough
      for a counterparty to route into their own execution stack.
    * ``RICH`` — ``STANDARD`` + rationale tags + bounded feature snapshot.
      Premium tier; reveals more of the strategy's internals.
    """

    MINIMAL = "MINIMAL"
    STANDARD = "STANDARD"
    RICH = "RICH"
