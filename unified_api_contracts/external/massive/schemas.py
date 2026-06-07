"""Massive (Polygon.io-compatible) raw reference-data response schemas.

Massive rebranded from Polygon.io (2025-10-30) and serves the same REST API on
``https://api.polygon.io``. These Pydantic models capture the *raw* vendor
response shapes for the reference-data (instrument-definition) endpoints used by
instruments-service. Normalisation to the canonical :class:`InstrumentRecord`
lives in :mod:`unified_api_contracts.external.massive.normalize` so the canonical
instrument schema is identical regardless of data source (Databento vs Massive).

Endpoints covered (verified live 2026-06-07 against the operator's active plans —
Stocks Starter / Options Developer / Indices Basic / Futures Developer /
Currencies Basic):

* ``GET /v3/reference/tickers``            — equities / ETFs / indices / FX
* ``GET /v3/reference/options/contracts``  — listed option contracts
* ``GET /futures/vX/contracts``            — futures contracts (NOT
  ``/v3/reference/futures/*`` — that path 404s; the ``/futures/vX/`` base is the
  working one, confirmed 2026-06-07)
* ``GET /futures/vX/products``             — futures product metadata (contract
  size via ``unit_of_measure_qty``)
"""

from __future__ import annotations

from pydantic import BaseModel


class MassiveTicker(BaseModel):
    """A ``/v3/reference/tickers`` row (stocks / indices / fx market).

    ``primary_exchange`` is an ISO-10383 MIC (``XNAS``/``XNYS``/``ARCX``…) used to
    resolve the canonical venue. FX rows carry ``base_currency_symbol`` /
    ``currency_symbol`` instead; index rows (``I:VIX``) carry neither an exchange
    nor currency fields.
    """

    ticker: str | None = None
    name: str | None = None
    market: str | None = None
    locale: str | None = None
    primary_exchange: str | None = None
    type: str | None = None
    active: bool = True
    currency_name: str | None = None
    # FX-only fields
    base_currency_symbol: str | None = None
    currency_symbol: str | None = None
    base_currency_name: str | None = None


class MassiveTickersResponse(BaseModel):
    """Pagination wrapper for ``/v3/reference/tickers``."""

    results: list[MassiveTicker] | None = None
    next_url: str | None = None
    status: str | None = None


class MassiveOptionContract(BaseModel):
    """A ``/v3/reference/options/contracts`` row."""

    ticker: str | None = None
    underlying_ticker: str | None = None
    contract_type: str | None = None
    exercise_style: str | None = None
    expiration_date: str | None = None
    strike_price: float | None = None
    shares_per_contract: int | None = None
    primary_exchange: str | None = None
    cfi: str | None = None


class MassiveOptionContractsResponse(BaseModel):
    """Pagination wrapper for ``/v3/reference/options/contracts``."""

    results: list[MassiveOptionContract] | None = None
    next_url: str | None = None
    status: str | None = None


class MassiveFuturesContract(BaseModel):
    """A ``/futures/vX/contracts`` row.

    ``first_trade_date`` / ``last_trade_date`` give the contract lifecycle
    (``available_from`` / ``expiry``); ``trading_venue`` is the MIC
    (``XCME``/``XCBT``/``XNYM``/``XCEC`` → CME; ICE MICs → ICE);
    ``product_code`` is the root (``ES``/``CL``/``GC``…).
    """

    ticker: str | None = None
    name: str | None = None
    product_code: str | None = None
    group_code: str | None = None
    trading_venue: str | None = None
    first_trade_date: str | None = None
    last_trade_date: str | None = None
    active: bool = True


class MassiveFuturesContractsResponse(BaseModel):
    """Pagination wrapper for ``/futures/vX/contracts``."""

    results: list[MassiveFuturesContract] | None = None
    next_url: str | None = None
    status: str | None = None


class MassiveFuturesProduct(BaseModel):
    """A ``/futures/vX/products`` row — product-level metadata.

    ``unit_of_measure_qty`` is the contract multiplier (e.g. 50.0 for ES);
    ``trade_currency_code`` the quote currency; ``asset_sub_class`` the
    coarse class (``equity``/``energy``/``metal``…).
    """

    product_code: str | None = None
    trading_venue: str | None = None
    asset_sub_class: str | None = None
    trade_currency_code: str | None = None
    unit_of_measure_qty: float | None = None
    type: str | None = None


class MassiveFuturesProductsResponse(BaseModel):
    """Pagination wrapper for ``/futures/vX/products``."""

    results: list[MassiveFuturesProduct] | None = None
    next_url: str | None = None
    status: str | None = None
