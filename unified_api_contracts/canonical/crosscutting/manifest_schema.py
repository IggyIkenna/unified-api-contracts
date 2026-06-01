"""Availability-manifest schema column declarations — v8 SSOT.

[UAC] half of the layer split per
``shard_granularity_ssot_propagation_2026_05_06.HANDOVER.md``:

* **[UAC]** (this module) — what the manifest columns ARE: their names,
  types, semantics, default values for back-compat.
* **[UTL]** (``unified_trading_library.manifest_writer``) — runtime
  ``ManifestWriter`` that writes rows + enforces validation gates.
* **[per-service]** — adapters thread the v8 kwargs through to
  ``record_captured`` / ``record_empty`` / ``record_failed`` /
  ``record_expected_empty`` / ``record_expected_unattempted``.

This module declares the **v8 schema column SSOT** — three NEW columns added
in the 2026-05-09 → 2026-05-23 schema-bump window. The full per-row schema
spans many other columns owned by UTL (row_key dimensions, capture_status,
error_reason, attempted_at, pipeline_mode, fixture_id, job_id, etc.); this
module DOES NOT redeclare them — it adds the three v8 emission-policy
columns + a frozen-version constant + back-compat semantics.

Plans:

* ``manifest_schema_final_gate_2026_05_09.md`` Phase 1.C — owns this module.
* ``writegate_honest_coverage_endtoend_2026_05_06.md`` Phase 3.D.5 Wave 4 —
  upstream slice-b design.

v8 schema-bump (this module):

* **service_emission_state** (``str | None`` — value drawn from
  :class:`~unified_api_contracts.canonical.crosscutting.service_emission_state.ServiceEmissionStateEnum`).
* **last_emission_decision_at** (``str | None`` — ISO-8601 milliseconds UTC).
* **expected_window_completeness_fraction** (``float | None``, range ``[0.0, 1.0]``).

All three NULLABLE for v7 row back-compat. UTL writer hot path may stamp
defaults of ``None`` for pre-v8 callsites during the migration window; once
the workspace consumer sweep (Phase 4 of the same plan) finishes, the
defaults are REMOVED at the UTL boundary and every write becomes
explicit-or-fail.

Frozen 2026-05-09 → 2026-05-23: no new columns / no semantic changes accepted
during the window per the plan's hard-stop directive.
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# Schema version constant.
#
# Mirrored in UTL ``manifest_writer.MANIFEST_SCHEMA_VERSION`` — the UTL value
# bumps when the writer actually emits new columns; the UAC value bumps the
# moment the column declaration lands (this module). Drift between the two
# is intentional during the slice rollout — the UAC declaration leads the
# UTL implementation by one version-number tick.
# ---------------------------------------------------------------------------


MANIFEST_SCHEMA_VERSION_V8: Final[int] = 8
"""The manifest schema version this module declares.

v8 adds three NULLABLE columns to v7 — see :data:`V8_NEW_COLUMNS`. v7's row
shape (UTL ``manifest_writer.MANIFEST_SCHEMA_VERSION = 8``) is the writer
default; the 30-day reader-fallback window for pre-v8 rows expires after the
Phase 7 bundled walk migrates all prod parquets to v8."""


# ---------------------------------------------------------------------------
# pipeline_mode column — always NOT NULL (Phase 3 backfill complete 2026-05-28).
#
# Declared here as the UAC SSOT. UTL ``_coerce_pipeline_mode`` enforces the
# constraint at write time: passing ``None`` raises ``ValueError``.
# Phase 3 backfill (43.5M+ rows across all asset-group buckets) completed
# 2026-05-28; all manifest rows now carry a valid PipelineMode value.
# ---------------------------------------------------------------------------

PIPELINE_MODE_COLUMN: Final[str] = "pipeline_mode"
"""Manifest column name for the source-and-mode tag.

Value type: ``str`` — always NOT NULL (Phase 3 backfill complete 2026-05-28).
Values MUST be members of
:class:`~unified_api_contracts.canonical.crosscutting.pipeline_mode.PipelineMode`
(StrEnum, lower-case ``batch_<source>`` / ``live_websocket``).

Historical note: pre-2026-05-28 rows carried ``""`` (empty-string sentinel
from the Phase 1B rollout window). Those rows were backfilled in Phase 3 via
``unified-trading-pm/scripts/migration/backfill_pipeline_mode.py``."""

PIPELINE_MODE_NOT_NULL_SINCE: Final[str] = "2026-05-28"
"""ISO-8601 date from which all manifest rows carry a non-empty ``pipeline_mode``.

After Phase 3 backfill (completed 2026-05-28), this date marks the transition
to "always NOT NULL" — there are no longer any exempt pre-history rows.
Retained for audit tooling that distinguishes write-time-stamped rows from
Phase 3 backfill-derived rows."""


# ---------------------------------------------------------------------------
# v8 column declarations.
#
# Each constant pins (a) the canonical column name (parquet header +
# row-key dict key) and (b) the column's documented value semantics. UTL
# ``ManifestWriter`` accepts kwargs matching these names; the names are the
# SSOT so callsite-grep audits work.
# ---------------------------------------------------------------------------


SERVICE_EMISSION_STATE_COLUMN: Final[str] = "service_emission_state"
"""Manifest column name for the v8 emission-state value.

Value type: ``str | None``. Non-null values MUST be members of
:data:`~unified_api_contracts.canonical.crosscutting.service_emission_state.SERVICE_EMISSION_STATES`
(string view of :class:`~unified_api_contracts.canonical.crosscutting.service_emission_state.ServiceEmissionStateEnum`).
The UTL writer-side validation (Phase 2.A of the manifest schema final gate
plan) raises on unknown values via the same fail-loud pattern as
``record_empty(reason=...)``.

