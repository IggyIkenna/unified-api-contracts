"""Verify top-level imports from unified_api_contracts.sports work."""

from __future__ import annotations

import pytest


@pytest.mark.unit
class TestSportsExports:
    def test_import_canonical_fixture(self) -> None:
        from unified_api_contracts import CanonicalFixture

        assert CanonicalFixture is not None

    def test_import_canonical_odds(self) -> None:
        from unified_api_contracts import CanonicalOdds

        assert CanonicalOdds is not None

    def test_import_bet_order(self) -> None:
        from unified_api_contracts import BetOrder

        assert BetOrder is not None

    def test_import_bet_execution(self) -> None:
        from unified_api_contracts import BetExecution

        assert BetExecution is not None

    def test_import_arbitrage_opportunity(self) -> None:
        from unified_api_contracts import ArbitrageOpportunity

        assert ArbitrageOpportunity is not None

    def test_import_bookmaker_registry(self) -> None:
        from unified_api_contracts import BookmakerRegistry

        assert len(BookmakerRegistry) == 78

    def test_import_odds_type(self) -> None:
        from unified_api_contracts import OddsType

        assert OddsType.H2H == "h2h"

    def test_import_canonical_types_betting(self) -> None:
        from unified_api_contracts import (
            ArbitrageMarket,
            ArbitrageOpportunity,
            ArbitrageStatus,
            BetExecution,
            BetOrder,
            BetStatus,
            BettingSignal,
            BookmakerCategory,
            BookmakerInfo,
            CanonicalBookmakerMarket,
            ExpectedValue,
        )

        assert all(
            [
                ArbitrageMarket,
                ArbitrageOpportunity,
                ArbitrageStatus,
                BetExecution,
                BetOrder,
                BetStatus,
                BettingSignal,
                BookmakerCategory,
                BookmakerInfo,
                CanonicalBookmakerMarket,
                ExpectedValue,
            ]
        )

    def test_import_canonical_types_fixture(self) -> None:
        from unified_api_contracts import (
            CanonicalFixture,
            CanonicalLeague,
            CanonicalOdds,
            CanonicalPlayer,
            CanonicalReferee,
            CanonicalTeam,
            CanonicalVenue,
            MarketStatus,
            OddsType,
            OutcomeType,
            SignalSource,
        )

        assert all(
            [
                CanonicalFixture,
                CanonicalLeague,
                CanonicalOdds,
                CanonicalPlayer,
                CanonicalReferee,
                CanonicalTeam,
                CanonicalVenue,
                MarketStatus,
                OddsType,
                OutcomeType,
                SignalSource,
            ]
        )

    def test_import_errors(self) -> None:
        from unified_api_contracts import (
            BetRejectedError,
            BookmakerUnavailableError,
            FixtureNotFoundError,
            MarketClosedError,
            OddsChangedError,
            ScraperError,
            SportsError,
        )

        assert issubclass(BetRejectedError, SportsError)
        assert issubclass(BookmakerUnavailableError, SportsError)
        assert issubclass(FixtureNotFoundError, SportsError)
        assert issubclass(MarketClosedError, SportsError)
        assert issubclass(OddsChangedError, SportsError)
        assert issubclass(ScraperError, SportsError)

    # ------------------------------------------------------------------
    # P2 — FSS→strategy capture_status contract (sports_manifest_canon)
    # ------------------------------------------------------------------

    def test_sports_feature_capture_status_key_exported(self) -> None:
        """SPORTS_FEATURE_PAYLOAD_CAPTURE_STATUS_KEY must be importable from
        the sports domain and equal the canonical dict key name."""
        from unified_api_contracts.canonical.domain.sports import (
            SPORTS_FEATURE_PAYLOAD_CAPTURE_STATUS_KEY,
        )

        assert SPORTS_FEATURE_PAYLOAD_CAPTURE_STATUS_KEY == "capture_status"
        assert isinstance(SPORTS_FEATURE_PAYLOAD_CAPTURE_STATUS_KEY, str)

    def test_sports_feature_capture_status_type_exported(self) -> None:
        """SportsFeatureCaptureStatus must be importable from the sports domain."""
        from unified_api_contracts.canonical.domain.sports import (
            SportsFeatureCaptureStatus,
        )

        # type aliases are not None; runtime value is a typing.Literal
        assert SportsFeatureCaptureStatus is not None

    def test_sports_feature_capture_status_valid_values(self) -> None:
        """The 4-state closed set must include all honest-absence states."""
        import typing

        from unified_api_contracts.canonical.domain.sports.live import (
            SportsFeatureCaptureStatus,
        )

        args = typing.get_args(SportsFeatureCaptureStatus)
        assert set(args) == {
            "captured",
            "empty_confirmed",
            "attempted_failed",
            "expected_unattempted",
        }

    # ------------------------------------------------------------------
    # P1 — sports IS reference data_type lowercase-merge CONTRACT
    # (sports_taxonomy_p1_capture_and_contracts_2026_08_08.md, operator
    # ruling 7). Physical manifest re-stamp is P2 — this only guards the
    # target-form mapping table.
    # ------------------------------------------------------------------

    def test_sports_is_data_type_lowercase_form_exported(self) -> None:
        from unified_api_contracts import SPORTS_IS_DATA_TYPE_LOWERCASE_FORM

        assert isinstance(SPORTS_IS_DATA_TYPE_LOWERCASE_FORM, dict)
        assert SPORTS_IS_DATA_TYPE_LOWERCASE_FORM  # non-empty

    def test_sports_is_data_type_lowercase_form_covers_every_axis_key(self) -> None:
        """Drift guard: every ``SPORTS_DATA_TYPE_TO_SOURCE`` key must have a
        registered lowercase target form, so a newly-added IS data_type can
        never silently miss the P1 contract (mirrors the drift-guard pattern
        used for ``SPORTS_HORIZONS``/MDPS's bucket-name assertion)."""
        from unified_api_contracts import (
            SPORTS_DATA_TYPE_TO_SOURCE,
            SPORTS_IS_DATA_TYPE_LOWERCASE_FORM,
        )

        missing = set(SPORTS_DATA_TYPE_TO_SOURCE) - set(SPORTS_IS_DATA_TYPE_LOWERCASE_FORM)
        assert not missing, f"IS data_type(s) missing a registered lowercase form: {sorted(missing)}"

    def test_sports_is_data_type_lowercase_form_values_are_lowercase(self) -> None:
        from unified_api_contracts import SPORTS_IS_DATA_TYPE_LOWERCASE_FORM

        for key, value in SPORTS_IS_DATA_TYPE_LOWERCASE_FORM.items():
            assert value == value.lower(), f"{key!r} maps to non-lowercase form {value!r}"
            assert value == key.lower(), f"{key!r} should map to its own lowercased form, got {value!r}"

    def test_canonical_sports_is_data_type_resolves_both_cases(self) -> None:
        from unified_api_contracts import canonical_sports_is_data_type

        assert canonical_sports_is_data_type("FIXTURES") == "fixtures"
        assert canonical_sports_is_data_type("fixtures") == "fixtures"
        assert canonical_sports_is_data_type("XG_SHOTS") == "xg_shots"
        assert canonical_sports_is_data_type("NOT_A_REAL_DATA_TYPE") is None
