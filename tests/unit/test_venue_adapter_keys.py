"""Gate tests for the venue → URDI adapter-key registry (registry-consolidation Phase 2).

The plan gate (instrument_universe_registry_consolidation_2026_06_29 Phase 2):
every venue in ``VENUES_BY_ASSET_GROUP`` has a key or a loud "no-adapter-yet"
sentinel — a canonical venue must never be MISSING from the map (missing =
someone forgot; sentinel = declared adapterless).

The key→class closure (every non-sentinel key instantiates an adapter class)
is asserted on the instruments-service side (``TestAdapterRoutingUACInvariant``)
because adapter classes live downstream of UAC.
"""

from __future__ import annotations

import re

from unified_api_contracts.registry import (
    NO_ADAPTER_YET,
    PROTOCOL_TO_ADAPTER_KEY,
    VENUE_PREFIX_TO_PROTOCOL,
    VENUE_TO_ADAPTER_KEY,
    VENUES_BY_ASSET_GROUP,
    VENUES_WITH_REFERENCE_ADAPTER,
)

# The full, deliberate set of declared-adapterless venues. Adding a venue here
# must be a conscious decision (MTDS-owned market-data venue, source-as-venue
# artifact, expand-only bare form) — never a shortcut for a missing adapter.
EXPECTED_SENTINEL_VENUES: frozenset[str] = frozenset(
    {
        # Bare execution-context alias; IS expands to COINBASE-SPOT/-FUTURES
        # before adapter lookup.
        "COINBASE",
        # Legacy source-as-venue artifact (Yahoo data provider).
        "YAHOO_FINANCE",
        # MTDS-owned sports odds venues (Decision C, 2026-06-29).
        "ODDS_API",
        "PINNACLE",
        "BETFAIR_SB_UK",
        "BETFAIR_EX_UK",
        "BETFAIR_EX_EU",
        "DRAFTKINGS",
        "FANDUEL",
    }
)

_ADAPTER_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class TestVenueAdapterKeyCoverage:
    """Every canonical venue has an entry — the Phase-2 plan gate."""

    def test_every_canonical_venue_has_an_entry(self) -> None:
        missing = {
            ag: [v for v in venues if v not in VENUE_TO_ADAPTER_KEY]
            for ag, venues in VENUES_BY_ASSET_GROUP.items()
        }
        missing = {ag: m for ag, m in missing.items() if m}
        assert not missing, (
            f"Venues in VENUES_BY_ASSET_GROUP with NO entry in VENUE_TO_ADAPTER_KEY: {missing}. "
            "Register a real adapter key, or map to NO_ADAPTER_YET with a reasoned comment."
        )

    def test_sentinel_set_is_exactly_the_declared_one(self) -> None:
        actual = frozenset(v for v, k in VENUE_TO_ADAPTER_KEY.items() if k == NO_ADAPTER_YET)
        assert actual == EXPECTED_SENTINEL_VENUES, (
            f"Sentinel venues drifted. Unexpected: {sorted(actual - EXPECTED_SENTINEL_VENUES)}; "
            f"missing: {sorted(EXPECTED_SENTINEL_VENUES - actual)}. Sentineling a venue is a "
            "deliberate decision — update EXPECTED_SENTINEL_VENUES with the reason."
        )

    def test_defi_producible_venues_all_have_real_adapters(self) -> None:
        # VENUES_BY_ASSET_GROUP["defi"] is the IS-producible denominator set —
        # by definition none of it may be adapterless.
        sentineled = [v for v in VENUES_BY_ASSET_GROUP["defi"] if VENUE_TO_ADAPTER_KEY[v] == NO_ADAPTER_YET]
        assert not sentineled, f"defi producible venues cannot be sentinel: {sentineled}"

    def test_prediction_and_cefi_resolve_modulo_bare_coinbase(self) -> None:
        for ag, allowed_sentinels in (("prediction", set()), ("cefi", {"COINBASE"})):
            sentineled = {v for v in VENUES_BY_ASSET_GROUP[ag] if VENUE_TO_ADAPTER_KEY[v] == NO_ADAPTER_YET}
            assert sentineled == allowed_sentinels, (
                f"{ag}: sentinel venues {sorted(sentineled)} != allowed {sorted(allowed_sentinels)}"
            )


class TestVenueAdapterKeyShape:
    def test_adapter_keys_are_snake_case(self) -> None:
        bad = {v: k for v, k in VENUE_TO_ADAPTER_KEY.items() if k != NO_ADAPTER_YET and not _ADAPTER_KEY_RE.match(k)}
        assert not bad, f"Adapter keys must be lowercase snake_case: {bad}"

    def test_venues_with_reference_adapter_excludes_sentinels(self) -> None:
        derived = frozenset(v for v, k in VENUE_TO_ADAPTER_KEY.items() if k != NO_ADAPTER_YET)
        assert derived == VENUES_WITH_REFERENCE_ADAPTER
        assert not (VENUES_WITH_REFERENCE_ADAPTER & EXPECTED_SENTINEL_VENUES)

    def test_subgraph_expansion_produces_multichain_entries(self) -> None:
        # Representative dynamic entries: direct slug + adapter-reuse slug.
        assert VENUE_TO_ADAPTER_KEY.get("AAVE_V3-ARBITRUM") == "aave_v3"
        assert VENUE_TO_ADAPTER_KEY.get("GMX-ARBITRUM") == "uniswap_v3"

    def test_reuse_map_targets_are_real_slugs(self) -> None:
        # Every reuse target must itself be a plausible adapter key (snake case);
        # every reuse source must be a known protocol in the prefix map values.
        known_protocols = set(VENUE_PREFIX_TO_PROTOCOL.values())
        for protocol, target in PROTOCOL_TO_ADAPTER_KEY.items():
            assert protocol in known_protocols, f"reuse source {protocol!r} not in VENUE_PREFIX_TO_PROTOCOL"
            assert _ADAPTER_KEY_RE.match(target), f"reuse target {target!r} not snake_case"
