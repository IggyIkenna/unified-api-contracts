"""Declarative data tables behind the source-priority facade.

Data split out of :mod:`unified_api_contracts.canonical.crosscutting.source_priority`
(2026-06-11 >900-line ratchet) so the facade keeps the lookup/merge logic and
this module carries the pure registries:

* :data:`SOURCE_PRIORITY` — ordered source list per ``(asset_group, data_type)``.
* :data:`COMPUTED_SOURCES` + :data:`MOCK_SOURCE` — provenance-exempt source keys.
* :data:`SOURCE_MODE_CAPABILITY` + :data:`CEFI_LIVE_VENUES` +
  :data:`BATCH_CAPABLE_CEFI_VENUES` — ratified per-source mode capability.
* :data:`EMISSION_LATENCY_MS_BY_SOURCE` — live-emission latency per source.

Import surface is UNCHANGED for consumers: every name here is re-exported by
``source_priority`` (and the crosscutting/root facades) — import from there.
Semantics/tie-breaker rules are documented on the facade module docstring.
"""

from __future__ import annotations

from typing import Final

from unified_api_contracts.canonical.crosscutting.pipeline_mode import Mode

SOURCE_PRIORITY: Final[dict[tuple[str, str], list[str]]] = {
    # ---- Sports ---------------------------------------------------------
    # Fixture lifecycle data — api_football is primary, footystats is the
    # multi-source merge candidate (deferred). Soccer-football-info handles
    # the SFI_PROGRESSIVE_STATS slice.
    ("sports", "FIXTURES"): [
        "api_football",
        "footystats",
    ],  # footystats is the deferred multi-source merge candidate (see module docstring Phase 1B)
    ("sports", "FIXTURE_LINEUPS"): ["api_football"],
    ("sports", "FIXTURE_EVENTS"): ["api_football"],
    ("sports", "FIXTURE_STATS"): ["api_football"],
    # PLAYER_STATS = api_football per-fixture player stats, captured by IS at the
    # PER_DAY_PER_LEAGUE grain. The canonical data_type name is PLAYER_STATS; the GCS
    # *entity* folder is `fixture_player_stats` — a deliberate name mismatch documented
    # in codex/02-data/sports-gcs-path-ssot.md § "non-obvious entity= folder names".
    # This registry was seeded (106430c9, 2026-05-06) with the ENTITY name
    # FIXTURE_PLAYER_STATS by analogy with its FIXTURE_* neighbours, while PLAYER_STATS
    # already existed in SPORTS_DATA_TYPE_TO_SOURCE (league_data.py) and the launch-date
    # override. Nothing ever wrote FIXTURE_PLAYER_STATS: the live IS sports index holds
    # 219,508 PLAYER_STATS rows and ZERO FIXTURE_PLAYER_STATS rows (read 2026-07-15).
    # The phantom name made has_source_priority("sports","PLAYER_STATS") False, which
    # silently DISABLED the UTL write-time mis-stamp guard for every IS PLAYER_STATS row
    # (_writer_ingest.py gates it on that call) — same class as the ODDS defect below.
    # Reconciled 2026-07-15 onto the name reality uses. SSOT:
    # codex/02-data/sports-gcs-path-ssot.md + codex/02-data/sports-data-types-catalog.md.
    ("sports", "PLAYER_STATS"): ["api_football"],
    ("sports", "INJURIES"): ["api_football"],
    ("sports", "RESULTS"): ["api_football"],
    ("sports", "UNDERSTAT_XG"): ["understat"],
    ("sports", "SFI_PROGRESSIVE_STATS"): ["soccer_football_info"],
    ("sports", "ODDS_SNAPSHOT"): ["odds_api"],
    ("sports", "ODDS_MOVEMENT"): ["odds_api"],
    ("sports", "ARBITRAGE"): ["odds_api"],
    ("sports", "WEATHER_FORECAST"): ["open_meteo"],
    # Sports raw data types (instruments-service manifest data_type names).
    ("sports", "XG"): ["understat"],
    ("sports", "XG_SHOTS"): ["understat"],
    ("sports", "MATCHES"): ["footystats"],
    ("sports", "STANDINGS"): ["api_football"],
    ("sports", "WEATHER"): ["open_meteo"],
    ("sports", "PREDICTIONS"): ["footystats"],
    # ODDS = footystats PRE-MATCH SNAPSHOT (kickoff-72h, books aggregated) — IS
    # reference data, NOT raw bookmaker ticks (those are ODDS_SNAPSHOT/ODDS_MOVEMENT/
    # ARBITRAGE → odds_api/MTDS above; the two legitimately coexist).
    # Removed 2026-06-25 by 8fb1f54f (#6 "coherent unit"), then decision #6 was REVERSED
    # by the operator 2026-06-27 — but c75101be restored ONLY SPORTS_DATA_TYPE_TO_SOURCE
    # (league_data.py), leaving this registry and AVAILABILITY_AT_SEMANTICS unreverted.
    # That split-brain made has_source_priority("sports","ODDS") False, which silently
    # DISABLED the UTL write-time mis-stamp guard for the pair and made the IS expected-
    # universe enumerator fall through to a non-canonical source. Restored 2026-07-15 to
    # the exact pre-8fb1f54f value. SSOT: codex/02-data/sports-data-types-catalog.md:48-52.
    ("sports", "ODDS"): ["footystats"],
    ("sports", "ODDS_HORIZON_BUCKET"): ["mdps_odds_horizon_bucket"],
    ("sports", "TRANSFER_RECORDS"): ["transfermarkt"],
    # Sports reference tables.
    ("sports", "TEAMS"): ["api_football"],
    ("sports", "PLAYERS"): ["api_football"],
    ("sports", "VENUES"): ["api_football"],
    ("sports", "LEAGUES"): ["api_football"],
    ("sports", "PLAYER_VALUES"): ["transfermarkt"],
    # ---- CeFi -----------------------------------------------------------
    # Tardis is the canonical CeFi tick source (multi-venue archive).
    # Per-venue REST/WS adapters serve live-time updates; archive falls
    # back to Tardis.
    # hyperliquid/aster (cefi on-chain perps, reclassified to cefi in UAC 0.30.0)
    # stamp their own per-venue source on BOTH live (exchange WS) and batch (S3
    # archive / native REST) rows — same shard, same schema; pipeline_mode
    # {batch,live}_<source> + source carry provenance (Live=batch). tardis stays the
    # index-0 batch primary for Tardis-covered venues. Mirrors the derivative_ticker
    # 2-source registration below (closed-set round-trip + per-venue source stamp).
    # kalshi_perp + polymarket_perp: CFTC-regulated crypto perp venues (launched
    # 2026-05-29 and 2026-04-21 respectively), each self-archiving their own trade
    # tape via public-read REST (cursor-paginated). They stamp their own per-venue
    # source on batch rows (like aster/hyperliquid — native REST, not Tardis).
    # polymarket_perp is BLOCKED-UPSTREAM-OUTAGE (DNS NXDOMAIN 2026-06-21); scaffold
    # registered for when the endpoint recovers. SSOT: prediction-perps-sourcing.md.
    # "pacifica" source (PACIFICA (Solana) on-chain CeFi perp CLOB) removed
    # 2026-07-16 (operator ruling: all Solana perp DEXes dropped except
    # Jupiter, not integrated). SSOT: unified-trading-pm/codex/04-architecture/
    # solana-defi-coverage.md.
    ("cefi", "trades"): [
        "tardis",
        "aster",
        "hyperliquid",
        "kalshi_perp",
        "polymarket_perp",
        "extended",
    ],
    # lighter_api appended LAST (2026-07-18) — LIGHTER-ZKSYNC self-archives ohlcv_1m via its
    # own REST /candles. LAST so source-blind priority[0] stays tardis for every OTHER cefi
    # venue; LIGHTER-ZKSYNC ohlcv_1m is handled source-blind → None by the UTL resolver guard,
    # and source-aware (source=lighter_api) → batch_lighter_api. Registered here to satisfy the
    # PipelineMode↔SOURCE_PRIORITY closed-set round-trip for BATCH_LIGHTER_API.
    ("cefi", "ohlcv_1m"): ["tardis", "aster", "hyperliquid", "extended", "lighter_api"],
    # ("cefi", "ohlcv_15m") RETIRED 2026-06-09 (operator-directed): cefi has no
    # 15m candles — the tardis entry was a planning placeholder. tradfi ohlcv_15m
    # remains (databento/massive/yahoo/barchart produce it). Exclusion entry in
    # test_validity_matrix_completeness.py removed alongside.
    # OPERATOR RULING 2026-07-13 (finding-77 escalation, resolved via option A — see
    # plans/active/issues/fleet_data_acquisition_health_2026_06_21.md): ONLY
    # (HYPERLIQUID, liquidations) is removed below. Hyperliquid publishes no
    # liquidations feed (no S3 prefix, no Tardis channel — VENUE_DATA_TYPE_
    # CAPABILITIES["HYPERLIQUID"] in market_data_categories.py carries no
    # ``liquidations`` key). The other three pairs originally targeted by
    # finding-77 STAY registered: (ASTER, book_snapshot_5), (ASTER, liquidations),
    # and (HYPERLIQUID, book_snapshot_5) are real, wired, tested live feeds
    # (uac@3652f99f "ASTER book_snapshot_5 + liquidations live-wire capability";
    # HYPERLIQUID book_snapshot_5 S3-archived since 2023-04-15) — removing them
    # would reopen bug#8 (MissingSourceError) for real live traffic.
    ("cefi", "book_snapshot"): ["tardis", "aster", "hyperliquid", "extended"],
    ("cefi", "liquidations"): ["tardis", "aster", "extended"],  # hyperliquid removed 2026-07-13 (no real feed)
    # derivative_ticker (perp mark/index/OI/funding). tardis is the multi-venue T+1
    # archive BATCH primary for every Tardis-covered CeFi perp venue (binance/okx/
    # bybit/deribit → batch_tardis, resolved via this index-0 entry). **aster** is the
    # SECOND source: Aster (reclassified CeFi on-chain CLOB) self-archives funding +
    # premiumIndex over its native Binance-Futures-compatible REST and is routed to
    # ``batch_aster`` by the UTL ``_VENUE_OVERRIDES["ASTER"]`` venue override (which
    # runs BEFORE this lookup), so ASTER never resolves through index-0 tardis. This
    # 2-source registration (a) closes the SOURCE_PRIORITY↔PipelineMode closed-set
    # round-trip for ``batch_aster``, and (b) lets the MTDS orchestrator stamp the
    # correct per-venue ``source`` (tardis for Tardis venues, aster for the
    # venue-override Aster shard). source_required becomes True, but every
    # derivative_ticker writer already passes an explicit source. SSOT:
    # ``perp_funding_data_semantics_and_cadence_2026_06_16.md`` §genesis.
    ("cefi", "derivative_ticker"): ["tardis", "aster", "hyperliquid", "extended"],
    # ERA-B (operator 2026-06-07): options_chain / futures_chain are
    # INSTRUMENT_TYPES (per-underlying chain bundles), captured as data_type=trades
    # — so the Era-B writer resolves source via ``(cefi, "trades")`` above (same
    # primary, tardis). These data_type-keyed entries are RETAINED only for (a) the
    # legacy data_type=options_chain rows pending the per-AG v8→v9 relabel
    # (OUT OF SCOPE here) and (b) the bidirectional SOURCE_PRIORITY ↔
    # AVAILABILITY_AT_SEMANTICS closed-set round-trip; drop them once the per-AG
    # migrators relabel the legacy rows to trades.
    # Crypto options chain — tardis (T+1 archive) is the BATCH primary; the
    # LIVE/REPLAY source is the EXCHANGE (deribit), resolved per-shard by the
    # venue-override layer (same pattern as (cefi, trades) → tardis batch +
    # deribit live). The SAME shard carries source=tardis in batch and
    # source=deribit in live/replay — batch==live, one canonical options_chain
    # data_type. (instruments-service DeribitOptionsReferenceDataAdapter feeds
    # live; the Tardis historical-crypto adapter SCAFFOLD is BLOCKED-CREDENTIALS.)
    ("cefi", "options_chain"): ["tardis"],
    ("cefi", "futures_chain"): ["tardis"],
    ("cefi", "perpetual"): ["tardis"],
    ("cefi", "funding_rate"): ["tardis"],
    # volatility_index (DVOL) — Deribit's public REST history endpoint
    # (``/public/get_volatility_index_data``) SELF-ARCHIVES the DVOL index back
    # to 2021-03-24, no credentials — a genuine BATCH primary, unlike deribit's
    # other CeFi data_types (trades/derivative_ticker/options_chain/...) where
    # deribit is only the LIVE/REPLAY per-venue override and tardis is the batch
    # archive. deribit is therefore a BATCH_CAPABLE_CEFI_VENUES exception for
    # THIS data_type only (same "self-archiving vendor" pattern as
    # aster/extended). SSOT: vol_dvol_backtestable_engines_2026_07_13.md.
    ("cefi", "volatility_index"): ["deribit"],
    # perp_funding (periodic funding settlements) for the new CFTC-regulated crypto
    # perp venues. kalshi_perp + polymarket_perp each expose a dedicated
    # /markets/{ticker}/funding_rates endpoint (cursor-paginated, public-read).
    # polymarket_perp is BLOCKED-UPSTREAM-OUTAGE (DNS NXDOMAIN 2026-06-21).
    # SSOT: prediction-perps-sourcing.md.
    ("cefi", "perp_funding"): ["kalshi_perp", "polymarket_perp"],
    # greeks_snapshot + implied_vol_surface — computed in-house by greeks-service
    # from the canonical options_chain (venue mark_iv, else BS-fitted). Internal
    # computed source (greeks_service, COMPUTED_SOURCES-exempt from external
    # provenance); batch==live (same kernel both modes). The crypto chains feed
    # the cefi rows; the TradFi (Massive/Databento) chains feed the tradfi rows.
    ("cefi", "greeks_snapshot"): ["greeks_service"],
    ("cefi", "implied_vol_surface"): ["greeks_service"],
    # L2 microstructure (Phase D P2) — depth_of_book_10 / queue_position are
    # MTDS-COMPUTED from the canonical book_snapshot_5 (L5 book) — honest gap
    # until a deeper capture lands. Internal computed source (mtds_microstructure,
    # COMPUTED_SOURCES-exempt from external provenance); batch==live (same
    # derivation both modes). The upstream L5 book is sourced via
    # (cefi, book_snapshot) → tardis batch + venue live; these rows carry the
    # COMPUTED emitter as the provenance, like greeks_snapshot. (order_flow_imbalance
    # — the third L2-microstructure data_type that shared this mtds_microstructure
    # source — RETIRED 2026-07-08; zero real consumers, zero production rows ever
    # captured. depth_of_book_10/queue_position remain, so mtds_microstructure
    # stays registered as a source below.)
    ("cefi", "depth_of_book_10"): ["mtds_microstructure"],
    ("cefi", "queue_position"): ["mtds_microstructure"],
    # ---- DeFi -----------------------------------------------------------
    # DeFi has per-protocol on-chain readers; no single canonical source.
    ("defi", "swap"): ["onchain_subgraph"],
    ("defi", "fx_rate"): ["onchain_subgraph"],
    ("defi", "liquidity"): ["onchain_subgraph"],
    ("defi", "market_state"): ["onchain_subgraph"],
    ("defi", "gas_fees"): ["onchain_rpc"],
    ("defi", "lst_yields"): ["onchain_subgraph"],
    ("defi", "vault_state"): ["onchain_subgraph"],
    # Phase 1A feature_dag seed gap closeout (2026-05-07): 5 on-chain DeFi
    # data_types declared in AVAILABILITY_AT_SEMANTICS but missing from
    # SOURCE_PRIORITY. Top-entry-only seeds per the Phase 1B convention
    # documented in this module's docstring; multi-source merge (e.g. The
    # Graph for AaveV3 + morpho_blue_api for Morpho on lending_indices)
    # is deferred to ``multi_source_priority_merge_2026_*<TBD>.md``.
    # `risk_params` reads protocol configurator state at the contract level
    # (Aave LendingPoolConfigurator, Morpho IRM params) → ``onchain_rpc``;
    # the other four are event-stream / index reads → ``onchain_subgraph``.
    ("defi", "lending_indices"): ["onchain_subgraph"],
    ("defi", "risk_params"): ["onchain_rpc"],
    ("defi", "rewards"): ["onchain_subgraph"],
    ("defi", "flash_loan_events"): ["onchain_subgraph"],
    ("defi", "eigenlayer_rewards"): ["onchain_subgraph"],
    # Phase 4.MTDS / Phase 5 availability-semantic gap closeout (2026-05-12):
    # 14 DeFi data_types present in AVAILABILITY_AT_SEMANTICS (Ikenna Phase 5
    # audit 2026-05-11) but missing from SOURCE_PRIORITY. Source assignments
    # derived from MTDS handler survey in
    # ``scratch_codefreeze_phase4_mtds_fanout_2026_05_12.md`` per-source
    # mapping table. Subgraph = EVM The Graph / Messari indexer; RPC = direct
    # node call or signed transaction event; hyperliquid = Hyperliquid (vendor;
    # REST transport for the Solana-based perp + DEX legs — transport is a column,
    # never glued to the source name, operator R4 2026-06-07).
    ("defi", "bridge_events"): ["onchain_rpc"],
    ("defi", "dex_pool_state"): ["onchain_subgraph"],
    # dex pool SWAPS — canonical data_type ``dex_pool_swaps`` (the bucket-spec
    # ``canonical_dt`` in migrate_defi_full_v9_canonical.py:112 + the on-disk
    # ``data_type=dex_pool_swaps`` in ``dex-swaps-*``; the legacy ``dex_swaps``
    # logical key is retired). Read from The Graph subgraph (the uniswap_v3 /
    # curve adapters fetch pools + SWAPS + liquidity from the SAME subgraph —
    # uniswap_v3_adapter.py "primary for pools, swaps, liquidity"), so the source
    # is ``onchain_subgraph``, matching ``dex_pool_state`` above. Was previously
    # UNREGISTERED → fell through to the defi asset_group fallback
    # (``BATCH_ONCHAIN_RPC``), which mis-stamped swaps as ``onchain_rpc``. (F2
    # registry tidy slot-7 2026-06-07 mis-keyed this as ``("defi", "n")`` — a dead
    # key matching no real shard, so ``dex_pool_swaps`` kept falling to the
    # onchain_rpc fallback; corrected to the real canonical data_type by the slot-2
    # pre-apply audit 2026-06-08 so the v9 migrator derives
    # ``batch_onchain_subgraph`` for dex-swaps.)
    ("defi", "dex_pool_swaps"): ["onchain_subgraph"],
    ("defi", "governance_events"): ["onchain_subgraph"],
    ("defi", "liquidation_events"): ["onchain_rpc"],
    ("defi", "liquidations"): ["onchain_subgraph"],
    ("defi", "lst_rates"): ["onchain_subgraph"],
    ("defi", "mev_events"): ["onchain_rpc"],
    # native_staking_rates: Solana RPC (getInflationRate/getEpochInfo) is primary;
    # helius_rpc for per-validator APY breakdown (requires Helius API key).
    ("defi", "native_staking_rates"): ["solana_rpc", "helius_rpc"],
    # oracle_prices dispatches Pyth Hermes (Solana feeds) as primary and
    # Chainlink (EVM aggregator rounds) as secondary; per-row pipeline_mode
    # is resolved at callsite by the MTDS oracle_prices_handler resolver.
    # "aave" added 2026-07-21 (lst_rate_honest_coverage plan Phase 1): a THIRD,
    # distinct oracle_prices venue (write venue AAVE / IS venue AAVE-ETHEREUM,
    # AaveOracle.getAssetPrice per LST reserve) — never competes for the same
    # row as pyth_hermes/chainlink (disjoint venues), listed here purely to
    # satisfy the PipelineMode<->SOURCE_PRIORITY closed-set round-trip
    # (BATCH_AAVE requires a matching entry). See
    # codex/02-data/lst-exchange-rate-surfaces.md surface #3.
    ("defi", "oracle_prices"): ["pyth_hermes", "chainlink", "aave"],
    # perp_funding + solana_defi are Hyperliquid REST legs; Hyperliquid (the vendor,
    # via its REST transport) is the primary (and currently only) source for both
    # data_types. source=hyperliquid, transport=rest (a column, not the name).
    # NOTE (F2 registry tidy, slot-7 2026-06-07): non-Hyperliquid perp venues
    # (e.g. LIGHTER, which reads its perp funding from the Tardis archive) are
    # deliberately NOT listed here — they are resolved PER-SHARD by the venue
    # override layer (``pipeline_mode_resolver._VENUE_OVERRIDES["LIGHTER"] →
    # BATCH_TARDIS``), which runs BEFORE the SOURCE_PRIORITY lookup. Adding tardis
    # to this list would flip ``source_required(defi, perp_funding)`` to True (a
    # 2-external-source cell) and break the single-source auto-stamp for the
    # Hyperliquid-native cells. The venue-override layer is the correct home for a
    # per-venue source that differs from the data_type default.
    ("defi", "perp_funding"): ["hyperliquid"],
    ("defi", "position_data"): ["onchain_rpc"],
    ("defi", "solana_defi"): ["hyperliquid"],
    ("defi", "staking_yields"): ["onchain_subgraph"],
    ("defi", "token_transfers"): ["onchain_rpc"],
    ("defi", "vault_share_price"): ["onchain_subgraph"],
    # execution_fills — emitted by execution-service (not an external
    # market-data vendor); source tag is ``execution_service``.
    # d3_manifest_v8_finish_2026_05_20 Phase 1 — closes
    # PipelineMode.BATCH_EXECUTION_SERVICE closed-set round-trip with
    # SOURCE_PRIORITY (both CeFi + DeFi execution legs write execution_fills).
    ("cefi", "execution_fills"): ["execution_service"],
    ("defi", "execution_fills"): ["execution_service"],
    # hedge_ratio_snapshot — emitted by strategy-service (not an external
    # market-data vendor); source tag is ``strategy_service``.
    # hedge_ratio_snapshot_persistence_2026_05_13 Phase 1.
    ("defi", "hedge_ratio_snapshot"): ["strategy_service"],
    # strategy_decision_context — emitted by strategy-service on every tick
    # (pre-decision inputs for audit trail); same source as hedge_ratio_snapshot.
    # hedge_ratio_snapshot_persistence_2026_05_13 Phase 5.
    ("defi", "strategy_decision_context"): ["strategy_service"],
    # feature_observation_snapshot — emitted by features-onchain-service on every
    # tick (per-tick APY inputs + MTDS provenance for audit chain).
    # features_tick_observation_audit_2026_05_18 Phase 1.
    ("defi", "feature_observation_snapshot"): ["features_onchain_service"],
    # cross_instrument_signal — emitted by features-service cross_instrument
    # family on every batch run (multi-asset / multi-venue derived features).
    # d5_features_missing_data_downgrade_2026_05_20 Phase 2 — closes
    # PipelineMode.BATCH_CROSS_INSTRUMENT closed-set round-trip with
    # SOURCE_PRIORITY (the family crosses asset_groups; registered under
    # "defi" as the primary live archetype consumer per CLAUDE.md
    # "DeFi + CeFi hybrid" rule — carry_staked_basis + perp_funding_vs_spot
    # are the cross_instrument family's live targets).
    ("defi", "cross_instrument_signal"): ["cross_instrument"],
    # ---- TradFi ---------------------------------------------------------
    # Databento for CME/NQ/options/futures; Yahoo for VIX 15m rolling
    # window; Barchart for VIX 15m historical preload (handled at the
    # MTDS routing layer, not here — both are listed for the same shard
    # but the orchestrator picks by date).
    # EIA (US Energy Information Administration) — commodity storage + series data.
    # BATCH_EIA manifest mode: features-commodity-service D5 Phase 1.
    ("tradfi", "energy_data"): ["eia"],
    # DATABENTO-ONLY tick/chain sourcing (massive REMOVED 2026-07-19, operator
    # ruling): Databento is the batch source-of-truth — GLBX.MDP3 covers every CME
    # futures root, DBEQ.BASIC covers the live MVP equity/ETF universe (56/56
    # single-equities + 10/10 representative commodity/crypto ETFs, live-probed
    # 2026-06-24), XCBF.PITCH covers CFE/VX (which massive never carried). Yahoo
    # remains the source for the daily/rolling candle cells (ohlcv_1m/15m/24h) + the
    # KRX-only Korean underliers. Massive was the pre-2026-07-19 fallback [1]; its
    # routing is dropped here — a no-op for live traffic (databento was already
    # index[0], so derive_pipeline_mode_for_row already stamped batch_databento).
    # The historical ``pipeline_mode=batch_massive/`` GCS objects stay recognised by
    # possible_manifest + PipelineMode.BATCH_MASSIVE until the separate gated purge.
    # SSOT: codex/02-data/tradfi-databento-sourcing-ssot.md + issue
    # tradfi_canonical_path_migration_design_2026_07_19.md § Massive removal.
    ("tradfi", "trades"): ["databento"],
    ("tradfi", "tbbo"): ["databento"],
    # ohlcv_1s is DATABENTO-ONLY: fetched from Databento GLBX.MDP3 (L0/free 16y,
    # subscription lockdown 2026-06-18); derive_pipeline_mode_for_row stamps
    # pipeline_mode=batch_databento. SSOT: codex/02-data/tradfi-databento-sourcing-ssot.md.
    ("tradfi", "ohlcv_1s"): ["databento"],
    # ohlcv_1m: databento is priority[0] (primary); the source actually USED per fetch
    # is the per-launch ``--source`` gated by the venue-aware ``_VENUE_SOURCE_EXCLUSIONS``.
    # yahoo serves the KRX-only Korean underliers (HYUNDAI 005380 / SAMSUNG 005930 /
    # SKHYNIX 000660, venue=KRX, the ``.KS`` tickers — KRX excludes databento). SSOT:
    # codex/02-data/tradfi-databento-sourcing-ssot.md.
    ("tradfi", "ohlcv_1m"): ["databento", "yahoo"],
    # ohlcv_15m: barchart RETIRED 2026-06-24 (VIX 15m now aggregates from VX futures
    # via databento XCBF.PITCH). yahoo still serves KRX + the rolling VIX window.
    ("tradfi", "ohlcv_15m"): ["databento", "yahoo"],
    # ohlcv_24h — Yahoo-only daily bars (FX KRW/USD, KRX single stocks, the DXY +
    # treasury-yield indices). Added 2026-06-24 so the daily provenance resolves
    # via the registry (default_source auto-stamps source=yahoo) instead of an
    # ad-hoc fetcher stamp — the venue/source parity gate requires every captured
    # (asset_group, data_type) cell to have a registered source list.
    ("tradfi", "ohlcv_24h"): ["yahoo"],
    # ERA-B: options_chain / futures_chain are instrument_types captured as
    # data_type=trades → Era-B source resolves via ``(tradfi, "trades")`` above
    # (databento). Legacy-data_type keys retained for the pre-migration rows + the
    # closed-set round-trip (see the cefi note above).
    ("tradfi", "options_chain"): ["databento"],
    ("tradfi", "futures_chain"): ["databento"],
    # TradFi greeks_snapshot + implied_vol_surface — computed by greeks-service
    # from the Databento options chain (same kernel as the crypto rows).
    ("tradfi", "greeks_snapshot"): ["greeks_service"],
    ("tradfi", "implied_vol_surface"): ["greeks_service"],
    # commodity_signal — emitted by features-service commodity family from
    # EIA (crude oil + natural gas weekly storage) + CFTC + Baker Hughes +
    # Open-Meteo + Yahoo factor inputs. Top entry is EIA per the storage
    # factor's dominant role in the commodity feature set (per
    # features_service/commodity/README.md factor table).
    # d5_features_missing_data_downgrade_2026_05_20 Phase 1 — closes
    # PipelineMode.BATCH_EIA closed-set round-trip with SOURCE_PRIORITY.
    ("tradfi", "commodity_signal"): ["eia"],
    # ---- Prediction -----------------------------------------------------
    # Prediction is venue-disambiguated: Polymarket data comes from polymarket_clob, Kalshi
    # data from kalshi (the vendor IS the venue). Both serve the same data_types — the
    # READ-TIME priority order is polymarket-first, but the WRITE-TIME stamp is venue-resolved
    # (live_source_for_venue / _VENUE_OVERRIDES), never priority[0]. Kalshi registration:
    # prediction_venue_perps_and_live_clob_depth_2026_06_20.md (deep-history bulk seed + live).
    ("prediction", "trades"): ["polymarket_clob", "kalshi"],
    ("prediction", "book_snapshot_5"): ["polymarket_clob", "kalshi"],
    ("prediction", "prediction_canonical_question_group"): ["polymarket_clob", "kalshi"],
    # MARKET_LIFECYCLE source — instruments-service reads from Polymarket
    # gamma API ``/markets/{conditionId}`` for created/resolution/settlement
    # timestamps. Phase 1B writes top entry only; Kalshi metadata source is
    # a deferred follow-up plan slot. Predictions plan
    # ``predictions_canonical_question_group_polymarket_migration_2026_05_06.md``
    # Phase 1A.
    ("prediction", "MARKET_LIFECYCLE"): ["polymarket_gamma_api"],
    # cross_instrument — computed by features-service cross_instrument handler
    # (honest-absence manifest calls). BATCH_CROSS_INSTRUMENT mode: D5 Phase 2.
    ("cefi", "cross_instrument"): ["cross_instrument"],
    # ---- Reference (asset-group-agnostic) -------------------------------
    ("reference", "instruments"): ["instruments_service"],
    ("reference", "venue_trading_calendar"): ["instruments_service"],
    # ---- Features-service computed outputs ------------------------------
    # commodity_features — tradfi energy signals (storage, weather, COT, rig_count,
    # price_momentum) produced by features-service commodity sub-package from EIA + CFTC + BH feeds.
    # BATCH_EIA PipelineMode prerequisite (D5 Phase 1 / uac@fb3751e8).
    ("tradfi", "commodity_features"): ["eia"],
    # cross_instrument_features — cross-asset/cross-venue signals (paired_price_dispersion,
    # cross_venue_spreads, regime_detection, cross_asset_correlation, cross_instrument_dynamics)
    # produced by features-service cross_instrument sub-package from delta-one inputs.
    # BATCH_CROSS_INSTRUMENT PipelineMode prerequisite (D5 Phase 2 / uac@39733749).
    ("cefi", "cross_instrument_features"): ["cross_instrument"],
}


