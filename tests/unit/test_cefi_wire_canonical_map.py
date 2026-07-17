"""Tests for canonical/domain/cefi_wire_canonical.py — the cefi wire↔canonical map SSOT.

The load-bearing test here is ``test_both_bybit_rows_resolve_neither_excluded``:
it is the regression guard for the WHOLE canonical-completeness program. If the
key ever regresses to a 2-tuple, ``(BYBIT, BTCUSDT)`` becomes ambiguous, the
majors get excluded, the writer falls through to wrapped-wire ids, and those do
not join against the migration's decomposed form.
"""

from __future__ import annotations

from unified_api_contracts.canonical.domain.cefi_wire_canonical import (
    CeFiWireCanonicalMap,
)

# ---------------------------------------------------------------------------
# Fixtures — quads mirroring the real catalogue shapes
# ---------------------------------------------------------------------------

# (venue, instrument_type, raw_symbol, instrument_key)
_BITFINEX_PERP = (
    "BITFINEX-FUTURES",
    "PERPETUAL",
    "ADAF0:USTF0",
    "BITFINEX-FUTURES:PERPETUAL:ADA-USDT@LIN",
)
# The marquee 2-tuple clash: same venue, same wire symbol, two instrument types.
_BYBIT_SPOT = ("BYBIT", "SPOT_PAIR", "BTCUSDT", "BYBIT:SPOT_PAIR:BTC-USDT")
_BYBIT_PERP = ("BYBIT", "PERPETUAL", "BTCUSDT", "BYBIT:PERPETUAL:BTC-USDT@LIN")

# Genuinely ambiguous even on the 3-tuple: one dated-future wire symbol that
# resolves to two distinct ids (a real expiry-collision / rebuild-debris class).
_AMBIGUOUS_A = ("OKX-FUTURES", "FUTURE", "BTC-USD-200103", "OKX-FUTURES:FUTURE:BTC-USD@INV-20200103")
_AMBIGUOUS_B = ("OKX-FUTURES", "FUTURE", "BTC-USD-200103", "OKX-FUTURES:FUTURE:BTC-USD@INV-20200104")

_AMBIGUOUS_KEY = ("OKX-FUTURES", "FUTURE", "BTC-USD-200103")

_ALL_ROWS = [_BITFINEX_PERP, _BYBIT_SPOT, _BYBIT_PERP, _AMBIGUOUS_A, _AMBIGUOUS_B]


def _map() -> CeFiWireCanonicalMap:
    return CeFiWireCanonicalMap.from_rows(_ALL_ROWS)


# ---------------------------------------------------------------------------
# Forward resolution — the 3-tuple disambiguation (program regression guard)
# ---------------------------------------------------------------------------


def test_both_bybit_rows_resolve_neither_excluded() -> None:
    """THE program regression guard — instrument_type disambiguates the majors.

    A 2-tuple key would make (BYBIT, BTCUSDT) ambiguous and exclude BOTH rows.
    The 3-tuple must resolve each to exactly one id, and exclude neither.
    """
    m = _map()

    assert m.canonical_for("BYBIT", "SPOT_PAIR", "BTCUSDT") == "BYBIT:SPOT_PAIR:BTC-USDT"
    assert m.canonical_for("BYBIT", "PERPETUAL", "BTCUSDT") == "BYBIT:PERPETUAL:BTC-USDT@LIN"

    # Neither is honest-unresolved — the whole point of the 3-tuple.
    assert ("BYBIT", "SPOT_PAIR", "BTCUSDT") not in m.ambiguous_wire_keys
    assert ("BYBIT", "PERPETUAL", "BTCUSDT") not in m.ambiguous_wire_keys


def test_canonical_for_wrapped_wire_symbol() -> None:
    """A colon-bearing wire symbol (ADAF0:USTF0) resolves to the decomposed id."""
    m = _map()
    assert m.canonical_for("BITFINEX-FUTURES", "PERPETUAL", "ADAF0:USTF0") == "BITFINEX-FUTURES:PERPETUAL:ADA-USDT@LIN"


def test_canonical_for_unknown_key_returns_none() -> None:
    m = _map()
    assert m.canonical_for("BYBIT", "PERPETUAL", "NOSUCHCOIN") is None
    assert m.canonical_for("NOSUCHVENUE", "PERPETUAL", "BTCUSDT") is None
    # Right venue + symbol, wrong type → no guess.
    assert m.canonical_for("BITFINEX-FUTURES", "SPOT_PAIR", "ADAF0:USTF0") is None


