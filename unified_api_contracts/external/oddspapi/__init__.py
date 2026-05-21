"""OddsPapi historical odds API contracts (api.oddspapi.io/v4/).

Used by e2e-testing/scripts/sports/oddspapi_historical_backfill.py.
Status: BLOCKED-CREDENTIALS — oddspapi-api-key required.
"""

from unified_api_contracts.external.oddspapi.schemas import (
    OddspapiFixture,
    OddspapiOdds,
)

__all__ = ["OddspapiFixture", "OddspapiOdds"]
