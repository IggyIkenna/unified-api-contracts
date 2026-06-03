"""Canonical instrument_key parser — ``VENUE:INSTRUMENT_TYPE:SYMBOL``.

Every market-data identifier used across the UTS pipeline follows the
three-component canonical form defined here.  This module is the single
source of truth for parsing, validating, and formatting ``instrument_key``
values.

Codex SSOT: codex/06-coding-standards/cli-convention.md
            § "Instrument Identity and CLI Granularity"
Architecture audit: plans/active/mdps_long_running_multi_shard_architecture_audit_2026_05_28.md
                    § Phase 3.1

Canonical form
--------------
``VENUE:INSTRUMENT_TYPE:SYMBOL``

Examples::

    BINANCE-FUTURES:PERPETUAL:BTCUSDT
    BYBIT:PERPETUAL:ETHUSDT
    DERIBIT:OPTION:BTC-28JUN24-70000-C
    BINANCE-SPOT:SPOT_PAIR:BTCUSDT

Rules
-----
* Three colon-separated segments.  Split on the **first two** colons only so
  that option symbols containing ``:`` (e.g. ``BTC-28JUN24-70000-C``) parse
  correctly.
* All segments are non-empty strings.  Leading/trailing whitespace is not
  permitted; no normalisation is applied.
* ``INSTRUMENT_TYPE`` is stored uppercase in canonical form, but blob-path
  hive segments use lowercase (``instrument_type=perpetual/``).  Callers that
  compare against blob paths must lower-case before matching.

Axis derivability
-----------------
Given only an ``instrument_key``:

+------------------+-------------------+
| Axis             | Derivable?        |
+==================+===================+
| venue            | Yes — segment[0]  |
+------------------+-------------------+
| instrument_type  | Yes — segment[1]  |
+------------------+-------------------+
| symbol           | Yes — segment[2]  |
+------------------+-------------------+
| data_type        | No — independent  |
+------------------+-------------------+
| asset_group      | No — independent  |
+------------------+-------------------+
| date             | No — independent  |
+------------------+-------------------+

The **atomic shard** is ``(asset_group, venue, instrument_type, data_type,
symbol, date)``.  An ``instrument_key`` pins three of the six axes.

Legacy bare-symbol form
-----------------------
Some callers still pass bare symbols (e.g. ``BTCUSDT``) inherited from earlier
pipeline versions.  The ``parse_instrument_key`` function returns ``None`` for
bare symbols; callers should fall back to substring matching and emit a
deprecation log.  The bare-symbol form is **not** the documented surface and
will be removed in a future release.
"""

from __future__ import annotations


def parse_instrument_key(iid: str) -> tuple[str, str, str] | None:
    """Parse an ``instrument_key`` into its three canonical axes.

    Args:
        iid: Candidate identifier.  Either the canonical
             ``VENUE:INSTRUMENT_TYPE:SYMBOL`` form or a legacy bare-symbol
             string such as ``BTCUSDT``.

    Returns:
        ``(venue, instrument_type, symbol)`` when *iid* is a valid canonical
        key.  ``None`` when *iid* is a bare symbol, malformed, or has any
        empty segment.  This function never raises.

    Examples::

        >>> parse_instrument_key("BINANCE-FUTURES:PERPETUAL:BTCUSDT")
        ('BINANCE-FUTURES', 'PERPETUAL', 'BTCUSDT')

        >>> parse_instrument_key("DERIBIT:OPTION:BTC-28JUN24-70000-C")
        ('DERIBIT', 'OPTION', 'BTC-28JUN24-70000-C')

        >>> parse_instrument_key("BTCUSDT")  # bare symbol — legacy
        None

        >>> parse_instrument_key("BINANCE-FUTURES:PERPETUAL:")  # empty symbol
        None
    """
    parts: list[str] = iid.split(":", 2)
    if len(parts) != 3:
        return None
    venue, instrument_type, symbol = parts[0], parts[1], parts[2]
    if not venue or not instrument_type or not symbol:
        return None
    return venue, instrument_type, symbol


def format_instrument_key(venue: str, instrument_type: str, symbol: str) -> str:
    """Construct a canonical ``instrument_key`` from its three components.

    Args:
        venue:           Exchange/venue identifier, e.g. ``BINANCE-FUTURES``.
        instrument_type: Instrument class in uppercase, e.g. ``PERPETUAL``.
        symbol:          Venue-native ticker, e.g. ``BTCUSDT``.

    Returns:
        Canonical ``VENUE:INSTRUMENT_TYPE:SYMBOL`` string.

    Raises:
        ValueError: If any segment is empty.
    """
    if not venue or not instrument_type or not symbol:
        raise ValueError(
            f"All segments must be non-empty: venue={venue!r}, instrument_type={instrument_type!r}, symbol={symbol!r}"
        )
    return f"{venue}:{instrument_type}:{symbol}"


def derive_venue_set(instrument_keys: list[str]) -> set[str]:
    """Extract the distinct venue axis values from a list of instrument keys.

    Keys that fail to parse as canonical are silently skipped.
    """
    return {parsed[0] for iid in instrument_keys if (parsed := parse_instrument_key(iid))}


def derive_instrument_type_set(instrument_keys: list[str]) -> set[str]:
    """Extract the distinct instrument_type axis values from a list of keys.

    Keys that fail to parse as canonical are silently skipped.
    """
    return {parsed[1] for iid in instrument_keys if (parsed := parse_instrument_key(iid))}


def derive_symbol_set(instrument_keys: list[str]) -> set[str]:
    """Extract the distinct symbol axis values from a list of instrument keys.

    Keys that fail to parse as canonical are silently skipped.
    """
    return {parsed[2] for iid in instrument_keys if (parsed := parse_instrument_key(iid))}
