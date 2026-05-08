"""Cloud target taxonomy — closed-set of {GCP, AWS} the workspace deploys to.

SSOT for the cloud-target axis the deployment-UI / deployment-api header toggle
dispatches against. Defined by ``deployment_ui_lifecycle_tabs_2026_05_08`` plan
Phase A.5 — the doc-touchpoint plan section names this module as the typed
Python mirror of the deployment-UI ``CloudProviderContext.tsx`` ``CloudTarget``
type alias (``"gcp" | "aws"``). Both client + server agree on a 2-member closed
set; never a free-form string.

The two members
---------------

* :attr:`CloudTarget.GCP` — Google Cloud Platform (asia-northeast1 primary
  region today).
* :attr:`CloudTarget.AWS` — Amazon Web Services (cloud-parity peer; same
  workloads, mirror buckets, mirror Cloud Run / ECS services).

There is no ``LOCAL`` or ``MULTI`` member by design. Local-dev mode is
discriminated separately via :class:`EnvironmentTier` (``DEV``); a request is
always dispatched against EXACTLY ONE cloud, and toggling re-routes the next
request without re-authenticating (deployment-api boots with both GCP + AWS
auth/credentials loaded into its session per the
``UnifiedCloudConfig`` always-available pattern; the toggle just changes which
client gets used).

Layer split
-----------

* **[UAC]** — this module. The 2-member StrEnum.
* **[deployment-ui]** — ``src/contexts/CloudProviderContext.tsx`` ``CloudTarget``
  type alias (``"gcp" | "aws"``). Phase H.3 + B.7 wire the UAC mirror into the
  UI's typed surface so client + server share the same vocabulary; until then
  the TypeScript type alias is the canonical UI shape.
* **[deployment-api]** — request-dispatch layer reads ``CloudTarget`` from the
  per-request header / query param to pick the GCP-vs-AWS client.
"""

from __future__ import annotations

from enum import StrEnum


class CloudTarget(StrEnum):
    """Closed-set 2-cloud taxonomy.

    Each member's value equals its name (canonical UAC StrEnum convention,
    see :class:`unified_api_contracts.canonical.crosscutting.lifecycle_class.LifecycleClass`
    + :class:`unified_api_contracts.canonical.crosscutting.share_class.ShareClass`
    for the precedent).
    """

    GCP = "GCP"
    """Google Cloud Platform — asia-northeast1 primary region today."""

    AWS = "AWS"
    """Amazon Web Services — cloud-parity peer; mirror workloads + buckets."""
