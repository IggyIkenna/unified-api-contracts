"""Unit tests for strategy_naming (parse_strategy_id + format_strategy_id).

SSOT codex:
``unified-trading-pm/codex/09-strategy/architecture-v2/naming-convention.md``.
"""

from __future__ import annotations

import pytest

from unified_api_contracts.strategy import (
    ParsedStrategyId,
    StrategyArchetype,
    StrategyFamily,
    format_strategy_id,
    parse_strategy_id,
)

# ---------------------------------------------------------------------------
# parse_strategy_id — slot-label form
# ---------------------------------------------------------------------------


def test_parse_slot_label_form() -> None:
    parsed = parse_strategy_id("CARRY_BASIS_PERP@binance-eth-perp-10m-usdt-prod")

    assert isinstance(parsed, ParsedStrategyId)
    assert parsed.family is StrategyFamily.CARRY_AND_YIELD
    assert parsed.archetype is StrategyArchetype.CARRY_BASIS_PERP
    assert parsed.slot_id == "binance-eth-perp-10m-usdt-prod"
    assert parsed.source_form == "slot_label"


def test_parse_slot_label_all_archetypes_roundtrip_via_format() -> None:
    """Every archetype must format and re-parse identically in slot-label form."""
    for archetype in StrategyArchetype:
        formatted = format_strategy_id(archetype, "demo-slot-id", fully_qualified=False)
        assert formatted == f"{archetype.value}@demo-slot-id"
        parsed = parse_strategy_id(formatted)
        assert parsed.archetype is archetype
        assert parsed.slot_id == "demo-slot-id"
        assert parsed.source_form == "slot_label"


# ---------------------------------------------------------------------------
# parse_strategy_id — fully-qualified form
# ---------------------------------------------------------------------------


def test_parse_fully_qualified_form() -> None:
    parsed = parse_strategy_id("CARRY_AND_YIELD.CARRY_BASIS_PERP.binance-eth-perp-10m-usdt-prod")

    assert parsed.family is StrategyFamily.CARRY_AND_YIELD
    assert parsed.archetype is StrategyArchetype.CARRY_BASIS_PERP
    assert parsed.slot_id == "binance-eth-perp-10m-usdt-prod"
    assert parsed.source_form == "fully_qualified"


def test_parse_fq_all_archetypes_roundtrip_via_format() -> None:
    """Every archetype must format and re-parse identically in FQ form."""
    for archetype in StrategyArchetype:
        formatted = format_strategy_id(archetype, "some-slot", fully_qualified=True)
        parsed = parse_strategy_id(formatted)
        assert parsed.archetype is archetype
        assert parsed.family.value == formatted.split(".", 1)[0]
        assert parsed.slot_id == "some-slot"
        assert parsed.source_form == "fully_qualified"


def test_parse_fq_family_archetype_mismatch_raises() -> None:
    """A FQ id whose FAMILY doesn't match the archetype's declared family fails loud."""
    with pytest.raises(ValueError, match="belongs to family"):
        parse_strategy_id("ML_DIRECTIONAL.CARRY_BASIS_PERP.slot-x")


def test_parse_fq_slot_id_allows_hyphens() -> None:
    """Slot ids with internal hyphens + underscores parse cleanly."""
    parsed = parse_strategy_id("STAT_ARB_PAIRS.STAT_ARB_PAIRS_FIXED.binance-eth_btc_pair-1h-usdt-prod")
    assert parsed.slot_id == "binance-eth_btc_pair-1h-usdt-prod"


# ---------------------------------------------------------------------------
# parse_strategy_id — malformed inputs
# ---------------------------------------------------------------------------


def test_parse_empty_string_raises() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        parse_strategy_id("")


def test_parse_no_separator_raises() -> None:
    with pytest.raises(ValueError, match="Malformed"):
        parse_strategy_id("JUST_A_STRING")


def test_parse_unknown_archetype_slot_label_raises() -> None:
    with pytest.raises(ValueError, match="Unknown archetype"):
        parse_strategy_id("NOT_AN_ARCHETYPE@slot-id")


def test_parse_unknown_archetype_fq_raises() -> None:
    with pytest.raises(ValueError, match="Unknown archetype"):
        parse_strategy_id("CARRY_AND_YIELD.NOT_AN_ARCHETYPE.slot-id")


def test_parse_unknown_family_fq_raises() -> None:
    with pytest.raises(ValueError, match="Unknown family"):
        parse_strategy_id("NOT_A_FAMILY.CARRY_BASIS_PERP.slot-id")


def test_parse_fq_missing_slot_segment_raises() -> None:
    with pytest.raises(ValueError, match=r"3 '\.'-separated segments|Empty segment"):
        parse_strategy_id("CARRY_AND_YIELD.CARRY_BASIS_PERP")


def test_parse_fq_empty_family_segment_raises() -> None:
    with pytest.raises(ValueError, match="Empty segment"):
        parse_strategy_id(".CARRY_BASIS_PERP.slot-id")


def test_parse_slot_label_empty_slot_raises() -> None:
    with pytest.raises(ValueError, match="Empty slot_id"):
        parse_strategy_id("CARRY_BASIS_PERP@")


def test_parse_slot_label_empty_archetype_raises() -> None:
    with pytest.raises(ValueError, match="Empty archetype"):
        parse_strategy_id("@some-slot-id")


# ---------------------------------------------------------------------------
# format_strategy_id
# ---------------------------------------------------------------------------


def test_format_strategy_id_defaults_to_fully_qualified() -> None:
    formatted = format_strategy_id(StrategyArchetype.CARRY_BASIS_PERP, "my-slot-id")
    assert formatted == "CARRY_AND_YIELD.CARRY_BASIS_PERP.my-slot-id"


def test_format_strategy_id_slot_label_mode() -> None:
    formatted = format_strategy_id(
        StrategyArchetype.ML_DIRECTIONAL_CONTINUOUS,
        "binance-btc-spot-5m",
        fully_qualified=False,
    )
    assert formatted == "ML_DIRECTIONAL_CONTINUOUS@binance-btc-spot-5m"


def test_format_strategy_id_rejects_slot_id_with_at() -> None:
    with pytest.raises(ValueError, match="must not contain '@'"):
        format_strategy_id(StrategyArchetype.CARRY_BASIS_PERP, "has@sign")


def test_format_strategy_id_rejects_empty_slot_id() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        format_strategy_id(StrategyArchetype.CARRY_BASIS_PERP, "")
