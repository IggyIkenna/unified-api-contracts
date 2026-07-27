"""Write-time canonical-value guardrail for prediction market writers.

Re-drift prevention (``prediction_phase_ab_residuals_2026_07_24.md`` A2 / the
2026-07-25 batch1 AO-dispatch todo "Route every prediction id/underlying/CQG
writer through the shared canonical builder + a QG that fails a non-canonical
prediction ``instrument_id``/``canonical_question_group`` on write"). The
2026-07-18 A0 corpus audit enumerated the live dupes this module closes:
manifest ``instrument_type`` mixed the canonical ``PREDICTION_MARKET`` with
lowercase casing dupes (``prediction``, ``prediction_market``) and
underlying-asset LEAKAGE (a raw underlying ticker — ``BTC``/``ETH``/``SPX``/
``DJIA``/``NDX``/``GOLD``/``SILVER``/``CRUDE_OIL``/``DOGE``/``XRP``/``BNB``/
``HYPE``/``OTHER``/``''`` — stamped into the ``instrument_type`` column
instead of the type), while the catalogue stayed clean at
``PREDICTION_MARKET`` only.

Both prediction venue writers (instruments-service's ``kalshi.py`` /
``polymarket/parsing.py``, market-tick-data-service's ``kalshi_adapter.py`` /
``polymarket_adapter.py``) call these two validators at the point they set
``instrument_type`` / ``canonical_question_group``, so a future regression is
rejected at the writer rather than silently persisted — the same
defense-in-depth shape as the CeFi `*-PERP` write guard
(``instruments_service.reference_data.adapters.cefi._perp_write_guard``).
"""

from __future__ import annotations

from unified_api_contracts._instrument_enums import InstrumentType
from unified_api_contracts.canonical.domain.predictions.canonical_groups import CanonicalQuestionGroup

__all__ = [
    "validate_canonical_question_group",
    "validate_prediction_instrument_type",
]

_CANONICAL_PREDICTION_INSTRUMENT_TYPE = InstrumentType.PREDICTION_MARKET.value


def validate_prediction_instrument_type(value: str) -> None:
    """Raise ``ValueError`` unless ``value`` is the canonical PREDICTION_MARKET instrument_type.

    Rejects both A0-enumerated dupe classes: lowercase casing (``prediction``,
    ``prediction_market``) and underlying-asset leakage (a raw underlying
    ticker like ``BTC``/``ETH`` stamped into the instrument_type column).
    """
    if value != _CANONICAL_PREDICTION_INSTRUMENT_TYPE:
        msg = (
            f"non-canonical prediction instrument_type {value!r} — must be "
            f"{_CANONICAL_PREDICTION_INSTRUMENT_TYPE!r} (InstrumentType.PREDICTION_MARKET.value). "
            "Lowercase casing dupes and underlying-asset leakage into this column are the two "
            "dupe classes the 2026-07-18 A0 audit enumerated in the manifest instrument_type axis."
        )
        raise ValueError(msg)


def validate_canonical_question_group(value: str) -> None:
    """Raise ``ValueError`` unless ``value`` is a genuine :class:`CanonicalQuestionGroup` member.

    Case-sensitive membership check — the closed set is UPPERCASE by
    convention (81 canonical values, confirmed dupe-free by the 2026-07-18 A0
    audit); this guards against a future writer re-introducing a stray string.
    """
    try:
        CanonicalQuestionGroup(value)
    except ValueError:
        msg = (
            f"non-canonical canonical_question_group {value!r} — not a member of "
            "CanonicalQuestionGroup. Add the group to the enum + seed its metadata entry "
            "(canonical_groups.py) first rather than writing a raw string."
        )
        raise ValueError(msg) from None
