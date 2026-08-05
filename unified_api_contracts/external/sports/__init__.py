"""Per-league team-name alias tables for non-soccer sports leagues.

Mirrors the soccer precedent (:mod:`unified_api_contracts.external.api_football.team_mappings`)
for MLB, NFL, NBA, and tennis so Kalshi's city-only venue renderings ("Seattle") and
Polymarket's team-name renderings ("Seattle Mariners") canonicalise to the same id before
:meth:`SportsFixtureKey.pairing_key` is computed in
:mod:`unified_api_contracts.canonical.domain.predictions.fixture_parsing`.
"""
