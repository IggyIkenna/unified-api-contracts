"""Canonical feature domain — schemas + DAG SSOT + coverage registry."""

from .models import CanonicalFeatureRecord, FeatureMetadata
from .registry import (
    EXPECTED_FEATURE_GROUPS_BY_SERVICE,
    FEATURE_COVERAGE_START,
    get_feature_coverage_start,
    is_known_feature_group,
    list_services,
)
from .required_inputs import (
    FEATURE_REQUIRED_INPUTS,
    InputReq,
    get_required_inputs,
    has_required_inputs,
    list_feature_groups,
    validate_required_inputs,
)

__all__ = [
    "EXPECTED_FEATURE_GROUPS_BY_SERVICE",
    "FEATURE_COVERAGE_START",
    "FEATURE_REQUIRED_INPUTS",
    "CanonicalFeatureRecord",
    "FeatureMetadata",
    "InputReq",
    "get_feature_coverage_start",
    "get_required_inputs",
    "has_required_inputs",
    "is_known_feature_group",
    "list_feature_groups",
    "list_services",
    "validate_required_inputs",
]
