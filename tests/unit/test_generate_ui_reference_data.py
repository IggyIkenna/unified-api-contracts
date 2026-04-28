"""Tests for generate_ui_reference_data.py — one test per registry category."""

from __future__ import annotations

import json

# Import the generator directly
import sys
from pathlib import Path

import pytest

_repo_root = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(_repo_root / "scripts"))

from generate_ui_reference_data import generate  # noqa: E402


@pytest.fixture(scope="module")
def reference_data() -> dict:
    """Generate reference data once for all tests."""
    return generate()


class TestMeta:
    def test_meta_version_populated(self, reference_data: dict) -> None:
        assert reference_data["_meta"]["version"] != "unknown"

    def test_meta_registry_count(self, reference_data: dict) -> None:
        assert reference_data["_meta"]["registry_count"] == 15

    def test_all_registries_present(self, reference_data: dict) -> None:
        expected = {
            "venue_error_map",
            "instruction_constraints",
            "market_data_categories",
            "venue_rate_limits",
            "risk_taxonomy",
            "defi_protocol_registry",
            "chain_rpc_templates",
            "subgraph_ids",
            "capability_declarations",
            "venue_capabilities",
            "data_pipeline_config",
            "deployment_enums",
            "error_classifications",
            "tradfi_symbology",
            "representative_instrument_sample",
        }
        actual = set(reference_data.keys()) - {"_meta"}
        assert actual == expected


class TestVenueErrorMap:
    def test_not_empty(self, reference_data: dict) -> None:
        assert reference_data["venue_error_map"]["venue_count"] > 0

    def test_entries_present(self, reference_data: dict) -> None:
        entries = reference_data["venue_error_map"]["entries"]
        assert len(entries) > 0

    def test_entry_schema(self, reference_data: dict) -> None:
        entries = reference_data["venue_error_map"]["entries"]
        first_venue = next(iter(entries))
        first_error = entries[first_venue][0]
        assert "venue" in first_error
        assert "error_code" in first_error
        assert "retry_safe" in first_error
        assert "action" in first_error

    def test_version_populated(self, reference_data: dict) -> None:
        assert reference_data["venue_error_map"]["version"] != "unknown"


class TestInstructionConstraints:
    def test_not_empty(self, reference_data: dict) -> None:
        assert reference_data["instruction_constraints"]["entry_count"] > 0

    def test_entry_schema(self, reference_data: dict) -> None:
        entries = reference_data["instruction_constraints"]["entries"]
        first_key = next(iter(entries))
        constraint = entries[first_key]
        assert "order_types" in constraint
        assert "instrument_types" in constraint
        assert "requires_price" in constraint


class TestMarketDataCategories:
    def test_data_types_present(self, reference_data: dict) -> None:
        entries = reference_data["market_data_categories"]["entries"]
        assert len(entries["data_types_by_asset_group"]) > 0

    def test_timeframes_present(self, reference_data: dict) -> None:
        entries = reference_data["market_data_categories"]["entries"]
        assert len(entries["timeframes"]) > 0

    def test_venues_present(self, reference_data: dict) -> None:
        entries = reference_data["market_data_categories"]["entries"]
        assert len(entries["venues_by_asset_group"]) > 0


class TestVenueRateLimits:
    def test_not_empty(self, reference_data: dict) -> None:
        assert reference_data["venue_rate_limits"]["venue_count"] > 0

    def test_entry_schema(self, reference_data: dict) -> None:
        entries = reference_data["venue_rate_limits"]["entries"]
        first_venue = next(iter(entries))
        limit = entries[first_venue]
        assert "venue" in limit
        assert "notes" in limit


class TestRiskTaxonomy:
    def test_risk_types_present(self, reference_data: dict) -> None:
        entries = reference_data["risk_taxonomy"]["entries"]
        assert len(entries["risk_types"]) > 0

    def test_risk_categories_present(self, reference_data: dict) -> None:
        entries = reference_data["risk_taxonomy"]["entries"]
        assert len(entries["risk_categories"]) > 0

    def test_category_mapping_covers_all_types(self, reference_data: dict) -> None:
        entries = reference_data["risk_taxonomy"]["entries"]
        all_mapped = set()
        for types in entries["category_mapping"].values():
            all_mapped.update(types)
        all_types = {rt["value"] for rt in entries["risk_types"]}
        assert all_mapped == all_types


