"""Betdaq Exchange API: errors, selections, markets, orders, balances.

Uses PascalCase JSON aliases matching Betdaq REST API conventions.

Ref: https://docs.betdaq.com/
"""

from __future__ import annotations

from pydantic import BaseModel, Field


class BetdaqErrorResponse(BaseModel, frozen=True):
    """Betdaq API error response."""

    message: str = Field("", alias="Message")
    error_code: str = Field("", alias="ErrorCode")

    model_config = {"populate_by_name": True}


class BetdaqBackPrice(BaseModel, frozen=True):
    """Betdaq back price — scaled integer representation."""

    price: int = Field(0, alias="Price")


class BetdaqSelection(BaseModel, frozen=True):
    """Betdaq selection (runner) within a market."""

    id: int | str = Field(0, alias="Id")
    name: str = Field("", alias="Name")
    reset_id: int = Field(0, alias="ResetId")
    back_prices: list[BetdaqBackPrice] = Field(default_factory=list, alias="BackPrices")


class BetdaqMarket(BaseModel, frozen=True):
    """Betdaq market."""

    id: int | str = Field(0, alias="Id")
    name: str = Field("", alias="Name")
    selections: list[BetdaqSelection] = Field(default_factory=list, alias="Selections")


class BetdaqMarketsResponse(BaseModel, frozen=True):
    """Betdaq markets response."""

    markets: list[BetdaqMarket] = Field(default_factory=list, alias="Markets")

    model_config = {"populate_by_name": True}


class BetdaqOrder(BaseModel, frozen=True):
    """Betdaq order result."""

    id: int | str = Field(0, alias="Id")
    result: int = Field(-1, alias="Result")


class BetdaqOrdersResponse(BaseModel, frozen=True):
    """Betdaq orders response."""

    orders: list[BetdaqOrder] = Field(default_factory=list, alias="Orders")

    model_config = {"populate_by_name": True}


class BetdaqBalance(BaseModel, frozen=True):
    """Betdaq account balance entry."""

    currency: str = Field("", alias="Currency")
    balance: int = Field(0, alias="Balance")


class BetdaqBalancesResponse(BaseModel, frozen=True):
    """Betdaq balances response."""

    balances: list[BetdaqBalance] = Field(default_factory=list, alias="Balances")

    model_config = {"populate_by_name": True}


class BetdaqPriceLevel(BaseModel, frozen=True):
    """Betdaq price level (back or lay)."""

    price: float | None = Field(None, alias="Price")
    amount: float | None = Field(None, alias="Amount")

    model_config = {"populate_by_name": True}


class BetdaqOdds(BaseModel, frozen=True):
    """Betdaq odds — selection-level back/lay prices."""

    selection_id: int | str | None = Field(None, alias="SelectionId")
    back_prices: list[BetdaqPriceLevel] = Field(default_factory=list, alias="BackPrices")
    lay_prices: list[BetdaqPriceLevel] = Field(default_factory=list, alias="LayPrices")

    model_config = {"populate_by_name": True}


class BetdaqEvent(BaseModel, frozen=True):
    """Betdaq event (e.g. a sports fixture)."""

    id: int | str = Field(0, alias="Id")
    name: str = Field("", alias="Name")
    markets: list[BetdaqMarket] = Field(default_factory=list, alias="Markets")

    model_config = {"populate_by_name": True}
