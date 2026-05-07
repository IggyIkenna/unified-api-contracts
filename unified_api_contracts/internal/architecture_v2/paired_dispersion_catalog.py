"""SSOT for ``paired_price_dispersion`` catalog rows.

Static representation of the strategy-service catalog rows that the
features-cross-instrument-service ``paired_price_dispersion`` calculator
consumes. Lifted to UAC because:

1. features-cross-instrument-service must NOT depend on strategy-service
   (workspace import-graph rule).
2. The rows are pure data (archetype + params dict) — no Python compute,
   no runtime state.
3. The catalog spec slot label is a contract surface, so the canonical
   home is UAC.

Each row is a ``PairedDispersionCatalogRow`` (archetype + params).
``params`` mirrors ``TargetInstanceSpec.params`` from
``strategy-service/strategy_service/engine/strategies/v2/target_universe/
catalog.py``.

Active rows (11 total):

* CARRY_BASIS_DATED commodity single-instrument (3): ICE-CME crude /
  CME-CME gold / NYMEX-CME natgas
* CARRY_BASIS_DATED equity-index ETF-vs-future (2): CBOE-CME spx-es /
  CBOE-CME ndx-nq
* CARRY_BASIS_DATED crypto spot/dated (2): BINANCE-DERIBIT btc / eth
* CARRY_BASIS_DATED ETF-vs-CME-micro (2, Phase 9): NASDAQ-CME ibit-mbt /
  NASDAQ-CME etha-met
* CARRY_BASIS_DATED intra-Deribit (2, Phase 9): DERIBIT-DERIBIT btc / eth
* ARBITRAGE_PRICE_DISPERSION cross-venue dated futures (2, Phase 9):
  CME-DERIBIT mbt-btc / met-eth

Inactive rows (status=databento_pending — skipped by builder):

* CARRY_BASIS_DATED NYSE-CME ETF-vs-future placeholders (5): gld-gc /
  uso-cl / ung-ng / spy-es / qqq-nq

Updates to this catalog must be made HERE (not in strategy-service) and
then propagated downstream — strategy-service will source-of-truth from
UAC once the v2 target_universe migration completes.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PairedDispersionCatalogRow:
    """One paired_price_dispersion catalog row.

    Mirrors the shape of ``unified_api_contracts.internal.architecture_v2``
    target_universe ``TargetInstanceSpec`` (archetype + params), scoped
    to the dispatch surface.
    """

    archetype: str
    params: dict[str, str]


_PAIRED_DISPERSION_CATALOG_ROWS: list[PairedDispersionCatalogRow] = [
    # CARRY_BASIS_DATED — commodity single-instrument (3)
    PairedDispersionCatalogRow(
        archetype="CARRY_BASIS_DATED",
        params={
            "cash_venue": "ice",
            "future_venue": "cme",
            "instrument": "cl",
            "hold_policy": "HOLD_UNTIL_FLIP",
            "roll_on_dte": "10",
        },
    ),
    PairedDispersionCatalogRow(
        archetype="CARRY_BASIS_DATED",
        params={
            "cash_venue": "cme",
            "future_venue": "cme",
            "instrument": "gc",
            "hold_policy": "HOLD_UNTIL_FLIP",
            "roll_on_dte": "10",
        },
    ),
    PairedDispersionCatalogRow(
        archetype="CARRY_BASIS_DATED",
        params={
            "cash_venue": "nymex",
            "future_venue": "cme",
            "instrument": "ng",
            "hold_policy": "HOLD_UNTIL_FLIP",
            "roll_on_dte": "10",
        },
    ),
    # CARRY_BASIS_DATED — equity-index ETF-vs-future (2)
    PairedDispersionCatalogRow(
        archetype="CARRY_BASIS_DATED",
        params={
            "cash_venue": "cboe",
            "future_venue": "cme",
            "cash_instrument": "spx",
            "future_instrument": "es",
            "hold_policy": "HOLD_UNTIL_FLIP",
            "roll_on_dte": "7",
        },
    ),
    PairedDispersionCatalogRow(
        archetype="CARRY_BASIS_DATED",
        params={
            "cash_venue": "cboe",
            "future_venue": "cme",
            "cash_instrument": "ndx",
            "future_instrument": "nq",
            "hold_policy": "HOLD_UNTIL_FLIP",
            "roll_on_dte": "7",
        },
    ),
    # CARRY_BASIS_DATED — crypto spot/dated (2)
    PairedDispersionCatalogRow(
        archetype="CARRY_BASIS_DATED",
        params={
            "spot_venue": "binance",
            "dated_venue": "deribit",
            "instrument": "btc",
            "hold_policy": "HOLD_UNTIL_FLIP",
            "target_basis_bps": "50",
        },
    ),
    PairedDispersionCatalogRow(
        archetype="CARRY_BASIS_DATED",
        params={
            "spot_venue": "binance",
            "dated_venue": "deribit",
            "instrument": "eth",
            "hold_policy": "HOLD_UNTIL_FLIP",
            "target_basis_bps": "50",
        },
    ),
    # CARRY_BASIS_DATED — Phase 9 ETF-vs-CME-micro (2)
    PairedDispersionCatalogRow(
        archetype="CARRY_BASIS_DATED",
        params={
            "cash_venue": "nasdaq",
            "future_venue": "cme",
            "cash_instrument": "ibit",
            "future_instrument": "mbt",
            "asset": "btc",
            "hold_policy": "HOLD_UNTIL_FLIP",
            "roll_on_dte": "7",
        },
    ),
    PairedDispersionCatalogRow(
        archetype="CARRY_BASIS_DATED",
        params={
            "cash_venue": "nasdaq",
            "future_venue": "cme",
            "cash_instrument": "etha",
            "future_instrument": "met",
            "asset": "eth",
            "hold_policy": "HOLD_UNTIL_FLIP",
            "roll_on_dte": "7",
        },
    ),
    # CARRY_BASIS_DATED — Phase 9 intra-Deribit (2)
    PairedDispersionCatalogRow(
        archetype="CARRY_BASIS_DATED",
        params={
            "spot_venue": "deribit",
            "dated_venue": "deribit",
            "instrument": "btc",
            "hold_policy": "HOLD_UNTIL_FLIP",
            "target_basis_bps": "50",
        },
    ),
    PairedDispersionCatalogRow(
        archetype="CARRY_BASIS_DATED",
        params={
            "spot_venue": "deribit",
            "dated_venue": "deribit",
            "instrument": "eth",
            "hold_policy": "HOLD_UNTIL_FLIP",
            "target_basis_bps": "50",
        },
    ),
    # ARBITRAGE_PRICE_DISPERSION — Phase 9 cross-venue dated futures (2)
    PairedDispersionCatalogRow(
        archetype="ARBITRAGE_PRICE_DISPERSION",
        params={
            "long_venue": "cme",
            "short_venue": "deribit",
            "long_instrument": "mbt",
            "asset": "btc",
            "match_expiry": "true",
            "min_spread_bps": "20",
        },
    ),
    PairedDispersionCatalogRow(
        archetype="ARBITRAGE_PRICE_DISPERSION",
        params={
            "long_venue": "cme",
            "short_venue": "deribit",
            "long_instrument": "met",
            "asset": "eth",
            "match_expiry": "true",
            "min_spread_bps": "20",
        },
    ),
    # CARRY_BASIS_DATED — Phase 9 NYSE-CME ETF-vs-future placeholders
    # (5, all status=databento_pending). Builder skips these until
    # databento adds GLD/USO/UNG/SPY/QQQ tick coverage.
    PairedDispersionCatalogRow(
        archetype="CARRY_BASIS_DATED",
        params={
            "cash_venue": "nyse",
            "future_venue": "cme",
            "cash_instrument": "gld",
            "future_instrument": "gc",
            "asset": "gold",
            "status": "databento_pending",
            "hold_policy": "HOLD_UNTIL_FLIP",
            "roll_on_dte": "7",
        },
    ),
    PairedDispersionCatalogRow(
        archetype="CARRY_BASIS_DATED",
        params={
            "cash_venue": "nyse",
            "future_venue": "cme",
            "cash_instrument": "uso",
            "future_instrument": "cl",
            "asset": "wti_crude",
            "status": "databento_pending",
            "hold_policy": "HOLD_UNTIL_FLIP",
            "roll_on_dte": "7",
        },
    ),
    PairedDispersionCatalogRow(
        archetype="CARRY_BASIS_DATED",
        params={
            "cash_venue": "nyse",
            "future_venue": "cme",
            "cash_instrument": "ung",
            "future_instrument": "ng",
            "asset": "natgas",
            "status": "databento_pending",
            "hold_policy": "HOLD_UNTIL_FLIP",
            "roll_on_dte": "7",
        },
    ),
    PairedDispersionCatalogRow(
        archetype="CARRY_BASIS_DATED",
        params={
            "cash_venue": "nyse",
            "future_venue": "cme",
            "cash_instrument": "spy",
            "future_instrument": "es",
            "asset": "sp500",
            "status": "databento_pending",
            "hold_policy": "HOLD_UNTIL_FLIP",
            "roll_on_dte": "7",
        },
    ),
    PairedDispersionCatalogRow(
        archetype="CARRY_BASIS_DATED",
        params={
            "cash_venue": "nyse",
            "future_venue": "cme",
            "cash_instrument": "qqq",
            "future_instrument": "nq",
            "asset": "nasdaq100",
            "status": "databento_pending",
            "hold_policy": "HOLD_UNTIL_FLIP",
            "roll_on_dte": "7",
        },
    ),
]


PAIRED_DISPERSION_CATALOG: tuple[PairedDispersionCatalogRow, ...] = tuple(_PAIRED_DISPERSION_CATALOG_ROWS)
"""Tuple of all paired_price_dispersion catalog rows (active + databento_pending).

Consumers iterate this tuple and pass each row to the dispatch's
``build_pair_specs(row.archetype, row.params, as_of)``. The builder
skips ``status: "databento_pending"`` rows automatically.

Update history:
- 2026-05-07: lifted from strategy-service catalog. 11 active rows + 5
  databento_pending placeholders.
"""


__all__ = ["PAIRED_DISPERSION_CATALOG", "PairedDispersionCatalogRow"]