class TestDefiProtocolRegistry:
    def test_protocols_present(self, reference_data: dict) -> None:
        entries = reference_data["defi_protocol_registry"]["entries"]
        assert len(entries["protocols"]) > 0

    def test_venue_to_protocol_present(self, reference_data: dict) -> None:
        entries = reference_data["defi_protocol_registry"]["entries"]
        assert len(entries["venue_to_protocol"]) > 0


class TestChainRpcTemplates:
    def test_not_empty(self, reference_data: dict) -> None:
        assert reference_data["chain_rpc_templates"]["chain_count"] > 0

    def test_entries_have_templates(self, reference_data: dict) -> None:
        entries = reference_data["chain_rpc_templates"]["entries"]
        for _chain_id, template in entries.items():
            assert template is not None


class TestSubgraphIds:
    def test_not_empty(self, reference_data: dict) -> None:
        assert reference_data["subgraph_ids"]["protocol_count"] > 0

    def test_nested_chain_structure(self, reference_data: dict) -> None:
        entries = reference_data["subgraph_ids"]["entries"]
        for _protocol, chains in entries.items():
            assert isinstance(chains, dict)
            for _chain, sid in chains.items():
                assert isinstance(sid, str)


class TestCapabilityDeclarations:
    def test_not_empty(self, reference_data: dict) -> None:
        assert reference_data["capability_declarations"]["entry_count"] > 0

    def test_entry_schema(self, reference_data: dict) -> None:
        entries = reference_data["capability_declarations"]["entries"]
        first = entries[0]
        assert "source" in first
        assert "domains" in first
        assert "operations" in first


class TestVenueCapabilities:
    def test_not_empty(self, reference_data: dict) -> None:
        entries = reference_data["venue_capabilities"]["entries"]
        assert len(entries) > 0

    def test_error_code_count(self, reference_data: dict) -> None:
        entries = reference_data["venue_capabilities"]["entries"]
        first_venue = next(iter(entries))
        assert "error_code_count" in entries[first_venue]


class TestErrorClassifications:
    def test_not_empty(self, reference_data: dict) -> None:
        entries = reference_data["error_classifications"]["entries"]
        assert len(entries) > 0


class TestTradfiSymbology:
    def test_instruments_present(self, reference_data: dict) -> None:
        entries = reference_data["tradfi_symbology"]["entries"]
        assert entries["instrument_count"] > 0

    def test_instrument_schema(self, reference_data: dict) -> None:
        entries = reference_data["tradfi_symbology"]["entries"]
        inst = entries["instruments"][0]
        assert "symbol" in inst
        assert "instrument_type" in inst
        assert "venue" in inst


class TestRepresentativeInstrumentSample:
    def test_cefi_base_assets(self, reference_data: dict) -> None:
        entries = reference_data["representative_instrument_sample"]["entries"]
        assert len(entries["cefi_base_assets"]) >= 3

    def test_tradfi_equities(self, reference_data: dict) -> None:
        entries = reference_data["representative_instrument_sample"]["entries"]
        assert len(entries["tradfi_equities"]) > 0

    def test_defi_instruments(self, reference_data: dict) -> None:
        entries = reference_data["representative_instrument_sample"]["entries"]
        assert len(entries["defi_instruments"]) > 0

    def test_sports_leagues(self, reference_data: dict) -> None:
        entries = reference_data["representative_instrument_sample"]["entries"]
        assert len(entries["sports_leagues"]) > 0

    def test_options_chain_config(self, reference_data: dict) -> None:
        entries = reference_data["representative_instrument_sample"]["entries"]
        config = entries["options_chain_config"]
        assert "atm_price_usd" in config
        assert "strike_interval_usd" in config


class TestDeterminism:
    def test_output_is_deterministic(self) -> None:
        """Two calls must produce identical JSON."""
        data1 = generate()
        data2 = generate()
        json1 = json.dumps(data1, sort_keys=False, default=str)
        json2 = json.dumps(data2, sort_keys=False, default=str)
        assert json1 == json2
