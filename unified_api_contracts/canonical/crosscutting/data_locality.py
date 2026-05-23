"""Data-locality enforcement utilities.

Workspace policy (aws_migration_defi_first_2026_05_07.md §Phase 6.5 + dual-cloud-active
2026-05-13 sequencing update): all UI/API surfaces MUST co-locate with the data they
read. A service running on GCP reading from AWS buckets (or vice-versa) pays
cross-cloud egress at $0.08-0.12/GB and introduces latency that degrades live-trading
dashboards.

``DATA_LOCALITY_REGION`` env-var contract
-----------------------------------------

Each deployed service receives two env vars:

* ``CLOUD_PROVIDER`` — ``"gcp"`` | ``"aws"`` | ``"local"``
  The cloud the service itself is running on.

* ``DATA_LOCALITY_REGION`` — ``"gcp:asia-northeast1"`` | ``"aws:ap-northeast-1"``
  The cloud + region where the primary data bucket lives.  If omitted, the check
  is skipped (graceful no-op for local-dev where both resolve to ``local``).

When the cloud-prefix of ``DATA_LOCALITY_REGION`` does not match ``CLOUD_PROVIDER``,
a ``CROSS_CLOUD_QUERY`` event should be emitted and the alerting-service will surface
it as :attr:`~unified_api_contracts.canonical.crosscutting.alerting.codes.AlertCode.CROSS_CLOUD_EGRESS_DETECTED`
(HIGH severity, PagerDuty P2 + Telegram).

Usage in services
-----------------

.. code-block:: python

    from unified_api_contracts.canonical.crosscutting.data_locality import (
        check_data_locality,
        DataLocalityViolation,
    )

    # In service boot / request middleware:
    result = check_data_locality()
    if result is not None and not result.ok:
        logger.warning(
            "CROSS_CLOUD_QUERY detected — service on %s, data in %s",
            result.service_cloud,
            result.data_cloud,
        )
        # Emit CROSS_CLOUD_EGRESS_DETECTED event via alerting bus.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class DataLocalityResult:
    """Result of a data-locality check.

    :param ok: ``True`` if service cloud matches data cloud (or check was skipped).
    :param service_cloud: The cloud the service is running on (from ``CLOUD_PROVIDER``).
    :param data_cloud: The cloud the data lives on (from ``DATA_LOCALITY_REGION`` prefix).
    :param skipped: ``True`` if ``DATA_LOCALITY_REGION`` was not set (local-dev / legacy).
    """

    ok: bool
    service_cloud: str
    data_cloud: str
    skipped: bool = False


def check_data_locality() -> DataLocalityResult | None:
    """Check that the running service's cloud matches the data-locality region.

    Reads ``CLOUD_PROVIDER`` and ``DATA_LOCALITY_REGION`` from the environment.

    Returns ``None`` if ``CLOUD_PROVIDER`` is not set (avoids noise in test contexts
    that don't inject either variable).

    Returns a :class:`DataLocalityResult` with ``skipped=True`` if
    ``DATA_LOCALITY_REGION`` is unset (graceful no-op for local dev).

    Returns a :class:`DataLocalityResult` with ``ok=False`` if the cloud-prefix of
    ``DATA_LOCALITY_REGION`` does not match ``CLOUD_PROVIDER`` (cross-cloud violation).

    Callers must emit the ``CROSS_CLOUD_EGRESS_DETECTED`` alert themselves via the
    alerting bus — this function only performs the check and reports the result.
    """
    service_cloud = (os.getenv("CLOUD_PROVIDER") or "").lower().strip()  # config-bootstrap: data-locality-check
    if not service_cloud:
        return None

    data_locality_region = (os.getenv("DATA_LOCALITY_REGION") or "").strip()  # config-bootstrap: data-locality-check
    if not data_locality_region:
        return DataLocalityResult(
            ok=True,
            service_cloud=service_cloud,
            data_cloud="",
            skipped=True,
        )

    data_cloud = data_locality_region.split(":")[0].lower()
    ok = service_cloud == data_cloud or service_cloud == "local"
    return DataLocalityResult(
        ok=ok,
        service_cloud=service_cloud,
        data_cloud=data_cloud,
        skipped=False,
    )


# Canonical DATA_LOCALITY_REGION values for each cloud.
DATA_LOCALITY_REGION_GCP = "gcp:asia-northeast1"
DATA_LOCALITY_REGION_AWS = "aws:ap-northeast-1"