COMPUTED_SOURCES: Final[frozenset[str]] = frozenset(
    {
        # Internal service emitters — NOT external market-data vendors. Their
        # rows' lineage is the upstream cell they were computed from, not a
        # vendor, so the data-source provenance gate is N/A for them
        # (data_source_provenance_all_asset_groups_2026_06_01.md § Scope
        # boundary — "EXEMPT: computed, no external vendor"). These source
        # strings exist in SOURCE_PRIORITY only to satisfy the PipelineMode
        # closed-set round-trip; they are exempt from source stamping.
        "execution_service",  # execution-service fills
        "strategy_service",  # strategy-service hedge-ratio / decision-context
        "features_onchain_service",  # features-onchain per-tick snapshots
        "cross_instrument",  # features-service cross_instrument family outputs
        "greeks_service",  # greeks-service greeks_snapshot / implied_vol_surface
        "mtds_microstructure",  # MTDS L2 microstructure (depth_of_book_10/queue_position) from book_snapshot_5
    }
)
"""Source strings denoting internal computed/service emitters (provenance-exempt).

The data-source provenance gate
(``data_source_provenance_all_asset_groups_2026_06_01.md``) stamps ``source``
on every *external-vendor* market-data cell. Cells whose only source(s) are
internal service emitters carry no external provenance — their lineage is the
upstream cell, not a vendor — so they are exempt from the gate. Membership here
is the principled exemption (vs a hardcoded data_type list)."""


