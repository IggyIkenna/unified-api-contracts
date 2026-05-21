"""Phoenix DEX API contracts (market discovery via api.phoenix.trade).

NOTE: The Phoenix REST API (api.phoenix.trade) was deprecated / taken offline 2026-05-15.
The IS adapter (instruments_service/reference_data/adapters/defi/phoenix.py) still calls
api.phoenix.trade/markets for market discovery; quote data flows via Jupiter
(lite-api.jup.ag/swap/v1/quote) specified in source_archive_url_template.
Cassette documents the api.phoenix.trade/markets interaction pattern for canary
drift detection. Mark as BLOCKED-UPSTREAM-OUTAGE if endpoint returns 4xx/5xx.
"""

from unified_api_contracts.external.phoenix.schemas import (
    PhoenixMarket,
    PhoenixMarketsResponse,
)

__all__ = ["PhoenixMarket", "PhoenixMarketsResponse"]
