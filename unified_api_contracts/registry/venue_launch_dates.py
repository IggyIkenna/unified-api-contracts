"""Venue launch dates — SSOT for CeFi + Prediction "venue did not exist yet" semantics.

Sister registry to ``chain_env.CHAIN_GENESIS_DATES`` (DeFi pre-genesis) and the sports
``SOURCE_COVERAGE_START`` dict (api_football / footystats / understat archive starts).
All three express the same idea ("no data possible because the venue/chain/source did
not exist yet on this date") for different asset_groups, but the SSOTs are deliberately
separate because the underlying data sources are different.

Used by:

- ``instruments-service/scripts/enumerate_expected_universe.py`` Phase 3.D.4 backward-fill —
  generates ``record_expected_empty(reason=EXPECTED_PRE_VENUE_LAUNCH)`` rows for every
  ``(asset_group, venue, data_type, day)`` tuple where ``day < launch_date``.
- ``deployment-api`` data-status panel: clip pre-venue-launch dates from the expected
  denominator so the panel doesn't render thousands of "missing" days for venues that
  only existed for the last few months (Hyperliquid, Aster, Lighter, Extended).

**Conservative principle**: when uncertain, prefer the LATER (more recent) date. A
later date means fewer ``EXPECTED_PRE_VENUE_LAUNCH`` rows are emitted; if our value is
later than the actual launch, the missing few days simply stay as ``capture_status=
captured`` (or ``empty_confirmed`` if the orchestrator already ran). The cost of a
slightly-stale date is "a few days of pre-launch dates rendered as missing in the
denominator." The cost of a too-early date would be "real data dates marked as
PRE_VENUE_LAUNCH" — a correctness bug. Better to undercount than overcount.

Add a venue here when:

1. The venue appears in ``VENUES_BY_ASSET_GROUP['cefi']`` or
   ``VENUES_BY_ASSET_GROUP['prediction']``, AND
2. Its public launch date is after 2018-01-01 (the workspace's default backfill start
   date) — otherwise the [2018-01-01, today] window has zero pre-launch days and the
   entry is no-op.

Sources for the dates below: official venue announcements + CoinGecko / DefiLlama
"founded" fields cross-checked. Documented per-venue inline so future audits can verify.
"""

from __future__ import annotations

from typing import Final

# ---------------------------------------------------------------------------
# CeFi venue launch dates — the date the venue began offering public trading
# of the data_type axis we'd actually backfill against (spot trades, perp
# futures, etc.). For venues with separate spot vs futures launches, the two
# are tracked as distinct VENUES_BY_ASSET_GROUP entries (e.g. KRAKEN-SPOT vs
# KRAKEN-FUTURES) and dated independently.
# ---------------------------------------------------------------------------

