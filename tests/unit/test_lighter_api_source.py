"""lighter_api source wiring (2026-07-18).

LIGHTER-ZKSYNC self-archives ohlcv_1m via its own REST /candles (mainnet.zkln.elliot.ai),
source=lighter_api. Fully wired as a batch-only cefi source so native rows get an HONEST
concrete BATCH_LIGHTER_API stamp instead of a fabricated batch_tardis (the bug) or a bare None.
"""

from __future__ import annotations

from unified_api_contracts.canonical.crosscutting._source_priority_data import (
    EMISSION_LATENCY_MS_BY_SOURCE,
    SOURCE_MODE_CAPABILITY,
    SOURCE_PRIORITY,
)
from unified_api_contracts.canonical.crosscutting.pipeline_mode import Mode, PipelineMode, pipeline_mode_for_source
from unified_api_contracts.registry.capability_declarations._cefi import CEFI_CAPABILITIES


def test_batch_lighter_api_member_exists() -> None:
    assert PipelineMode.BATCH_LIGHTER_API.value == "batch_lighter_api"


def test_source_aware_lighter_api_resolves_to_batch_lighter_api() -> None:
    assert pipeline_mode_for_source("lighter_api", Mode.BATCH) is PipelineMode.BATCH_LIGHTER_API


def test_lighter_api_is_batch_only() -> None:
    """Native /candles is batch-only; live capture is Tardis, so no LIVE/REPLAY member."""
    assert SOURCE_MODE_CAPABILITY["lighter_api"] == frozenset({Mode.BATCH})


def test_lighter_api_registered_in_cefi_ohlcv_1m_source_priority_last() -> None:
    sources = SOURCE_PRIORITY[("cefi", "ohlcv_1m")]
    assert sources[-1] == "lighter_api", "lighter_api appended last (not a new default)"
    assert sources[0] == "tardis", "source-blind priority[0] stays tardis for other cefi venues"


def test_lighter_source_capability_declared() -> None:
    """The closed-set requires a SourceCapability for every SOURCE_PRIORITY source."""
    lighter = [c for c in CEFI_CAPABILITIES if c.source == "lighter_api"]
    assert len(lighter) == 1, "exactly one lighter_api SourceCapability"
    cap = lighter[0]
    assert cap.supports_batch is True
    assert cap.supports_live is False
    assert cap.base_urls["mainnet"] == "https://mainnet.zkln.elliot.ai/api/v1"
    assert "candles" in cap.operations["market"]


def test_lighter_api_has_emission_latency() -> None:
    assert EMISSION_LATENCY_MS_BY_SOURCE["lighter_api"] == 1_000