# ---------------------------------------------------------------------------
# Ambiguity — excluded, never guessed
# ---------------------------------------------------------------------------


def test_ambiguous_key_is_excluded_and_reported() -> None:
    """Honest-unresolved: absent from the forward map AND present in the set."""
    m = _map()

    assert m.canonical_for("OKX-FUTURES", "FUTURE", "BTC-USD-200103") is None
    assert _AMBIGUOUS_KEY in m.ambiguous_wire_keys
    assert _AMBIGUOUS_KEY not in m.canonical_by_wire


def test_ambiguous_set_holds_only_genuine_conflicts() -> None:
    m = _map()
    assert m.ambiguous_wire_keys == frozenset({_AMBIGUOUS_KEY})


def test_duplicate_identical_rows_are_not_ambiguous() -> None:
    """The same row twice is one id, not a conflict — dedup, don't exclude."""
    m = CeFiWireCanonicalMap.from_rows([_BYBIT_PERP, _BYBIT_PERP])

    assert m.canonical_for("BYBIT", "PERPETUAL", "BTCUSDT") == "BYBIT:PERPETUAL:BTC-USDT@LIN"
    assert m.ambiguous_wire_keys == frozenset()


# ---------------------------------------------------------------------------
# Reverse resolution — round-trip
# ---------------------------------------------------------------------------


def test_raw_symbol_for_round_trips() -> None:
    m = _map()

    for venue, instrument_type, raw_symbol, instrument_key in (_BITFINEX_PERP, _BYBIT_SPOT, _BYBIT_PERP):
        assert m.canonical_for(venue, instrument_type, raw_symbol) == instrument_key
        assert m.raw_symbol_for(venue, instrument_key) == raw_symbol


def test_reverse_map_resolves_both_bybit_ids_to_the_same_wire_symbol() -> None:
    """Reverse is injective on instrument_key — no instrument_type needed."""
    m = _map()

    assert m.raw_symbol_for("BYBIT", "BYBIT:SPOT_PAIR:BTC-USDT") == "BTCUSDT"
    assert m.raw_symbol_for("BYBIT", "BYBIT:PERPETUAL:BTC-USDT@LIN") == "BTCUSDT"


def test_reverse_map_covers_forward_ambiguous_keys() -> None:
    """A forward-ambiguous wire key still reverses per distinct id.

    The reverse axis is keyed on instrument_key, which stays unique even when
    the wire symbol collides — so candidate-stem recovery must keep working.
    """
    m = _map()

    assert m.raw_symbol_for("OKX-FUTURES", "OKX-FUTURES:FUTURE:BTC-USD@INV-20200103") == "BTC-USD-200103"
    assert m.raw_symbol_for("OKX-FUTURES", "OKX-FUTURES:FUTURE:BTC-USD@INV-20200104") == "BTC-USD-200103"


def test_raw_symbol_for_unknown_returns_none() -> None:
    m = _map()
    assert m.raw_symbol_for("BYBIT", "BYBIT:PERPETUAL:NOSUCH-USDT@LIN") is None
    assert m.raw_symbol_for("NOSUCHVENUE", "BYBIT:SPOT_PAIR:BTC-USDT") is None


def test_reverse_preserves_wire_symbol_case() -> None:
    """Filename stems are rebuilt from this value — the on-disk spelling wins."""
    m = CeFiWireCanonicalMap.from_rows([("BINANCE-SPOT", "SPOT_PAIR", "btcusdt", "BINANCE-SPOT:SPOT_PAIR:BTC-USDT")])

    assert m.raw_symbol_for("BINANCE-SPOT", "BINANCE-SPOT:SPOT_PAIR:BTC-USDT") == "btcusdt"


# ---------------------------------------------------------------------------
# Case-insensitivity — build side and lookup side
# ---------------------------------------------------------------------------


def test_lookup_is_case_insensitive() -> None:
    m = _map()

    assert m.canonical_for("bybit", "perpetual", "btcusdt") == "BYBIT:PERPETUAL:BTC-USDT@LIN"
    assert m.canonical_for("ByBiT", "PeRpEtUaL", "BtCuSdT") == "BYBIT:PERPETUAL:BTC-USDT@LIN"
    assert m.raw_symbol_for("bybit", "BYBIT:PERPETUAL:BTC-USDT@LIN") == "BTCUSDT"


