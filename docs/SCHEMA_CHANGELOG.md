<!-- POST_PLAN_BANNER_2026_05_06_FINAL -->

> **Post-2026-05-06** — read [`../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md`](../../unified-trading-pm/codex/POST_PLAN_REALITY_2026_05_06.md) before code/doc changes informed by this doc. The post-plan-reality doc summarizes the 10 cross-cutting principles codified in workspace `CLAUDE.md` (live=batch, no double SSOT, three-category empty-output decision A/B/C, cluster validation MANDATORY at `record_captured`, `available_at` per-row write-time, prediction lifecycle, temporary state must have named successor, per-VM shard isolation, multi-axis shard-vs-display distinction) plus the active plans (`writegate_honest_coverage_endtoend_2026_05_06.plan.md`, `predictions_canonical_question_group_polymarket_migration_2026_05_06.plan.md`, `data_status_multi_axis_shard_propagation_2026_05_06.plan.md`). If this doc disagrees with the active plans, the plans win. Flag conflicts to user — don't decide unilaterally.

# UAC Canonical Schema Changelog

Tracks per-type version bumps for all canonical Pydantic types in
`canonical/domain.py` and `execution.py`.

Semver rules: MAJOR = breaking (required field add/remove/type-change/rename);
MINOR = optional field added, new Enum member; PATCH = docs/metadata only.

See full rules: `unified-trading-codex/02-data/canonical-schema-versioning.md`

---

## CanonicalBetOrder

- **1.1.0** (2026-03-06): Added `american_odds: int | None` and `odds_format: OddsFormat` (optional fields — minor bump). Negative `american_odds` encodes bookmaker favorites (e.g. -110).
- **1.0.0** (2026-03-06): Initial semver release (promoted from "1.0" string).

## CanonicalComboBet _(new in 1.0.0)_

- **1.0.0** (2026-03-06): Initial release. Multi-leg parlay/accumulator/options-combo. `net_premium` can be negative for options combos.

## CanonicalComboLeg _(new in 1.0.0)_

- **1.0.0** (2026-03-06): Initial release. Single leg of a combo bet with `american_odds: int | None` and `odds_format`.

## CanonicalOrderBook

- **1.0.0** (2026-03-06): Initial semver release (promoted from "1.0" string).

## CanonicalTrade

- **1.0.0** (2026-03-06): Initial semver release (promoted from "1.0" string).

## CanonicalTicker

- **1.0.0** (2026-03-06): Initial semver release (promoted from "1.0" string).

## CanonicalLiquidation

- **1.0.0** (2026-03-06): Initial semver release (promoted from "1.0" string).

## CanonicalDerivativeTicker

- **1.0.0** (2026-03-06): Initial semver release (promoted from "1.0" string).

## CanonicalWebSocketLifecycle

- **1.0.0** (2026-03-06): Initial semver release (promoted from "1.0" string).

## CanonicalFee

- **1.0.0** (2026-03-06): Initial semver release (promoted from "1.0" string).

## CanonicalOdds

- **1.0.0** (2026-03-06): Initial semver release (promoted from "1.0" string).

## CanonicalBetMarket

- **1.0.0** (2026-03-06): Initial semver release (promoted from "1.0" string).

## CanonicalOrder _(execution.py)_

- **1.0.0** (2026-03-06): Initial semver release. Added `schema_version` field.

## CanonicalFill _(execution.py)_

- **1.0.0** (2026-03-06): Initial semver release. Added `schema_version` field.

## ExecutionInstruction _(execution.py)_

- **1.0.0** (2026-03-06): Initial semver release. Added `schema_version` field.

## ExecutionResult _(execution.py)_

- **1.0.0** (2026-03-06): Initial semver release. Added `schema_version` field.
