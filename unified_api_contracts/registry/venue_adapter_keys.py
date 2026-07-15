"""Venue → URDI adapter-key registry (pure data — adapter CLASSES live in instruments-service).

UAC owns WHICH adapter key serves each canonical venue; instruments-service owns
the key→class instantiation table (`reference_data/factory.py::_ADAPTERS`). This
split respects the tier/import architecture (UAC is upstream of IS, so no IS
import may appear here) while killing the last venue-truth mirror: before
2026-07-03 this mapping lived as an independent hardcoded dict inside the IS
factory, where it could silently drift from ``VENUES_BY_ASSET_GROUP``.
SSOT: codex/04-architecture/instrument-universe-registry-consolidation.md.

A venue may be mapped to :data:`NO_ADAPTER_YET` — an explicit, loud sentinel for
venues that exist in the canonical universe but have no URDI reference adapter
(MTDS-owned odds venues, source-as-venue artifacts, expand-only bare forms).
Resolving a sentinel venue MUST raise, never silently skip: the sentinel exists
so "no adapter" is a declared fact, not a missing dict entry.
"""

from __future__ import annotations

from .capability_declarations import get_supported_chains_for_protocol

#: Explicit "venue is canonical but has no URDI reference adapter" marker.
#: Consumers must treat this as NOT resolvable (raise / classify UNSUPPORTED) —
#: it is present so coverage checks can distinguish "declared adapterless"
#: from "someone forgot to register the venue".
NO_ADAPTER_YET: str = "__no_adapter_yet__"

# Maps UAC venue PREFIX → protocol slug for subgraph-backed multi-chain DeFi
# venues (AAVE_V3-ARBITRUM → aave_v3, …). The chain axis comes from
# SUBGRAPH_IDS via get_supported_chains_for_protocol(). Legacy glued forms
# (VELODROMEV2/TRADER_JOEV2) kept for back-compat during the
# venue-canonicalisation migration window.
VENUE_PREFIX_TO_PROTOCOL: dict[str, str] = {
    "AAVE_V3": "aave_v3",
    "COMPOUND_V3": "compound_v3",
    "MORPHO": "morpho",
    "FLUID": "fluid",
    "UNISWAP_V2": "uniswap_v2",
    "UNISWAP_V3": "uniswap_v3",
    "UNISWAP_V4": "uniswap_v4",
    "BALANCER": "balancer",
    "CURVE": "curve",
    # DEX forks — each has own subgraph IDs, reuse the UniV3 adapter downstream.
    "PANCAKESWAP_V3": "pancakeswap_v3",
    "SUSHISWAP_V3": "sushiswap_v3",
    "AERODROME_V3": "aerodrome_v3",
    "CAMELOT_V3": "camelot_v3",
    "VELODROME_V2": "velodrome_v2",
    "VELODROMEV2": "velodrome_v2",
    "TRADER_JOE_V2": "trader_joe_v2",
    "TRADER_JOEV2": "trader_joe_v2",
    "GMX": "gmx",
    # Messari lending (Spark = Aave V3 fork, same schema).
    "SPARK": "spark",
    "SUSHISWAP": "sushiswap",
    # DeFi pipeline extension Phase 4 — lending protocols.
    "EULER_V2": "euler_v2",
    "RADIANT": "radiant",
    "VENUS": "venus",
    "BENQI": "benqi",
}

# Protocols that reuse another adapter's key. If not listed, adapter_key == protocol_slug.
PROTOCOL_TO_ADAPTER_KEY: dict[str, str] = {
    "pancakeswap_v3": "uniswap_v3",
    "sushiswap_v3": "uniswap_v3",
    "aerodrome_v3": "uniswap_v3",
    "camelot_v3": "uniswap_v3",
    "velodrome_v2": "uniswap_v3",
    "trader_joe_v2": "uniswap_v3",
    "gmx": "uniswap_v3",
    "sushiswap": "uniswap_v3",
}

