"""Instruments-service catalog read contract — SSOT for all asset groups.

Defines ``CatalogRow`` (the per-instrument lifecycle shape) and
``list_instruments()`` (the uniform read interface). Every consumer that
needs to derive an expected universe — the writegate Phase 3.D.5 v2
enumerator, the MTDS preflight skip-check, the data-status drilldown, and
the MDPS dependency gate — reads through this contract, not directly from
GCS paths.

Convention (codified in CLAUDE.md after v2 ships):
  MTDS / instruments-service / data-status missing-data checks for any
  asset_group derive their expected universe from this catalog interface,
  NOT from inline / hardcoded venue / data_type / date lists.

Usage::

    from unified_api_contracts.canonical.domain.instruments_catalog import (
        list_instruments,
        CatalogRow,
    )

    for row in list_instruments("sports", date(2025, 1, 1), date(2025, 12, 31)):
        # row.league_id, row.fixture_id, row.kickoff_time, ...
        ...
"""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date
from typing import Protocol, runtime_checkable

from pydantic import AwareDatetime

from unified_api_contracts._instrument_enums import InstrumentType

from ._base import CanonicalBase

# ---------------------------------------------------------------------------
# CatalogRow — per-instrument lifecycle shape
# ---------------------------------------------------------------------------


class CatalogRow(CanonicalBase):
    """One row from the instruments-service catalog for a single instrument.

    Shared columns (all asset groups):

    - ``asset_group``: one of cefi / defi / tradfi / sports / prediction
    - ``venue``: exchange / bookmaker / protocol identifier
    - ``data_type``: uppercase string matching MTDS / MDPS data_type registry
    - ``instrument_type``: UAC InstrumentType enum value
    - ``instrument_id``: canonical instrument identifier — asset_group specific:
        cefi/tradfi → ticker or symbol (BTC-USDT, ES, AAPL)
        defi → pool_address or protocol_instrument_id
        sports → fixture_id (per-fixture) or league_id (per-league aggregate)
        prediction → market_id or canonical_question_group

    Lifecycle columns (presence varies by asset_group — use None when absent):

    - ``available_from``: first date this instrument is visible in our pipeline
    - ``available_to``: last date (None = still active / no known end)
    - ``expiry``: contract expiry (futures, options, prediction market settlement)

    Sports-specific columns:

    - ``league_id``: numerical league identifier (API-Football league_id)
    - ``fixture_id``: numerical fixture identifier (None for league-aggregate rows)
    - ``kickoff_time``: UTC kickoff datetime (None for league-aggregate rows)
    - ``fixture_status``: e.g. "NS" (not-started), "FT" (full-time), "PST" (postponed)
    - ``season``: season year (e.g. 2024 for 2024/25 season)

    CeFi / TradFi additional columns:

    - ``chain``: blockchain identifier for DeFi (None otherwise)
    - ``instrument_type``: SPOT_PAIR / PERPETUAL / FUTURE / OPTION / ETF / etc.
    - ``margin_type``: linear / inverse / quanto (derivatives only, None otherwise)
    - ``quote_asset``: settlement currency (USDT, USD, BTC — None when n/a)

    Prediction-specific:

    - ``canonical_question_group``: e.g. "US_ELECTION_2024", "CRYPTO_BTC_DAILY"
    - ``resolution_time``: when the market resolves (None if ongoing)
    """

    asset_group: str
    venue: str
    data_type: str
    instrument_type: InstrumentType
    instrument_id: str

    # Lifecycle
    available_from: date | None = None
    available_to: date | None = None
    expiry: date | None = None

    # Sports
    league_id: int | None = None
    fixture_id: int | None = None
    kickoff_time: AwareDatetime | None = None
    fixture_status: str | None = None
    season: int | None = None

    # CeFi / DeFi / TradFi
    chain: str | None = None
    margin_type: str | None = None
    quote_asset: str | None = None

    # Prediction
    canonical_question_group: str | None = None
    resolution_time: AwareDatetime | None = None


