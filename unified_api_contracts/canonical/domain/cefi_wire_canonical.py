"""CeFi wire↔canonical identity map — the single contract SSOT.

Defines ``CeFiWireCanonicalMap``: the pure, in-memory contract that maps a
venue's **wire** symbol (what the exchange actually puts on the tape, e.g.
``ADAF0:USTF0``) to our **canonical** ``instrument_id`` (e.g.
``BITFINEX-FUTURES:PERPETUAL:ADA-USDT@LIN``), and back.

Every cefi surface — the writer's parquet ``instrument_id`` column, the GCS
filename stem, the manifest key, and reader resolution — keys off THIS map, so
all four agree byte-for-byte (the "shard atom identical" HARD RULE) and
``paper(W) == batch-rerun(W)``.

**The key is a 3-tuple** ``(venue, instrument_type, raw_symbol)`` — never a
2-tuple. Measured against the live catalogue (424,699 rows, 2026-07-17): the
2-tuple ``(venue, raw_symbol)`` yields **781 ambiguous keys**, the 3-tuple only
**439** — it rescues 342. The marquee case: ``(BYBIT, BTCUSDT)`` maps to BOTH
``BYBIT:SPOT_PAIR:BTC-USDT`` AND ``BYBIT:PERPETUAL:BTC-USDT@LIN``, so a 2-tuple
builder EXCLUDES exactly the majors this program exists to fix — the writer then
falls through to wrapped-wire ids that do NOT join against the migration's
decomposed form. ``instrument_type`` disambiguates both to exactly one id.

**Ambiguous keys are excluded, never guessed** (honest-unresolved): a 3-tuple
resolving to >1 distinct ``instrument_key`` is dropped from the forward map and
recorded in ``ambiguous_wire_keys``, so writer and reader honest-drop the SAME
set. Callers treat a ``None`` lookup as "leave the value alone", never as
licence to invent an id.

This module is **pure — pandas-free and I/O-free by design**. Both
market-tick-data-service and market-data-processing-service depend on UAC and
never on each other, so the map lives here while each service supplies its own
thin catalogue loader that reads the parquet and feeds ``from_rows()``. Keeping
UAC dependency-light is why the constructor takes plain tuples, not a DataFrame.

Rows are always sourced from the catalogue's ``instrument_id`` column, NEVER
``canonical_instrument_id`` — the latter is a stale/vestigial trap that still
holds raw-glued forms (e.g. ``BINANCE-DELIVERY:FUTURE:ADAUSD_200925``).

Usage::

    from unified_api_contracts.canonical.domain.cefi_wire_canonical import (
        CeFiWireCanonicalMap,
    )

    m = CeFiWireCanonicalMap.from_rows(
        [
            ("BYBIT", "SPOT_PAIR", "BTCUSDT", "BYBIT:SPOT_PAIR:BTC-USDT"),
            ("BYBIT", "PERPETUAL", "BTCUSDT", "BYBIT:PERPETUAL:BTC-USDT@LIN"),
        ]
    )
    m.canonical_for("BYBIT", "PERPETUAL", "btcusdt")
    # → "BYBIT:PERPETUAL:BTC-USDT@LIN"
    m.raw_symbol_for("BYBIT", "BYBIT:PERPETUAL:BTC-USDT@LIN")
    # → "BTCUSDT"

SSOT: plans/active/issues/_cefi_canonical_blueprint_2026_07_17.md § 2 "FIX 0".
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass

__all__ = ["CeFiWireCanonicalMap"]


def _norm(value: str) -> str:
    """Uppercase + strip one wire-key field.

    Applied identically at build time and at lookup time so a lowercase wire
    symbol (BINANCE puts ``btcusdt`` on the tape) resolves against a catalogue
    row spelled ``BTCUSDT``.
    """
    return value.strip().upper()


def _iter_normalized(
    rows: Iterable[tuple[str, str, str, str]],
) -> Iterator[tuple[str, str, str, str, str]]:
    """Normalize input quads, dropping any row with a blank field.

    Yields ``(venue, instrument_type, raw_symbol, instrument_key, wire_symbol)``
    where the first three are uppercased key fields, ``instrument_key`` is
    stripped-but-verbatim (it is already canonical), and ``wire_symbol`` is the
    raw symbol with its original case preserved for the reverse map.

    A blank in ANY field drops the row: a blank cannot key anything, and
    substituting a value for it would be a silent guess.
    """
    for venue, instrument_type, raw_symbol, instrument_key in rows:
        key_venue = _norm(venue)
        key_type = _norm(instrument_type)
        key_raw = _norm(raw_symbol)
        key_id = instrument_key.strip()
        if not (key_venue and key_type and key_raw and key_id):
            continue
        yield key_venue, key_type, key_raw, key_id, raw_symbol.strip()


@dataclass(frozen=True)
class CeFiWireCanonicalMap:
    """Immutable wire↔canonical identity map for cefi instruments.

    Build it with :meth:`from_rows`; never construct the fields directly — the
    classmethod is what enforces the ambiguity exclusion that makes the map
    honest.

    Attributes:
        canonical_by_wire: FORWARD map, ``(venue, instrument_type, raw_symbol)``
            → ``instrument_key``. All three key fields are uppercased. Contains
            only unambiguously-resolving keys; see ``ambiguous_wire_keys``.
        wire_by_canonical: REVERSE map, ``(venue, instrument_key)`` →
            ``raw_symbol``. Injective by construction — ``instrument_key`` is
            unique — so no ``instrument_type`` is needed on this axis. The
            ``raw_symbol`` value is stored VERBATIM (case preserved), because
            callers reconstruct on-disk filename stems from it and the wire
            spelling is what is actually on the object.
        ambiguous_wire_keys: The honest-unresolved set — every 3-tuple that
            resolved to more than one distinct ``instrument_key``. Excluded from
            ``canonical_by_wire`` (never guessed) and reported as ONE number by
            every surface (writer WARNING, reader honest-fallback, migration).
    """

    canonical_by_wire: dict[tuple[str, str, str], str]
    wire_by_canonical: dict[tuple[str, str], str]
    ambiguous_wire_keys: frozenset[tuple[str, str, str]]

    @classmethod
    def from_rows(cls, rows: Iterable[tuple[str, str, str, str]]) -> CeFiWireCanonicalMap:
        """Build the map from ``(venue, instrument_type, raw_symbol, instrument_key)`` rows.

        Named ``from_rows`` (not the blueprint's provisional ``from_triples``)
        because the arity is 4, not 3: the KEY is a 3-tuple, but each input row
        carries the resolved ``instrument_key`` alongside it. ``from_triples``
        would misname the input; this is the one exported constructor.

        Rows are typically the catalogue's ``venue`` / ``instrument_type`` /
        ``raw_symbol`` / ``instrument_id`` columns, zipped by the caller's own
        loader (UAC stays pandas-free — see the module docstring).

        Args:
            rows: Iterable of ``(venue, instrument_type, raw_symbol,
                instrument_key)``. Any row with a blank field (after strip) is
                skipped — see ``_iter_normalized``.

        Returns:
            A ``CeFiWireCanonicalMap``. Keys resolving to >1 distinct
            ``instrument_key`` land in ``ambiguous_wire_keys`` and are ABSENT
            from the forward map (honest-unresolved, never guessed).
        """
        by_wire: dict[tuple[str, str, str], set[str]] = {}
        reverse: dict[tuple[str, str], str] = {}

        for key_venue, key_type, key_raw, key_id, wire in _iter_normalized(rows):
            by_wire.setdefault((key_venue, key_type, key_raw), set()).add(key_id)
            # Reverse stays valid even for forward-ambiguous keys: each distinct
            # instrument_key maps back to its own wire symbol unambiguously.
            # First row wins so the map is deterministic if a defective
            # catalogue ever repeats an instrument_key with two spellings.
            reverse.setdefault((key_venue, key_id), wire)

        ambiguous = frozenset(k for k, ids in by_wire.items() if len(ids) > 1)
        canonical = {k: next(iter(ids)) for k, ids in by_wire.items() if len(ids) == 1}

        return cls(
            canonical_by_wire=canonical,
            wire_by_canonical=reverse,
            ambiguous_wire_keys=ambiguous,
        )

    def canonical_for(self, venue: str, instrument_type: str, raw_symbol: str) -> str | None:
        """Resolve a wire symbol to its canonical ``instrument_key``.

        Args:
            venue: Venue id (case-insensitive), e.g. ``BYBIT``.
            instrument_type: Instrument type (case-insensitive), e.g.
                ``PERPETUAL``. Load-bearing — it is what disambiguates the
                spot/perp wire-symbol clash on the majors.
            raw_symbol: The venue's wire symbol (case-insensitive), e.g.
                ``BTCUSDT``.

        Returns:
            The canonical ``instrument_key``, or ``None`` when the key is
            unknown or ambiguous. ``None`` means "leave the value as-is"
            (honest) — never a licence to guess.
        """
        return self.canonical_by_wire.get((_norm(venue), _norm(instrument_type), _norm(raw_symbol)))

    def raw_symbol_for(self, venue: str, instrument_key: str) -> str | None:
        """Recover the venue's wire symbol for a canonical ``instrument_key``.

        The inverse of :meth:`canonical_for`, used to build candidate filename
        stems during the MIXED window when an object may be on disk under
        either the wire or the canonical spelling.

        Args:
            venue: Venue id (case-insensitive).
            instrument_key: The canonical instrument id (matched verbatim).

        Returns:
            The wire ``raw_symbol`` with its original case, or ``None`` when
            the pair is unknown.
        """
        return self.wire_by_canonical.get((_norm(venue), instrument_key.strip()))