CEFI_VENUE_LAUNCH_DATES: dict[str, str] = {
    # Pre-2018-01-01 venues — entries are kept for completeness + downstream
    # data-status display, but the enumerator's pre-launch loop yields zero
    # rows for them within the default [2018-01-01, today] window.
    "BINANCE-SPOT": "2017-07-14",  # Binance launch
    "BINANCE-FUTURES": "2019-09-08",  # USDT-M futures launch
    "OKX": "2017-01-01",  # OKEx founded; rebranded OKX 2022
    "DERIBIT": "2016-06-29",  # mainnet
    # Deribit combo/spread instruments (future_combo + option_combo) — distinct
    # manifest venue. Verified 2026-07-12 (cefi_deribit_combo_and_okx_bare_venue_
    # gaps issue) against live Tardis ``deribit`` exchange metadata
    # (api.tardis.dev/v1/exchanges/deribit): the earliest ``availableSince``
    # across all 68,720 ``type=='combo'`` symbols is 2022-08-23 — combos are a
    # materially newer product than plain options (bare DERIBIT launched
    # 2016-06-29), so the prior 2019-01-01 placeholder undercounted the
    # pre-launch window by ~3.5 years.
    "DERIBIT-COMBO": "2022-08-23",
    "UPBIT": "2017-10-24",  # KRW market launch
    "COINBASE-SPOT": "2014-12-08",  # GDAX launch (rebranded Coinbase Pro 2018)
    "BITFINEX-SPOT": "2012-12-27",  # founded
    "BITFINEX-FUTURES": "2019-08-01",  # perp launch
    "BITGET-SPOT": "2018-04-01",  # founded
    "BITGET-FUTURES": "2019-04-01",  # futures product launch
    "KRAKEN-SPOT": "2013-09-10",  # BTC trading launch (founded 2011)
    "KRAKEN-FUTURES": "2019-09-01",  # acquired CryptoFacilities, rebranded Kraken Futures
    # Post-2018 venues — these are the ones that actually generate
    # EXPECTED_PRE_VENUE_LAUNCH rows in the [2018-01-01, today] window.
    "BYBIT": "2018-12-01",  # founded Mar 2018, public trading Dec 2018
    "HYPERLIQUID": "2023-06-14",  # mainnet beta
    # Astherus pre-rebrand genesis (operator-confirmed 2026-06-17);
    # pre-2024 funding is Binance-proxied (imported, not Aster-native).
    "ASTER": "2023-07-22",
    # DRIFT / PACIFICA (Solana) removed 2026-07-16 (operator ruling: all Solana
    # perp DEXes dropped except Jupiter, not integrated). SSOT: unified-
    # trading-pm/codex/04-architecture/solana-defi-coverage.md.
    "EXTENDED-STARKNET": "2024-09-01",  # Extended on Starknet
    "LIGHTER-ZKSYNC": "2024-09-01",  # Lighter on zkSync Era
    "GMX": "2021-09-01",  # GMX V1 on Arbitrum (V2 launched 2023-08)
    # Prediction-platform PERPETUAL FUTURES — crypto perps with funding. NOT
    # the same as KALSHI/POLYMARKET prediction YES/NO markets (those are in
    # PREDICTION_VENUE_LAUNCH_DATES). These are CFTC-regulated crypto perps in
    # the CeFi perp universe. SSOT:
    # plans/active/prediction_venue_perps_and_live_clob_depth_2026_06_20.md
    "KALSHI-PERP": "2026-05-29",  # Kalshi CFTC crypto perp futures launch
    "POLYMARKET-PERP": "2026-04-21",  # Polymarket perp beta launch
}
"""CeFi venue → public-launch date (ISO YYYY-MM-DD).

Date is the venue's earliest public-trading-available date for the data axis
we'd want to backfill (spot trades for spot venues, perp futures for futures
venues). For venues launched before the workspace's default 2018-01-01 backfill
start, the entry is informational — the enumerator yields zero pre-launch rows
within the default window.
"""


# ---------------------------------------------------------------------------
# Prediction venue launch dates — when the venue began offering public
# binary/multi-outcome markets that our pipeline could ingest.
# ---------------------------------------------------------------------------

PREDICTION_VENUE_LAUNCH_DATES: dict[str, str] = {
    "POLYMARKET": "2020-09-01",  # mainnet launch on Polygon
    "KALSHI": "2021-07-30",  # CFTC-approved exchange launch
}
"""Prediction venue → public-launch date (ISO YYYY-MM-DD).

Polymarket launched on Polygon mainnet 2020-09 (early markets used Matic
sidechain). Kalshi opened trading 2021-07 after CFTC approval. Both are
well after the workspace 2018-01-01 default — so both contribute
EXPECTED_PRE_VENUE_LAUNCH rows in the default window.
"""


# ---------------------------------------------------------------------------
# DeFi venue launch dates — when the protocol-chain combination became
# publicly active on-chain. Distinct from ``CHAIN_GENESIS_DATES`` (which only
# tells us the chain existed). A protocol-chain row in the manifest needs
# BOTH chain genesis AND protocol launch to be live on that date.
#
# Codified 2026-05-13 (slot 3) after `_classify_defi` was found to only check
# chain genesis (Ethereum 2015-07-30) but not protocol launch (Aave V3
# 2022-03-16). Result: 604,951 defi rows wrongly flipped from
# ``empty_confirmed/EXPECTED_INSTRUMENT_NOT_LISTED`` to
# ``attempted_failed/LegacyBlankErrorReasonError`` because the wrapper had no
# way to detect pre-protocol-launch dates. See issue doc
# ``plans/active/issues/defi_legacy_blank_reclassification_2026_05_13.md``.
#
# Keys are the ``protocol-chain`` venue string used in the defi manifest's
# ``venue`` column (e.g. ``"AAVE_V3-ETHEREUM"``). Bare protocol names (e.g.
# ``"MAKER"``, ``"YEARN_V3"``) are protocols that span all chains via a single
# manifest row — those use just the protocol name without chain suffix.
#
# Per the conservative-prefer-later principle (see CeFi block above):
# undercounting EXPECTED_PRE_VENUE_LAUNCH rows is safer than overcounting.
# If unsure, pick a slightly LATER date.
# ---------------------------------------------------------------------------

