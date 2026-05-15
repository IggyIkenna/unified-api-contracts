"""Unit tests for MinimalCandidateManifest — Phase U1 May-23 promote workflow."""

from __future__ import annotations

from datetime import datetime

import pytest

from unified_api_contracts.internal.architecture_v2.enums import StrategyArchetype
from unified_api_contracts.internal.domain.strategy_service.candidate_manifest import (
    GroupBMetrics,
    MinimalCandidateManifest,
    ModelRef,
    make_manifest_id,
)
from unified_api_contracts.internal.domain.strategy_service.lifecycle import (
    StrategyMaturityPhase,
)


def _score() -> GroupBMetrics:
    return GroupBMetrics(
        sharpe_ratio=1.8,
        calmar_ratio=0.9,
        max_drawdown_pct=12.5,
        win_rate=0.62,
        backtest_days=365,
        total_return_pct=42.3,
    )


def _manifest(
    target_phase: StrategyMaturityPhase = StrategyMaturityPhase.PAPER_1D,
) -> MinimalCandidateManifest:
    return MinimalCandidateManifest(
        strategy_instance_id="strat_abc123",
        archetype=StrategyArchetype.CARRY_STAKED_BASIS,
        config_json={"threshold": 0.01},
        score_vector=_score(),
        target_phase=target_phase,
        created_by="ikenna",
        reason="Group B score exceeds cutover floor",
    )


def test_make_manifest_id_is_uuid4_string() -> None:
    mid = make_manifest_id()
    assert isinstance(mid, str)
    assert len(mid) == 36
    assert mid.count("-") == 4


def test_group_b_metrics_is_frozen() -> None:
    score = _score()
    with pytest.raises(Exception):
        score.sharpe_ratio = 0.0  # type: ignore[misc]


def test_model_ref_is_frozen() -> None:
    ref = ModelRef(model_id="m1", version="v2", artifact_uri="gs://bucket/model")
    with pytest.raises(Exception):
        ref.model_id = "m2"  # type: ignore[misc]


def test_valid_paper_1d_manifest() -> None:
    m = _manifest(StrategyMaturityPhase.PAPER_1D)
    assert m.strategy_instance_id == "strat_abc123"
    assert m.target_phase is StrategyMaturityPhase.PAPER_1D
    assert m.pinned_shas is None
    assert m.model_refs is None
    assert m.features_manifest_version is None
    assert m.chain_rpc_pins is None


def test_valid_live_early_manifest() -> None:
    m = _manifest(StrategyMaturityPhase.LIVE_EARLY)
    assert m.target_phase is StrategyMaturityPhase.LIVE_EARLY


def test_invalid_target_phase_raises() -> None:
    with pytest.raises(ValueError, match="target_phase must be PAPER_1D or LIVE_EARLY"):
        MinimalCandidateManifest(
            strategy_instance_id="strat_x",
            archetype=StrategyArchetype.CARRY_STAKED_BASIS,
            config_json={},
            score_vector=_score(),
            target_phase=StrategyMaturityPhase.LIVE_STABLE,
            created_by="ikenna",
            reason="reason",
        )


def test_empty_strategy_instance_id_raises() -> None:
    with pytest.raises(ValueError, match="strategy_instance_id is required"):
        MinimalCandidateManifest(
            strategy_instance_id="",
            archetype=StrategyArchetype.CARRY_STAKED_BASIS,
            config_json={},
            score_vector=_score(),
            target_phase=StrategyMaturityPhase.PAPER_1D,
            created_by="ikenna",
            reason="reason",
        )


def test_empty_created_by_raises() -> None:
    with pytest.raises(ValueError, match="created_by is required"):
        MinimalCandidateManifest(
            strategy_instance_id="strat_x",
            archetype=StrategyArchetype.CARRY_STAKED_BASIS,
            config_json={},
            score_vector=_score(),
            target_phase=StrategyMaturityPhase.PAPER_1D,
            created_by="",
            reason="reason",
        )


def test_to_firestore_dict_round_trip() -> None:
    m = _manifest()
    d = m.to_firestore_dict()
    assert d["strategy_instance_id"] == "strat_abc123"
    assert d["target_phase"] == StrategyMaturityPhase.PAPER_1D.value
    assert isinstance(d["score_vector"], dict)
    assert d["score_vector"]["sharpe_ratio"] == 1.8
    assert d["model_refs"] is None
    assert d["pinned_shas"] is None


def test_from_firestore_dict_round_trip() -> None:
    m = _manifest()
    d = m.to_firestore_dict()
    m2 = MinimalCandidateManifest.from_firestore_dict(d)
    assert m2.strategy_instance_id == m.strategy_instance_id
    assert m2.target_phase is m.target_phase
    assert m2.score_vector.sharpe_ratio == m.score_vector.sharpe_ratio
    assert m2.score_vector.backtest_days == m.score_vector.backtest_days
    assert m2.model_refs is None


def test_from_firestore_dict_with_model_refs() -> None:
    m = _manifest()
    d = m.to_firestore_dict()
    d["model_refs"] = [{"model_id": "mdl_1", "version": "v3", "artifact_uri": "gs://b/m"}]
    m2 = MinimalCandidateManifest.from_firestore_dict(d)
    assert m2.model_refs is not None
    assert len(m2.model_refs) == 1
    assert m2.model_refs[0].model_id == "mdl_1"


def test_from_firestore_dict_with_pinned_shas() -> None:
    m = _manifest()
    d = m.to_firestore_dict()
    d["pinned_shas"] = {"strategy-service": "abc123def456"}
    m2 = MinimalCandidateManifest.from_firestore_dict(d)
    assert m2.pinned_shas == {"strategy-service": "abc123def456"}


def test_manifest_id_generated_by_default() -> None:
    m1 = _manifest()
    m2 = _manifest()
    assert m1.manifest_id != m2.manifest_id


def test_version_id_defaults_to_none() -> None:
    m = _manifest()
    assert m.version_id is None


def test_to_firestore_dict_created_at_is_datetime() -> None:
    m = _manifest()
    d = m.to_firestore_dict()
    assert isinstance(d["created_at"], datetime)
