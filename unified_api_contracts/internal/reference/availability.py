"""Per-day availability filter for InstrumentRecord catalogues.

SSOT for "was this instrument listed on date D?" logic. Consumers
(instruments-service, market-tick-data-service, features-*, strategy-service,
execution-service, risk-service, position-balance-monitor-service) MUST use
this function rather than re-implementing the `available_from/to` window
check locally.

Design notes
------------
- Pure function: the catalogue is *injected* (Iterable[InstrumentRecord]).
  UAC never reaches out to GCS / network — loading is a consumer concern.
- Window semantics:
    * ``available_from_datetime is None`` → instrument has existed since
      inception (treat as -infinity).
    * ``available_to_datetime is None``  → instrument is still active / open
      ended (treat as +infinity).
    * A day D is "in window" iff
          available_from_datetime.date() <= D <= available_to_datetime.date()
      with None bounds skipped per the rules above. Boundary dates are
      INCLUSIVE on both ends.
- Filter args (``category``, ``venue``, ``instrument_type``, ``chain``) are
  AND-combined. ``None`` = wildcard. Matching is case-insensitive.
- ``InstrumentRecord`` currently carries ``venue`` and ``instrument_type``
  but NOT ``category`` or ``chain`` as first-class fields (see
  ``internal/reference/instrument.py``). Phase 1.5 of the canonicalisation
  plan will populate ``category`` / ``chain``. Until then, records that
  don't expose those attributes are treated as wildcard matches for those
  filters (i.e. they match only when the caller passes ``None``). This is
  implemented via ``getattr(record, field, None)`` with an explicit sentinel
  so the filter semantics upgrade cleanly once the fields land.
"""

from __future__ import annotations

import datetime as _dt
from collections.abc import Iterable

from unified_api_contracts.internal.reference.instrument import InstrumentRecord


def _norm(value: str | None) -> str | None:
    """Lowercase-and-strip a filter arg, returning None for empty/None."""
    if value is None:
        return None
    stripped = value.strip()
    if not stripped:
        return None
    return stripped.lower()


def _record_field_str(record: InstrumentRecord, attr: str) -> str | None:
    """Extract a string attribute from a record, lowercased. None if missing/empty.

    Used for ``category`` / ``chain`` which may not yet be present on
    ``InstrumentRecord`` (see module docstring). When the attribute is
    absent we treat the record as having no declared value for that axis.
    """
    raw: object = getattr(record, attr, None)
    if raw is None:
        return None
    as_str = str(raw).strip()
    if not as_str:
        return None
    return as_str.lower()


def _instrument_type_str(record: InstrumentRecord) -> str:
    """Return the instrument_type as a lowercase string.

    ``instrument_type`` is a ``StrEnum``; ``str(enum_member)`` yields the
    value (e.g. ``"FUTURE"``), so we just lowercase it.
    """
    return str(record.instrument_type).strip().lower()


def _is_in_window(record: InstrumentRecord, ref_date: _dt.date) -> bool:
    """Return True iff ``ref_date`` falls within the instrument's availability window.

    None bounds are open-ended (see module docstring).
    """
    from_dt = record.available_from_datetime
    to_dt = record.available_to_datetime
    if from_dt is not None and ref_date < from_dt.date():
        return False
    return not (to_dt is not None and ref_date > to_dt.date())


def get_instruments_available_on(
    ref_date: _dt.date,
    catalogue: Iterable[InstrumentRecord],
    category: str | None = None,
    venue: str | None = None,
    instrument_type: str | None = None,
    chain: str | None = None,
) -> list[InstrumentRecord]:
    """Filter ``catalogue`` to records available on ``ref_date``.

    Parameters
    ----------
    ref_date:
        The calendar date to test. Inclusive on both ``available_from`` and
        ``available_to`` boundaries.
    catalogue:
        Iterable of ``InstrumentRecord`` (loaded by the caller — UAC does not
        fetch from GCS).
    category:
        Optional category filter (e.g. ``"cefi"``, ``"defi"``, ``"tradfi"``,
        ``"sports"``, ``"prediction"``). Case-insensitive. ``None`` = wildcard.
    venue:
        Optional venue filter (e.g. ``"BINANCE_FUTURES"``). Case-insensitive.
        ``None`` = wildcard.
    instrument_type:
        Optional instrument-type filter (e.g. ``"FUTURE"``, ``"PERPETUAL"``).
        Case-insensitive. ``None`` = wildcard.
    chain:
        Optional DeFi chain filter (e.g. ``"ethereum"``). Case-insensitive.
        ``None`` = wildcard.

    Returns
    -------
    list[InstrumentRecord]
        Records that satisfy all active filters AND the availability window
        on ``ref_date``. Preserves input ordering.
    """
    cat_f = _norm(category)
    venue_f = _norm(venue)
    itype_f = _norm(instrument_type)
    chain_f = _norm(chain)

    results: list[InstrumentRecord] = []
    for record in catalogue:
        if not _is_in_window(record, ref_date):
            continue
        if venue_f is not None and record.venue.strip().lower() != venue_f:
            continue
        if itype_f is not None and _instrument_type_str(record) != itype_f:
            continue
        if cat_f is not None:
            rec_cat = _record_field_str(record, "category")
            if rec_cat != cat_f:
                continue
        if chain_f is not None:
            rec_chain = _record_field_str(record, "chain")
            if rec_chain != chain_f:
                continue
        results.append(record)
    return results


__all__ = ["get_instruments_available_on"]
