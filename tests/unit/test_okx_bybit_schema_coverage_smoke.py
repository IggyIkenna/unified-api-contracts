"""Smoke test: OKX and Bybit schema coverage for Phase 6 endpoints.

Asserts mark_price_kline, index_price_kline and other Phase 6 endpoints
have resolvable schema classes in ENDPOINT_SCHEMA_MAP.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.registry.endpoints import ENDPOINT_SCHEMA_MAP, get_schema_class_for_endpoint

OKX_PHASE6_ENDPOINTS = [
    "mark_price_kline",
    "index_price_kline",
    "option_summary",
    "option_ticker",
    "funding_rate_history",
    "long_short_ratio",
    "open_interest",
    "open_interest_history",
]
BYBIT_PHASE6_ENDPOINTS = [
    "mark_price_kline",
    "index_price_kline",
    "funding_rate_history",
    "long_short_ratio",
    "insurance_fund",
]


@pytest.mark.smoke
@pytest.mark.unit
def test_okx_phase6_endpoints_have_resolvable_schemas() -> None:
    """Assert OKX Phase 6 endpoints have resolvable schema classes."""
    gaps: list[tuple[str, str]] = []
    for endpoint in OKX_PHASE6_ENDPOINTS:
        key = ("okx", endpoint)
        if key not in ENDPOINT_SCHEMA_MAP:
            continue
        cls = get_schema_class_for_endpoint("okx", endpoint)
        if cls is None:
            gaps.append((endpoint, ENDPOINT_SCHEMA_MAP[key]))
    assert not gaps, f"OKX schema gaps (schema class not found): {gaps}"


@pytest.mark.smoke
@pytest.mark.unit
def test_bybit_phase6_endpoints_have_resolvable_schemas() -> None:
    """Assert Bybit Phase 6 endpoints have resolvable schema classes."""
    gaps: list[tuple[str, str]] = []
    for endpoint in BYBIT_PHASE6_ENDPOINTS:
        key = ("bybit", endpoint)
        if key not in ENDPOINT_SCHEMA_MAP:
            continue
        cls = get_schema_class_for_endpoint("bybit", endpoint)
        if cls is None:
            gaps.append((endpoint, ENDPOINT_SCHEMA_MAP[key]))
    assert not gaps, f"Bybit schema gaps (schema class not found): {gaps}"


@pytest.mark.smoke
@pytest.mark.unit
def test_okx_all_endpoints_resolvable() -> None:
    """Report any OKX endpoint in ENDPOINT_SCHEMA_MAP without resolvable schema."""
    okx_keys = [(v, e) for (v, e) in ENDPOINT_SCHEMA_MAP if v == "okx"]
    gaps: list[tuple[str, str, str]] = []
    for venue, endpoint in okx_keys:
        schema_name = ENDPOINT_SCHEMA_MAP[(venue, endpoint)]
        cls = get_schema_class_for_endpoint(venue, endpoint)
        if cls is None:
            gaps.append((venue, endpoint, schema_name))
    assert not gaps, f"OKX schema gaps (schema class not found): {gaps}"


@pytest.mark.smoke
@pytest.mark.unit
def test_bybit_all_endpoints_resolvable() -> None:
    """Report any Bybit endpoint in ENDPOINT_SCHEMA_MAP without resolvable schema."""
    bybit_keys = [(v, e) for (v, e) in ENDPOINT_SCHEMA_MAP if v == "bybit"]
    gaps: list[tuple[str, str, str]] = []
    for venue, endpoint in bybit_keys:
        schema_name = ENDPOINT_SCHEMA_MAP[(venue, endpoint)]
        cls = get_schema_class_for_endpoint(venue, endpoint)
        if cls is None:
            gaps.append((venue, endpoint, schema_name))
    assert not gaps, f"Bybit schema gaps (schema class not found): {gaps}"
