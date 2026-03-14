"""Manifold Markets API response schemas."""

__api_version__ = "v0"  # matches provider_api_versions.yaml

from pydantic import BaseModel


class ManifoldMarket(BaseModel):
    """Manifold market schema."""

    id: str | None = None
    question: str | None = None
    probability: float | None = None
    volume: float | None = None
    volume_24_hours: float | None = None
    outcome_type: str | None = None
    resolution: str | None = None
    close_time: int | None = None
    created_time: int | None = None
    slug: str | None = None
    url: str | None = None


class ManifoldPrice(BaseModel):
    """Manifold price/probability schema."""

    contract_id: str | None = None
    outcome: str | None = None
    price: float | None = None
    probability: float | None = None


class ManifoldTrade(BaseModel):
    """Manifold trade schema."""

    id: str | None = None
    contract_id: str | None = None
    price: float | None = None
    amount: float | None = None
