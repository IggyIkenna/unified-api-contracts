"""Domain facade -- re-exports from canonical/domain/sports/."""

from unified_api_contracts.canonical.domain.reference import Sport as Sport
from unified_api_contracts.canonical.domain.sports import *
from unified_api_contracts.canonical.domain.sports import ROUND_NAMES as ROUND_NAMES
from unified_api_contracts.canonical.domain.sports import ROUND_PREFIXES as ROUND_PREFIXES
from unified_api_contracts.canonical.domain.sports import RoundMatch as RoundMatch
from unified_api_contracts.canonical.domain.sports import is_known_round as is_known_round
from unified_api_contracts.canonical.domain.sports import resolve_round_name as resolve_round_name
from unified_api_contracts.external.api_football.team_mappings import (
    BUNDESLIGA_TEAM_ALIASES as BUNDESLIGA_TEAM_ALIASES,
)
from unified_api_contracts.external.api_football.team_mappings import (
    EPL_TEAM_ALIASES as EPL_TEAM_ALIASES,
)
from unified_api_contracts.external.odds_api.team_names import (
    CANONICAL_TO_ODDS_API_BUNDESLIGA as CANONICAL_TO_ODDS_API_BUNDESLIGA,
)
from unified_api_contracts.external.odds_api.team_names import (
    CANONICAL_TO_ODDS_API_EPL as CANONICAL_TO_ODDS_API_EPL,
)
from unified_api_contracts.external.odds_api.team_names import (
    CANONICAL_TO_UNDERSTAT_EPL as CANONICAL_TO_UNDERSTAT_EPL,
)