def test_build_is_case_insensitive() -> None:
    """BINANCE puts a lowercase symbol on the tape — it must key the same row."""
    m = CeFiWireCanonicalMap.from_rows([("binance-spot", "spot_pair", "btcusdt", "BINANCE-SPOT:SPOT_PAIR:BTC-USDT")])

    assert m.canonical_for("BINANCE-SPOT", "SPOT_PAIR", "BTCUSDT") == "BINANCE-SPOT:SPOT_PAIR:BTC-USDT"


def test_case_variant_rows_collapse_to_one_key() -> None:
    """Two spellings of one row are one key, not an ambiguity."""
    m = CeFiWireCanonicalMap.from_rows(
        [
            ("BYBIT", "PERPETUAL", "BTCUSDT", "BYBIT:PERPETUAL:BTC-USDT@LIN"),
            ("bybit", "perpetual", "btcusdt", "BYBIT:PERPETUAL:BTC-USDT@LIN"),
        ]
    )

    assert m.canonical_for("BYBIT", "PERPETUAL", "BTCUSDT") == "BYBIT:PERPETUAL:BTC-USDT@LIN"
    assert m.ambiguous_wire_keys == frozenset()


def test_lookup_tolerates_surrounding_whitespace() -> None:
    m = _map()
    assert m.canonical_for(" BYBIT ", " PERPETUAL ", " BTCUSDT ") == "BYBIT:PERPETUAL:BTC-USDT@LIN"
    assert m.raw_symbol_for(" BYBIT ", " BYBIT:PERPETUAL:BTC-USDT@LIN ") == "BTCUSDT"


# ---------------------------------------------------------------------------
# Blank fields — skipped, never keyed
# ---------------------------------------------------------------------------


def test_blank_fields_are_skipped() -> None:
    """A blank in ANY of the four fields drops the row — a blank keys nothing."""
    m = CeFiWireCanonicalMap.from_rows(
        [
            ("", "PERPETUAL", "BTCUSDT", "BYBIT:PERPETUAL:BTC-USDT@LIN"),
            ("BYBIT", "", "BTCUSDT", "BYBIT:PERPETUAL:BTC-USDT@LIN"),
            ("BYBIT", "PERPETUAL", "", "BYBIT:PERPETUAL:BTC-USDT@LIN"),
            ("BYBIT", "PERPETUAL", "BTCUSDT", ""),
            ("   ", "PERPETUAL", "BTCUSDT", "BYBIT:PERPETUAL:BTC-USDT@LIN"),
        ]
    )

    assert m.canonical_by_wire == {}
    assert m.wire_by_canonical == {}
    assert m.ambiguous_wire_keys == frozenset()


def test_blank_row_does_not_shadow_a_good_row() -> None:
    m = CeFiWireCanonicalMap.from_rows([("BYBIT", "PERPETUAL", "BTCUSDT", ""), _BYBIT_PERP])

    assert m.canonical_for("BYBIT", "PERPETUAL", "BTCUSDT") == "BYBIT:PERPETUAL:BTC-USDT@LIN"
    assert m.ambiguous_wire_keys == frozenset()


def test_blank_lookup_returns_none() -> None:
    m = _map()
    assert m.canonical_for("", "PERPETUAL", "BTCUSDT") is None
    assert m.canonical_for("BYBIT", "PERPETUAL", "") is None
    assert m.raw_symbol_for("BYBIT", "") is None


# ---------------------------------------------------------------------------
# Construction edge cases
# ---------------------------------------------------------------------------


def test_from_rows_empty_builds_empty_map() -> None:
    """Empty is a valid pure value — fail-loud on an empty catalogue is the
    CALLER's job (the registered prod resolver), not this pure contract's."""
    m = CeFiWireCanonicalMap.from_rows([])

    assert m.canonical_by_wire == {}
    assert m.wire_by_canonical == {}
    assert m.ambiguous_wire_keys == frozenset()


def test_from_rows_accepts_a_generator() -> None:
    m = CeFiWireCanonicalMap.from_rows(row for row in _ALL_ROWS)
    assert m.canonical_for("BYBIT", "SPOT_PAIR", "BTCUSDT") == "BYBIT:SPOT_PAIR:BTC-USDT"


def test_map_is_exported_from_package_root() -> None:
    """The root package is the public surface — deep paths are UAC-internal."""
    import unified_api_contracts

    assert unified_api_contracts.CeFiWireCanonicalMap is CeFiWireCanonicalMap
    assert "CeFiWireCanonicalMap" in unified_api_contracts.__all__