# ---------------------------------------------------------------------------
# InstrumentCatalogReader — pluggable backend Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class InstrumentCatalogReader(Protocol):
    """Backend that reads the instruments-service GCS catalog for one asset_group.

    Implementations live in instruments-service and register themselves via
    ``get_catalog_reader(asset_group)``. Consumers import the Protocol and
    call ``list_instruments()`` (the public API below) — they never import
    the concrete reader directly.
    """

    def list_instruments(
        self,
        asset_group: str,
        start_date: date,
        end_date: date,
        *,
        data_types: list[str] | None = None,
        venues: list[str] | None = None,
    ) -> Iterator[CatalogRow]:
        """Yield CatalogRows active during [start_date, end_date] inclusive.

        Args:
            asset_group: One of cefi / defi / tradfi / sports / prediction.
            start_date: First date of the query window (inclusive).
            end_date: Last date of the query window (inclusive).
            data_types: Optional filter — only yield rows for these data_types.
            venues: Optional filter — only yield rows for these venues.

        Yields:
            ``CatalogRow`` instances ordered by (instrument_id, date) or
            (fixture_id, date) for sports. Each row represents one
            (instrument, date) pair that should have data in MTDS / MDPS.
        """
        ...


# ---------------------------------------------------------------------------
# Module-level registry — populated by instruments-service at startup
# ---------------------------------------------------------------------------

_READERS: dict[str, InstrumentCatalogReader] = {}


def register_catalog_reader(asset_group: str, reader: InstrumentCatalogReader) -> None:
    """Register a concrete InstrumentCatalogReader for ``asset_group``.

    Called once at instruments-service startup (or in unit tests via mock).
    Overwrites any existing registration — last write wins.
    """
    _READERS[asset_group] = reader


def list_instruments(
    asset_group: str,
    start_date: date,
    end_date: date,
    *,
    data_types: list[str] | None = None,
    venues: list[str] | None = None,
) -> Iterator[CatalogRow]:
    """Yield CatalogRows for ``asset_group`` active during [start_date, end_date].

    This is the single public entry point for all expected-universe derivation.
    Concrete backends are registered by instruments-service; tests inject mocks
    via ``register_catalog_reader()``.

    Args:
        asset_group: One of cefi / defi / tradfi / sports / prediction.
        start_date: First date of the query window (inclusive).
        end_date: Last date of the query window (inclusive).
        data_types: Optional list to restrict output to specific data_types.
        venues: Optional list to restrict output to specific venues.

    Yields:
        CatalogRow instances — one per (instrument, date) that should exist.

    Raises:
        KeyError: If no reader is registered for ``asset_group``.
    """
    reader = _READERS.get(asset_group)
    if reader is None:
        raise KeyError(
            f"No InstrumentCatalogReader registered for asset_group={asset_group!r}. Registered: {list(_READERS)}"
        )
    yield from reader.list_instruments(
        asset_group,
        start_date,
        end_date,
        data_types=data_types,
        venues=venues,
    )


def list_not_yet_listed_cefi(
    processing_date: date,
    *,
    venues: list[str] | None = None,
) -> Iterator[CatalogRow]:
    """Yield CatalogRows for CeFi instruments not yet listed on processing_date.

    Delegates to the registered "cefi" reader's list_not_yet_listed method when
    available. Returns an empty iterator when no reader is registered or the
    reader does not implement the method (e.g. stub readers in test environments).

    Used by the MTDS orchestrator to emit EXPECTED_INSTRUMENT_NOT_LISTED manifest
    rows for instruments whose available_from_datetime > processing_date,
    distinguishing the "not-listed-yet" gap from "out-of-window" (OKX expiry)
    and "blocked-key" (Tardis 401) gaps in the §3 coverage map.
    """
    reader = _READERS.get("cefi")
    if reader is None:
        return
    fn = getattr(reader, "list_not_yet_listed", None)
    if fn is None:
        return
    yield from fn(processing_date, venues=venues)
