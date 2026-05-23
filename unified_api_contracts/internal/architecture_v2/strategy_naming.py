"""Canonical strategy-ID naming convention (v2).

A strategy in the v2 architecture has three identifiers depending on the
audience:

1. **Slot label** — ``ARCHETYPE@venue-asset-instrument-period-quote-env``.
   Used inside the registry + records pipeline. Example:
   ``CARRY_BASIS_PERP@binance-eth-perp-10m-usdt-prod``.

2. **Fully-qualified (FQ) strategy-id** — ``FAMILY.ARCHETYPE.slot_id``.
   Used in UI URLs, admin surfaces, and codex cross-references where the
   family prefix makes lineage explicit. Example:
   ``CARRY_AND_YIELD.CARRY_BASIS_PERP.binance-eth-perp-10m-usdt-prod``.

3. **Bare slot-id** — the tail after ``@`` in the slot label (or after the
   third ``.`` in the FQ form). Used when the archetype + family are
   already known. Example: ``binance-eth-perp-10m-usdt-prod``.

SSOT codex: ``unified-trading-pm/codex/09-strategy/architecture-v2/naming-convention.md``.

This module owns parsing + formatting + validation. It MUST NOT depend on
the strategy-service runtime registry — purely static on the enum axes
defined in ``enums.py`` + the ``ARCHETYPE_TO_FAMILY`` map.
"""

from __future__ import annotations

from dataclasses import dataclass

from unified_api_contracts.internal.architecture_v2.enums import (
    ARCHETYPE_TO_FAMILY,
    StrategyArchetype,
    StrategyFamily,
)

__all__ = [
    "ParsedStrategyId",
    "format_strategy_id",
    "parse_strategy_id",
]


@dataclass(frozen=True, slots=True)
class ParsedStrategyId:
    """Result of parsing a canonical strategy identifier.

    Attributes
    ----------
    family : StrategyFamily
        The v2 family the archetype belongs to (looked up from
        ``ARCHETYPE_TO_FAMILY`` — not carried in the slot label itself).
    archetype : StrategyArchetype
        The v2 archetype declared in the slot label prefix or FQ form.
    slot_id : str
        Bare slot id (the part after ``@`` or the trailing FQ segment).
    source_form : str
        ``"slot_label"`` if the input used the ``ARCHETYPE@slot`` grammar,
        ``"fully_qualified"`` if it used ``FAMILY.ARCHETYPE.slot``.
    """

    family: StrategyFamily
    archetype: StrategyArchetype
    slot_id: str
    source_form: str


def _parse_slot_label(raw: str) -> ParsedStrategyId:
    """Parse ``ARCHETYPE@slot_id`` form."""
    archetype_token, slot_id = raw.split("@", 1)
    if not archetype_token:
        raise ValueError(f"Empty archetype token in slot label: {raw!r}")
    if not slot_id:
        raise ValueError(f"Empty slot_id after '@' in slot label: {raw!r}")
    try:
        archetype = StrategyArchetype(archetype_token)
    except ValueError as exc:
        raise ValueError(f"Unknown archetype token {archetype_token!r} in strategy id {raw!r}") from exc
    family = ARCHETYPE_TO_FAMILY[archetype]
    return ParsedStrategyId(
        family=family,
        archetype=archetype,
        slot_id=slot_id,
        source_form="slot_label",
    )


def _parse_fully_qualified(raw: str) -> ParsedStrategyId:
    """Parse ``FAMILY.ARCHETYPE.slot_id`` form.

    Note: ``slot_id`` itself may contain dots (e.g.
    ``binance-eth-perp-10m.usdt-prod``) so we only split on the first two
    dots.
    """
    parts = raw.split(".", 2)
    if len(parts) != 3:
        raise ValueError(
            f"Fully-qualified strategy id must have 3 '.'-separated segments "
            f"(FAMILY.ARCHETYPE.slot_id), got {len(parts)} in {raw!r}"
        )
    family_token, archetype_token, slot_id = parts
    if not family_token or not archetype_token or not slot_id:
        raise ValueError(f"Empty segment in fully-qualified id {raw!r}")
    try:
        family = StrategyFamily(family_token)
    except ValueError as exc:
        raise ValueError(f"Unknown family token {family_token!r} in strategy id {raw!r}") from exc
    try:
        archetype = StrategyArchetype(archetype_token)
    except ValueError as exc:
        raise ValueError(f"Unknown archetype token {archetype_token!r} in strategy id {raw!r}") from exc
    expected_family = ARCHETYPE_TO_FAMILY[archetype]
    if expected_family is not family:
        raise ValueError(
            f"Archetype {archetype.value!r} belongs to family "
            f"{expected_family.value!r}, not {family.value!r} "
            f"(strategy id: {raw!r})"
        )
    return ParsedStrategyId(
        family=family,
        archetype=archetype,
        slot_id=slot_id,
        source_form="fully_qualified",
    )


def parse_strategy_id(fq_id: str) -> ParsedStrategyId:
    """Parse a canonical strategy identifier.

    Accepts EITHER:
      * ``ARCHETYPE@slot_id`` (slot-label grammar) — e.g.
        ``CARRY_BASIS_PERP@binance-eth-perp-10m-usdt-prod``.
      * ``FAMILY.ARCHETYPE.slot_id`` (fully-qualified) — e.g.
        ``CARRY_AND_YIELD.CARRY_BASIS_PERP.binance-eth-perp-10m-usdt-prod``.

    In the FQ form, the family is cross-validated against the archetype's
    declared family in ``ARCHETYPE_TO_FAMILY`` — a mismatch raises
    ``ValueError``.

    Raises
    ------
    ValueError
        If the input is empty, does not match either grammar, declares an
        unknown family/archetype token, or has an inconsistent
        family/archetype pairing in the FQ form.
    """
    if not fq_id:
        raise ValueError("strategy_id must be a non-empty string")
    if not isinstance(fq_id, str):  # pragma: no cover - belt-and-braces for bad callers
        raise TypeError(f"strategy_id must be str, got {type(fq_id).__name__}")
    if "@" in fq_id:
        return _parse_slot_label(fq_id)
    if "." in fq_id:
        return _parse_fully_qualified(fq_id)
    raise ValueError(
        f"Malformed strategy id {fq_id!r}: expected either 'ARCHETYPE@slot_id' or 'FAMILY.ARCHETYPE.slot_id'"
    )


def format_strategy_id(
    archetype: StrategyArchetype,
    slot_id: str,
    *,
    fully_qualified: bool = True,
) -> str:
    """Format a canonical strategy id from its components.

    Parameters
    ----------
    archetype : StrategyArchetype
        v2 archetype. Family is looked up automatically.
    slot_id : str
        Bare slot id (no ``@`` or family prefix).
    fully_qualified : bool
        If True (default), emit ``FAMILY.ARCHETYPE.slot_id``. If False,
        emit the slot-label form ``ARCHETYPE@slot_id``.
    """
    if not slot_id:
        raise ValueError("slot_id must be a non-empty string")
    if "@" in slot_id or "." in slot_id.split("@", 1)[0]:
        raise ValueError(
            f"slot_id {slot_id!r} must not contain '@' (use archetype param) "
            f"or '.' before any '@' (reserved for FQ separator)"
        )
    family = ARCHETYPE_TO_FAMILY[archetype]
    if fully_qualified:
        return f"{family.value}.{archetype.value}.{slot_id}"
    return f"{archetype.value}@{slot_id}"
