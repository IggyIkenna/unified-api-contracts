"""Cost derivation — formula #2 extracted from derivation.py.

Wave E closure (2026-04-20): derivation.py grew past the 900-line QG
ceiling. Cost was the largest single formula (163 lines with local
constants), so it moves out here. Public API stable — callers still
import ``cost`` via the ``unified_api_contracts.strategy`` facade
OR ``unified_api_contracts.internal.architecture_v2``.

SSOT: ``codex/14-playbooks/infra-spec/stage-3c-derivation-engine.md`` §1.2.
"""

from __future__ import annotations

from unified_api_contracts.internal.architecture_v2.compliance import (
    ComplianceEvent,
    ComplianceSink,
    combo_id_for,
)
from unified_api_contracts.internal.architecture_v2.derivation import (
    Combo,
    IntegrationDepth,
    InternalCostLeakageError,
    PriceQuote,
    PricingTier,
    QuoteLine,
    Rule08Violation,
)

# Blocks per stage-3c §1.2 Ex 1 ("signals-only, hybrid tier") — truncated.
_DEFAULT_BLOCK_SCOPE: tuple[str, ...] = (
    "block_1_reporting_core",
    "block_4_strategy_service_entry",
    "block_5_instructions_integration",
    "block_7_execution_layer",
    "block_8_venue_packs",
    "block_9_chain_packs",
    "block_10_instrument_type_packs",
    "block_11_analytics_packs",
)

_DEPTH_BLOCKS: frozenset[str] = frozenset({"block_5_instructions_integration", "block_7_execution_layer"})


def cost(
    combo_cell: Combo,
    tier: PricingTier,
    *,
    integration_depth: IntegrationDepth | None = None,
    block_scope: tuple[str, ...] = _DEFAULT_BLOCK_SCOPE,
    has_exclusivity: bool = False,
    has_raw_data_framing: bool = False,
    caller_has_internal_read: bool = False,
    caller_audience: str = "unknown",
    org_id: str | None = None,
    compliance_sink: ComplianceSink | None = None,
) -> PriceQuote:
    """Return the priced line items for a combo at a tier.

    Stage-3C §1.2:
        cost(combo, tier, integration_depth) =
              Sum[ block_price(b, tier, integration_depth) for b in combo.blocks ]
            + Sum[ premium_price(p, tier) for p in combo.premiums ]     # Tier B only
            - discount_if_applicable(combo, client_contract)

    **Shape-only today** — every :class:`QuoteLine` carries
    ``todo_numeric=True`` and zero amounts. Real pricing tables populate
    once finance signs off on Stage-2 ``commercial-model/pricing-
    building-blocks.md``. Tracked as follow-up in plan §"Future follow-up".

    Rule-08 guards:
      * ``tier='internal'`` + ``caller_has_internal_read=False`` raises
        :class:`InternalCostLeakageError` (stage-3c §1.2 Ex 4).
      * ``tier='tier_a'`` + ``has_exclusivity=True`` populates
        ``rule_08_violations`` (stage-3c §1.2 Ex 3).

    Stage-3E G2 § 5: when ``compliance_sink`` is supplied, every
    detected violation (raised OR collected) is also forwarded as a
    :class:`ComplianceEvent` so the caller can emit
    ``PRICING_RULE_0[78]_VIOLATION`` via UTL → Pub/Sub
    ``<env>-compliance-events``. ``caller_audience`` + ``org_id`` exist
    purely to enrich the event — they do not influence pricing logic.
    """

    cid = combo_id_for(
        str(combo_cell.archetype_id),
        str(combo_cell.category),
        str(combo_cell.instrument_type),
        combo_cell.venue_id,
        combo_cell.chain,
    )

    violations: list[Rule08Violation] = []

    # Rule 07 (BL-19 raw-data framing on Tier A): breaches both rules 07
    # and 08 (rule 08 §"No raw data on any tier"). Compliance event is
    # tagged rule_id="07" for routing; the violation lands in
    # ``rule_08_violations`` because rule 08's "no raw data" clause is the
    # same breach surface — keeps one violations container on the quote.
    if has_raw_data_framing and tier == "tier_a":
        violations.append(
            Rule08Violation(
                code="raw_data_framing_on_tier_a",
                message="Raw-data framing is not permitted on any tier (rules 07 + 08).",
            )
        )
        if compliance_sink is not None:
            compliance_sink(
                ComplianceEvent(
                    rule_id="07",
                    violation_code="raw_data_framing_on_tier_a",
                    combo_id=cid,
                    caller_audience=caller_audience,
                    org_id=org_id,
                    requested_tier=tier,
                    details=(
                        "Raw-data framing requested on Tier A (BL-19). "
                        "Breaches rule 07 data-licensing + rule 08 no-raw-data."
                    ),
                )
            )

    if tier == "internal" and not caller_has_internal_read:
        if compliance_sink is not None:
            compliance_sink(
                ComplianceEvent(
                    rule_id="08",
                    violation_code="internal_cost_leakage",
                    combo_id=cid,
                    caller_audience=caller_audience,
                    org_id=org_id,
                    requested_tier=tier,
                    details="tier='internal' requested without pricing.read_internal capability",
                )
            )
        raise InternalCostLeakageError("tier='internal' requires pricing.read_internal capability (stage-3c §1.2 Ex 4)")

    if has_exclusivity and tier == "tier_a":
        violations.append(
            Rule08Violation(
                code="exclusivity_on_tier_a",
                message="Exclusivity premium requires Tier B (rule 08).",
            )
        )
        if compliance_sink is not None:
            compliance_sink(
                ComplianceEvent(
                    rule_id="08",
                    violation_code="exclusivity_on_tier_a",
                    combo_id=cid,
                    caller_audience=caller_audience,
                    org_id=org_id,
                    requested_tier=tier,
                    details="Exclusivity premium requires Tier B (rule 08).",
                )
            )

    lines: list[QuoteLine] = []
    if not violations:
        for block_id in block_scope:
            depth = integration_depth if block_id in _DEPTH_BLOCKS else None
            lines.append(
                QuoteLine(
                    block_id=block_id,
                    tier=tier,
                    integration_depth=depth,
                    notes="shape-only — numeric pricing populates after finance sign-off",
                )
            )

    premiums: list[QuoteLine] = []
    if has_exclusivity and tier == "tier_b":
        premiums.append(
            QuoteLine(
                block_id="block_12_exclusivity_premium",
                tier=tier,
                notes="exclusivity premium (rule 08 Tier-B only)",
            )
        )

    return PriceQuote(
        combo=combo_cell,
        tier=tier,
        integration_depth=integration_depth,
        lines=tuple(lines),
        premiums=tuple(premiums),
        rule_08_violations=tuple(violations),
    )


__all__ = ["cost"]
