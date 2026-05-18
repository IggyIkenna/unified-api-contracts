"""Manifold Markets API response schemas."""

__api_version__ = "v0"  # matches provider_api_versions.yaml

from pydantic import BaseModel, Field


class ManifoldMarket(BaseModel):
    """Manifold market schema. API returns camelCase — aliases handle the mapping."""

    id: str | None = None
    question: str | None = None
    slug: str | None = None
    url: str | None = None
    probability: float | None = None
    p: float | None = None  # probability parameter for BINARY markets
    volume: float | None = None
    volume_24_hours: float | None = Field(None, alias="volume24Hours")
    outcome_type: str | None = Field(None, alias="outcomeType")
    mechanism: str | None = None  # dpm-2, cpmm-1
    resolution: str | None = None
    is_resolved: bool | None = Field(None, alias="isResolved")
    close_time: int | None = Field(None, alias="closeTime")
    created_time: int | None = Field(None, alias="createdTime")
    last_updated_time: int | None = Field(None, alias="lastUpdatedTime")
    total_liquidity: float | None = Field(None, alias="totalLiquidity")
    unique_bettor_count: int | None = Field(None, alias="uniqueBettorCount")
    pool: dict[str, float] | None = None
    creator_id: str | None = Field(None, alias="creatorId")
    creator_name: str | None = Field(None, alias="creatorName")
    creator_username: str | None = Field(None, alias="creatorUsername")
    creator_avatar_url: str | None = Field(None, alias="creatorAvatarUrl")

    model_config = {"populate_by_name": True}


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