DEFI_VENUE_LAUNCH_DATES: dict[str, str] = {
    # Aave V3 — March 16 2022 multi-chain launch (POLY/AVAX/ARB/OPT). ETHEREUM is
    # the exception: Aave V3 did NOT deploy on Ethereum mainnet until 2023-01-27
    # (2022-03-16 was the L2/side-chain cohort date, NOT Ethereum). Corrected
    # 2026-07-18 to match the subgraph-audited `chain_env.PROTOCOL_LAUNCH_DATES`
    # (("ETHEREUM","AAVE_V3")="2023-01-27", first reserveParamsHistoryItems event
    # 2023-01-27 08:00:11 UTC, audit 2026-05-08) — the old 2022-03-16 mis-classified
    # 11 months of legitimate 2022-03→2023-01 Aave-V3-ETH data as empty_confirmed.
    # Also aligns with this registry's own "prefer LATER when uncertain" principle.
    # SSOT-reconciliation issue: uac_defi_launch_date_registry_drift_2026_07_18.
    # BSC/LINEA/ZKSYNC/SCROLL came later per official deployment timelines.
    "AAVE_V3-ETHEREUM": "2023-01-27",
    "AAVE_V3-POLYGON": "2022-03-12",
    "AAVE_V3-AVALANCHE": "2022-03-12",
    "AAVE_V3-ARBITRUM": "2022-03-16",
    "AAVE_V3-OPTIMISM": "2022-03-15",
    # On-chain verified 2026-07-18 (issue uac_defi_launch_date_registry_drift): Aave's own
    # changelog dates BNB Chain market go-live 2024-01-23 (2023-04-06 was the ARFC governance
    # date) and Linea 2025-02-11 (2024-09-26 matched no Linea deployment/vote/changelog event).
    "AAVE_V3-BSC": "2024-01-23",
    "AAVE_V3-LINEA": "2025-02-11",
    "AAVE_V3-ZKSYNC": "2024-04-09",
    "AAVE_V3-SCROLL": "2024-04-29",
    # Compound V3 ("Comet") — aligned 2026-07-18 to chain_env.PROTOCOL_LAUNCH_DATES, whose
    # Tab-14 subgraph audit (2026-05-08) gives day-precise FIRST-MARKET-ACTIVITY dates (the
    # "launch" the data denominator needs) for these pairs. A 2026-07-18 pass had briefly
    # overridden ARBITRUM/OPTIMISM with medium-confidence GOVERNANCE-execution dates
    # (2023-05-15 / 2024-04-16) — reverted: the subgraph audit outranks a governance date, and
    # the instruments-service evm_creation_resolver test pins the audited values. ETHEREUM's
    # 2022-08-26 (a launch-blog date) vs the audited 2022-08-13 first-event is a residual
    # contract-creation-vs-subgraph question flagged in the SSOT issue doc (needs Dune re-verify).
    "COMPOUND_V3-ETHEREUM": "2022-08-13",
    "COMPOUND_V3-POLYGON": "2023-02-15",
    "COMPOUND_V3-ARBITRUM": "2023-05-04",
    "COMPOUND_V3-BASE": "2023-08-04",
    "COMPOUND_V3-OPTIMISM": "2024-04-06",
    "COMPOUND_V3-SCROLL": "2024-04-22",
    # Uniswap V2 (May 2020), V3 (May 2021 ETH, Dec 2021 Polygon), V4 (Jan 2025).
    "UNISWAP_V2-ETHEREUM": "2020-05-04",
    "UNISWAP_V3-ETHEREUM": "2021-05-04",
    "UNISWAP_V3-POLYGON": "2021-12-21",
    "UNISWAP_V4-ETHEREUM": "2025-01-31",
    # SushiSwap V3 — April 2023.
    "SUSHISWAP_V3-ETHEREUM": "2023-04-04",
    # Curve — Jan 2020 launch (CRV token mainnet later, but pools live earlier).
    "CURVE-ETHEREUM": "2020-01-19",
    # Balancer V2 — March 2020 (V1 earlier but V2 is the active reference).
    "BALANCER-ETHEREUM": "2020-03-31",
    # Lido stETH — Dec 19 2020 ETH mainnet.
    "LIDO-ETHEREUM": "2020-12-19",
    # Frax stablecoin — Dec 21 2020.
    "FRAX-ETHEREUM": "2020-12-21",
    "FRAX": "2020-12-21",  # bare-protocol variant
    # Rocket Pool Atlas — Nov 9 2021 (rETH liquid staking).
    "ROCKETPOOL-ETHEREUM": "2021-11-08",
    # Ethena USDe — Feb 20 2024 mainnet launch.
    "ETHENA-ETHEREUM": "2024-02-19",
    "ETHENA": "2024-02-20",  # bare-protocol variant
    # ether.fi liquid restaking — April 26 2023 mainnet.
    "ETHERFI-ETHEREUM": "2023-04-25",
    # Solana DeFi protocols
    "KAMINO-SOLANA": "2022-08-24",  # Kamino Aug 2022
    "JITO-SOLANA": "2022-08-16",  # Jito MEV+staking Aug 2022
    "MARINADE-SOLANA": "2021-08-02",  # Marinade mSOL launch
    # DRIFT (Solana) removed 2026-07-16 (operator ruling: all Solana perp DEXes
    # dropped except Jupiter, not integrated).
    "RAYDIUM-SOLANA": "2021-02-21",  # Raydium AMM launch
    "ORCA-SOLANA": "2021-02-09",  # Orca AMM launch
    # GMX — Sept 2021 Arbitrum, Jan 2022 Avalanche.
    "GMX-ARBITRUM": "2021-09-01",
    "GMX-AVALANCHE": "2022-01-05",
    # Yearn V3 — March 13 2024 launch (V2 earlier but V3 is referenced here).
    "YEARN_V3": "2024-03-13",
    # Morpho Vaults (MetaMorpho) — Jan 4 2024 launch.
    "MORPHOVAULTS": "2024-01-04",
    # On-chain perp DEX venues — the DeFi manifest keys perp_funding rows for
    # these (A2a). Dates mirror CEFI_VENUE_LAUNCH_DATES above (the same venues
    # feed the carry archetype's CeFi-perp leg); kept in sync. Added 2026-06-08
    # (slot-2 A2a) — clear new venues with documented public-launch dates, unlike
    # the DEX per-chain rows whose uniform 2021-01-01 first-captured date is a
    # data-quality artefact (see the A2a DEX-investigation todo — NOT added here
    # per the "do not bulk-add ambiguous dates" instruction).
    "HYPERLIQUID": "2023-06-14",  # Hyperliquid L1 perp DEX mainnet beta
    # Astherus pre-rebrand genesis (operator-confirmed 2026-06-17);
    # pre-2024 funding is Binance-proxied (imported, not Aster-native).
    "ASTER": "2023-07-22",
    "LIGHTER-ZKSYNC": "2024-09-01",  # Lighter perp DEX on zkSync Era
    # PACIFICA (Solana) removed 2026-07-16 (operator ruling: all Solana perp
    # DEXes dropped except Jupiter, not integrated). SSOT: unified-trading-pm/
    # codex/04-architecture/solana-defi-coverage.md.
    # Pre-2018 venues kept for completeness (no EXPECTED_PRE_VENUE_LAUNCH rows
    # within the default [2018-01-01, today] window):
    "MAKER": "2017-12-19",  # MakerDAO single-collateral DAI launch
    # ---------------------------------------------------------------------------
    # Bare-protocol launch dates for the LST / lending / DEX / restaking venues
    # that are in EXPECTED_COVERAGE_BY_ASSET_GROUP["defi"] (flat venue keys) but
    # had NO launch-date entry — the dominant residual DIVERGENT_EMPTY class
    # after the flat-protocol fallback landed (2026-06-22). Without these the
    # oracle returns SHOULD_HAVE_DATA for every date back to the 2018 window
    # start, flagging tens of thousands of honest pre-launch empties as
    # divergent. Conservative EARLIEST documented mainnet launch (per the
    # "prefer LATER when uncertain" rule these are well-documented dates).
    "MORPHO": "2022-06-16",  # Morpho Optimizer mainnet (Morpho Blue 2024-01; earliest = Optimizer)
    "MORPHOVAULTS-ETHEREUM": "2024-01-04",  # MetaMorpho vaults (sister of bare MORPHOVAULTS above)
    "AERODROME_V3": "2023-08-28",  # Aerodrome Finance launch on Base
    "CAMELOT_V3": "2023-05-15",  # Camelot V3 (Algebra) on Arbitrum
    "FLUID": "2024-01-30",  # Fluid (Instadapp) lending/DEX mainnet
    "SPARK": "2023-05-09",  # Spark Protocol (MakerDAO sub-DAO lending) mainnet
    "PUFFER": "2024-06-14",  # Puffer Finance pufETH liquid restaking mainnet
    "SWELL": "2023-04-12",  # Swell Network swETH liquid staking
    "STAKEWISE": "2021-03-24",  # StakeWise V2 liquid staking
    "STADER": "2023-01-10",  # Stader ETHx liquid staking (Polygon MaticX earlier; ETH = 2023)
    "MANTLE": "2024-01-26",  # Mantle mETH liquid staking (Mantle LSP)
    "ANKR": "2020-12-22",  # Ankr ankrETH liquid staking
    "COINBASE": "2022-08-24",  # Coinbase cbETH wrapped staked ETH launch
    "EIGENLAYER": "2023-06-14",  # EigenLayer restaking mainnet stage-1
    # PROTOCOL-CHAIN forms for the LST/vault venues IS-wired 2026-07-18. Each
    # AGREES with chain_env.PROTOCOL_LAUNCH_DATES (drift guard
    # test_venue_launch_dates_no_new_drift_vs_chain_env).
    "COINBASE-ETHEREUM": "2022-08-24",  # Coinbase cbETH LST
    "BINANCE-ETHEREUM": "2023-04-27",  # Binance wBETH LST (ETH Staking GA)
    "BINANCE-BSC": "2023-04-27",  # Binance wBETH LST on BSC (same-address deploy)
    "SANCTUM-SOLANA": "2023-06-01",  # Sanctum v1 LST marketplace
    "SOLBLAZE-SOLANA": "2022-10-15",  # SolBlaze bSOL stake-pool (conservative floor)
    "SOLANA-NATIVE-SOLANA": "2020-03-16",  # native SOL staking == mainnet-beta genesis
}
"""DeFi venue (``PROTOCOL-CHAIN`` or bare ``PROTOCOL``) → public-launch date.

Sister registry to ``CEFI_VENUE_LAUNCH_DATES``. The protocol-chain combo is
the relevant launch date because a protocol may deploy to a new chain years
after its original launch (e.g. Aave V3 launched 2022-03 on ETH/POLY/AVAX/
ARB/OPT but didn't reach BSC until 2023-04 or Linea until 2024-09).

Used by ``_classify_defi`` in
``unified_trading_library.legacy_reason_classifier`` to detect pre-protocol-
launch dates that should be classified as ``EXPECTED_PRE_VENUE_LAUNCH``
rather than falling through to ``SOURCE_RETURNED_ZERO`` (which then flips to
``attempted_failed`` for cefi/defi/tradfi per the per-asset-group empty rules).

Conservative principle: prefer LATER dates when uncertain. A later date
emits fewer EXPECTED_PRE_VENUE_LAUNCH rows; the cost is "a few pre-launch
days look like real data gaps" vs "real data dates marked as pre-launch"
(correctness bug).
"""