# Maps UAC canonical venue names → URDI adapter keys.
# Key: UAC canonical venue name (uppercase, hyphenated).
# Value: adapter key resolved by instruments-service `_ADAPTERS` (key→class),
#        or NO_ADAPTER_YET for declared-adapterless venues.
VENUE_TO_ADAPTER_KEY: dict[str, str] = {
    # CeFi — Tardis for batch (historical instrument universe); the IS factory
    # routes live mode to CCXT for these venues (mode seam lives in IS, not here).
    "BINANCE-SPOT": "tardis",
    "BINANCE-FUTURES": "tardis",
    # Binance COIN-M (inverse/delivery) perps + dated futures. Distinct Tardis
    # endpoint ``binance-delivery`` from the USDT-M ``binance-futures`` endpoint.
    "BINANCE-DELIVERY": "tardis",
    "BYBIT": "tardis",
    "BYBIT-SPOT": "tardis",
    "BYBIT-FUTURES": "tardis",
    "OKX": "tardis",
    "OKX-SPOT": "tardis",
    "OKX-SWAP": "tardis",
    "OKX-FUTURES": "tardis",
    "DERIBIT": "tardis",
    # DERIBIT-COMBO: batch (historical) combo instruments come via the Tardis
    # adapter — confirmed live 2026-07-14, api.tardis.dev/v1/exchanges/deribit
    # carries 68,847 type=='combo' symbols back to 2022-08-23. IS factory's
    # mode seam routes mode="live" to the Deribit public REST adapter instead
    # (deribit_combo) — Deribit's get_combos endpoint only exposes currently-
    # active combos, no historical retention, so it is live-only; Tardis's
    # archived feed covers historical. See
    # cefi_layer1_denominator_gaps_2026_07_03.md (NEW FINDING 2026-07-14).
    "DERIBIT-COMBO": "tardis",
    # DERIBIT-OPTIONS: live option-chain enumeration + mark IV via Deribit public REST.
    "DERIBIT-OPTIONS": "deribit_options",
    "COINBASE-SPOT": "tardis",
    # Coinbase Derivatives (perps) via Tardis ``coinbase-international``.
    "COINBASE-FUTURES": "tardis",
    "UPBIT": "tardis",
    # Tier-3 CeFi (2026-05-01) — Tardis archives spot + perp/dated futures.
    "BITFINEX-SPOT": "tardis",
    "BITFINEX-FUTURES": "tardis",
    "BITGET-SPOT": "tardis",
    "BITGET-FUTURES": "tardis",
    "KRAKEN-SPOT": "tardis",
    "KRAKEN-FUTURES": "tardis",
    # Non-Tardis CeFi
    "HYPERLIQUID": "hyperliquid",
    "ASTER": "aster",
    "COINBASE-CDE": "coinbase_cde",  # 2026-07-10, native Advanced Trade REST, zero Tardis coverage
    # TradFi
    "CME": "databento",
    "NASDAQ": "databento",
    "NYSE": "databento",
    "CBOE": "databento",
    "ICE": "databento",
    # FX never touches Databento — execution is FXAdapter (IBKR IDEALPRO), market data is
    # Yahoo Finance fetched via a hardcoded venue_upper == "FX" branch in MTDS's
    # umi_tick_provider.py, bypassing VENUE_TO_ADAPTER_KEY/URDI entirely. No URDI reference-data
    # adapter class exists for Yahoo Finance (checked instruments-service's _ADAPTERS) — FX
    # genuinely has no URDI adapter, so this is NO_ADAPTER_YET, not a phantom vendor key.
    "FX": NO_ADAPTER_YET,
    "KRX": "databento",
    # YAHOO_FINANCE removed 2026-07-15 — it was a source-as-venue modeling error, not
    # a real venue (no adapter, no fetch code stamps venue=YAHOO_FINANCE). Yahoo is a
    # SOURCE; its rows land under real venues with source=yahoo. IS's
    # _TRADFI_NON_VENUE_KEYS filter no longer needs to exclude it.
    # Prediction markets
    "POLYMARKET": "polymarket",
    "KALSHI": "kalshi",
    # Prediction-platform crypto-perp CLOBs (CFTC-regulated perpetual futures,
    # NOT prediction YES/NO markets). Treated as cefi asset_group.
    "KALSHI-PERP": "kalshi_perp",
    "POLYMARKET-PERP": "polymarket_perp",
    # DeFi — LST/Yield protocols (Ethereum-only, no subgraph multi-chain)
    "LIDO-ETHEREUM": "lido",
    "ETHERFI-ETHEREUM": "etherfi",
    "ETHENA-ETHEREUM": "ethena",
    "ROCKETPOOL-ETHEREUM": "rocket_pool",
    "RENZO-ETHEREUM": "renzo",
    "RENZO-ARBITRUM": "renzo",
    "KELPDAO-ETHEREUM": "kelpdao",
    "PUFFER-ETHEREUM": "puffer",
    "SYMBIOTIC-ETHEREUM": "symbiotic",
    "KARAK-ETHEREUM": "karak",
    "KARAK-ARBITRUM": "karak",
    # DeFi — Vault/yield-aggregator protocols (Ethereum + L2, static curated registry)
    "CONVEX-ETHEREUM": "convex",
    "IDLE-ETHEREUM": "idle",
    "IDLE-ARBITRUM": "idle",
    # YEARN_V3, not bare YEARN — PROTOCOL_CAPABILITIES / DEPRECATED_DEFI_GHOST_VENUE_NAMES /
    # defi_venue_capabilities.py / venue_launch_dates.py / defi_venues.py / chain_env.py all
    # treat YEARN_V3 as canonical (operator decision 2026-07-08, instrument_id_format_
    # canonicalization systemic-duplicate-spelling pass — this was the outlier registry).
    "YEARN_V3-ETHEREUM": "yearn",
    "YEARN_V3-ARBITRUM": "yearn",
    # Beefy multi-chain yield aggregator (curated TOP-vault snapshot per chain).
    # Polygon intentionally excluded 2026-05-12 — every Polygon vault was
    # status=eol on the curated snapshot date.
    "BEEFY-ETHEREUM": "beefy",
    "BEEFY-ARBITRUM": "beefy",
    "BEEFY-BASE": "beefy",
    "BEEFY-BSC": "beefy",
    "BEEFY-AVALANCHE": "beefy",
    # Pendle yield-tokenization (PT/YT/SY tokens — curated active-markets snapshot).
    "PENDLE-ETHEREUM": "pendle",
    "PENDLE-ARBITRUM": "pendle",
    # Jito Restaking — distinct from JITO-SOLANA (LST). Solana NCN-vault primitive.
    "JITORESTAKING-SOLANA": "jito_restaking",
    # DeFi — Governance tokens (on-chain, Ethereum)
    "EIGENLAYER-ETHEREUM": "eigenlayer",
    "ETHERFI-GOV-ETHEREUM": "ethfi_governance",
    # Sports — IS-owned reference providers with URDI adapters.
    "BETFAIR": "betfair",
    "API_FOOTBALL": "api_football",
    # Sports — MTDS-owned odds venues (registry-consolidation Decision C,
    # 2026-06-29: two separate registries; odds/bookmaker market data is
    # captured by MTDS, so IS has no reference adapter for them).
    "ODDS_API": NO_ADAPTER_YET,
    "PINNACLE": NO_ADAPTER_YET,
    "BETFAIR_SB_UK": NO_ADAPTER_YET,
    "BETFAIR_EX_UK": NO_ADAPTER_YET,
    "BETFAIR_EX_EU": NO_ADAPTER_YET,
    "DRAFTKINGS": NO_ADAPTER_YET,
    "FANDUEL": NO_ADAPTER_YET,
    # Solana DeFi (REST API, no subgraph)
    "DRIFT-SOLANA": "drift",
    "KAMINO-SOLANA": "kamino",
    "RAYDIUM-SOLANA": "raydium",
    "ORCA-SOLANA": "orca",
    "MARINADE-SOLANA": "marinade",
    "JITO-SOLANA": "jito",
    "SANCTUM-SOLANA": "sanctum",
    "SOLBLAZE-SOLANA": "solblaze",
    "SOLANA-NATIVE-SOLANA": "solana_native",
    # Solana lending adapters (2026-07-09) — real public REST/JSON APIs.
    "MARGINFI-SOLANA": "marginfi",
    "SOLEND-SOLANA": "solend",
    # RADIANT-BSC (2026-07-10): the auto-gen loop below only covers chains with
    # a registered subgraph_id (SUBGRAPH_IDS["radiant"] = ARBITRUM+ETHEREUM
    # only — Radiant's BSC deployment has no verified subgraph). The IS
    # reference-data adapter (radiant.py) is NOT subgraph-based for instrument
    # DISCOVERY though — it uses a curated per-chain markets dict that DOES
    # include BSC — so this venue is genuinely IS-producible via that curated
    # path even without a subgraph_id. Explicit entry since the auto-gen loop
    # can't infer it. mtds_is_full_adapter_smoketest_findings_2026_07_07.md P1.
    "RADIANT-BSC": "radiant",
    # Jupiter is execution-only (swap aggregator), not instrument discovery.
    # DEX perp venues (L2 + StarkNet + Solana clone)
    "LIGHTER-ZKSYNC": "lighter",
    "EXTENDED-STARKNET": "extended",
    "PACIFICA-SOLANA": "pacifica",
    # MANGO-SOLANA/ZETA-SOLANA/FLASH-SOLANA (Plan B 2026-05-13) removed 2026-07-15
    # (operator ruling): all 3 declared API hosts are dead (api.mngo.cloud/
    # api.flash.trade NXDOMAIN, dex.zeta.markets/api returns HTML not JSON), ~$0
    # DeFiLlama TVL, zero MTDS market-data capture ever wired. SSOT:
    # unified-trading-pm/codex/04-architecture/solana-defi-coverage.md.
    # SOLAYER/PICASSO/CAMBRIAN-SOLANA removed 2026-06-02 (operator decision; no
    # usable/decodable DeFi data source).
}

# Dynamically add multi-chain DeFi venues from SUBGRAPH_IDS (SSOT above in this
# package). Auto-generates entries like AAVE_V3-ARBITRUM → aave_v3.
for _prefix, _protocol_slug in VENUE_PREFIX_TO_PROTOCOL.items():
    _adapter_key = PROTOCOL_TO_ADAPTER_KEY.get(_protocol_slug, _protocol_slug)
    for _chain in get_supported_chains_for_protocol(_protocol_slug):
        _venue = f"{_prefix}-{_chain}"
        if _venue not in VENUE_TO_ADAPTER_KEY:
            VENUE_TO_ADAPTER_KEY[_venue] = _adapter_key

#: Venues with a real URDI reference adapter (sentinel entries excluded).
#: This is the canonical "URDI-supported" membership set — instruments-service
#: URDI_SUPPORTED_VENUES and UTL startup venue-name validation both read it.
VENUES_WITH_REFERENCE_ADAPTER: frozenset[str] = frozenset(
    venue for venue, key in VENUE_TO_ADAPTER_KEY.items() if key != NO_ADAPTER_YET
)
