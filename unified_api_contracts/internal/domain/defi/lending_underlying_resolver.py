"""Canonical A_TOKEN/DEBT_TOKEN instrument_key -> flat-LENDING ``lending_indices`` join key.

Session-3 (2026-07-26) decision, documented in unified-trading-pm
``plans/active/defi_lending_writer_retire_prerequisite_2026_07_20.md`` (Progress Log,
todo 15) and ``codex/02-data/defi-canonical-naming-ssot.md``: the physical
A_TOKEN/DEBT_TOKEN retire of MTDS's market/event lending data_types
(``lending_indices``/``liquidations``/``liquidation_events``/``flash_loan_events``/
``position_data``/``risk_params``) will NOT ship -- those data_types stay flat
``LENDING``/``SOLANA_LENDING``-keyed permanently, after two prior reversal attempts.
Downstream code holding a canonical A_TOKEN/DEBT_TOKEN instrument_key (minted by
instruments-service's reference-data adapters) and needing the current supply/borrow
rate for it resolves through THIS module instead of a physical re-key.

The instrument_key itself carries everything needed -- no instruments-service API call
(no service-to-service dependency). instruments-service mints keys shaped
``{PROTOCOL}-{CHAIN}:{A_TOKEN|DEBT_TOKEN}:{PREFIX}{UNDERLYING_SYMBOL}`` (verified
against ``instruments-service/reference_data/adapters/defi/{aave_v3,spark,
compound_v3}.py``, 2026-07-26). The symbol PREFIX is protocol-specific:

- ``aave_v3``, ``spark``: A_TOKEN -> ``"A"``, DEBT_TOKEN -> ``"DEBT"`` (e.g. ``AUSDC`` /
  ``DEBTUSDC``).
- ``compound_v3``: A_TOKEN -> ``"C"``, DEBT_TOKEN -> ``"BORROW"`` (e.g. ``CUSDC`` /
  ``BORROWUSDC``) -- a DIFFERENT prefix pair, verified from ``compound_v3.py``'s
  ``supply_symbol = f"C{sym_upper}"`` / ``borrow_symbol = f"BORROW{sym_upper}"``. A
  universal "A"/"DEBT" prefix would silently mis-resolve every Compound V3 instrument.

Isolated-market protocols (``morpho``, ``euler_v2``, ``fluid``, ``radiant``, ``venus``,
``benqi``) synthesize a DIFFERENT ``A{marketId-derived-pair}`` form (verified against
``morpho.py``: ``f"A{pair_key}"`` where ``pair_key`` derives from the market's bytes32
``marketId``, not a single reserve symbol) that does not reduce to one underlying
reserve -- this module returns ``None`` for those rather than guess. This is not a
practical gap: MTDS's flat-``LENDING`` ``lending_indices`` capture
(``lending_indices_handler.py`` ``_DEFAULT_PROTOCOLS``) only covers
``aave_v3``/``spark``/``compound_v3``/``morpho`` among EVM protocols, and morpho's
rates come from its own blue-api (no reserve-based subgraph row to join against
regardless), so isolated-market instruments were never joinable to begin with.
"""

from pydantic import BaseModel

from unified_api_contracts._instrument_enums import InstrumentType

# Per-protocol A_TOKEN symbol prefix, as minted by instruments-service's reference-data
# adapters. Only protocols whose ``lending_indices`` flat-LENDING capture exists
# (``lending_indices_handler.py`` ``_DEFAULT_PROTOCOLS``) AND whose IS adapter mints a
# single-reserve-symbol form are listed -- everything else resolves to ``None``.
_A_TOKEN_PREFIX_BY_PROTOCOL: dict[str, str] = {
    "aave_v3": "A",
    "spark": "A",
    "compound_v3": "C",
}

# Per-protocol DEBT_TOKEN symbol prefix -- see module docstring, NOT uniform with the
# A_TOKEN prefix (Compound V3 uses "BORROW", not "DEBT").
_DEBT_TOKEN_PREFIX_BY_PROTOCOL: dict[str, str] = {
    "aave_v3": "DEBT",
    "spark": "DEBT",
    "compound_v3": "BORROW",
}


class LendingUnderlyingRef(BaseModel):
    """Where to look up a flat-``LENDING`` ``lending_indices`` row for a canonical
    A_TOKEN/DEBT_TOKEN instrument, and which column answers this instrument's rate.
    """

    protocol: str
    chain: str
    underlying_symbol: str
    rate_field: str  # "supply_apy" for A_TOKEN callers, "borrow_apy" for DEBT_TOKEN


def resolve_lending_underlying(
    instrument_key: str,
    instrument_type: InstrumentType,
) -> LendingUnderlyingRef | None:
    """Decompose a canonical A_TOKEN/DEBT_TOKEN ``instrument_key`` into the
    ``(protocol, chain, underlying_symbol)`` a flat-``LENDING`` ``lending_indices`` row
    is keyed by, plus which rate column answers this instrument's question.

    ``instrument_key`` is the instruments-service-minted form
    ``{PROTOCOL}-{CHAIN}:{TYPE}:{SYMBOL}`` (e.g. ``AAVE_V3-ETHEREUM:A_TOKEN:AUSDC``).
    Pure string decomposition -- no instruments-service API call, no GCS/manifest read.
    Callers still perform the actual ``lending_indices`` row lookup for
    ``(protocol, chain, underlying_symbol, day)`` against MTDS raw_tick_data via their
    existing read path (e.g. the canonical parquet reader); this function only resolves
    the join key.

    Returns ``None`` -- an honest absence, never a fabricated guess -- when
    ``instrument_type`` isn't A_TOKEN/DEBT_TOKEN, the key doesn't parse, or the
    protocol uses the isolated-market synthesized symbol form with no single
    underlying reserve to join against (see module docstring).
    """
    if instrument_type not in (InstrumentType.A_TOKEN, InstrumentType.DEBT_TOKEN):
        return None

    venue_part, venue_sep, rest = instrument_key.partition(":")
    if not venue_sep:
        return None
    _type_tag, type_sep, symbol = rest.partition(":")
    if not type_sep or not symbol:
        return None

    protocol_tag, chain_sep, chain = venue_part.partition("-")
    if not chain_sep or not chain:
        return None
    protocol = protocol_tag.lower()
    if protocol not in _A_TOKEN_PREFIX_BY_PROTOCOL:
        return None

    if instrument_type is InstrumentType.A_TOKEN:
        prefix = _A_TOKEN_PREFIX_BY_PROTOCOL[protocol]
        rate_field = "supply_apy"
    else:
        prefix = _DEBT_TOKEN_PREFIX_BY_PROTOCOL[protocol]
        rate_field = "borrow_apy"

    if not symbol.startswith(prefix):
        return None
    underlying_symbol = symbol[len(prefix) :]
    if not underlying_symbol:
        return None

    return LendingUnderlyingRef(
        protocol=protocol,
        chain=chain,
        underlying_symbol=underlying_symbol,
        rate_field=rate_field,
    )
