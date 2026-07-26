"""Unit tests for the DeFi completeness-oracle ``CompletenessProbe`` schema.

Schema-only landing (P0 step, ``/codex/02-data/defi-completeness-oracle.md``
§9) — no probe implementations exist yet. These tests pin the §1 semantic
table (complete / gap / over_enumerated / undefined / probe_failed) as
direct :class:`CompletenessProbe` constructions, plus the
``factory_address_by_chain`` population on ``_ProtocolCapability`` for the
top-10 DEX protocols.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from unified_api_contracts.canonical.crosscutting.honest_coverage import (
    CompletenessProbe,
    CompletenessProbeKind,
    CompletenessProbeStatus,
)
from unified_api_contracts.registry.capability_declarations import PROTOCOL_CAPABILITIES

_AS_OF = date(2026, 7, 26)
_PROBE_TS = datetime(2026, 7, 26, 12, 0, tzinfo=UTC)


def _probe(**overrides: object) -> CompletenessProbe:
    base: dict[str, object] = {
        "protocol": "uniswap_v3",
        "chain": "ETHEREUM",
        "as_of_date": _AS_OF,
        "probe_block": 20_000_000,
        "probe_ts_utc": _PROBE_TS,
        "probe_kind": CompletenessProbeKind.DEX_FACTORY_RPC_TIER_B,
        "probe_source": "0x1F98431c8aD98523631AE4a59f267346ea31F984",
        "expected_count": 0,
        "enumerated_count": 0,
        "missing_delta": 0,
        "stray_delta": 0,
        "completeness_pct": None,
        "status": CompletenessProbeStatus.UNDEFINED,
        "error_reason": None,
        "creation_blocks": None,
    }
    base.update(overrides)
    return CompletenessProbe(**base)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# §1 semantic table
# ---------------------------------------------------------------------------


def test_enumerated_and_expected_both_zero_is_undefined() -> None:
    probe = _probe(expected_count=0, enumerated_count=0, missing_delta=0, stray_delta=0, completeness_pct=None)
    assert probe.status == CompletenessProbeStatus.UNDEFINED
    assert probe.completeness_pct is None


def test_enumerated_equals_expected_above_zero_is_complete() -> None:
    probe = _probe(
        expected_count=100,
        enumerated_count=100,
        missing_delta=0,
        stray_delta=0,
        completeness_pct=100.0,
        status=CompletenessProbeStatus.COMPLETE,
    )
    assert probe.status == CompletenessProbeStatus.COMPLETE
    assert probe.completeness_pct == 100.0
    assert probe.missing_delta == 0
    assert probe.stray_delta == 0


def test_enumerated_below_expected_is_gap_with_named_delta() -> None:
    probe = _probe(
        expected_count=100,
        enumerated_count=80,
        missing_delta=20,
        stray_delta=0,
        completeness_pct=80.0,
        status=CompletenessProbeStatus.GAP,
    )
    assert probe.status == CompletenessProbeStatus.GAP
    assert probe.missing_delta == 20
    assert probe.stray_delta == 0
    assert probe.completeness_pct == 80.0


def test_enumerated_above_expected_is_over_enumerated_with_stray_delta() -> None:
    probe = _probe(
        expected_count=100,
        enumerated_count=105,
        missing_delta=0,
        stray_delta=5,
        completeness_pct=105.0,
        status=CompletenessProbeStatus.OVER_ENUMERATED,
    )
    assert probe.status == CompletenessProbeStatus.OVER_ENUMERATED
    assert probe.stray_delta == 5
    assert probe.missing_delta == 0


def test_probe_failed_never_reports_100_pct() -> None:
    probe = _probe(
        expected_count=0,
        enumerated_count=0,
        missing_delta=0,
        stray_delta=0,
        completeness_pct=None,
        status=CompletenessProbeStatus.PROBE_FAILED,
        error_reason="subgraph_indexing_behind",
    )
    assert probe.status == CompletenessProbeStatus.PROBE_FAILED
    assert probe.completeness_pct is None
    assert probe.error_reason == "subgraph_indexing_behind"


def test_probe_is_immutable() -> None:
    probe = _probe()
    try:
        probe.expected_count = 999  # type: ignore[misc]
    except (AttributeError, TypeError):
        pass
    else:
        raise AssertionError("CompletenessProbe must be frozen")


def test_creation_blocks_optional_and_defaults_none() -> None:
    probe = _probe()
    assert probe.creation_blocks is None

    with_blocks = _probe(creation_blocks={"0xpool1": 12_345_678})
    assert with_blocks.creation_blocks == {"0xpool1": 12_345_678}


def test_all_probe_kind_members_present() -> None:
    values = {member.value for member in CompletenessProbeKind}
    assert values == {
        "dex_factory_subgraph_tierA",
        "lending_registry_subgraph_tierA",
        "perps_markets_api_tierA",
        "yield_registry_tierA",
        "dex_factory_rpc_tierB",
        "lending_registry_rpc_tierB",
        "perps_markets_rpc_tierB",
    }


def test_all_probe_status_members_present() -> None:
    values = {member.value for member in CompletenessProbeStatus}
    assert values == {"complete", "gap", "over_enumerated", "undefined", "probe_failed"}


# ---------------------------------------------------------------------------
# factory_address_by_chain — top-10 DEX protocols
# ---------------------------------------------------------------------------

_TOP_10_DEX_PROTOCOLS = (
    "uniswap_v2",
    "uniswap_v3",
    "uniswap_v4",
    "sushiswap_v3",
    "balancer",
    "curve",
    "pancakeswap_v3",
    "aerodrome_v3",
    "velodrome_v2",
    "camelot_v3",
)


def test_top_10_dex_protocols_have_nonempty_factory_address_by_chain() -> None:
    for protocol in _TOP_10_DEX_PROTOCOLS:
        capability = PROTOCOL_CAPABILITIES[protocol]
        assert capability.factory_address_by_chain, f"{protocol} has an empty factory_address_by_chain"


def test_factory_addresses_are_checksum_shaped_hex() -> None:
    for protocol in _TOP_10_DEX_PROTOCOLS:
        for chain, address in PROTOCOL_CAPABILITIES[protocol].factory_address_by_chain.items():
            assert address.startswith("0x"), f"{protocol}/{chain} address missing 0x prefix"
            assert len(address) == 42, f"{protocol}/{chain} address is not 20 bytes: {address}"


def test_uniswap_v3_factory_address_same_across_all_declared_chains() -> None:
    addresses = set(PROTOCOL_CAPABILITIES["uniswap_v3"].factory_address_by_chain.values())
    assert addresses == {"0x1F98431c8aD98523631AE4a59f267346ea31F984"}


def test_factory_address_by_chain_default_empty_for_undeclared_protocol() -> None:
    assert PROTOCOL_CAPABILITIES["sushiswap"].factory_address_by_chain == {}
    assert PROTOCOL_CAPABILITIES["trader_joe_v2"].factory_address_by_chain == {}


def test_gmx_not_present_removed_2026_07_25() -> None:
    assert "gmx" not in PROTOCOL_CAPABILITIES
