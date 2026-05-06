<!-- POST_PLAN_BANNER_2026_05_06_FINAL -->

> **Post-2026-05-06** — read [`../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md`](../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md) before code/doc changes informed by this doc. The post-plan-reality doc summarizes the 10 cross-cutting principles codified in workspace `CLAUDE.md` (live=batch, no double SSOT, three-category empty-output decision A/B/C, cluster validation MANDATORY at `record_captured`, `available_at` per-row write-time, prediction lifecycle, temporary state must have named successor, per-VM shard isolation, multi-axis shard-vs-display distinction) plus the active plans (`writegate_honest_coverage_endtoend_2026_05_06.plan.md`, `predictions_canonical_question_group_polymarket_migration_2026_05_06.plan.md`, `data_status_multi_axis_shard_propagation_2026_05_06.plan.md`). If this doc disagrees with the active plans, the plans win. Flag conflicts to user — don't decide unilaterally.

# Negative Prices in Canonical Schemas

This document defines precisely which canonical fields can hold negative values
and what those negative values represent.

---

## Fields That CAN Be Negative

### `CanonicalBetOrder.american_odds: int | None`

American moneyline odds for **bookmaker favorites** are expressed as negative
integers. This is the standard US sportsbook convention.

| American | Meaning                        | Decimal equivalent |
| -------- | ------------------------------ | ------------------ |
| -110     | Bet 110 to win 100             | ~1.909             |
| -150     | Bet 150 to win 100             | ~1.667             |
| -300     | Bet 300 to win 100             | ~1.333             |
| +200     | Bet 100 to win 200             | 3.000              |
| +100     | Even money (underdog notation) | 2.000              |

**Type:** `int` (always an integer, never float)
**Range:** any non-zero integer except -100 (degenerate even-money case)
**How to convert:** `american_to_decimal(american_odds)` in `odds.py`

### `CanonicalComboBet.net_premium: Decimal | None`

For **options combos** (1×2, risk reversal, straddle, collar, etc.), the
`net_premium` is the net cost of the combined position:

```
net_premium = sum(long_leg_premiums) - sum(short_leg_premiums)
```

This value **CAN be negative** when the premium received from short legs exceeds
the premium paid for long legs. Examples:

| Strategy                       | Long       | Short   | Typical sign of net_premium     |
| ------------------------------ | ---------- | ------- | ------------------------------- |
| Long call (vanilla)            | Call       | —       | Positive (net cost)             |
| 1×2 (buy 1 call, sell 2 calls) | 1 call     | 2 calls | Often **negative** (net credit) |
| Risk reversal                  | Call       | Put     | Positive or negative            |
| Straddle                       | Call + Put | —       | Positive (net cost)             |
| Collar                         | Call       | Put     | Positive or negative            |

**Type:** `Decimal` (can represent fractional premium values)
**Unit:** Same currency as `total_stake`

---

## Fields That Are NEVER Negative

| Field                                     | Why always positive                    |
| ----------------------------------------- | -------------------------------------- |
| `CanonicalBetOrder.price`                 | Decimal odds — always ≥ 1.01           |
| `CanonicalOdds.decimal_odds`              | Decimal odds — always ≥ 1.01           |
| `CanonicalComboLeg.decimal_odds`          | Decimal odds — always ≥ 1.01           |
| `CanonicalBetOrder.size`                  | Stake amount — always positive         |
| `CanonicalComboBet.total_stake`           | Stake amount — always positive         |
| `CanonicalComboBet.combined_decimal_odds` | Product of decimal odds — always ≥ 1   |
| Betfair SP (starting price)               | Always decimal — always positive       |
| Fractional odds (e.g. 3/1)                | Converted to decimal — always positive |

---

## Normalizer Guidance

When receiving American odds from a provider:

```python
from unified_api_contracts.canonical.odds import american_to_decimal
from unified_api_contracts.canonical.domain import OddsFormat

# Store both the source format and the decimal equivalent
canonical_order = CanonicalBetOrder(
    ...
    price=american_to_decimal(-110),   # canonical decimal (always positive)
    american_odds=-110,                # original American (can be negative)
    odds_format=OddsFormat.AMERICAN,   # records source format
)
```

When building a 1×2 or other options-combo:

```python
CanonicalComboBet(
    ...
    net_premium=Decimal("-2.50"),  # credit received — negative is valid
    ...
)
```
