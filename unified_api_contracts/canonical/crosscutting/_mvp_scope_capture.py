"""MVP CAPTURE universe — the perp-gated CeFi capture predicate.

Split out of ``mvp_scope.py`` (900-line file-size QG, 2026-07-09) — pure
file-organization move, no behavior change. ``mvp_scope.py`` re-exports
everything here so the public import path
(``unified_api_contracts.canonical.crosscutting.mvp_scope``) is unchanged.

``is_mvp`` answers "is this (asset_group, venue, instrument_type, base,
data_type) cell in the MVP scope rule" — base-membership + instrument-type +
the Deribit-options/TradFi-perp carve-outs. It does NOT enforce the
**HARD perp-gate** (operator 2026-06-23): a SPOT instrument is captured ONLY
IF that venue also lists a PERP for the same base at that time. That gate
needs an extra fact — ``has_perp_for_base`` — that ``is_mvp`` cannot derive
from a single cell, so it lives in this dedicated capture predicate that the
catalogue rollup (which sees ALL instruments per venue/day and so can compute
``has_perp_for_base``), the MTDS capture-universe derivation, and the
expected_unattempted enumerator + manifest reclassifier all call. ONE
implementation → no drift (shard-granularity SSOT).

Rule (per (venue, base, instrument_type), keyed on a per-(venue,base,day)
``has_perp_for_base`` flag the caller computes from the full catalogue):
  - base ∈ the CeFi capture universe (``is_mvp`` base-membership). NECESSARY
    but NOT sufficient.
  - PERPETUAL / EQUITY_PERP  ⇒ MVP on base-membership (the perp IS the gate;
    a TradFi-linked equity perp rides ``CEFI_EQUITY_PERP_BASE_UNIVERSE``).
  - SPOT_PAIR / SPOT_ASSET   ⇒ MVP ONLY IF ``has_perp_for_base`` (the venue
    also lists a perp for that base). spot-and-no-perp ⇒ DROP (even top-100).
  - FUTURE (dated/quarterly, shares a universe base) ⇒ MVP on base-membership
    + venue, NOT perp-gated (operator 2026-06-23: dated futures are part of the
    futures complex sharing the base and are included for any universe base the
    venue lists). ``has_perp_for_base`` is irrelevant for a dated future.
  - OPTION                   ⇒ MVP ONLY for venue==DERIBIT AND base∈{BTC,ETH}
    (the Deribit-options carve-out, via ``is_mvp``); ``has_perp_for_base`` is
    NOT required for options (Deribit options are the carve-out, not perp-gated).
  - anything else / base not in universe / venue not in rule ⇒ NOT MVP.

SSOT: ``plans/active/mvp_scope_catalogue_tagging_2026_06_08.md``.
"""

from __future__ import annotations

from typing import Final

from unified_api_contracts.canonical.crosscutting._mvp_scope_predicate import is_mvp

# The staking/restaking/LST spot-without-perp allow-list — the ONE carve-out
# from the hard perp-gate below (operator 2026-06-23). Imported from the leaf
# module (NOT the registry package ``__init__``), same acyclic-import
# discipline as the rest of the mvp_scope split.
from unified_api_contracts.registry.cefi_instrument_universe import (
    STAKING_SPOT_EXCEPTION,
)

#: CeFi instrument types whose MVP membership is gated on the venue also listing
#: a PERP for the same base — SPOT legs ONLY. (operator 2026-06-23: spot-and-no-perp
#: ⇒ drop. Dated FUTURES are NOT perp-gated — they ride base-membership + venue,
#: as part of the futures complex sharing the base.)
_CEFI_PERP_GATED_TYPES: Final[frozenset[str]] = frozenset(
    {
        "SPOT_PAIR",  # InstrumentType.SPOT_PAIR
        "SPOT_ASSET",  # InstrumentType.SPOT_ASSET
    }
)

#: CeFi DATED-FUTURES types — MVP on base-membership + venue (NOT perp-gated).
#: Dated/quarterly futures sharing a universe base (e.g. BTC-27JUN25) are part of
#: the futures complex; per the operator spec they're included for any universe
#: base the venue lists, independent of a sibling perp.
_CEFI_DATED_FUTURE_TYPES: Final[frozenset[str]] = frozenset(
    {
        "FUTURE",  # InstrumentType.FUTURE
    }
)

#: CeFi instrument types that ARE perps (self-qualify the perp-gate on base-membership).
_CEFI_PERP_TYPES: Final[frozenset[str]] = frozenset(
    {
        "PERPETUAL",  # InstrumentType.PERPETUAL
        "EQUITY_PERP",  # InstrumentType.EQUITY_PERP — TradFi-linked single-stock perps
    }
)

#: Venue ENTITY prefixes (split on '-') that are exempt from the SPOT perp-gate —
#: their SPOT is mvp=true REGARDLESS of perp existence (operator 2026-06-23,
#: cefi_universe_capture_rule). UPBIT is the ONE such venue: it lists NO perps
#: (Korean spot-only exchange) but we capture all its spot pairs for the kimchi
#: premium + cross-currency dispersion. This is a VENUE-scoped exception, distinct
#: from the BASE-scoped ``STAKING_SPOT_EXCEPTION`` (LSTs on any venue).
_CEFI_SPOT_PERP_GATE_EXEMPT_VENUES: Final[frozenset[str]] = frozenset({"UPBIT"})