# ---------------------------------------------------------------------------
# M2 — source-mode capability registry + M9 mock source
# (pipeline_mode_source_batch_live_replay_standardisation_2026_06_05.md)
# ---------------------------------------------------------------------------

MOCK_SOURCE: Final[str] = "mock"
"""M9 — simulated/fake data source. Routes to the DEV cloud-storage path via the
env-tier bucket split (``-dev-``/`-stg-` vs `-prd-`) so it NEVER touches prod;
makes test fixtures first-class. Mock implies dev-tier only."""

# RATIFIED source-mode capability (operator 2026-06-07) — encodes
# ``plans/audit/results/source_mode_capability_matrix_2026_06_07.md`` row-for-row,
# including its "CORRECTED MODEL" section. These flags are LOAD-BEARING (M2/M3/M4/M6
# read them), not a draft seed.
#
# Every EXTERNAL source is batch-capable (the ``batch_<source>`` closed-set floor).
# LIVE = a real-time stream (or a short-interval poll for push-less sources like
# onchain_subgraph). REPLAY (format-agnostic) = the ability to re-fetch
# "today-since-start" ON DEMAND to fill an intraday / startup / live-downtime gap;
# a source that cannot re-fetch intraday simply means its live-downtime gap waits
# for batch (honest absence) — NOT a decision.
#
# Notes on the ratified rows:
# * tardis = {batch} ONLY — the academic licence blocks replay AND CeFi live/replay
#   come from the EXCHANGES (the per-venue ``live_<venue>``/``replay_<venue>`` sources),
#   not Tardis. Tardis is the CeFi BATCH (T+1 archive) source. (Matrix R1 + CORRECTED
#   MODEL.) The SAME shard therefore carries source=tardis in batch and source=<venue>
#   in live/replay — the row-level ``source`` column already models this.
# * massive (= Polygon.io) removed 2026-07-19 (operator ruling: Databento is the
#   tradfi batch source-of-truth, Yahoo for daily candles). Only the routing is
#   dropped — the historical batch_massive/ objects keep PipelineMode.BATCH_MASSIVE
#   recognition until the separate gated GCS purge.
# * Internal service sources (instruments_service/execution_service/strategy_service/
#   features_onchain_service/cross_instrument/mdps_odds_horizon_bucket) = service mode:
#   batch=live symmetry, re-run = replay.
SOURCE_MODE_CAPABILITY: Final[dict[str, frozenset[Mode]]] = {
    # ---- CeFi ----
    "tardis": frozenset({Mode.BATCH}),  # batch (archive) ONLY; live/replay = exchanges
    # ---- TradFi ----
    "databento": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    # "massive" (= Polygon.io) removed 2026-07-19 — routing dropped; the historical
    # batch_massive/ objects keep PipelineMode.BATCH_MASSIVE recognition until the purge.
    "yahoo": frozenset({Mode.BATCH}),
    # "barchart" RETIRED 2026-06-24 (VIX 15m → VX futures via databento XCBF.PITCH).
    "eia": frozenset({Mode.BATCH, Mode.REPLAY}),  # weekly series re-fetchable by date
    # ---- DeFi ----
    # hyperliquid (unified vendor) lives in the CeFi-venue block below — it is the
    # ONE venue that is ALSO batch-capable (DeFi perp_funding/solana_defi via REST
    # candleSnapshot), so it carries {BATCH, LIVE, REPLAY}. The former
    # ``hyperliquid_rest`` key (transport glued into the source) is retired (R4).
    "onchain_rpc": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "solana_rpc": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "helius_rpc": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "onchain_subgraph": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),  # live = poll
    "chainlink": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "pyth_hermes": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    # AAVE on-chain oracle (AaveOracle.getAssetPrice) — added 2026-07-21
    # (lst_rate_honest_coverage plan Phase 1). BATCH-only for now: the
    # collection branch (Phase 2) is a batch RPC backfill; only BATCH_AAVE
    # exists in PipelineMode (no LIVE_AAVE/REPLAY_AAVE member) — widen this
    # + add the matching enum members together if/when a live leg lands.
    "aave": frozenset({Mode.BATCH}),
    # ---- Prediction ----
    "polymarket_clob": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "polymarket_gamma_api": frozenset({Mode.BATCH}),  # market metadata; not a tick series
    "kalshi": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),  # REST historical + WS live + re-fetch replay
    # ---- Sports ----
    # odds_api (The Odds API) is the FIRST live sports source: a polling live-odds
    # stream (the ``odds_api_ws`` WSFeedConnector) makes the Live==Batch sports
    # archetype real → {BATCH, LIVE, REPLAY} (it also historical-re-fetches, so
    # replay survives). The other sports vendors stay batch+replay until a live
    # source lands for each (historical odds + Secret-Manager keys already held).
    "api_football": frozenset({Mode.BATCH, Mode.REPLAY}),
    "footystats": frozenset({Mode.BATCH, Mode.REPLAY}),
    "odds_api": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "understat": frozenset({Mode.BATCH, Mode.REPLAY}),
    "transfermarkt": frozenset({Mode.BATCH, Mode.REPLAY}),
    "soccer_football_info": frozenset({Mode.BATCH, Mode.REPLAY}),
    "open_meteo": frozenset({Mode.BATCH, Mode.REPLAY}),
    # ---- Internal service sources (service mode = batch=live symmetry, re-run=replay)
    "instruments_service": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "mdps_odds_horizon_bucket": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "execution_service": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "strategy_service": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "features_onchain_service": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "cross_instrument": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "greeks_service": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "mtds_microstructure": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    # ---- CeFi per-venue live/replay sources ----
    # CeFi `live`/`replay` `source` = the EXCHANGE (CeFi `batch` source = tardis).
    # The SAME shard carries source=tardis in batch and source=<venue> in live/replay.
    # These venue sources are NOT batch-capable (Tardis is the CeFi archive) — they
    # have NO batch_<venue> PipelineMode. Replay-fact table (matrix 2026-06-07):
    # binance/okx/deribit/kraken/hyperliquid re-fetch a same-day window via REST
    # (replay ✓); Bybit (public REST recent-only) + Aster (newer venue, unverified)
    # are LIVE-only — a live-downtime gap waits for batch (T+1), replay ABSENT.
    # hyperliquid is the SOLE batch-capable venue: it is ALSO the DeFi
    # perp_funding/solana_defi batch source (REST candleSnapshot), so it carries
    # {BATCH, LIVE, REPLAY} (operator R4 2026-06-07 — the unified ``hyperliquid``
    # vendor). The other venues stay live/replay-only (CeFi batch = tardis).
    "binance": frozenset({Mode.LIVE, Mode.REPLAY}),
    "okx": frozenset({Mode.LIVE, Mode.REPLAY}),
    # deribit carries BATCH here (unlike binance/okx/kraken) because it is ALSO
    # the self-archiving batch source for (cefi, volatility_index) — Deribit's
    # public REST DVOL-history endpoint, no creds, back to 2021-03-24. For
    # every OTHER CeFi data_type deribit still serves only live/replay (tardis
    # is those data_types' batch archive) — the extra Mode.BATCH here is a
    # per-source coarse capability (mirrors the aster/extended unified
    # -vendor exceptions), refined per-data_type by ``modes_for()`` at the call
    # site. SSOT: vol_dvol_backtestable_engines_2026_07_13.md.
    "deribit": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "kraken": frozenset({Mode.LIVE, Mode.REPLAY}),
    "hyperliquid": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    "bybit": frozenset({Mode.LIVE}),
    # aster, like hyperliquid, is a UNIFIED vendor: its native ``fapi.asterdex.com``
    # funding/premiumIndex REST is a HISTORICAL time-range endpoint (startTime/endTime,
    # verified 2026-06-16 — ``perp_funding_data_semantics_and_cadence_2026_06_16.md``
    # §genesis), so Aster SELF-ARCHIVES its derivative_ticker (perp funding) → batch +
    # replay capable. It is NOT Tardis-archived; the Aster derivative_ticker shard
    # resolves to ``batch_aster`` via the UTL ``_VENUE_OVERRIDES["ASTER"]`` override.
    "aster": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    # Extended (EXTENDED-STARKNET on-chain CeFi perp CLOB) uses its own public REST API
    # (api.starknet.extended.exchange) — NOT Tardis-archived. Self-archives its trade +
    # funding tape → batch + replay capable. WS live stream = LIVE capable. Same pattern
    # as aster. SSOT: data_completion_to_100_all_ag_2026_06_21.md task-085.
    "extended": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    # "pacifica" source (PACIFICA (Solana) on-chain CeFi perp CLOB) removed
    # 2026-07-16 (operator ruling: all Solana perp DEXes dropped except
    # Jupiter, not integrated). SSOT: unified-trading-pm/codex/04-architecture/
    # solana-defi-coverage.md.
    # Kalshi-perp (CFTC crypto perps, launched 2026-05-29): public-read REST
    # (GET /markets/{ticker}/trades + /funding_rates, cursor-paginated).
    # Self-archives its own trade + funding tape → batch + replay capable.
    # WS live stream confirmed. SSOT: prediction-perps-sourcing.md.
    "kalshi_perp": frozenset({Mode.BATCH, Mode.LIVE, Mode.REPLAY}),
    # Polymarket-perp (CFTC crypto perps, launched 2026-04-21):
    # BLOCKED-UPSTREAM-OUTAGE (DNS NXDOMAIN for perps-api.polymarket.com, 2026-06-21).
    # Scaffold registered for {BATCH, LIVE} recovery (no replay confirmed yet).
    # SSOT: prediction_venue_perps_and_live_clob_depth_2026_06_20.md.
    "polymarket_perp": frozenset({Mode.BATCH, Mode.LIVE}),
    # lighter_api (LIGHTER-ZKSYNC native REST /candles, mainnet.zkln.elliot.ai) self-archives
    # ohlcv_1m only → BATCH-only. Its trades/book/derivative_ticker use the Tardis archive
    # (from 2026-04-17), and its live capture is Tardis too — so no LIVE/REPLAY member here
    # (that would demand LIVE_/REPLAY_LIGHTER_API PipelineMode values it does not need). SSOT:
    # non_tardis_dexperp_venue_data_status_smoketest_2026_07_07.md.
    "lighter_api": frozenset({Mode.BATCH}),
}

