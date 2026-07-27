"""Unit tests for the prediction write-time canonical-value guardrail.

Re-drift prevention (``prediction_phase_ab_residuals_2026_07_24.md`` A2 / the
2026-07-25 batch1 AO-dispatch todo "route every prediction id/underlying/CQG
writer through the shared canonical builder + a QG that fails a non-canonical
prediction ``instrument_id``/``canonical_question_group`` on write"). These
tests are the "new QG/test" the todo's done-when requires: each rejects a
synthetic non-canonical value (the exact A0-enumerated dupe classes) and
passes on the canonical values the current writers now emit.
"""

from __future__ import annotations

import pytest

from unified_api_contracts._instrument_enums import InstrumentType
from unified_api_contracts.predictions import (
    validate_canonical_question_group,
    validate_prediction_instrument_type,
)


class TestValidatePredictionInstrumentType:
    def test_canonical_value_passes(self) -> None:
        validate_prediction_instrument_type(InstrumentType.PREDICTION_MARKET.value)
        validate_prediction_instrument_type("PREDICTION_MARKET")

    @pytest.mark.parametrize(
        "bad_value",
        [
            "prediction_market",  # lowercase casing dupe (A0-enumerated)
            "prediction",  # lowercase, no-underscore casing dupe (A0-enumerated)
            "BTC",  # underlying-asset leakage (A0-enumerated)
            "ETH",
            "SPX",
            "DJIA",
            "NDX",
            "GOLD",
            "SILVER",
            "CRUDE_OIL",
            "DOGE",
            "XRP",
            "BNB",
            "HYPE",
            "OTHER",
            "",
        ],
    )
    def test_non_canonical_value_rejected(self, bad_value: str) -> None:
        with pytest.raises(ValueError, match="non-canonical prediction instrument_type"):
            validate_prediction_instrument_type(bad_value)


class TestValidateCanonicalQuestionGroup:
    @pytest.mark.parametrize(
        "good_value",
        ["BTC_UP_DOWN_HOURLY", "SPX_UP_DOWN_DAILY", "ELECTION_PRESIDENT_2028", "OTHER"],
    )
    def test_genuine_member_passes(self, good_value: str) -> None:
        validate_canonical_question_group(good_value)

    @pytest.mark.parametrize(
        "bad_value",
        [
            "btc_up_down_hourly",  # case-sensitivity — lowercase dupe of a real member
            "NOT_A_REAL_GROUP",
            "",
        ],
    )
    def test_non_member_rejected(self, bad_value: str) -> None:
        with pytest.raises(ValueError, match="non-canonical canonical_question_group"):
            validate_canonical_question_group(bad_value)
