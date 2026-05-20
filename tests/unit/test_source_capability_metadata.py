"""Tests for SourceCapability 4-field metadata promotion (Phase 1).

Verifies:
- Roundtrip: new fields serialize/deserialize correctly
- Backwards compat: existing declarations without new fields still validate
- Validator: coverage_start rejects empty-string keys
- Kind enum: invalid kind raises ValidationError
"""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from unified_api_contracts.registry.capability import SourceCapability


def _minimal() -> dict[str, object]:
    return {
        "source": "test_venue",
        "domains": ["market"],
        "crosscutting": ["errors"],
    }


class TestRoundtrip:
    def test_all_four_fields_populated(self) -> None:
        cap = SourceCapability(
            **_minimal(),
            chain="starknet",
            kind="perp_dex",
            mandatory_user_agent="odum-group-unified-trading/extended-mtds",
            coverage_start={"candles": date(2024, 7, 26), "funding_rates": date(2025, 7, 18)},
        )
        assert cap.chain == "starknet"
        assert cap.kind == "perp_dex"
        assert cap.mandatory_user_agent == "odum-group-unified-trading/extended-mtds"
        assert cap.coverage_start == {
            "candles": date(2024, 7, 26),
            "funding_rates": date(2025, 7, 18),
        }

    def test_json_roundtrip(self) -> None:
        cap = SourceCapability(
            **_minimal(),
            chain="ethereum",
            kind="lending_protocol",
            coverage_start={"candles": date(2020, 1, 1)},
        )
        data = cap.model_dump()
        restored = SourceCapability(**data)
        assert restored.chain == "ethereum"
        assert restored.kind == "lending_protocol"
        assert restored.coverage_start == {"candles": date(2020, 1, 1)}

    def test_all_kind_values_are_valid(self) -> None:
        valid_kinds = [
            "perp_dex",
            "spot_dex",
            "perp_cex",
            "spot_cex",
            "options_cex",
            "options_dex",
            "prediction_dex",
            "sports_book",
            "lending_protocol",
            "staking_protocol",
            "amm_dex",
            "vault_protocol",
        ]
        for k in valid_kinds:
            cap = SourceCapability(**_minimal(), kind=k)
            assert cap.kind == k


class TestBackwardsCompat:
    def test_legacy_declaration_without_new_fields_validates(self) -> None:
        """Old SourceCapability declarations without the 4 new fields must not break."""
        cap = SourceCapability(
            source="binance",
            domains=["market", "execution"],
            crosscutting=["errors", "rate_limits"],
            supports_live=True,
            supports_batch=True,
        )
        assert cap.chain is None
        assert cap.kind is None
        assert cap.mandatory_user_agent is None
        assert cap.coverage_start is None

    def test_none_defaults_for_all_new_fields(self) -> None:
        cap = SourceCapability(**_minimal())
        assert cap.chain is None
        assert cap.kind is None
        assert cap.mandatory_user_agent is None
        assert cap.coverage_start is None


class TestValidators:
    def test_coverage_start_empty_key_raises(self) -> None:
        with pytest.raises(ValidationError):
            SourceCapability(
                **_minimal(),
                coverage_start={"": date(2020, 1, 1)},
            )

    def test_coverage_start_valid_keys_pass(self) -> None:
        cap = SourceCapability(
            **_minimal(),
            coverage_start={"candles": date(2020, 1, 1), "trades": date(2019, 6, 1)},
        )
        assert len(cap.coverage_start) == 2  # type: ignore[arg-type]

    def test_invalid_kind_raises(self) -> None:
        with pytest.raises(ValidationError):
            SourceCapability(**_minimal(), kind="invalid_kind_xyz")

    def test_chain_is_freeform_str(self) -> None:
        """chain is not an enum — arbitrary strings must be accepted."""
        cap = SourceCapability(**_minimal(), chain="some-new-chain-2027")
        assert cap.chain == "some-new-chain-2027"


class TestImportedRegistryDeclarations:
    """Smoke test: existing registered declarations still validate after schema change."""

    def test_cefi_capabilities_all_validate(self) -> None:
        from unified_api_contracts.registry.capability_declarations._cefi import (
            CEFI_CAPABILITIES,
        )

        assert len(CEFI_CAPABILITIES) > 0
        for cap in CEFI_CAPABILITIES:
            assert isinstance(cap, SourceCapability)

    def test_defi_capabilities_all_validate(self) -> None:
        from unified_api_contracts.registry.capability_declarations._defi_source_capabilities import (
            DEFI_CAPABILITIES,
        )

        assert len(DEFI_CAPABILITIES) > 0
        for cap in DEFI_CAPABILITIES:
            assert isinstance(cap, SourceCapability)

    def test_tradfi_capabilities_all_validate(self) -> None:
        from unified_api_contracts.registry.capability_declarations._tradfi import (
            TRADFI_CAPABILITIES,
        )

        assert len(TRADFI_CAPABILITIES) > 0
        for cap in TRADFI_CAPABILITIES:
            assert isinstance(cap, SourceCapability)

    def test_sports_capabilities_all_validate(self) -> None:
        from unified_api_contracts.registry.capability_declarations._sports import (
            SPORTS_CAPABILITIES,
        )

        assert len(SPORTS_CAPABILITIES) > 0
        for cap in SPORTS_CAPABILITIES:
            assert isinstance(cap, SourceCapability)

    def test_altdata_capabilities_all_validate(self) -> None:
        from unified_api_contracts.registry.capability_declarations._altdata import (
            ALTDATA_CAPABILITIES,
        )

        assert len(ALTDATA_CAPABILITIES) > 0
        for cap in ALTDATA_CAPABILITIES:
            assert isinstance(cap, SourceCapability)
