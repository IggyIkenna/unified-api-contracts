"""Tests for Stage 3E § 2.8 fund business-unit registry."""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.architecture_v2.fund_business_unit import (
    FUND_BUSINESS_UNIT_REGISTRY,
    CustodyModel,
    FundBusinessUnitEntry,
    FundNotFoundError,
    _validate_registry_invariants,
    fund_for,
    funds_for_business_unit,
    reserving_business_unit_for,
)


class TestRegistryShape:
    """Shape invariants over the seed registry."""

    def test_registry_not_empty(self) -> None:
        assert len(FUND_BUSINESS_UNIT_REGISTRY) >= 6

    def test_every_entry_is_frozen_basemodel(self) -> None:
        from pydantic import ValidationError

        for entry in FUND_BUSINESS_UNIT_REGISTRY:
            with pytest.raises(ValidationError):
                # pydantic frozen — mutation must raise ValidationError.
                entry.fund_id = "mutated"  # type: ignore[misc]

    def test_fund_ids_unique(self) -> None:
        ids = [entry.fund_id for entry in FUND_BUSINESS_UNIT_REGISTRY]
        assert len(ids) == len(set(ids))

    def test_reserving_business_unit_ids_unique(self) -> None:
        keys = [entry.reserving_business_unit_id for entry in FUND_BUSINESS_UNIT_REGISTRY]
        assert len(keys) == len(set(keys))


class TestCustodyModelCoverage:
    """Custody-model semantics per 2026-04-20 memo."""

    def test_im_pooled_uses_copper_custodian(self) -> None:
        entry = fund_for("imp_alpha")
        assert entry.custody_model is CustodyModel.COPPER_CUSTODIAN
        assert entry.service_family == "IM"

    def test_im_sma_uses_client_owned_venue(self) -> None:
        entry = fund_for("sma_acme_llc")
        assert entry.custody_model is CustodyModel.CLIENT_OWNED_VENUE
        assert entry.service_family == "IM"

    def test_reg_umbrella_uses_client_owned_venue(self) -> None:
        entry = fund_for("reg_umbrella_odum_fca")
        assert entry.custody_model is CustodyModel.CLIENT_OWNED_VENUE
        assert entry.service_family == "RegUmbrella"

    def test_dart_uses_client_owned_venue(self) -> None:
        entry = fund_for("dart_saas_default")
        assert entry.custody_model is CustodyModel.CLIENT_OWNED_VENUE
        assert entry.service_family == "DART"
        assert entry.business_unit == "saas"

    def test_admin_and_im_desk_use_not_applicable(self) -> None:
        assert fund_for("admin").custody_model is CustodyModel.NOT_APPLICABLE
        assert fund_for("im_desk_trading").custody_model is CustodyModel.NOT_APPLICABLE


class TestHelpers:
    """fund_for + funds_for_business_unit + reserving_business_unit_for."""

    def test_fund_for_happy_path(self) -> None:
        assert fund_for("imp_alpha").fund_id == "imp_alpha"

    def test_fund_for_unknown_raises_loudly(self) -> None:
        with pytest.raises(FundNotFoundError, match="not found"):
            fund_for("nonexistent_fund")

    def test_funds_for_business_unit_im_desk(self) -> None:
        entries = funds_for_business_unit("im_desk")
        # IM Pooled + 2 SMAs + Reg Umbrella + IM-desk internal.
        assert len(entries) >= 5
        assert all(e.business_unit == "im_desk" for e in entries)

    def test_funds_for_business_unit_saas(self) -> None:
        entries = funds_for_business_unit("saas")
        assert len(entries) >= 1
        assert entries[0].fund_id == "dart_saas_default"

    def test_funds_for_business_unit_admin(self) -> None:
        entries = funds_for_business_unit("admin")
        assert len(entries) == 1
        assert entries[0].fund_id == "admin"

    def test_reserving_business_unit_for_resolves(self) -> None:
        assert reserving_business_unit_for("imp_alpha") == "im_desk_pooled_alpha"
        assert reserving_business_unit_for("reg_umbrella_odum_fca") == "im_desk_reg_umbrella"

    def test_reserving_business_unit_for_unknown_raises(self) -> None:
        with pytest.raises(FundNotFoundError):
            reserving_business_unit_for("nonexistent")

    def test_injected_registry_overrides_default(self) -> None:
        fixture = (
            FundBusinessUnitEntry(
                fund_id="test_fund_xyz",
                fund_name="Test Fund XYZ",
                business_unit="saas",
                reserving_business_unit_id="saas_test_xyz",
                custody_model=CustodyModel.CLIENT_OWNED_VENUE,
                service_family="DART",
            ),
        )
        entry = fund_for("test_fund_xyz", registry=fixture)
        assert entry.fund_name == "Test Fund XYZ"


class TestInvariantValidation:
    """Import-time invariant enforcement (POD leak, duplicates)."""

    def test_duplicate_fund_id_rejected(self) -> None:
        bad = (
            FundBusinessUnitEntry(
                fund_id="dup",
                fund_name="A",
                business_unit="admin",
                reserving_business_unit_id="a",
                custody_model=CustodyModel.NOT_APPLICABLE,
            ),
            FundBusinessUnitEntry(
                fund_id="dup",
                fund_name="B",
                business_unit="admin",
                reserving_business_unit_id="b",
                custody_model=CustodyModel.NOT_APPLICABLE,
            ),
        )
        with pytest.raises(ValueError, match="duplicate fund_id"):
            _validate_registry_invariants(bad)

    def test_duplicate_reserving_business_unit_id_rejected(self) -> None:
        bad = (
            FundBusinessUnitEntry(
                fund_id="a",
                fund_name="A",
                business_unit="admin",
                reserving_business_unit_id="same_key",
                custody_model=CustodyModel.NOT_APPLICABLE,
            ),
            FundBusinessUnitEntry(
                fund_id="b",
                fund_name="B",
                business_unit="admin",
                reserving_business_unit_id="same_key",
                custody_model=CustodyModel.NOT_APPLICABLE,
            ),
        )
        with pytest.raises(
            ValueError,
            match="duplicate reserving_business_unit_id",
        ):
            _validate_registry_invariants(bad)

    def test_pod_leak_in_copper_row_rejected(self) -> None:
        leaky = (
            FundBusinessUnitEntry(
                fund_id="leaky_fund",
                fund_name="Leaky Pooled Fund",
                business_unit="im_desk",
                reserving_business_unit_id="im_desk_leaky",
                custody_model=CustodyModel.COPPER_CUSTODIAN,
                service_family="IM",
                notes="Operated by POD affiliate.",
            ),
        )
        with pytest.raises(ValueError, match="POD affiliate"):
            _validate_registry_invariants(leaky)

    def test_pod_leak_in_non_copper_row_allowed(self) -> None:
        # POD mention is only banned in COPPER_CUSTODIAN rows.
        # NOT_APPLICABLE admin rows may mention POD in internal notes.
        # (Separate review-gate, not blocked by invariant.)
        ok = (
            FundBusinessUnitEntry(
                fund_id="internal_note",
                fund_name="Internal",
                business_unit="admin",
                reserving_business_unit_id="admin_internal",
                custody_model=CustodyModel.NOT_APPLICABLE,
                notes="(internal-only note — POD context acceptable here)",
            ),
        )
        # Should not raise.
        _validate_registry_invariants(ok)
