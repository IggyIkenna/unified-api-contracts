"""Risk-rule registry aggregator — 7-axis SSOT for Layer-2 pre-flight.

This package aggregates the 7 per-axis registry seed tuples shipped by Phase 2
of ``plans/active/risk_simulations_limits_alerting_2026_05_10.md``:

* ``ARCHETYPE_RULES``   — Phase 2.A — per-archetype rules (cutover: 2 archetypes)
* ``VENUE_RULES``       — Phase 2.B — per-venue rules (6 perp + 3 Solana protocols)
* ``ACCOUNT_RULES``     — Phase 2.C — per-account rules (paper + live)
* ``CLIENT_RULES``      — Phase 2.D — per-client rules (cutover demo client)
* ``ASSET_GROUP_RULES`` — Phase 2.E — per-asset_group rules (defi + cefi)
* ``GLOBAL_RULES``      — Phase 2.F — workspace-wide kill-condition rules
* ``STRATEGY_FAMILY_RULES`` — Phase 2.H — per-family aggregate rules

The ``ALL_RULES`` constant is the full union across every axis; consumers that
need a single iterable use it. The ``get_rules_for(scope, applies_to)`` helper
returns the subset of rules whose scope matches and whose ``applies_to`` matches
the supplied key (or ``"*"`` for catch-all).

§ 7 SSOT reconciliation
-----------------------

Composes with the 5 canonical workspace SSOTs (risk-gates layers, 8-event
lifecycle, kill-switch trigger set, circuit-breaker action set, strategy
kill-switch behaviour set). Per the seam diagram in
``risk_simulations_limits_alerting_2026_05_10.md`` lines 44-87, this registry
is the source-of-truth for what rules fire pre-flight at Layer 2; downstream
the UTL ``risk_preflight()`` helper iterates ``get_rules_for(...)`` per
order-context axis and aggregates decisions.
"""

from __future__ import annotations

from collections.abc import Iterable

from ...canonical.crosscutting.risk_rule import RiskRule, RiskRuleScope
from .account import ACCOUNT_RULES
from .archetype import ARCHETYPE_RULES
from .asset_group import ASSET_GROUP_RULES
from .client import CLIENT_RULES
from .global_rules import GLOBAL_RULES
from .strategy_family import STRATEGY_FAMILY_RULES
from .venue import VENUE_RULES

ALL_RULES: tuple[RiskRule, ...] = (
    *ARCHETYPE_RULES,
    *VENUE_RULES,
    *ACCOUNT_RULES,
    *CLIENT_RULES,
    *ASSET_GROUP_RULES,
    *GLOBAL_RULES,
    *STRATEGY_FAMILY_RULES,
)
"""Full union across every per-axis registry. Iteration order: archetype →
venue → account → client → asset_group → global → strategy_family. Stable for
reproducible pre-flight evaluation."""


_RULES_BY_SCOPE: dict[RiskRuleScope, tuple[RiskRule, ...]] = {
    RiskRuleScope.PER_ARCHETYPE: ARCHETYPE_RULES,
    RiskRuleScope.PER_VENUE: VENUE_RULES,
    RiskRuleScope.PER_ACCOUNT: ACCOUNT_RULES,
    RiskRuleScope.PER_CLIENT: CLIENT_RULES,
    RiskRuleScope.PER_ASSET_GROUP: ASSET_GROUP_RULES,
    RiskRuleScope.GLOBAL: GLOBAL_RULES,
    RiskRuleScope.PER_STRATEGY_FAMILY: STRATEGY_FAMILY_RULES,
}


def get_rules_for(scope: RiskRuleScope, applies_to: str) -> tuple[RiskRule, ...]:
    """Return the subset of rules matching ``scope`` and ``applies_to``.

    Args:
        scope: The risk-rule scope axis (e.g. ``PER_VENUE``, ``GLOBAL``).
        applies_to: The applies-to key (e.g. venue name, archetype id,
            account id). Pass ``"*"`` to match every rule in the scope.

    Returns:
        Tuple of matching rules. May be empty if no rules registered for the
        ``(scope, applies_to)`` pair.

    Rules with ``applies_to="*"`` always match (catch-all per-scope). Otherwise
    exact-match string comparison on ``rule.applies_to``.
    """
    bucket = _RULES_BY_SCOPE.get(scope, ())
    if applies_to == "*":
        return bucket
    return tuple(r for r in bucket if r.applies_to == applies_to or r.applies_to == "*")


def iter_applicable_rules(
    archetype_id: str | None = None,
    venue_id: str | None = None,
    account_id: str | None = None,
    client_id: str | None = None,
    asset_group: str | None = None,
    strategy_family_id: str | None = None,
) -> Iterable[RiskRule]:
    """Yield every rule applicable to the given order-context axes.

    For each axis with a non-``None`` value, yields rules matching that key
    plus any catch-all (``applies_to="*"``) rules in that scope. Global rules
    always yield.

    This is the canonical helper consumers (UTL ``risk_preflight``,
    risk-and-exposure-service, execution-service) should use when building
    the ``applicable_rules`` argument for pre-flight evaluation.
    """
    if archetype_id is not None:
        yield from get_rules_for(RiskRuleScope.PER_ARCHETYPE, archetype_id)
    if venue_id is not None:
        yield from get_rules_for(RiskRuleScope.PER_VENUE, venue_id)
    if account_id is not None:
        yield from get_rules_for(RiskRuleScope.PER_ACCOUNT, account_id)
    if client_id is not None:
        yield from get_rules_for(RiskRuleScope.PER_CLIENT, client_id)
    if asset_group is not None:
        yield from get_rules_for(RiskRuleScope.PER_ASSET_GROUP, asset_group)
    if strategy_family_id is not None:
        yield from get_rules_for(RiskRuleScope.PER_STRATEGY_FAMILY, strategy_family_id)
    yield from GLOBAL_RULES


__all__ = [
    "ACCOUNT_RULES",
    "ALL_RULES",
    "ARCHETYPE_RULES",
    "ASSET_GROUP_RULES",
    "CLIENT_RULES",
    "GLOBAL_RULES",
    "STRATEGY_FAMILY_RULES",
    "VENUE_RULES",
    "get_rules_for",
    "iter_applicable_rules",
]