def is_in_mvp_capture_universe(
    venue: str,
    base: str,
    instrument_type: str,
    *,
    has_perp_for_base: bool,
    source: str | None = None,
) -> bool:
    """Return ``True`` iff the CeFi cell is in the **MVP capture universe**.

    The shared SSOT predicate (operator 2026-06-23) consumed by the THREE
    capture consumers that MUST agree (drift = silent correctness bug):

    1. the IS catalogue rollup ``_add_mvp_column`` (tags the ``mvp`` column);
    2. the MTDS cefi capture-universe derivation (what tick data we download);
    3. the ``expected_unattempted`` enumerator + manifest reclassifier
       (honest-coverage denominator).

    It composes the base-membership / instrument-type / Deribit-options /
    TradFi-perp rules from :func:`is_mvp` (cefi asset group, unbound data_type)
    with the **HARD perp-gate**: a spot/dated-future cell is in-universe ONLY
    IF the venue also lists a perp for the same base at that time
    (``has_perp_for_base``). A PERP/EQUITY_PERP self-qualifies on
    base-membership; an OPTION rides the Deribit BTC/ETH carve-out (not
    perp-gated).

    Args:
        venue: Canonical CeFi venue id (``BINANCE-SPOT`` / ``OKX-SWAP`` / …; a
            bare ``OKX`` resolves to its sub-venues via :func:`is_mvp`).
        base: Base asset / underlying (``BTC``, ``ETH``, ``AAPL`` for an equity
            perp, …) — the axis the universe-membership rule gates on.
        instrument_type: Canonical :class:`InstrumentType` string value.
        has_perp_for_base: Whether the SAME venue lists a PERPETUAL (or
            EQUITY_PERP) for ``base`` at the relevant time. The caller computes
            this from the full catalogue (per venue/day). Ignored for
            PERP/EQUITY_PERP/OPTION cells (they don't need a sibling perp).
        source: Optional source key (passed through to :func:`is_mvp`).

    Returns:
        ``True`` iff the cell is in the MVP capture universe.
    """
    itype = (instrument_type or "").strip().upper()

    # OPTION: Deribit BTC/ETH carve-out ONLY — NOT perp-gated. The venue MUST be
    # DERIBIT (the is_mvp options carve-out only narrows base_ccy to BTC/ETH, but
    # the cefi venue set also contains BINANCE/OKX/… so a bare is_mvp("OPTION")
    # would wrongly pass a Binance BTC option — operator: options mvp ONLY for
    # venue==deribit). Gate the venue explicitly here.
    if itype == "OPTION":
        if venue.strip().upper().split("-", 1)[0] != "DERIBIT":
            return False
        return is_mvp(
            "cefi",
            venue=venue,
            instrument_type="OPTION",
            base_ccy=base,
            source=source,
        )

    # PERP / EQUITY_PERP: in-universe on base-membership (the perp IS the gate).
    if itype in _CEFI_PERP_TYPES:
        return is_mvp(
            "cefi",
            venue=venue,
            instrument_type=itype,
            base_ccy=base,
            source=source,
        )

    # SPOT: base-membership AND the venue lists a perp for the base (HARD perp-gate)
    # — EXCEPT the staking/restaking/LST allow-list (STAKING_SPOT_EXCEPTION,
    # operator 2026-06-23): a base in that set has its SPOT captured on ANY venue
    # that lists it, REGARDLESS of perp existence (the carry_staked_basis legs).
    # This is the ONLY spot-without-perp carve-out.
    if itype in _CEFI_PERP_GATED_TYPES:
        base_in_staking_exception = (base or "").strip().upper() in STAKING_SPOT_EXCEPTION
        venue_exempt = (venue or "").strip().upper().split("-", 1)[0] in _CEFI_SPOT_PERP_GATE_EXEMPT_VENUES
        if not has_perp_for_base and not base_in_staking_exception and not venue_exempt:
            return False
        return is_mvp(
            "cefi",
            venue=venue,
            instrument_type=itype,
            base_ccy=base,
            source=source,
        )

    # DATED FUTURE: base-membership + venue only (NOT perp-gated — part of the
    # futures complex sharing the base; operator 2026-06-23).
    if itype in _CEFI_DATED_FUTURE_TYPES:
        return is_mvp(
            "cefi",
            venue=venue,
            instrument_type=itype,
            base_ccy=base,
            source=source,
        )

    # TOKENIZED_EQUITY and any other type: defer to the base rule (no extra
    # perp-gate — tokenized equities are an explicit allow-listed type, not a
    # spot-needs-perp case). Out-of-rule types fall through to is_mvp → False.
    return is_mvp(
        "cefi",
        venue=venue,
        instrument_type=itype,
        base_ccy=base,
        source=source,
    )
