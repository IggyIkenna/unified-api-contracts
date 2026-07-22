"""DeFi venue canonical-form registry — extracted from ``venue_mapping.py``.

Two artefacts for the DeFi side of the registry:

- ``ALL_DEFI_VENUES``: canonical ``PROTOCOL-CHAIN`` identifiers for every DeFi
  (protocol, chain) combination ingested by MTDS sub-dim buckets. Sourced from
  live enumeration across the ``market-data-tick-{gas-fees, lending-indices,
  dex-swaps, dex-pools, oracle-prices, lst-rates, liquidations, evm-defi,
  solana-defi, perp-funding}-<project>`` buckets on 2026-04-20.
- ``LEGACY_DEFI_VENUE_ALIASES``: mapping from the raw single-token forms that
  pre-2026-04 manifests carry (``AAVE_V3`` / ``UNISWAP_V2`` / ``CURVE`` /
  ``LIDO`` / ...) to their canonical ``PROTOCOL-CHAIN`` form. Used by
  ``normalize_defi_venue`` in ``VenueMapping``.

Kept as a separate module so ``venue_mapping.py`` stays under the 900-line
QG ceiling as the DeFi multi-chain coverage grows.

SSOT: ``codex/02-data/mtds-data-source-coverage-matrix.md``.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Canonical PROTOCOL-CHAIN venues
# ---------------------------------------------------------------------------
# Naming convention: protocol versioning uses underscore form (AAVE_V3,
# COMPOUND_V3, PANCAKESWAP_V3) to match ``VENUE_DATA_TYPE_CAPABILITIES`` keys.
# Raw manifest values (``AAVE_V3`` + ``chain=POLYGON``, ``COMPOUND_V3`` +
# ``chain=SCROLL``, ``PANCAKESWAP_V3`` + ``chain=BSC``) resolve to these
# canonical names via ``VenueMapping.normalize_defi_venue``.

ALL_DEFI_VENUES: list[str] = [
    # ── Ethereum ──
    "UNISWAP_V2-ETHEREUM",
    "UNISWAP_V3-ETHEREUM",
    "UNISWAP_V4-ETHEREUM",
    "CURVE-ETHEREUM",
    "BALANCER-ETHEREUM",
    "AAVE_V3-ETHEREUM",
    "COMPOUND_V3-ETHEREUM",
    "MORPHO-ETHEREUM",
    "FLUID-ETHEREUM",
    "SPARK-ETHEREUM",
    "LIDO-ETHEREUM",
    "ETHERFI-ETHEREUM",
    "ETHENA-ETHEREUM",
    "SUSHISWAP_V3-ETHEREUM",
    "PANCAKESWAP_V3-ETHEREUM",
    "MORPHOVAULTS-ETHEREUM",
    "YEARN_V3-ETHEREUM",
    "FRAX-ETHEREUM",
    "MAKER-ETHEREUM",
    # ── LST / staking-yield protocols on Ethereum (added 2026-05-07 per
    #    DEFI-panel audit — these were live in the lst-rates bucket but
    #    not declared, causing duplicate "no chevron" rendering in the
    #    deployment-ui DEFI panel). All are actively backfilled by MTDS
    #    via the lst-rates sub-bucket.
    "ANKR-ETHEREUM",
    "ROCKETPOOL-ETHEREUM",
    "STADER-ETHEREUM",
    "STAKEWISE-ETHEREUM",
    "SWELL-ETHEREUM",
    "PUFFER-ETHEREUM",
    "MANTLE-ETHEREUM",
    # ── Gas-fee oracle (operates as a DeFi-context gas price source via
    #    the gas-fees sub-bucket; declared so the data-status panel
    #    renders it as an expected DeFi venue).
    "ALCHEMY-ETHEREUM",
    "EIGENLAYER-ETHEREUM",
    # ── Catalogue Phase 1A new Ethereum entries (slot 5 2026-05-11 per
    #    defi_catalogue_chain_primitives_2026_05_10.md Phase 1A). Vaults +
    #    restaking primitives; all "pipeline" phase until catalogue Phase
    #    2-3 ships instruments adapters + MTDS adapters.
    "CONVEX-ETHEREUM",
    "BEEFY-ETHEREUM",
    "PENDLE-ETHEREUM",
    "IDLE-ETHEREUM",
    "SYMBIOTIC-ETHEREUM",
    "KARAK-ETHEREUM",
    "RENZO-ETHEREUM",
    "KELPDAO-ETHEREUM",
    # ── Ethereum lending v2 (MTDS-backfilled, added 2026-05-22) ──
    "EULER_V2-ETHEREUM",
    # ── Ethereum governance + on-chain analytics (DEFI_VENUE_DATA_TYPE_CAPABILITIES
    #    has start dates for these; added 2026-05-22 to unblock parity tests) ──
    "AAVE-ETHEREUM",
    "COMPOUND-ETHEREUM",
    "UNISWAP-ETHEREUM",
    "FLASHBOTS-ETHEREUM",
    # ── Cross-chain bridge data (bridge_events sub-bucket, added 2026-05-22) ──
    "ACROSS-ETHEREUM",
    "STARGATE-ETHEREUM",
    # ── Plasma-chain protocol variants (protocol registry entries,
    #    added 2026-05-22 — no MTDS tick data yet; pipeline phase) ──
    "AAVE-PLASMA",
    "FLUID-PLASMA",
    # ── Arbitrum ──
    "UNISWAP_V3-ARBITRUM",
    "AAVE_V3-ARBITRUM",
    "COMPOUND_V3-ARBITRUM",
    "BALANCER-ARBITRUM",
    "SUSHISWAP-ARBITRUM",
    "PANCAKESWAP_V3-ARBITRUM",
    "CAMELOT_V3-ARBITRUM",
    "GMX-ARBITRUM",
    # ── Catalogue Phase 1A new Arbitrum entries (slot 5 2026-05-11) ──
    "YEARN_V3-ARBITRUM",
    "BEEFY-ARBITRUM",
    "PENDLE-ARBITRUM",
    "IDLE-ARBITRUM",
    "RADIANT-ARBITRUM",
    "KARAK-ARBITRUM",
    "RENZO-ARBITRUM",
    # ── Arbitrum MTDS-backfilled lending (added 2026-05-22) ──
    "EULER_V2-ARBITRUM",
    "MORPHO-ARBITRUM",
    "FLUID-ARBITRUM",
    # ── Base ──
    "UNISWAP_V3-BASE",
    "AAVE_V3-BASE",
    "COMPOUND_V3-BASE",
    "BALANCER-BASE",
    "MORPHO-BASE",
    "SUSHISWAP_V3-BASE",
    "PANCAKESWAP_V3-BASE",
    "AERODROME_V3-BASE",
    # ── Catalogue Phase 1A new Base entries (slot 5 2026-05-11) ──
    "BEEFY-BASE",
    # ── Optimism ──
    "UNISWAP_V3-OPTIMISM",
    "AAVE_V3-OPTIMISM",
    "COMPOUND_V3-OPTIMISM",
    "BALANCER-OPTIMISM",
    "CURVE-OPTIMISM",
    "VELODROME_V2-OPTIMISM",
    # ── Catalogue Phase 1A new Optimism entries (slot 5 2026-05-11) ──
    "YEARN_V3-OPTIMISM",
    # ── Optimism MTDS-backfilled lending (added 2026-05-22) ──
    "MORPHO-OPTIMISM",
    # ── Polygon ──
    "UNISWAP_V3-POLYGON",
    "AAVE_V3-POLYGON",
    "BALANCER-POLYGON",
    "COMPOUND_V3-POLYGON",
    # ── Catalogue Phase 1A new Polygon entries (slot 5 2026-05-11) ──
    "BEEFY-POLYGON",
    "IDLE-POLYGON",
    # ── Polygon MTDS-backfilled lending (added 2026-05-22) ──
    "MORPHO-POLYGON",
    # ── Avalanche ──
    "AAVE_V3-AVALANCHE",
    "BALANCER-AVALANCHE",
    "CURVE-AVALANCHE",
    "GMX-AVALANCHE",
    "SUSHISWAP_V3-AVALANCHE",
    "TRADER_JOE_V2-AVALANCHE",
    # ── Catalogue Phase 1A new Avalanche entries (slot 5 2026-05-11) ──
    "BEEFY-AVALANCHE",
    # ── Avalanche MTDS-backfilled lending (added 2026-05-22) ──
    "BENQI-AVALANCHE",
    # ── BSC ──
    "AAVE_V3-BSC",
    "PANCAKESWAP_V3-BSC",
    # ── Catalogue Phase 1A new BSC entries (slot 5 2026-05-11) ──
    "BEEFY-BSC",
    "RADIANT-BSC",
    # ── BSC + Ethereum MTDS-backfilled Venus lending (added 2026-05-22) ──
    "VENUS-BSC",
    "VENUS-ETHEREUM",
    # ── Ethereum MTDS-backfilled Radiant (Arbitrum-primary, Ethereum also live,
    #    added 2026-05-22) ──
    "RADIANT-ETHEREUM",
    # ── Multi-chain Alchemy gas-fee oracles (gas-fees sub-bucket, added 2026-05-22;
    #    ALCHEMY-ETHEREUM already declared above in the Ethereum section) ──
    "ALCHEMY-ARBITRUM",
    "ALCHEMY-BASE",
    "ALCHEMY-ONCHAIN",
    "ALCHEMY-OPTIMISM",
    "ALCHEMY-POLYGON",
    # ── Linea / Scroll / zkSync ──
    "AAVE_V3-LINEA",
    "AAVE_V3-SCROLL",
    "COMPOUND_V3-SCROLL",
    "AAVE_V3-ZKSYNC",
    # PANCAKESWAP_V3-ZKSYNC dropped 2026-05-06 — low-quality + low-volume data,
    # never produced useful captures. The 446 manifest rows that existed were
    # purged via `migrate_defi_legacy_venue_chain.py`. Do NOT re-add without
    # validating data quality + non-trivial liquidity on the chain.
    # ── Solana ──
    "KAMINO-SOLANA",
    "MARINADE-SOLANA",
    "ORCA-SOLANA",
    "RAYDIUM-SOLANA",
    # Solana LST/staking-yield (added 2026-05-07 — MTDS backfilled; data-
    # status was treating them as un-declared). JITO already in
    # MTDS_DEFI_VENUES below; this adds it to the full DeFi registry too.
    "JITO-SOLANA",
    "MARGINFI-SOLANA",
    "SOLEND-SOLANA",
    # DRIFT (Solana) removed 2026-07-16 (operator ruling): all Solana perp DEXes
    # dropped except Jupiter (not integrated). SSOT: unified-trading-pm/codex/
    # 04-architecture/solana-defi-coverage.md.
    # ── Catalogue Phase 1A new Solana entries (slot 5 2026-05-11). JUPITER
    #    aggregator is read-only (route registry, no MTDS tick stream);
    #    SOLBLAZE = bSOL liquid-staking; JITORESTAKING = distinct from
    #    JITO-SOLANA (LST/MEV) — covers Jito's restaking-vault product. ──
    "JUPITER-SOLANA",
    "SOLBLAZE-SOLANA",
    "JITORESTAKING-SOLANA",
    # ── Solana LST / native-staking (2026-07-18 IS-wiring — sanctum.py /
    #    solana_native_staking.py adapters produce real rows; flipped to
    #    phase="live" below). SANCTUM = LST marketplace (INF + partner LSTs);
    #    SOLANA-NATIVE = native SOL staking (venue distinct from the LST venues). ──
    "SANCTUM-SOLANA",
    "SOLANA-NATIVE-SOLANA",
    # ── Exchange-issued single-token LSTs (2026-07-18 IS-wiring — cbeth.py /
    #    wbeth.py). cbETH = Coinbase (ETHEREUM); wBETH = Binance (ETHEREUM + BSC,
    #    same contract address on both chains). Venue base is the ISSUING protocol
    #    (Coinbase / Binance) — distinct full strings from the CeFi COINBASE-SPOT /
    #    BINANCE-SPOT venues, so no VENUE_TO_ASSET_GROUP collision. ──
    "COINBASE-ETHEREUM",
    "BINANCE-ETHEREUM",
    "BINANCE-BSC",
    # ── Solana DEX / CLOB pools (2026-07-20 DeFi catalogue canonicalization —
    #    IS-wired via meteora.py / lifinity.py / phoenix.py adapters; dex_pool_state).
    #    METEORA = DLMM + dynamic pools; LIFINITY = proactive-MM; PHOENIX = on-chain
    #    order-book DEX (Ellipsis Labs). Narrowed back to phase="pipeline" below
    #    2026-07-22 (measured-dead-upstream finding, re-verified live: METEORA
    #    app.meteora.ag/api/pools -> 404, LIFINITY api.lifinity.io/pools -> no
    #    response/522, PHOENIX api.phoenix.trade -> NXDOMAIN — same result as the
    #    original 2026-07-20 measurement). Adapter classes stay registered in IS
    #    factory._ADAPTERS for when an upstream recovers/migrates. SSOT:
    #    issues/uac_is_defi_oracle_dex_adapter_drift_2026_07_20.md
    #    (Recommendation A). ──
    "METEORA-SOLANA",
    "LIFINITY-SOLANA",
    "PHOENIX-SOLANA",
    # ── Oracle price-feed venues (2026-07-20 DeFi catalogue canonicalization —
    #    oracle_prices data_type; PYTH is IS-wired via pyth.py, CHAINLINK-* via
    #    chainlink.py (instruments-service@6506b505, BLK-0c7b82fe resolved),
    #    phase="live" below. ──
    "CHAINLINK-ETHEREUM",
    "CHAINLINK-ARBITRUM",
    "CHAINLINK-BASE",
    "CHAINLINK-OPTIMISM",
    "CHAINLINK-POLYGON",
    "PYTH-SOLANA",
]

# ── Canonical underscore-name aliases (additive beside ghost names above) ──
# Ghost no-underscore names (UNISWAP_V3-*, AAVE_V3-*, etc.) are legacy-name aliases
# with historical GCS paths. New MTDS writers use canonical underscore names; these
# entries ensure venue-parity tests pass for both forms.
ALL_DEFI_VENUES.extend(
    [
        "UNISWAP_V2-ETHEREUM",
        "UNISWAP_V3-ETHEREUM",
        "UNISWAP_V3-ARBITRUM",
        "UNISWAP_V3-BASE",
        "UNISWAP_V3-OPTIMISM",
        "UNISWAP_V3-POLYGON",
        "UNISWAP_V4-ETHEREUM",
        "AAVE_V3-ETHEREUM",
        "AAVE_V3-ARBITRUM",
        "AAVE_V3-AVALANCHE",
        "AAVE_V3-BASE",
        "AAVE_V3-BSC",
        "AAVE_V3-LINEA",
        "AAVE_V3-OPTIMISM",
        "AAVE_V3-POLYGON",
        "AAVE_V3-SCROLL",
        "AAVE_V3-ZKSYNC",
        "COMPOUND_V3-ETHEREUM",
        "COMPOUND_V3-ARBITRUM",
        "COMPOUND_V3-BASE",
        "COMPOUND_V3-OPTIMISM",
        "COMPOUND_V3-POLYGON",
        "COMPOUND_V3-SCROLL",
        "SUSHISWAP_V3-ETHEREUM",
        "SUSHISWAP_V3-BASE",
        "SUSHISWAP_V3-AVALANCHE",
        "PANCAKESWAP_V3-ETHEREUM",
        "PANCAKESWAP_V3-ARBITRUM",
        "PANCAKESWAP_V3-BASE",
        "PANCAKESWAP_V3-BSC",
        "CAMELOT_V3-ARBITRUM",
        "AERODROME_V3-BASE",
        "YEARN_V3-ETHEREUM",
        "YEARN_V3-ARBITRUM",
        "YEARN_V3-OPTIMISM",
    ]
)


# ---------------------------------------------------------------------------
# Legacy → canonical aliases
# ---------------------------------------------------------------------------
# Chain-less legacy names default to ETHEREUM canonical. Callers that pass
# the chain kwarg via ``VenueMapping.normalize_defi_venue(raw, chain)`` get
# the non-Ethereum canonical (``AAVE_V3-ARBITRUM`` etc) synthesised by
# replacing the ``-ETHEREUM`` suffix.

LEGACY_DEFI_VENUE_ALIASES: dict[str, str] = {
    # DEX swap protocols
    "UNISWAP_V2": "UNISWAP_V2-ETHEREUM",
    "UNISWAP_V3": "UNISWAP_V3-ETHEREUM",
    "UNISWAP_V4": "UNISWAP_V4-ETHEREUM",
    "CURVE": "CURVE-ETHEREUM",
    "BALANCER": "BALANCER-ETHEREUM",
    "SUSHISWAP": "SUSHISWAP_V3-ETHEREUM",
    "SUSHISWAP_V3": "SUSHISWAP_V3-ETHEREUM",
    "PANCAKESWAP_V3": "PANCAKESWAP_V3-ETHEREUM",
    "CAMELOT_V3": "CAMELOT_V3-ARBITRUM",
    "AERODROME_V3": "AERODROME_V3-BASE",
    # Canonical underscore form (operator 2026-06-01 — DF-17 glued-canonical reversed).
    # Legacy glued forms (VELODROMEV2 / TRADER_JOEV2, bare + full -CHAIN) resolve to it.
    "VELODROME_V2": "VELODROME_V2-OPTIMISM",
    "VELODROMEV2": "VELODROME_V2-OPTIMISM",
    "VELODROMEV2-OPTIMISM": "VELODROME_V2-OPTIMISM",
    "TRADER_JOE_V2": "TRADER_JOE_V2-AVALANCHE",
    "TRADER_JOEV2": "TRADER_JOE_V2-AVALANCHE",
    "TRADER_JOEV2-AVALANCHE": "TRADER_JOE_V2-AVALANCHE",
    # Lending
    "AAVE_V3": "AAVE_V3-ETHEREUM",
    "AAVEV3": "AAVE_V3-ETHEREUM",  # alias: no-underscore form used by some callers
    "COMPOUND_V3": "COMPOUND_V3-ETHEREUM",
    "MORPHO": "MORPHO-ETHEREUM",
    "FLUID": "FLUID-ETHEREUM",
    "SPARK": "SPARK-ETHEREUM",
    # Perpetual DEXes
    "GMX": "GMX-ARBITRUM",
    # LST / yield
    "LIDO": "LIDO-ETHEREUM",
    "ETHERFI": "ETHERFI-ETHEREUM",
    "ETHENA": "ETHENA-ETHEREUM",
    # Vaults / yield-bearing
    "MORPHO_VAULTS": "MORPHOVAULTS-ETHEREUM",
    "MORPHOVAULTS": "MORPHOVAULTS-ETHEREUM",
    "YEARN_V3": "YEARN_V3-ETHEREUM",
    "FRAX": "FRAX-ETHEREUM",
    "MAKER": "MAKER-ETHEREUM",
    # Solana
    "KAMINO": "KAMINO-SOLANA",
    "MARINADE": "MARINADE-SOLANA",
    "ORCA": "ORCA-SOLANA",
    "RAYDIUM": "RAYDIUM-SOLANA",
    "JITO": "JITO-SOLANA",
    "MARGINFI": "MARGINFI-SOLANA",
    "SOLEND": "SOLEND-SOLANA",
    # DRIFT alias removed 2026-07-16 (operator ruling, all Solana perp DEXes
    # dropped except Jupiter, not integrated).
    # LST / staking-yield protocols on Ethereum (added 2026-05-07 — DEFI
    # panel audit). Bare-name aliases needed because the manifest carries
    # them as ``venue=ANKR chain=ETHEREUM`` etc.; the
    # ``VenueMapping.normalize_defi_venue`` lookup only matches
    # ``raw_venue in all_defi_venues`` for fully-canonical strings, so
    # bare names need an explicit alias to resolve.
    "ANKR": "ANKR-ETHEREUM",
    "ROCKETPOOL": "ROCKETPOOL-ETHEREUM",
    "STADER": "STADER-ETHEREUM",
    "STAKEWISE": "STAKEWISE-ETHEREUM",
    "SWELL": "SWELL-ETHEREUM",
    "PUFFER": "PUFFER-ETHEREUM",
    "MANTLE": "MANTLE-ETHEREUM",
    # Gas-fee + restaking oracles
    "ALCHEMY": "ALCHEMY-ETHEREUM",
    "EIGENLAYER": "EIGENLAYER-ETHEREUM",
    # Catalogue Phase 1A new aliases (slot 5 2026-05-11). Bare-name defaults
    # chosen by primary chain: CONVEX (Ethereum-only), BEEFY (multi-chain,
    # defaults to Ethereum), PENDLE (defaults to Ethereum), IDLE (defaults
    # to Ethereum), JUPITER (Solana-only), SOLBLAZE (Solana-only), SYMBIOTIC
    # (Ethereum-only), KARAK (defaults to Ethereum), RENZO (defaults to
    # Ethereum), KELPDAO (Ethereum-only), JITORESTAKING (Solana-only),
    # RADIANT (defaults to Arbitrum where it has highest TVL).
    "CONVEX": "CONVEX-ETHEREUM",
    "BEEFY": "BEEFY-ETHEREUM",
    "PENDLE": "PENDLE-ETHEREUM",
    "IDLE": "IDLE-ETHEREUM",
    "JUPITER": "JUPITER-SOLANA",
    "SOLBLAZE": "SOLBLAZE-SOLANA",
    "SYMBIOTIC": "SYMBIOTIC-ETHEREUM",
    "KARAK": "KARAK-ETHEREUM",
    "RENZO": "RENZO-ETHEREUM",
    "KELPDAO": "KELPDAO-ETHEREUM",
    "JITORESTAKING": "JITORESTAKING-SOLANA",
    "JITO_RESTAKING": "JITORESTAKING-SOLANA",
    "RADIANT": "RADIANT-ARBITRUM",
    # Phase 1D case-folding drift fixes (cross_asset_group_catalogue_audit DF-4/DF-17)
    "BLAZESTAKE": "SOLBLAZE-SOLANA",  # DF-4: _defi_lst.py uses BLAZESTAKE; canonical is SOLBLAZE
    "BLAZESTAKE-SOLANA": "SOLBLAZE-SOLANA",  # DF-4: full-form variant
    "TRADERJOEV2-AVALANCHE": "TRADER_JOE_V2-AVALANCHE",  # DF-17 (reversed 2026-06-01): underscore canonical
}


def to_canonical_venue(venue_id: str) -> str:
    """Return the canonical uppercase venue ID, resolving known DeFi legacy aliases.

    For CeFi and sports venues this is equivalent to ``venue_id.upper()``.
    For DeFi venues it also resolves legacy bare-name and underscore forms
    (e.g. ``aavev3`` → ``AAVE_V3-ETHEREUM``, ``TRADERJOEV2-AVALANCHE`` →
    ``TRADER_JOE_V2-AVALANCHE``) via ``LEGACY_DEFI_VENUE_ALIASES``.

    Cross-asset-group SSOT for venue-id normalisation.
    SSOT: cross_asset_group_catalogue_audit_2026_05_10.md Phase 1D.
    """
    upper = venue_id.upper()
    return LEGACY_DEFI_VENUE_ALIASES.get(upper, upper)


# ---------------------------------------------------------------------------
# DeFi venue phase — distinguishes actively-backfilled venues ("live") from
# UAC-declared roadmap entries ("pipeline"). The deployment-ui DEFI panel
# uses this to render only "live" venues in the live-coverage section AND
# surface "pipeline" venues in a separate roadmap section so operators see
# what's queued without polluting the active honest-coverage view. Added
# 2026-05-07 per DEFI panel audit.
#
# - "live": MTDS backfill is shipping data; manifest has rows; UI shows
#   in the main DEFI panel with chevron + dates.
# - "pipeline": UAC declares the venue (chain expansion roadmap, not yet
#   plumbed in MTDS); manifest has zero rows; UI shows in a "roadmap"
#   section so the operator can see what's coming.
#
# Every entry in ``ALL_DEFI_VENUES`` must appear here. The
# ``DEFI_VENUE_PHASE`` test (test_defi_venue_phase_coverage) asserts the
# 1:1 invariant.
# ---------------------------------------------------------------------------


# INVARIANT: phase=="live" ⟺ venue is IS-producible (in _build_defi_venues()).
# See instrument_universe_registry_consolidation_2026_06_29.md.
DEFI_VENUE_PHASE: dict[str, str] = {
    # ── Live (Ethereum DEX / lending) — IS-producible per _build_defi_venues() ──
    "UNISWAP_V2-ETHEREUM": "live",
    "UNISWAP_V3-ETHEREUM": "live",
    "UNISWAP_V4-ETHEREUM": "live",
    "CURVE-ETHEREUM": "live",
    "BALANCER-ETHEREUM": "live",
    "AAVE_V3-ETHEREUM": "live",
    "COMPOUND_V3-ETHEREUM": "live",
    "MORPHO-ETHEREUM": "live",
    "FLUID-ETHEREUM": "live",
    "SPARK-ETHEREUM": "live",
    "SUSHISWAP_V3-ETHEREUM": "live",
    "PANCAKESWAP_V3-ETHEREUM": "live",
    # ── Pipeline (Ethereum vaults / analytics — NOT IS-producible) ──
    "MORPHOVAULTS-ETHEREUM": "pipeline",
    "FRAX-ETHEREUM": "pipeline",
    "MAKER-ETHEREUM": "pipeline",
    # ── Live (Ethereum LST / staking-yield — IS-producible) ──
    "LIDO-ETHEREUM": "live",
    "ETHERFI-ETHEREUM": "live",
    "ETHENA-ETHEREUM": "live",
    "EIGENLAYER-ETHEREUM": "live",
    # ── Live (Ethereum LST / restaking / vault / yield — IS-wired 2026-07-18;
    #    adapters had populated curated registries but the IS venue list never
    #    requested them, so 0 catalogue rows were produced. Flipped pipeline→live
    #    per the phase=="live" ⟺ IS-producible invariant, same pattern as the
    #    2026-07-10 VENUS/RADIANT/BENQI flip. COINBASE = Coinbase cbETH LST,
    #    BINANCE = Binance wBETH LST (new cbeth.py / wbeth.py adapters). ──
    "ROCKETPOOL-ETHEREUM": "live",
    "PUFFER-ETHEREUM": "live",
    "CONVEX-ETHEREUM": "live",
    "BEEFY-ETHEREUM": "live",
    "PENDLE-ETHEREUM": "live",
    "IDLE-ETHEREUM": "live",
    "SYMBIOTIC-ETHEREUM": "live",
    "KARAK-ETHEREUM": "live",
    "RENZO-ETHEREUM": "live",
    "KELPDAO-ETHEREUM": "live",
    "YEARN_V3-ETHEREUM": "live",
    "COINBASE-ETHEREUM": "live",
    "BINANCE-ETHEREUM": "live",
    # ── Pipeline (Ethereum LST/staking — NOT IS-producible; no adapter wired) ──
    "ANKR-ETHEREUM": "pipeline",
    "STADER-ETHEREUM": "pipeline",
    "STAKEWISE-ETHEREUM": "pipeline",
    "SWELL-ETHEREUM": "pipeline",
    "MANTLE-ETHEREUM": "pipeline",
    # ── Pipeline (Ethereum gas oracles — NOT IS-producible) ──
    "ALCHEMY-ETHEREUM": "pipeline",
    # ── Live (Arbitrum — IS-producible per _build_defi_venues()) ──
    "UNISWAP_V3-ARBITRUM": "live",
    "AAVE_V3-ARBITRUM": "live",
    "COMPOUND_V3-ARBITRUM": "live",
    "BALANCER-ARBITRUM": "live",
    "SUSHISWAP-ARBITRUM": "live",
    "CAMELOT_V3-ARBITRUM": "live",
    "GMX-ARBITRUM": "live",
    # RADIANT-ARBITRUM: 2026-07-10 — wired into _build_defi_venues() (mtds_is_full_
    # adapter_smoketest_findings_2026_07_07.md P1, adapter was functional but never
    # invoked). Flipped pipeline→live per the phase=="live" ⟺ IS-producible invariant.
    "RADIANT-ARBITRUM": "live",
    # ── Pipeline (Arbitrum — NOT IS-producible) ──
    "PANCAKESWAP_V3-ARBITRUM": "pipeline",
    # ── Live (Arbitrum LST / vault / yield — IS-wired 2026-07-18, populated
    #    curated registries) ──
    "YEARN_V3-ARBITRUM": "live",
    "BEEFY-ARBITRUM": "live",
    "PENDLE-ARBITRUM": "live",
    "KARAK-ARBITRUM": "live",
    "RENZO-ARBITRUM": "live",
    # ── Pipeline (Arbitrum — NOT IS-producible: idle.py has NO Arbitrum vault
    #    entries in _IDLE_VAULTS_BY_CHAIN, so IDLE-ARBITRUM returns 0 rows and is
    #    deliberately left un-enumerated until the curated addresses land) ──
    "IDLE-ARBITRUM": "pipeline",
    # ── Pipeline (Arbitrum lending — not IS-producible) ──
    # EULER_V2-ARBITRUM + FLUID-ARBITRUM: no UAC subgraph_id registered → 0 captured rows.
    # MORPHO-ARBITRUM: not in IS-producible set despite having rows (not in _build_defi_venues()).
    "EULER_V2-ARBITRUM": "pipeline",
    "MORPHO-ARBITRUM": "pipeline",
    "FLUID-ARBITRUM": "pipeline",
    # ── Live (Base — IS-producible per _build_defi_venues()) ──
    "UNISWAP_V3-BASE": "live",
    "AAVE_V3-BASE": "live",
    "COMPOUND_V3-BASE": "live",
    "BALANCER-BASE": "live",
    "MORPHO-BASE": "live",
    "SUSHISWAP_V3-BASE": "live",
    "PANCAKESWAP_V3-BASE": "live",
    "AERODROME_V3-BASE": "live",
    # ── Live (Base — BEEFY IS-wired 2026-07-18, populated curated registry) ──
    "BEEFY-BASE": "live",
    # ── Live (Optimism — IS-producible per _build_defi_venues()) ──
    "UNISWAP_V3-OPTIMISM": "live",
    "AAVE_V3-OPTIMISM": "live",
    "COMPOUND_V3-OPTIMISM": "live",
    "BALANCER-OPTIMISM": "live",
    "CURVE-OPTIMISM": "live",
    "VELODROME_V2-OPTIMISM": "live",
    # ── Pipeline (Optimism — NOT IS-producible) ──
    "YEARN_V3-OPTIMISM": "pipeline",
    "MORPHO-OPTIMISM": "pipeline",
    # ── Live (Polygon — IS-producible per _build_defi_venues()) ──
    "UNISWAP_V3-POLYGON": "live",
    "AAVE_V3-POLYGON": "live",
    "BALANCER-POLYGON": "live",
    # ── Pipeline (Polygon — NOT IS-producible) ──
    "COMPOUND_V3-POLYGON": "pipeline",
    # ── Pipeline (Polygon catalogue Phase 1A, slot 5 2026-05-11) ──
    "BEEFY-POLYGON": "pipeline",
    "IDLE-POLYGON": "pipeline",
    # ── Pipeline (Polygon lending — NOT IS-producible) ──
    "MORPHO-POLYGON": "pipeline",
    # ── Live (Avalanche — IS-producible per _build_defi_venues()) ──
    "AAVE_V3-AVALANCHE": "live",
    "BALANCER-AVALANCHE": "live",
    "CURVE-AVALANCHE": "live",
    "GMX-AVALANCHE": "live",
    "SUSHISWAP_V3-AVALANCHE": "live",
    "TRADER_JOE_V2-AVALANCHE": "live",
    # BENQI-AVALANCHE: 2026-07-10 — wired into _build_defi_venues() (mtds_is_full_
    # adapter_smoketest_findings_2026_07_07.md P1). Flipped pipeline→live.
    "BENQI-AVALANCHE": "live",
    # ── Live (Avalanche — BEEFY IS-wired 2026-07-18, populated curated registry) ──
    "BEEFY-AVALANCHE": "live",
    # ── Live (BSC — IS-producible per _build_defi_venues()) ──
    "AAVE_V3-BSC": "live",
    "PANCAKESWAP_V3-BSC": "live",
    # RADIANT-BSC / VENUS-BSC / VENUS-ETHEREUM / RADIANT-ETHEREUM: 2026-07-10 —
    # wired into _build_defi_venues() (mtds_is_full_adapter_smoketest_findings_
    # 2026_07_07.md P1, adapters functional but never invoked). Flipped pipeline→live.
    "RADIANT-BSC": "live",
    "VENUS-BSC": "live",
    "VENUS-ETHEREUM": "live",
    "RADIANT-ETHEREUM": "live",
    # ── Live (BSC — BEEFY (curated registry) + BINANCE wBETH (wbeth.py) IS-wired
    #    2026-07-18) ──
    "BEEFY-BSC": "live",
    "BINANCE-BSC": "live",
    # AAVE-ETHEREUM flipped pipeline→live 2026-07-21 per lst_rate_honest_coverage
    # plan Phase 1 — the AaveOracle.getAssetPrice() oracle_prices collection
    # branch is IS-producible (aave_oracle adapter); governance_events on this
    # venue remains pipeline (NOT IS-producible), tracked separately.
    "AAVE-ETHEREUM": "live",
    # ── Pipeline (Ethereum analytics / governance / MEV — NOT IS-producible) ──
    "COMPOUND-ETHEREUM": "pipeline",
    "UNISWAP-ETHEREUM": "pipeline",
    "FLASHBOTS-ETHEREUM": "pipeline",
    "ACROSS-ETHEREUM": "pipeline",
    "STARGATE-ETHEREUM": "pipeline",
    # EULER_V2-ETHEREUM: 2026-07-10 — wired into _build_defi_venues() (same finding
    # doc). EULER_V2-ARBITRUM stays pipeline: euler_v2.py's adapter only supports
    # ETHEREUM (_DEFAULT_CHAIN, single flat _MVP_MARKETS list, no per-chain dict).
    "EULER_V2-ETHEREUM": "live",
    # ── Pipeline (Alchemy multi-chain gas-fee oracles — NOT IS-producible) ──
    "ALCHEMY-ARBITRUM": "pipeline",
    "ALCHEMY-BASE": "pipeline",
    "ALCHEMY-ONCHAIN": "pipeline",
    "ALCHEMY-OPTIMISM": "pipeline",
    "ALCHEMY-POLYGON": "pipeline",
    # ── Pipeline (Plasma chain variants — no MTDS tick data yet, added 2026-05-22) ──
    "AAVE-PLASMA": "pipeline",
    "FLUID-PLASMA": "pipeline",
    # ── Live (Linea — IS-producible per _build_defi_venues()) ──
    "AAVE_V3-LINEA": "live",
    # ── Pipeline (Scroll / zkSync — NOT IS-producible) ──
    "AAVE_V3-SCROLL": "pipeline",
    "COMPOUND_V3-SCROLL": "pipeline",
    "AAVE_V3-ZKSYNC": "pipeline",
    # ── Live (Solana — IS-producible per _build_defi_venues()) ──
    "KAMINO-SOLANA": "live",
    "MARINADE-SOLANA": "live",
    "ORCA-SOLANA": "live",
    "RAYDIUM-SOLANA": "live",
    "JITO-SOLANA": "live",
    # DRIFT (Solana) removed 2026-07-16 (operator ruling: all Solana perp DEXes
    # dropped except Jupiter, not integrated).
    # MarginFi + Solend Solana lending adapters (2026-07-09) — real,
    # IS-producible per _build_defi_venues() (marginfi.py / solend.py now
    # wired into instruments-service's factory + the Solana venue list).
    "MARGINFI-SOLANA": "live",
    "SOLEND-SOLANA": "live",
    # ── Live (Solana LST / restaking / native-staking — IS-wired 2026-07-18:
    #    sanctum.py / solblaze.py / jito_restaking.py / solana_native_staking.py
    #    adapters produce real rows via _build_defi_venues()) ──
    "SOLBLAZE-SOLANA": "live",
    "JITORESTAKING-SOLANA": "live",
    "SANCTUM-SOLANA": "live",
    "SOLANA-NATIVE-SOLANA": "live",
    # ── Pipeline (Solana — JUPITER is execution-only aggregator, no IS adapter) ──
    "JUPITER-SOLANA": "pipeline",
    # ── Pipeline (Solana DEX pools — 2026-07-20 DeFi catalogue canonicalization,
    #    narrowed back from "live" 2026-07-22: meteora.py/lifinity.py/phoenix.py
    #    adapters are correctly wired + registered in IS factory._ADAPTERS, but
    #    all 3 upstreams are measurably dead (404/522/NXDOMAIN, re-verified
    #    2026-07-22 — same as the original 2026-07-20 finding), so phase="live"
    #    manufactured a permanently-unattainable numerator in the honest-coverage
    #    denominator. Re-promote to "live" in the SAME commit an upstream
    #    migration/replacement lands. SSOT:
    #    issues/uac_is_defi_oracle_dex_adapter_drift_2026_07_20.md) ──
    "METEORA-SOLANA": "pipeline",
    "LIFINITY-SOLANA": "pipeline",
    "PHOENIX-SOLANA": "pipeline",
    # ── Live (Oracle price feeds — 2026-07-20 DeFi catalogue canonicalization;
    #    pyth.py / chainlink.py adapters produce oracle_prices; CHAINLINK-*
    #    flipped live once instruments-service@6506b505 landed the real
    #    per-chain adapter, resolving BLK-0c7b82fe) ──
    "PYTH-SOLANA": "live",
    "CHAINLINK-ETHEREUM": "live",
    "CHAINLINK-ARBITRUM": "live",
    "CHAINLINK-BASE": "live",
    "CHAINLINK-OPTIMISM": "live",
    "CHAINLINK-POLYGON": "live",
}


# ---------------------------------------------------------------------------
# DEFI_VENUE_MTDS_ADAPTER_VERIFIED_NOT_YET_SCHEDULED — venues whose on-chain-
# read ADAPTER has been independently verified accurate (cross-RPC, same
# historical block, exact match to N decimal places), but which are NOT YET
# captured by any healthy scheduled production job.
#
# Membership here means "if you backfill/schedule this venue, the read logic
# is correct" -- it does NOT mean "the pipeline is capturing this venue," and
# it is deliberately NOT named/shaped like a "captured data" constant: the
# verification behind every entry is a SINGLE manual/ad-hoc invocation on one
# historical day, not an ongoing or scheduled capture. Do not promote a venue
# out of this dict until there is evidence of an actual scheduled/cron-driven
# capture succeeding (see uts-prod-mtds-collect-lst-rates, which currently
# fails both of its tracked runs -- OOM/timeout crash-loop -- and additionally
# targets "yesterday" relative to run date rather than an explicit historical
# day, so it could not have produced this data even if healthy).
#
# This is NOT wired into DEFI_VENUE_PHASE (phase stays "pipeline" for every
# entry below -- none of these venues has an instruments-service reference-
# data adapter), VENUES_BY_ASSET_GROUP["defi"], or MVP_SCOPE["defi"].venues.
#
# SSOT: unified-trading-pm design doc "Correction Design: 11 DeFi Venues →
# Honest-Coverage Registry" (2026-07-22). Of the 11 venues investigated, only
# these 6 qualified as ACCURATE-BUT-MANUAL-ONLY; FRAX (UNVERIFIED-CLAIM: real
# data exists but stopped dead 2026-06-21, no scheduler) and ALCHEMY /
# FLASHBOTS / ACROSS / STARGATE (STILL-BROKEN: crash-looping cron or never
# scheduled at all, two with no SchemaContract registered) do NOT qualify and
# are deliberately excluded -- see that design doc for the full per-venue
# evidence and the deferred follow-up items for those five.
# ---------------------------------------------------------------------------
DEFI_VENUE_MTDS_ADAPTER_VERIFIED_NOT_YET_SCHEDULED: dict[str, str] = {
    "ANKR-ETHEREUM": (
        "single verified-accurate ratio() read for ankrETH, day=2026-07-20, "
        "block 25573787, via manual/ad-hoc invocation -- NOT the scheduled "
        "uts-prod-mtds-collect-lst-rates cron (currently crash-looping on "
        "OOM/timeout; also targets 'yesterday' relative to run date, never "
        "day=2026-07-20 as run on 2026-07-22)."
    ),
    "STADER-ETHEREUM": (
        "single verified-accurate getExchangeRate() read for ETHx, "
        "day=2026-07-20, block 25573787, manual/ad-hoc invocation only; "
        "production cron not yet capturing this venue."
    ),
    "STAKEWISE-ETHEREUM": (
        "single verified-accurate convertToAssets(1e18) read for osETH, "
        "day=2026-07-20, block 25573787, manual/ad-hoc invocation only; "
        "production cron not yet capturing this venue."
    ),
    "SWELL-ETHEREUM": (
        "single verified-accurate swETHToETHRate() read for swETH, "
        "day=2026-07-20, block 25573787, manual/ad-hoc invocation only; "
        "production cron not yet capturing this venue."
    ),
    "MANTLE-ETHEREUM": (
        "single verified-accurate mETHToETH(1e18) read for mETH, "
        "day=2026-07-20, block 25573787, manual/ad-hoc invocation only; "
        "production cron not yet capturing this venue."
    ),
    "MAKER-ETHEREUM": (
        "single verified-accurate convertToAssets(1e18) read for sDAI, "
        "day=2026-07-20, block 25573787, manual/ad-hoc invocation only; "
        "GCS object present but manifest row MISSING for this day (artifact "
        "of the manual run's execution order, not a MAKER-specific writer "
        "bug -- see provenance note); production cron not yet capturing "
        "this venue."
    ),
}


# On-chain perpetual DEX venues that are DeFi by settlement (wallet-signed
# transactions, on-chain custody) but eligible as hedge leg candidates for
# cross-venue funding arbitrage and basis trades alongside CeFi perp venues.
# Strategy archetypes MUST NOT assume perp_venues ⊆ cefi — include this list
# when building hedge leg candidate universes.
#
# SSOT: cross_asset_group_catalogue_audit_2026_05_10.md Phase 1C
# (revised 2026-05-13 per operator — GMX/DRIFT are DeFi-only; prior cefi-axis
# routing via DEFI_VENUE_AXIS_OVERRIDES was incorrect).
DEFI_PERP_VENUES: list[str] = [
    # GMX perpetual DEX — Arbitrum + Avalanche (on-chain, wallet-signed settlement)
    "GMX-ARBITRUM",
    "GMX-AVALANCHE",
    # DRIFT (Solana) removed 2026-07-16 (operator ruling): all Solana perp DEXes
    # dropped except Jupiter (not integrated). SSOT: unified-trading-pm/codex/
    # 04-architecture/solana-defi-coverage.md.
]

# Formerly routed GMX/DRIFT to the cefi axis (CLOB-style data shape reasoning).
# Emptied 2026-05-13: operator revised — GMX/DRIFT are DeFi-only; see
# DEFI_PERP_VENUES above. Preserved for future venue axis-override semantics.
DEFI_VENUE_AXIS_OVERRIDES: dict[str, str] = {}


# Curated subset of DeFi venues that MTDS actively backfills. Used as
# ``VENUES_BY_ASSET_GROUP['defi']`` in ``market_data_categories.py``.
# Extracted here to keep that module under the 900-line QG ceiling as the
# DeFi multi-chain coverage grows.
MTDS_DEFI_VENUES: list[str] = [
    # --- DEX protocols (swaps + liquidity) ---
    "UNISWAP_V2-ETHEREUM",
    "UNISWAP_V3-ETHEREUM",
    "UNISWAP_V3-ARBITRUM",
    "UNISWAP_V3-BASE",
    "UNISWAP_V3-OPTIMISM",
    "UNISWAP_V3-POLYGON",
    "UNISWAP_V4-ETHEREUM",
    "CURVE-ETHEREUM",
    "CURVE-AVALANCHE",
    "CURVE-OPTIMISM",
    "BALANCER-ETHEREUM",
    "BALANCER-ARBITRUM",
    "BALANCER-AVALANCHE",
    "BALANCER-BASE",
    "BALANCER-OPTIMISM",
    "BALANCER-POLYGON",
    # --- Lending protocols ---
    "AAVE_V3-ETHEREUM",
    "AAVE_V3-ARBITRUM",
    "AAVE_V3-AVALANCHE",
    "AAVE_V3-BASE",
    "AAVE_V3-BSC",
    "AAVE_V3-LINEA",
    "AAVE_V3-OPTIMISM",
    "AAVE_V3-POLYGON",
    "COMPOUND_V3-ETHEREUM",
    "COMPOUND_V3-ARBITRUM",
    "COMPOUND_V3-BASE",
    "COMPOUND_V3-OPTIMISM",
    "COMPOUND_V3-POLYGON",
    "MORPHO-ETHEREUM",
    "MORPHO-ARBITRUM",
    "MORPHO-BASE",
    "MORPHO-OPTIMISM",
    "MORPHO-POLYGON",
    "FLUID-ETHEREUM",
    "FLUID-ARBITRUM",
    "EULER_V2-ETHEREUM",
    "EULER_V2-ARBITRUM",
    "RADIANT-ETHEREUM",
    "RADIANT-ARBITRUM",
    "RADIANT-BSC",
    "VENUS-BSC",
    "VENUS-ETHEREUM",
    "BENQI-AVALANCHE",
    # --- LST/Yield protocols ---
    "LIDO-ETHEREUM",
    "ETHERFI-ETHEREUM",
    "ETHENA-ETHEREUM",
    "JITO-SOLANA",
    # --- DeFi perp DEXes (EVM + Solana) ---
    # GMX: operator revised 2026-05-13 — DeFi-only (not CeFi axis).
    "GMX-ARBITRUM",
    "GMX-AVALANCHE",
    # DRIFT (Solana) removed 2026-07-16 (operator ruling): all Solana perp DEXes
    # dropped except Jupiter (not integrated). SSOT: unified-trading-pm/codex/
    # 04-architecture/solana-defi-coverage.md.
    # METEORA-SOLANA / LIFINITY-SOLANA / PHOENIX-SOLANA excluded 2026-07-22:
    # phase="pipeline" (measured-dead upstreams), see DEFI_VENUE_PHASE above.
    # --- Oracle price feeds (2026-07-20 DeFi catalogue canonicalization) ---
    "CHAINLINK-ETHEREUM",
    "CHAINLINK-ARBITRUM",
    "CHAINLINK-BASE",
    "CHAINLINK-OPTIMISM",
    "CHAINLINK-POLYGON",
    "PYTH-SOLANA",
]


__all__ = [
    "ALL_DEFI_VENUES",
    "DEFI_VENUE_AXIS_OVERRIDES",
    "DEFI_VENUE_MTDS_ADAPTER_VERIFIED_NOT_YET_SCHEDULED",
    "DEFI_VENUE_PHASE",
    "LEGACY_DEFI_VENUE_ALIASES",
    "MTDS_DEFI_VENUES",
    "to_canonical_venue",
]
