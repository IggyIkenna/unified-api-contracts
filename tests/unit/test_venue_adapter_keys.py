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
    DECOMMISSIONED_VENUE_BASES,
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
        # (YAHOO_FINANCE removed 2026-07-15 — it was a source-as-venue modeling error,
        #  no longer enumerated as a venue, so it is no longer a sentinel here.)
        # (FX removed 2026-07-23 — it now has a real URDI reference-data adapter, "fx"
        #  (instruments-service/reference_data/adapters/tradfi/fx.py, static
        #  FX_SPOT_PAIRS-derived, no vendor call). MTDS's own FX tick/OHLCV path is
        #  unaffected — it still bypasses VENUE_TO_ADAPTER_KEY/URDI via its hardcoded
        #  Yahoo branch; this sentinel was specifically about the reference-data side.)
        # MTDS-owned sports odds venues (Decision C, 2026-06-29).
        "ODDS_API",
        "PINNACLE",
        "BETFAIR_SB_UK",
        "BETFAIR_EX_UK",
        "BETFAIR_EX_EU",
        "DRAFTKINGS",
        "FANDUEL",
        # The 20 ODDS_API fan-out bookmakers (BETMGM..WILLIAMHILL) that were
        # promoted into VENUES_BY_ASSET_GROUP["sports"] + sentineled here
        # 2026-07-20 were REVERTED 2026-07-22 (operator ruling: "do NOT add
        # them, in fact remove them everywhere so they don't come up in audit"
        # — distinct_values_noncanonical_audit_2026_07_20.md). They are no
        # longer canonical venues, so they are correctly ABSENT from this set
        # too (this set only covers canonical-but-adapterless venues). See
        # `market_data_categories.SPORTS_ODDS_API_ACCEPTED_NONCANONICAL_BOOKMAKERS`
        # for where they now live instead.
    }
)

_ADAPTER_KEY_RE = re.compile(r"^[a-z][a-z0-9_]*$")


class TestVenueAdapterKeyCoverage:
    """Every canonical venue has an entry — the Phase-2 plan gate."""

    def test_every_canonical_venue_has_an_entry(self) -> None:
        missing = {
            ag: [v for v in venues if v not in VENUE_TO_ADAPTER_KEY] for ag, venues in VENUES_BY_ASSET_GROUP.items()
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

    def test_prediction_and_cefi_resolve_with_no_sentinels(self) -> None:
        # cefi has no sentinel venues since coinbase_bare_name_migration S3
        # (2026-07-10) removed the bare-COINBASE alias entry; COINBASE-SPOT
        # resolves to a real adapter ("tardis").
        for ag, allowed_sentinels in (("prediction", set()), ("cefi", set())):
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
        assert VENUE_TO_ADAPTER_KEY.get("CAMELOT_V3-ARBITRUM") == "uniswap_v3"

    def test_reuse_map_targets_are_real_slugs(self) -> None:
        # Every reuse target must itself be a plausible adapter key (snake case);
        # every reuse source must be a known protocol in the prefix map values.
        known_protocols = set(VENUE_PREFIX_TO_PROTOCOL.values())
        for protocol, target in PROTOCOL_TO_ADAPTER_KEY.items():
            assert protocol in known_protocols, f"reuse source {protocol!r} not in VENUE_PREFIX_TO_PROTOCOL"
            assert _ADAPTER_KEY_RE.match(target), f"reuse target {target!r} not snake_case"


class TestDecommissionedVenueBases:
    """``DECOMMISSIONED_VENUE_BASES`` is the machine-readable removed-venue SSOT.

    Consumers (e.g. deployment-api's data-status drilldown) base-prefix-match
    against this set to hide manifest rows for fully-retired protocols. The
    gate here: no CURRENTLY REGISTERED venue (bare or ``-<CHAIN>`` suffixed)
    may resolve to a base in this set — a removal recorded here while an
    active venue entry still exists would be a contradiction (either the
    removal or the venue registration is stale).
    """

    def test_no_active_venue_has_a_decommissioned_base(self) -> None:
        offenders = {
            venue for venue in VENUE_TO_ADAPTER_KEY if venue.split("-", 1)[0].upper() in DECOMMISSIONED_VENUE_BASES
        }
        assert not offenders, (
            f"Venues still registered under a decommissioned base: {sorted(offenders)}. Either the "
            "venue needs to be removed from VENUE_TO_ADAPTER_KEY, or it was wrongly added to "
            "DECOMMISSIONED_VENUE_BASES."
        )

    def test_bases_are_uppercase(self) -> None:
        assert all(base == base.upper() for base in DECOMMISSIONED_VENUE_BASES)
        assert all("-" not in base for base in DECOMMISSIONED_VENUE_BASES), (
            "Members must be BASE names (pre-first-'-'), not full venue strings."
        )

    def test_matches_the_declared_removed_set(self) -> None:
        # Locks exact membership so a future removal/addition is a conscious,
        # reviewed change (same discipline as EXPECTED_SENTINEL_VENUES above).
        assert frozenset({"DRIFT", "PACIFICA", "MANGO", "ZETA", "FLASH"}) == DECOMMISSIONED_VENUE_BASES
