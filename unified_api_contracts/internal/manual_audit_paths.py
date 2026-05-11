"""Path SSOT for `ManualInstructionAuditLog` persistence.

Pure-function path helpers — no GCS / S3 code. The caller (execution-service
`/manual/instruction` handler + ml-training-service `/training/{archetype}/{action}`
handler) constructs the path via :func:`manual_audit_object_key` and writes via
the standard cloud-interface client.

§ Layout

Audit rows persist as line-delimited JSON (one row per `ManualInstructionAuditLog`)
under a dedicated env-tiered bucket whose `kind="manual-audit"` resolves via
:func:`unified_trading_library.cloud_interface.bucket_naming.resolve_bucket_name`.
The kind addition lands in `bucket_name_ssot_canonicalisation_2026_05_10.md`
Phase 0i tail (slot 4 owned scope; this module documents the path shape so the
bucket-kind addition is mechanical).

Object key shape::

    manual_audit/{YYYY-MM-DD}/{action_category}/{audit_id}.jsonl

Concrete examples::

    manual_audit/2026-05-12/manual_trade/aud-defi-100.jsonl
    manual_audit/2026-05-12/ml_training_control/aud-ml-200.jsonl

§ Why separate from operational events

Operational events at ``gs://{pid}-events-{env}/events/{service}/...`` are
short-retention (~30d) hourly-partitioned streams optimised for log-tail. Manual
audit rows have different requirements:

* **Long retention** for compliance (≥7 years).
* **Append-only / immutable** — operator actions are durable record.
* **Indexed by wallet / strategy / submitted_by** for pnl-attribution +
  batch-live-reconciliation + alerting queries.

A dedicated `manual-audit` bucket (env-tiered per bucket-name SSOT) gives the
operations team independent retention + access controls + lifecycle policies
without polluting the operational events surface.

§ Date partitioning

UTC date string (``YYYY-MM-DD``) computed from
:attr:`ManualInstructionAuditLog.persisted_at`. The `action_category`
sub-partition matches :class:`ManualAuditCategory` value strings
(``manual_trade`` / ``ml_training_control``) so consumers can selectively read
only one category for cheaper queries.

§ Audit ID convention

`audit_id` is the row's unique identifier (UUIDv4 or similar). Object keys
include the `.jsonl` suffix even for single-row writes — readers iterate via
``readlines()`` for forward-compat with future multi-row append batches.

§ Cross-references

* :class:`ManualInstructionAuditLog` —
  ``unified_api_contracts/internal/execution.py``
* :class:`ManualAuditCategory` —
  ``unified_api_contracts/internal/execution.py``
* Bucket-kind SSOT —
  ``deployment-service/configs/cloud-providers.yaml`` (slot 4 Phase 0i tail
  adds ``manual-audit`` kind)
* Codex doc — ``codex/04-architecture/manual-trade-booking.md``
  § "Audit log persistence (GCS / S3)"
"""

from __future__ import annotations

from datetime import date, datetime

from unified_api_contracts.internal.execution import ManualAuditCategory

BUCKET_KIND_MANUAL_AUDIT = "manual-audit"
"""Bucket-name SSOT `kind=` key for the manual-audit bucket.

Resolves via
``resolve_bucket_name(cloud=..., kind=BUCKET_KIND_MANUAL_AUDIT, env=...)``
once `bucket_name_ssot_canonicalisation_2026_05_10.md` Phase 0i tail adds
the entry. Pre-Phase-0i: callers should NOT inline a bucket name — the
audit-log persistence ships AFTER Phase 0i lands.
"""

OBJECT_KEY_TEMPLATE = "manual_audit/{date}/{action_category}/{audit_id}.jsonl"
"""Template for the audit-log object key under the manual-audit bucket."""


def manual_audit_object_key(
    audit_id: str,
    action_category: ManualAuditCategory,
    persisted_at: datetime,
) -> str:
    """Return the object key for a single audit row.

    Args:
        audit_id: Unique row identifier (UUIDv4 or similar).
        action_category: Closed-set `ManualAuditCategory` value.
        persisted_at: UTC wall-clock time of persistence; date component used
            for the date partition.

    Returns:
        Relative object key (NO bucket prefix). Caller composes the full URI
        via the cloud-interface client + `resolve_bucket_name`.

    Raises:
        ValueError: if `audit_id` is empty or contains path separators.
    """

    if not audit_id:
        raise ValueError("audit_id must be non-empty")
    if "/" in audit_id or "\\" in audit_id:
        raise ValueError(f"audit_id must not contain path separators: {audit_id!r}")
    date_str = _date_partition(persisted_at)
    return OBJECT_KEY_TEMPLATE.format(
        date=date_str,
        action_category=action_category.value,
        audit_id=audit_id,
    )


def manual_audit_date_prefix(category: ManualAuditCategory, on: date) -> str:
    """Return the date-partition prefix for batch listing.

    Useful for downstream consumers (pnl-attribution / batch-live-reconciliation /
    alerting) that scan all audit rows for a given UTC date + category.

    Example::

        gs://{bucket}/manual_audit/2026-05-12/manual_trade/

    Args:
        category: Closed-set `ManualAuditCategory` value.
        on: UTC date.

    Returns:
        Object-key prefix ending in `/`. Caller composes the full URI prefix.
    """

    return f"manual_audit/{on.isoformat()}/{category.value}/"


def _date_partition(persisted_at: datetime) -> str:
    """Format the date partition string from a UTC `persisted_at` timestamp."""

    return persisted_at.date().isoformat()


__all__ = [
    "BUCKET_KIND_MANUAL_AUDIT",
    "OBJECT_KEY_TEMPLATE",
    "manual_audit_date_prefix",
    "manual_audit_object_key",
]