v7 (pre-2026-05-09) rows lack this column; the read-side reader-fallback
(Phase 2.C of the same plan) defaults missing values to ``None`` for ≤30
days post-Phase-7 migration. After 30d the fallback is deleted (workspace
"no double SSOT" rule)."""


LAST_EMISSION_DECISION_AT_COLUMN: Final[str] = "last_emission_decision_at"
"""Manifest column name for the v8 last-decision timestamp.

Value type: ``str | None`` — ISO-8601 milliseconds UTC (e.g.
``"2026-05-08T03:14:00.123Z"``). Captures the wall-clock time of the most
recent ``publish_with_policy`` decision for the shard's identity, so
downstream readers can detect stale state (no decision fired in expected
cadence → service alive but stuck) distinct from heartbeat-only state
(decision fired, decided "stale data").

Why string-typed rather than ``datetime``: parquet round-trip stability,
no timezone-aware-vs-naive footguns, and the manifest-reader hot path
already canonicalises timestamps as ISO strings. UTC suffix
``Z`` mandatory; the UTL writer rejects naive / local-tz timestamps."""


EXPECTED_WINDOW_COMPLETENESS_FRACTION_COLUMN: Final[str] = "expected_window_completeness_fraction"
"""Manifest column name for the v8 expected-window completeness fraction.

Value type: ``float | None`` in the closed interval ``[0.0, 1.0]``. Sibling
to UTL ``publish_with_policy`` 's ``completeness_fraction`` argument — the
manifest column records the operator-declared expected fraction so
downstream readers can detect a row that's degraded BELOW its expected
floor (e.g. an ``ohlcv_24h`` row whose policy is ``PARTIAL_OK`` with
``expected_window_completeness_fraction=0.95`` but actual completeness 0.80 →
escalate).

**Naming history (2026-05-11)**: originally shipped as
``expected_window_completeness_pct`` at UAC@``174f401`` (slot 6 Phase 1.C);
operator-renamed to ``_fraction`` at UAC@<this commit> per
[`plans/active/issues/expected_window_completeness_pct_range_drift_2026_05_11.md`](../../../../unified-trading-pm/plans/active/issues/expected_window_completeness_pct_range_drift_2026_05_11.md)
option (a) — the `_pct` suffix implied percentage (0-100) but the value
range is 0-1 fraction (matches UTL ``completeness_fraction`` arg + the
in-band parquet column). Rename window was free because zero on-disk writes
had shipped before the rename landed. Frozen 2026-05-11 → 2026-05-23.

UTL writer rejects out-of-range values with the same fail-loud pattern as
:class:`unified_trading_library.emission_publisher.InvalidCompletenessFractionError`."""


V8_NEW_COLUMNS: Final[tuple[str, str, str]] = (
    SERVICE_EMISSION_STATE_COLUMN,
    LAST_EMISSION_DECISION_AT_COLUMN,
    EXPECTED_WINDOW_COMPLETENESS_FRACTION_COLUMN,
)
"""Closed tuple of v8 new column names — what the Phase 7 bundled walk
backfills onto every v7 row + what the workspace consumer sweep (Phase 4)
threads through every ``ManifestWriter`` callsite.

Ordering pinned for stable grep audit + per-VM-shard migration script row
construction (``manifest_migrations/v7_to_v8.py`` per Phase 2.D)."""


# ---------------------------------------------------------------------------
# Back-compat semantics for v7 rows.
#
# Read-side fallback contract — :class:`unified_trading_library.manifest_writer`
# read paths populate missing v8 columns with these defaults for ≤30 days
# post-migration. After the 30d window the fallback is deleted (workspace
# "no double SSOT" rule); any v7-shaped row that survives the migration
# becomes a phantom-audit finding instead of silently round-tripping.
# ---------------------------------------------------------------------------


V8_COLUMN_DEFAULTS: Final[dict[str, None]] = {
    SERVICE_EMISSION_STATE_COLUMN: None,
    LAST_EMISSION_DECISION_AT_COLUMN: None,
    EXPECTED_WINDOW_COMPLETENESS_FRACTION_COLUMN: None,
}
"""Read-side defaults for v7 rows missing the v8 columns.

All three NULLABLE — a ``None`` observed at read time unambiguously means
"pre-v8 row" since ``next_state(...)`` never produces ``None`` for v8
writes. Downstream consumers branch on ``state is None`` → fall through to
``capture_status``-based reasoning."""


READER_FALLBACK_WINDOW_DAYS: Final[int] = 30
"""How long the manifest-reader fallback tolerates missing v8 columns.

Per ``manifest_schema_final_gate_2026_05_09.md`` Phase 2.C: post-Phase-7
bundled-walk migration runs 2026-05-13→05-15; the reader fallback is then
deleted on or after 2026-06-14 (30 days post). After deletion, any v7
row that survives is a phantom-audit finding.
"""


__all__ = [
    "EXPECTED_WINDOW_COMPLETENESS_FRACTION_COLUMN",
    "LAST_EMISSION_DECISION_AT_COLUMN",
    "MANIFEST_SCHEMA_VERSION_V8",
    "PIPELINE_MODE_COLUMN",
    "PIPELINE_MODE_NOT_NULL_SINCE",
    "READER_FALLBACK_WINDOW_DAYS",
    "SERVICE_EMISSION_STATE_COLUMN",
    "V8_COLUMN_DEFAULTS",
    "V8_NEW_COLUMNS",
]