# ---------------------------------------------------------------------------
# Combined lookup — keyed by ``(asset_group, venue)`` so a single helper
# call can resolve the launch date regardless of which asset_group's
# dict the venue lives in.
# ---------------------------------------------------------------------------

_ALL_VENUE_LAUNCH_DATES: Final[dict[tuple[str, str], str]] = {
    **{("cefi", venue): date for venue, date in CEFI_VENUE_LAUNCH_DATES.items()},
    **{("prediction", venue): date for venue, date in PREDICTION_VENUE_LAUNCH_DATES.items()},
    **{("defi", venue): date for venue, date in DEFI_VENUE_LAUNCH_DATES.items()},
}


def get_venue_launch_date(asset_group: str, venue: str) -> str | None:
    """Return the venue's public-launch date (ISO YYYY-MM-DD) or ``None``.

    Case-insensitive on ``asset_group`` (lowercase) and ``venue`` (uppercase).
    Returns ``None`` for unknown ``(asset_group, venue)`` pairs — caller can
    treat unknown as "unbounded" (date not constrained, fall through to other
    enumerator branches).
    """
    return _ALL_VENUE_LAUNCH_DATES.get((asset_group.lower(), venue.upper()))


__all__ = (
    "CEFI_VENUE_LAUNCH_DATES",
    "DEFI_VENUE_LAUNCH_DATES",
    "PREDICTION_VENUE_LAUNCH_DATES",
    "get_venue_launch_date",
)
