"""Experiment registry SSOT — Phase BB.1 of deployment_ui_lifecycle_tabs_2026_05_08.md.

Declares the experiment kind taxonomy and the typed ``ExperimentRunSpec``
dataclass. The deployment-api Monitor -> Experiments sub-tab reads specs
written by the UTL experiment-tracker helper; lifecycle action endpoints
(stop / restart) scope to runs tracked here.

Governance rules
----------------
* ``run_id`` MUST be a UUIDv7 string (lexicographically sortable by time).
  Callers that write experiment manifests use
  ``uuid_utils.uuid7()`` or an equivalent UUIDv7 generator — never UUIDv4.
* Persistence is GCS-only (no new database). One ``manifest.json`` blob
  per run, one append-only ``metrics.jsonl`` for per-step metrics:

  .. code-block:: text

      gs://<project_id>-experiments/
        by_kind={kind}/
          run_id={run_id}/
            manifest.json    ← ExperimentRunSpec serialised as JSON
            metrics.jsonl    ← one JSON object per line, appended per step

* Every experiment lifecycle event (started / step / completed / failed)
  MUST also flow through the UTL ``log_event()`` machinery so it appears
  in the events bucket alongside all other workspace events.

SSOT: ``deployment_ui_lifecycle_tabs_2026_05_08.md`` Phase BB.1.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ExperimentKind(StrEnum):
    """Closed-set taxonomy of experiment kinds.

    Adding a new kind requires a plan entry in
    ``deployment_ui_lifecycle_tabs_2026_05_08.md`` and a corresponding
    Monitor → Experiments renderer in the deployment-UI.
    """

    ML_TRAINING = "ML_TRAINING"
    """Supervised / reinforcement learning training runs producing model artefacts."""

    STRATEGY_BACKTEST = "STRATEGY_BACKTEST"
    """Full strategy simulation over historical data, producing P&L + risk metrics."""

    EXECUTION_BACKTEST = "EXECUTION_BACKTEST"
    """Execution-layer simulation (fill modelling, slippage, latency) over historical fills."""


class ExperimentStatus(StrEnum):
    """Closed-set lifecycle status for an experiment run."""

    RUNNING = "running"
    """Run is active — progress updates expected."""

    COMPLETED = "completed"
    """Run finished successfully; ``result_blob_uri`` is populated."""

    FAILED = "failed"
    """Run terminated with an error; ``error_message`` is populated."""

    CANCELLED = "cancelled"
    """Run was stopped by operator action before completion."""


@dataclass(frozen=True)
class ExperimentRunSpec:
    """Typed declaration of a single experiment run.

    Written by the UTL experiment-tracker helper on ``start_experiment()``
    and updated (via a new frozen instance) at each lifecycle transition.
    Serialised to ``manifest.json`` under the GCS prefix for that run.

    Attributes:
        run_id: UUIDv7 string — lexicographically sortable by creation time.
            Format: ``xxxxxxxx-xxxx-7xxx-xxxx-xxxxxxxxxxxx``.
        kind: Experiment kind from :class:`ExperimentKind`.
        owner: Operator or service account that started the run (e.g.
            ``"ikenna"`` or ``"strategy-service-sa@<project>.iam.gserviceaccount.com"``).
        asset_group: Lowercase workspace asset group (``cefi`` / ``defi`` /
            ``tradfi`` / ``sports`` / ``prediction`` / ``cross-cutting``).
        started_at: ISO-8601 UTC timestamp of run start.
        hyperparams: Arbitrary key-value configuration snapshotted at start.
            Values MUST be JSON-serialisable primitives (str, int, float, bool, None).
        expected_steps: Total number of steps / epochs / backtest-days expected.
            Used to compute progress percentage in the Monitor sub-tab.
        result_blob_uri: GCS URI of the primary artefact produced by the run,
            or ``None`` while the run is in progress or failed.
        status: Current run lifecycle status.
        error_message: Set when ``status == ExperimentStatus.FAILED``.
        owning_plan: Plan slug that declared this experiment kind (for auditability).
    """

    run_id: str
    kind: ExperimentKind
    owner: str
    asset_group: str
    started_at: str
    hyperparams: dict[str, object]
    expected_steps: int
    status: ExperimentStatus
    result_blob_uri: str | None = None
    error_message: str | None = None
    owning_plan: str = field(default="deployment_ui_lifecycle_tabs_2026_05_08")

    @property
    def gcs_prefix(self) -> str:
        """GCS path prefix for this run's blobs (without bucket name).

        The full manifest URI is:
            ``gs://<project_id>-experiments/{gcs_prefix}/manifest.json``
        """
        return f"by_kind={self.kind}/run_id={self.run_id}"

    @property
    def manifest_blob_path(self) -> str:
        """Relative blob path for the run manifest."""
        return f"{self.gcs_prefix}/manifest.json"

    @property
    def metrics_blob_path(self) -> str:
        """Relative blob path for the per-step append-only metrics stream."""
        return f"{self.gcs_prefix}/metrics.jsonl"
