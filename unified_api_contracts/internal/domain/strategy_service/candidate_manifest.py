"""MinimalCandidateManifest — May-23 promote-workflow type (Phase U1).

Captures the minimal data needed to round-trip a candidate config across the
promote workflow (batch → paper → live).  NOT the full pinned-shas treatment
(no commit shas, no model refs fully populated, no features manifest version)
— those are post-cutover Phase 2 enrichments.

SSOT:
    plans/active/promote_workflow_may23_cli_path_2026_05_10.md § Phase U1
    codex/04-architecture/live-deployment-manifest.md (ships with this type)
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from unified_api_contracts.internal.architecture_v2.enums import StrategyArchetype
from unified_api_contracts.internal.domain.strategy_service.lifecycle import (
    StrategyMaturityPhase,
)

__all__ = [
    "GroupBMetrics",
    "MinimalCandidateManifest",
    "ModelRef",
    "make_manifest_id",
]


def make_manifest_id() -> str:
    """Generate a UUID4 manifest ID string."""
    return str(uuid.uuid4())


@dataclass(frozen=True)
class GroupBMetrics:
    """Backtest score vector captured at promote time (Group B cutover criterion).

    Frozen at promote time so the decision audit trail is immutable.
    """

    sharpe_ratio: float
    calmar_ratio: float
    max_drawdown_pct: float
    win_rate: float
    backtest_days: int
    total_return_pct: float


@dataclass(frozen=True)
class ModelRef:
    """Lightweight reference to an ML model artifact (post-cutover Phase 2 only).

    Always None in MinimalCandidateManifest.model_refs at May-23 cutover.
    """

    model_id: str
    version: str
    artifact_uri: str


@dataclass
class MinimalCandidateManifest:
    """May-23 promote-workflow manifest — minimum viable for paper/live promotion.

    Captures just enough to round-trip a candidate config across the promote
    workflow (Promote UI → deployment-api → strategy VM launcher).  Post-cutover
    Phase 2 enriches with pinned_shas, model_refs, features_manifest_version,
    and chain_rpc_pins without requiring a UAC schema break (all fields typed
    Optional with None defaults).
    """

    strategy_instance_id: str
    archetype: StrategyArchetype
    config_json: dict[str, object]
    score_vector: GroupBMetrics
    target_phase: StrategyMaturityPhase
    created_by: str
    reason: str

    manifest_id: str = field(default_factory=make_manifest_id)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    version_id: str | None = None

    # Future-extension placeholders (post-cutover Phase 2) — always None at May-23
    pinned_shas: dict[str, str] | None = None
    model_refs: list[ModelRef] | None = None
    features_manifest_version: str | None = None
    chain_rpc_pins: dict[str, str] | None = None

    def __post_init__(self) -> None:
        if not self.strategy_instance_id:
            raise ValueError("strategy_instance_id is required")
        if not self.created_by:
            raise ValueError("created_by is required")
        if not self.reason:
            raise ValueError("reason is required")
        if self.target_phase not in (
            StrategyMaturityPhase.PAPER_1D,
            StrategyMaturityPhase.LIVE_EARLY,
        ):
            raise ValueError(
                f"target_phase must be PAPER_1D or LIVE_EARLY for May-23 promote workflow; got {self.target_phase!r}"
            )

    def to_firestore_dict(self) -> dict[str, object]:
        """Serialise to a Firestore-compatible dict."""
        return {
            "manifest_id": self.manifest_id,
            "strategy_instance_id": self.strategy_instance_id,
            "version_id": self.version_id,
            "archetype": self.archetype.value,
            "config_json": self.config_json,
            "score_vector": {
                "sharpe_ratio": self.score_vector.sharpe_ratio,
                "calmar_ratio": self.score_vector.calmar_ratio,
                "max_drawdown_pct": self.score_vector.max_drawdown_pct,
                "win_rate": self.score_vector.win_rate,
                "backtest_days": self.score_vector.backtest_days,
                "total_return_pct": self.score_vector.total_return_pct,
            },
            "target_phase": self.target_phase.value,
            "created_at": self.created_at,
            "created_by": self.created_by,
            "reason": self.reason,
            "pinned_shas": self.pinned_shas,
            "model_refs": (
                [
                    {
                        "model_id": r.model_id,
                        "version": r.version,
                        "artifact_uri": r.artifact_uri,
                    }
                    for r in self.model_refs
                ]
                if self.model_refs is not None
                else None
            ),
            "features_manifest_version": self.features_manifest_version,
            "chain_rpc_pins": self.chain_rpc_pins,
        }

    @classmethod
    def from_firestore_dict(cls, data: dict[str, object]) -> MinimalCandidateManifest:
        """Deserialise from a Firestore document dict."""
        score_raw = data.get("score_vector")
        score_dict: dict[str, object] = score_raw if isinstance(score_raw, dict) else {}
        score = GroupBMetrics(
            sharpe_ratio=float(score_dict.get("sharpe_ratio") or 0.0),
            calmar_ratio=float(score_dict.get("calmar_ratio") or 0.0),
            max_drawdown_pct=float(score_dict.get("max_drawdown_pct") or 0.0),
            win_rate=float(score_dict.get("win_rate") or 0.0),
            backtest_days=int(score_dict.get("backtest_days") or 0),
            total_return_pct=float(score_dict.get("total_return_pct") or 0.0),
        )

        model_refs_raw = data.get("model_refs")
        model_refs: list[ModelRef] | None = None
        if isinstance(model_refs_raw, list):
            model_refs = [
                ModelRef(
                    model_id=str(r.get("model_id") or ""),
                    version=str(r.get("version") or ""),
                    artifact_uri=str(r.get("artifact_uri") or ""),
                )
                for r in model_refs_raw
                if isinstance(r, dict)
            ]

        created_at_raw = data.get("created_at")
        created_at: datetime = created_at_raw if isinstance(created_at_raw, datetime) else datetime.now(timezone.utc)

        config_raw = data.get("config_json")
        config_json: dict[str, object] = config_raw if isinstance(config_raw, dict) else {}

        pinned_shas_raw = data.get("pinned_shas")
        pinned_shas: dict[str, str] | None = None
        if isinstance(pinned_shas_raw, dict):
            pinned_shas = {str(k): str(v) for k, v in pinned_shas_raw.items()}

        chain_rpc_pins_raw = data.get("chain_rpc_pins")
        chain_rpc_pins: dict[str, str] | None = None
        if isinstance(chain_rpc_pins_raw, dict):
            chain_rpc_pins = {str(k): str(v) for k, v in chain_rpc_pins_raw.items()}

        version_id_raw = data.get("version_id")
        version_id: str | None = str(version_id_raw) if version_id_raw is not None else None

        features_version_raw = data.get("features_manifest_version")
        features_manifest_version: str | None = str(features_version_raw) if features_version_raw is not None else None

        return cls(
            manifest_id=str(data.get("manifest_id") or make_manifest_id()),
            strategy_instance_id=str(data.get("strategy_instance_id") or ""),
            version_id=version_id,
            archetype=StrategyArchetype(str(data.get("archetype") or "")),
            config_json=config_json,
            score_vector=score,
            target_phase=StrategyMaturityPhase(str(data.get("target_phase") or "")),
            created_at=created_at,
            created_by=str(data.get("created_by") or ""),
            reason=str(data.get("reason") or ""),
            pinned_shas=pinned_shas,
            model_refs=model_refs,
            features_manifest_version=features_manifest_version,
            chain_rpc_pins=chain_rpc_pins,
        )
