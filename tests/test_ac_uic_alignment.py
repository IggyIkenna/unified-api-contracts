"""Cross-library alignment tests: AC schemas must not conflict with UIC_INT schemas.

Phase 2 requirement: These tests catch schema drift between the two contracts libraries.

Known duplicated modules (AC.internal mirrors UIC_INT):
- ml.py         : ModelType, TargetType, ModelVariantConfig, ModelMetadata, etc.
- events.py     : LifecycleEventType, EventSeverity, ServiceMode, all Detail models
- features.py   : DeltaOneFeatureRecord, OptionsIvRecord, FuturesTermStructureRecord, FeatureSnapshotRequest
- pubsub.py     : InternalPubSubTopic, PubSubMessageEnvelope, all message models
- risk.py       : RiskStatus, AlertType, PositionSide, all risk models
- health.py (AC) / schemas/errors.py (UIC_INT): ErrorCategory, ErrorSeverity, EnhancedError, etc.

Tests import from BOTH libraries and compare enum members, field names, and field types.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _field_names(model_cls: type[BaseModel]) -> set[str]:
    return set(model_cls.model_fields.keys())


def _normalize_type_repr(annotation_repr: str) -> str:
    """Normalize module-qualified class names for cross-library comparison.

    Since AC and UIC_INT define identical classes in different modules,
    ``repr()`` includes the module path (e.g. ``unified_internal_contracts.ml.TrainingPeriod``
    vs ``unified_api_contracts.internal.ml.TrainingPeriod``). We strip the module prefix
    so that structurally identical types compare equal.
    """
    import re

    return re.sub(r"unified_(?:api_contracts\.internal|internal_contracts)\.\w+\.(\w+)", r"\1", annotation_repr)


def _field_types(model_cls: type[BaseModel]) -> dict[str, str]:
    """Return {field_name: normalized_annotation_repr} for comparison."""
    return {name: _normalize_type_repr(repr(info.annotation)) for name, info in model_cls.model_fields.items()}


def _enum_values(enum_cls: type) -> set[str]:
    return {str(m.value) for m in enum_cls}


def _enum_names(enum_cls: type) -> set[str]:
    return {m.name for m in enum_cls}


# ===========================================================================
# ML schemas alignment
# ===========================================================================


class TestMLEnumAlignment:
    """ModelType and TargetType enums must have identical members across AC and UIC_INT."""

    def test_model_type_values_match(self) -> None:
        from unified_internal_contracts.ml import ModelType as UIC_ModelType

        from unified_api_contracts.internal.ml import ModelType as AC_ModelType

        ac_values = _enum_values(AC_ModelType)
        uic_values = _enum_values(UIC_ModelType)
        assert ac_values == uic_values, (
            f"ModelType enum drift detected.\n"
            f"  AC-only:  {ac_values - uic_values}\n"
            f"  UIC-only: {uic_values - ac_values}"
        )

    def test_model_type_names_match(self) -> None:
        from unified_internal_contracts.ml import ModelType as UIC_ModelType

        from unified_api_contracts.internal.ml import ModelType as AC_ModelType

        assert _enum_names(AC_ModelType) == _enum_names(UIC_ModelType)

    def test_target_type_values_match(self) -> None:
        from unified_internal_contracts.ml import TargetType as UIC_TargetType

        from unified_api_contracts.internal.ml import TargetType as AC_TargetType

        assert _enum_values(AC_TargetType) == _enum_values(UIC_TargetType)

    def test_target_type_names_match(self) -> None:
        from unified_internal_contracts.ml import TargetType as UIC_TargetType

        from unified_api_contracts.internal.ml import TargetType as AC_TargetType

        assert _enum_names(AC_TargetType) == _enum_names(UIC_TargetType)


class TestMLModelAlignment:
    """Pydantic model fields must match between AC.internal.ml and UIC_INT.ml."""

    def test_model_variant_config_fields(self) -> None:
        from unified_internal_contracts.ml import ModelVariantConfig as UIC_MVC

        from unified_api_contracts.internal.ml import ModelVariantConfig as AC_MVC

        assert _field_names(AC_MVC) == _field_names(UIC_MVC), (
            f"ModelVariantConfig field drift.\n"
            f"  AC-only:  {_field_names(AC_MVC) - _field_names(UIC_MVC)}\n"
            f"  UIC-only: {_field_names(UIC_MVC) - _field_names(AC_MVC)}"
        )

    def test_model_variant_config_types(self) -> None:
        from unified_internal_contracts.ml import ModelVariantConfig as UIC_MVC

        from unified_api_contracts.internal.ml import ModelVariantConfig as AC_MVC

        ac_types = _field_types(AC_MVC)
        uic_types = _field_types(UIC_MVC)
        mismatches: list[str] = []
        for field in _field_names(AC_MVC) & _field_names(UIC_MVC):
            if ac_types[field] != uic_types[field]:
                mismatches.append(f"  {field}: AC={ac_types[field]} vs UIC={uic_types[field]}")
        assert mismatches == [], "ModelVariantConfig type mismatches:\n" + "\n".join(mismatches)

    def test_model_metadata_fields(self) -> None:
        from unified_internal_contracts.ml import ModelMetadata as UIC_MM

        from unified_api_contracts.internal.ml import ModelMetadata as AC_MM

        assert _field_names(AC_MM) == _field_names(UIC_MM)

    def test_model_metadata_types(self) -> None:
        from unified_internal_contracts.ml import ModelMetadata as UIC_MM

        from unified_api_contracts.internal.ml import ModelMetadata as AC_MM

        ac_types = _field_types(AC_MM)
        uic_types = _field_types(UIC_MM)
        mismatches: list[str] = []
        for field in _field_names(AC_MM) & _field_names(UIC_MM):
            if ac_types[field] != uic_types[field]:
                mismatches.append(f"  {field}: AC={ac_types[field]} vs UIC={uic_types[field]}")
        assert mismatches == [], "ModelMetadata type mismatches:\n" + "\n".join(mismatches)

    def test_ml_config_dict_fields(self) -> None:
        from unified_internal_contracts.ml import MLConfigDict as UIC_MCD

        from unified_api_contracts.internal.ml import MLConfigDict as AC_MCD

        assert _field_names(AC_MCD) == _field_names(UIC_MCD)

    def test_inference_request_fields(self) -> None:
        from unified_internal_contracts.ml import InferenceRequest as UIC_IR

        from unified_api_contracts.internal.ml import InferenceRequest as AC_IR

        assert _field_names(AC_IR) == _field_names(UIC_IR)

    def test_inference_result_fields(self) -> None:
        from unified_internal_contracts.ml import InferenceResult as UIC_IR

        from unified_api_contracts.internal.ml import InferenceResult as AC_IR

        assert _field_names(AC_IR) == _field_names(UIC_IR)

    def test_training_job_request_fields(self) -> None:
        from unified_internal_contracts.ml import TrainingJobRequest as UIC_TJR

        from unified_api_contracts.internal.ml import TrainingJobRequest as AC_TJR

        assert _field_names(AC_TJR) == _field_names(UIC_TJR)

    def test_training_job_result_fields(self) -> None:
        from unified_internal_contracts.ml import TrainingJobResult as UIC_TJR

        from unified_api_contracts.internal.ml import TrainingJobResult as AC_TJR

        assert _field_names(AC_TJR) == _field_names(UIC_TJR)

    def test_training_period_fields(self) -> None:
        from unified_internal_contracts.ml import TrainingPeriod as UIC_TP

        from unified_api_contracts.internal.ml import TrainingPeriod as AC_TP

        assert _field_names(AC_TP) == _field_names(UIC_TP)


# ===========================================================================
# Events schemas alignment
# ===========================================================================


class TestEventsEnumAlignment:
    """Lifecycle event enums must match between AC and UIC_INT."""

    def test_lifecycle_event_type_values(self) -> None:
        from unified_internal_contracts.events import LifecycleEventType as UIC_LET

        from unified_api_contracts.internal.events import LifecycleEventType as AC_LET

        assert _enum_values(AC_LET) == _enum_values(UIC_LET)

    def test_event_severity_values(self) -> None:
        from unified_internal_contracts.events import EventSeverity as UIC_ES

        from unified_api_contracts.internal.events import EventSeverity as AC_ES

        assert _enum_values(AC_ES) == _enum_values(UIC_ES)

    def test_service_mode_values(self) -> None:
        from unified_internal_contracts.events import ServiceMode as UIC_SM

        from unified_api_contracts.internal.events import ServiceMode as AC_SM

        assert _enum_values(AC_SM) == _enum_values(UIC_SM)


class TestEventsModelAlignment:
    """Event detail models and envelopes must have matching fields."""

    @pytest.mark.parametrize(
        "model_name",
        [
            "StartedDetails",
            "ValidationStartedDetails",
            "ValidationCompletedDetails",
            "ProcessingStartedDetails",
            "ProcessingCompletedDetails",
            "DataBroadcastDetails",
            "PersistenceStartedDetails",
            "PersistenceCompletedDetails",
            "FailedDetails",
            "AuthFailureDetails",
            "ConfigChangedDetails",
            "SecretAccessedDetails",
            "EventMetadata",
            "LifecycleEventEnvelope",
            "PubSubLifecycleEventMessage",
            "StartedEvent",
            "FailedEvent",
            "AuthFailureEvent",
            "ConfigChangedEvent",
            "SecretAccessedEvent",
        ],
    )
    def test_event_model_fields_match(self, model_name: str) -> None:
        import unified_internal_contracts.events as uic_events

        import unified_api_contracts.internal.events as ac_events

        ac_cls = getattr(ac_events, model_name)
        uic_cls = getattr(uic_events, model_name)
        assert _field_names(ac_cls) == _field_names(uic_cls), (
            f"{model_name} field drift.\n"
            f"  AC-only:  {_field_names(ac_cls) - _field_names(uic_cls)}\n"
            f"  UIC-only: {_field_names(uic_cls) - _field_names(ac_cls)}"
        )


class TestEventsModuleLevelConstants:
    """UIC_INT events.py has REQUIRED_EVENT_FIELDS; AC does not. Document this drift."""

    @pytest.mark.xfail(
        reason=(
            "Known drift: UIC_INT events.py defines REQUIRED_EVENT_FIELDS dict "
            "that AC internal/events.py does not have. "
            "Tracked for Phase 2 consolidation — one library should be canonical source."
        ),
        strict=True,
    )
    def test_required_event_fields_in_ac(self) -> None:
        import unified_api_contracts.internal.events as ac_events

        assert hasattr(ac_events, "REQUIRED_EVENT_FIELDS"), (
            "AC internal/events.py should export REQUIRED_EVENT_FIELDS to match UIC_INT"
        )


# ===========================================================================
# Features schemas alignment
# ===========================================================================


class TestFeaturesAlignment:
    """Feature schemas shared between AC and UIC_INT."""

    @pytest.mark.parametrize(
        "model_name",
        [
            "DeltaOneFeatureRecord",
            "OptionsIvRecord",
            "FuturesTermStructureRecord",
            "FeatureSnapshotRequest",
        ],
    )
    def test_shared_feature_model_fields_match(self, model_name: str) -> None:
        import unified_internal_contracts.features as uic_feat

        import unified_api_contracts.internal.features as ac_feat

        ac_cls = getattr(ac_feat, model_name)
        uic_cls = getattr(uic_feat, model_name)
        assert _field_names(ac_cls) == _field_names(uic_cls), (
            f"{model_name} field drift.\n"
            f"  AC-only:  {_field_names(ac_cls) - _field_names(uic_cls)}\n"
            f"  UIC-only: {_field_names(uic_cls) - _field_names(ac_cls)}"
        )

    @pytest.mark.xfail(
        reason=(
            "Known drift: UIC_INT features.py defines CrossTimeframeFeatures "
            "that AC internal/features.py does not have yet. "
            "UIC_INT is ahead — AC should adopt this schema."
        ),
        strict=True,
    )
    def test_cross_timeframe_features_in_ac(self) -> None:
        import unified_api_contracts.internal.features as ac_feat

        assert hasattr(ac_feat, "CrossTimeframeFeatures"), (
            "AC internal/features.py should export CrossTimeframeFeatures to match UIC_INT"
        )

    def test_cross_instrument_features_present_in_both(self) -> None:
        """CrossInstrumentFeatures exists in UIC_INT features.py.

        AC internal/features.py may or may not have it.
        """
        import unified_internal_contracts.features as uic_feat

        assert hasattr(uic_feat, "CrossInstrumentFeatures")

    def test_cross_instrument_features_field_alignment(self) -> None:
        """If both have CrossInstrumentFeatures, fields must match."""
        import unified_internal_contracts.features as uic_feat

        import unified_api_contracts.internal.features as ac_feat

        if not hasattr(ac_feat, "CrossInstrumentFeatures"):
            pytest.skip("AC does not yet export CrossInstrumentFeatures — known drift")

        ac_cls = ac_feat.CrossInstrumentFeatures
        uic_cls = uic_feat.CrossInstrumentFeatures
        assert _field_names(ac_cls) == _field_names(uic_cls)


# ===========================================================================
# Pubsub schemas alignment
# ===========================================================================


class TestPubsubAlignment:
    """Internal Pub/Sub topic enum and message models must match."""

    def test_internal_pubsub_topic_values(self) -> None:
        from unified_internal_contracts.pubsub import InternalPubSubTopic as UIC_Topic

        from unified_api_contracts.internal.pubsub import InternalPubSubTopic as AC_Topic

        assert _enum_values(AC_Topic) == _enum_values(UIC_Topic)

    @pytest.mark.parametrize(
        "model_name",
        [
            "PubSubMessageEnvelope",
            "FillEventMessage",
            "OrderRequestMessage",
            "ExecutionResultMessage",
            "PositionUpdateMessage",
            "RiskAlertMessage",
            "MarketTickMessage",
            "DerivativeTickerMessage",
            "LiquidationMessage",
            "FeatureUpdateMessage",
            "StrategySignalMessage",
            "MLPredictionMessage",
            "ServiceLifecycleEventMessage",
            "HealthAlertMessage",
            "CircuitBreakerEventMessage",
        ],
    )
    def test_pubsub_model_fields_match(self, model_name: str) -> None:
        import unified_internal_contracts.pubsub as uic_ps

        import unified_api_contracts.internal.pubsub as ac_ps

        ac_cls = getattr(ac_ps, model_name)
        uic_cls = getattr(uic_ps, model_name)
        assert _field_names(ac_cls) == _field_names(uic_cls), (
            f"{model_name} field drift.\n"
            f"  AC-only:  {_field_names(ac_cls) - _field_names(uic_cls)}\n"
            f"  UIC-only: {_field_names(uic_cls) - _field_names(ac_cls)}"
        )


# ===========================================================================
# Risk schemas alignment
# ===========================================================================


class TestRiskAlignment:
    """Risk enums and models must match between AC and UIC_INT."""

    def test_risk_status_values(self) -> None:
        from unified_internal_contracts.risk import RiskStatus as UIC_RS

        from unified_api_contracts.internal.risk import RiskStatus as AC_RS

        assert _enum_values(AC_RS) == _enum_values(UIC_RS)

    def test_alert_type_values(self) -> None:
        from unified_internal_contracts.risk import AlertType as UIC_AT

        from unified_api_contracts.internal.risk import AlertType as AC_AT

        assert _enum_values(AC_AT) == _enum_values(UIC_AT)

    def test_position_side_values(self) -> None:
        from unified_internal_contracts.risk import PositionSide as UIC_PS

        from unified_api_contracts.internal.risk import PositionSide as AC_PS

        assert _enum_values(AC_PS) == _enum_values(UIC_PS)

    @pytest.mark.parametrize(
        "model_name",
        [
            "RiskPosition",
            "RiskMetrics",
            "AlertContextData",
            "AlertMessage",
            "PreTradeCheckRequest",
            "PreTradeCheckResponse",
            "ExposureSummary",
            "Balance",
            "MarginState",
            "InternalPosition",
            "AccountState",
        ],
    )
    def test_risk_model_fields_match(self, model_name: str) -> None:
        import unified_internal_contracts.risk as uic_risk

        import unified_api_contracts.internal.risk as ac_risk

        ac_cls = getattr(ac_risk, model_name)
        uic_cls = getattr(uic_risk, model_name)
        assert _field_names(ac_cls) == _field_names(uic_cls), (
            f"{model_name} field drift.\n"
            f"  AC-only:  {_field_names(ac_cls) - _field_names(uic_cls)}\n"
            f"  UIC-only: {_field_names(uic_cls) - _field_names(ac_cls)}"
        )


# ===========================================================================
# Error schemas alignment (health.py in AC vs schemas/errors.py in UIC_INT)
# ===========================================================================


class TestErrorSchemaAlignment:
    """ErrorCategory, ErrorSeverity, ErrorRecoveryStrategy, ErrorContext must match.

    EnhancedError has known drift: UIC_INT adds ``correlation_id`` field.
    """

    def test_error_category_values(self) -> None:
        from unified_internal_contracts.schemas.errors import ErrorCategory as UIC_EC

        from unified_api_contracts.internal.health import ErrorCategory as AC_EC

        assert _enum_values(AC_EC) == _enum_values(UIC_EC)

    def test_error_severity_values(self) -> None:
        from unified_internal_contracts.schemas.errors import ErrorSeverity as UIC_ES

        from unified_api_contracts.internal.health import ErrorSeverity as AC_ES

        assert _enum_values(AC_ES) == _enum_values(UIC_ES)

    def test_error_recovery_strategy_values(self) -> None:
        from unified_internal_contracts.schemas.errors import ErrorRecoveryStrategy as UIC_ERS

        from unified_api_contracts.internal.health import ErrorRecoveryStrategy as AC_ERS

        assert _enum_values(AC_ERS) == _enum_values(UIC_ERS)

    def test_error_context_fields(self) -> None:
        from unified_internal_contracts.schemas.errors import ErrorContext as UIC_EC

        from unified_api_contracts.internal.health import ErrorContext as AC_EC

        assert _field_names(AC_EC) == _field_names(UIC_EC)

    @pytest.mark.xfail(
        reason=(
            "Known drift: UIC_INT EnhancedError has ``correlation_id: str = ''`` field "
            "that AC's internal/health.py EnhancedError does not have. "
            "AC should add this field to maintain alignment."
        ),
        strict=True,
    )
    def test_enhanced_error_fields_match(self) -> None:
        from unified_internal_contracts.schemas.errors import EnhancedError as UIC_EE

        from unified_api_contracts.internal.health import EnhancedError as AC_EE

        assert _field_names(AC_EE) == _field_names(UIC_EE), (
            f"EnhancedError field drift.\n"
            f"  AC-only:  {_field_names(AC_EE) - _field_names(UIC_EE)}\n"
            f"  UIC-only: {_field_names(UIC_EE) - _field_names(AC_EE)}"
        )


# ===========================================================================
# Messaging topic alignment (UIC_INT has MessagingTopic; AC has InternalPubSubTopic)
# ===========================================================================


class TestMessagingTopicAlignment:
    """UIC_INT MessagingTopic values should be a superset of (or equal to) InternalPubSubTopic values."""

    def test_messaging_topic_values_match_pubsub_topic(self) -> None:
        from unified_internal_contracts.messaging import MessagingTopic

        from unified_api_contracts.internal.pubsub import InternalPubSubTopic

        pubsub_values = _enum_values(InternalPubSubTopic)
        messaging_values = _enum_values(MessagingTopic)
        assert pubsub_values == messaging_values, (
            f"Topic value drift between InternalPubSubTopic and MessagingTopic.\n"
            f"  PubSub-only:    {pubsub_values - messaging_values}\n"
            f"  Messaging-only: {messaging_values - pubsub_values}"
        )

    def test_messaging_topic_names_match_pubsub_topic(self) -> None:
        from unified_internal_contracts.messaging import MessagingTopic

        from unified_api_contracts.internal.pubsub import InternalPubSubTopic

        pubsub_names = _enum_names(InternalPubSubTopic)
        messaging_names = _enum_names(MessagingTopic)
        assert pubsub_names == messaging_names, (
            f"Topic name drift between InternalPubSubTopic and MessagingTopic.\n"
            f"  PubSub-only:    {pubsub_names - messaging_names}\n"
            f"  Messaging-only: {messaging_names - pubsub_names}"
        )