CEFI_LIVE_VENUES: Final[frozenset[str]] = frozenset(
    {
        "binance",
        "okx",
        "deribit",
        "kraken",
        "hyperliquid",
        "bybit",
        "aster",
        "kalshi_perp",
        "polymarket_perp",
        "extended",
    }
)

BATCH_CAPABLE_CEFI_VENUES: Final[frozenset[str]] = frozenset(
    {"hyperliquid", "aster", "kalshi_perp", "polymarket_perp", "extended", "deribit"}
)
"""CeFi live venues that are ALSO a batch source (operator R4 2026-06-07 + Aster
2026-06-16).

``hyperliquid`` is the unified vendor: a CeFi/DeFi live+replay venue AND the DeFi
``perp_funding``/``solana_defi`` BATCH source (REST candleSnapshot). ``aster`` is the
second such venue: its native Binance-Futures-compatible REST serves perp funding +
premiumIndex over a historical time-range, so it SELF-ARCHIVES its derivative_ticker
(``perp_funding_data_semantics_and_cadence_2026_06_16.md`` §genesis). Both carry a
``batch_<venue>`` PipelineMode + ``Mode.BATCH`` capability — every OTHER CeFi venue is
live/replay-only (CeFi batch = tardis). Exempts these two from the "CeFi venues are not
batch-capable" invariant without weakening it for the rest."""
"""CeFi exchange venues that serve the `live`/`replay` capture modes (M2/M3).

CeFi `batch` data comes from ``tardis`` (the T+1 multi-venue archive); CeFi
`live`/`replay` data comes from the exchange itself, so the ``source`` for a CeFi
shard is mode-dependent: ``tardis`` in batch, the venue here in live/replay. These
venues are NOT in :data:`SOURCE_PRIORITY` (the batch-priority registry) and are NOT
batch-capable — they carry only ``live_<venue>`` / ``replay_<venue>`` PipelineMode
members. The mode-contextual reader that picks the venue source per (shard, mode)
is the M3/M4 next tranche."""


EMISSION_LATENCY_MS_BY_SOURCE: Final[dict[str, int]] = {
    # Tick-level live sources — sub-second tick-to-pipeline arrival.
    "tardis": 50,  # multi-venue WS aggregator
    "databento": 10,  # CME direct feed, microsecond-grade infra
    "polymarket_clob": 200,  # HTTPS CLOB polling
    "kalshi": 200,  # HTTPS/WS CLOB polling (same class as polymarket_clob)
    "kalshi_perp": 200,  # HTTPS/WS CLOB polling (same latency class as kalshi)
    "polymarket_perp": 200,  # HTTPS/WS CLOB polling (BLOCKED-UPSTREAM-OUTAGE 2026-06-21)
    "onchain_rpc": 200,  # direct RPC, block-time bounded
    # Subgraph / indexer — block-confirmation latency dominates.
    "onchain_subgraph": 60_000,  # 1 min: block confirmation + Graph indexing
    # Sports REST APIs — emission cadence ≈ 1-5s.
    "api_football": 1_000,
    "odds_api": 5_000,
    # Equity / index intraday — free-tier delayed feeds (VIX 15m fallback route).
    # "massive" latency entry removed 2026-07-19 (Massive routing dropped).
    "yahoo": 900_000,  # 15 min: Yahoo Finance free-tier intraday delay for CBOE-sourced indices like ^VIX
    # Post-match / batch-only — cadence is hours-to-day.
    "understat": 7_200_000,  # 2h post-match xG
    "soccer_football_info": 3_600_000,  # 1h SFI freeze cadence
    "open_meteo": 3_600_000,  # 1h forecast issue
    "transfermarkt": 86_400_000,  # 24h market values
    # Metadata / lifecycle reads — minute-cadence.
    "polymarket_gamma_api": 60_000,
    "instruments_service": 60_000,
    # strategy-service hedge-ratio snapshots — emitted inline at rebalance time;
    # latency = 0ms relative to the event that triggered it (the rebalance
    # decision is the event; available_at = captured_at = write time).
    "strategy_service": 0,
    # execution-service result writes — emitted inline at write time;
    # latency = 0ms (available_at = captured_at = write time).
    "execution_service": 0,
    # features-onchain-service — feature snapshots emitted inline at calculation
    # time; latency = 0ms relative to the observation trigger.
    "features_onchain_service": 0,
    # cross_instrument feature family — features emitted inline at batch-tick
    # calculation time; latency = 0ms relative to the upstream multi-asset
    # delta_one/MTDS read-event that triggered it.
    "cross_instrument": 0,
    # greeks-service greeks_snapshot / implied_vol_surface — computed inline at
    # the options_chain read-event; latency = 0ms (available_at = the chain's).
    "greeks_service": 0,
    # MTDS L2 microstructure — derived inline at the book_snapshot_5 capture
    # tick; latency = 0ms (available_at = the source book's tick timestamp).
    "mtds_microstructure": 0,
    # EIA weekly storage publication — Wednesdays 10:30 AM ET covering the
    # prior Friday → ~5 day publication lag. Conservative 86_400_000 (24h)
    # matches barchart-tier daily-archive sources; tightenable later via
    # source_emission_latency_calibration_2026_*<TBD>.md.
    "eia": 86_400_000,
    # DeFi REST APIs — Hyperliquid + oracle aggregators.
    "hyperliquid": 1_000,  # 1s: HL REST API polling cadence (source=hyperliquid, transport=rest)
    "aster": 1_000,  # 1s: Aster native REST polling cadence (source=aster, transport=rest)
    "extended": 1_000,  # 1s: EXTENDED-STARKNET native REST polling cadence (source=extended, transport=rest)
    "lighter_api": 1_000,  # 1s: LIGHTER-ZKSYNC native REST /candles polling cadence (transport=rest)
    # "pacifica" latency entry removed 2026-07-16 (operator ruling: all Solana
    # perp DEXes dropped except Jupiter, not integrated).
    # DVOL history endpoint serves hourly/daily OHLC resolutions (no sub-minute
    # tick stream) — conservative hourly cadence, same class as the other
    # periodic-series REST sources below (footystats/mdps_odds_horizon_bucket).
    "deribit": 3_600_000,  # 1h: Deribit public DVOL-history REST cadence (source=deribit, transport=rest)
    "pyth_hermes": 1_000,  # 1s: Pyth Hermes batch endpoint
    "chainlink": 200,  # 200ms: on-chain EVM oracle aggregator round (RPC-style)
    # AAVE on-chain oracle (AaveOracle.getAssetPrice, RPC eth_call) — added
    # 2026-07-21 (lst_rate_honest_coverage plan Phase 1). Same RPC-style class
    # as chainlink (both are on-chain reads via Alchemy RPC).
    "aave": 200,  # 200ms: on-chain getAssetPrice eth_call (RPC-style, mirrors chainlink)
    # Solana native-staking sources — epoch-granularity (~2.5 day cadence).
    "solana_rpc": 60_000,  # 1 min: Solana RPC getInflationRate/getEpochInfo polling
    "helius_rpc": 60_000,  # 1 min: Helius APY aggregation endpoint polling
    # Sports odds-horizon bucket — GCS batch writes by mdps-sports VM.
    "mdps_odds_horizon_bucket": 3_600_000,  # 1h: conservative batch-write cadence (VM-driven)
    # Sports batch-data provider (deferred multi-source merge candidate).
    "footystats": 3_600_000,  # 1h: Footystats batch publication cadence
    # "barchart" emission-latency entry retired 2026-06-24 (Barchart removed).
}
"""Per-source emission latency (ms) — live-pipeline tick-to-pipeline arrival.

Used by the live=batch ``available_at`` formula:
``available_at = tick_event_time + emission_latency_ms_for_source(primary_source)``.

The values represent the wall-clock delta between when an event happens at the
source and when our live pipeline would actually have the row in-process. Per
the workspace ``Live = batch — same data, same fields, same timing semantics``
rule, batch writes MUST stamp ``available_at`` with this delta added so historical
features see the same arrival horizon they would in live mode.

**Phase 1B seed values are CONSERVATIVE estimates** — empirical calibration via
per-source tick-arrival sampling is deferred to follow-up plan
``source_emission_latency_calibration_2026_*<TBD>.md`` (named-successor per the
workspace ``Temporary state must have a named successor plan`` rule). Sources
whose primary is in batch-archive shape (e.g. ``tardis`` for CeFi ticks) carry
the LIVE-equivalent latency, NOT the archive-fetch latency — the archive read
happens at backfill time, but the stamped ``available_at`` reflects when a live
pipeline would have the row.

**Closed-set round-trip rule (mirrors :data:`PipelineMode`):** every source
string appearing in :data:`SOURCE_PRIORITY` MUST have an entry here. The
:func:`assert_emission_latency_round_trip` helper enforces this and is wired
into the UAC unit-test suite.

Plans:

* ``cefi_master`` Q1 — F2-v2 prerequisite for CeFi adapter
  ``available_at`` stamping.
* ``predictions_master`` Q2 — Polymarket / Kalshi bundled-row
  ``available_at`` stamping.
"""
