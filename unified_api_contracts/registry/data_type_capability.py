"""DataTypeCapability registry — per (asset_group, data_type, venue) live/batch.

The catalogue generator joins this registry with the manifest to compute
``live_ready`` / ``batch_ready`` per tuple and to surface retention /
TTM / liquidity cutoffs in the catalogue artefact.

This is a seed registry — populated against high-volume capture targets as
of 2026-04-29. Every entry carries a ``# source:`` reference (file or
ADR) so future maintainers can verify the row. Missing tuples in the
catalogue generator default to ``live_capable=False`` /
``batch_capable=True`` — the venue clearly writes data (it appears in the
manifest) but we don't have a streaming declaration for it.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Final

from unified_api_contracts.canonical.gcs_paths import AssetGroup


@dataclass(frozen=True)
class DataTypeCapability:
    """Per-tuple capability declaration.

    Identifying axes (``asset_group`` / ``data_type`` / ``venue`` /
    ``instrument_type``) match the manifest shard key columns. Coverage
    cutoffs (``ttm_cutoff_days`` / ``liquidity_cutoff_usd`` /
    ``retention_days``) carry through to the catalogue MD output so
    downstream readers can reason about expected denominator clipping.
    """

    asset_group: AssetGroup
    data_type: str
    venue: str
    instrument_type: str | None = None
    live_capable: bool = False  # WS / streaming feed exists
    batch_capable: bool = True  # REST / parquet snapshot exists
    streaming_protocol: str | None = None  # "ws" | "fix" | "sse" | None
    requires_credentials: bool = False
    ttm_cutoff_days: int | None = None  # options: ignore expiries beyond this
    liquidity_cutoff_usd: float | None = None  # ignore < this 24h volume
    retention_days: int | None = None  # rolling-window cutoff; None = unbounded
    notes: str | None = None
    sources: tuple[str, ...] = field(default_factory=tuple)


# ---------------------------------------------------------------------------
# Seed registry
# ---------------------------------------------------------------------------
# Ordering: by asset_group → data_type → venue. Each entry is a frozen
# dataclass — never mutate at import time.

DATA_TYPE_CAPABILITY_REGISTRY: Final[tuple[DataTypeCapability, ...]] = (
    # ── CeFi ─────────────────────────────────────────────────────────────
    # Wire-format SSOT verified 2026-04-30 against the per-asset-group
    # availability_index.parquet. CeFi venue tokens are exchange-product-specific
    # (BINANCE-SPOT vs BINANCE-FUTURES; OKX-FUTURES/SPOT/SWAP; BYBIT/DERIBIT/
    # HYPERLIQUID/UPBIT keep a single token). Top-volume data_types: trades,
    # book_snapshot_5 (NOT book_snapshot), derivative_ticker, futures_chain,
    # liquidations.
    #   - instrument_type is empty for spot venues + most derivative_ticker
    #     rows; perpetual for liquidations + funding-bearing rows on
    #     BINANCE-FUTURES / BYBIT / OKX-SWAP.
    # No `funding_rate` / `open_interest` data_types in the wire format —
    # those signals are folded into `derivative_ticker`.
    #
    # Trades — derivative venues
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="BINANCE-FUTURES",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/binance/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="BINANCE-SPOT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/binance/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="OKX-FUTURES",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/okx/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="OKX-SPOT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/okx/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="OKX-SWAP",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/okx/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="COINBASE-SPOT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="UPBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="BYBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/bybit/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="DERIBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/deribit.py",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="HYPERLIQUID",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/hyperliquid/",),
    ),
    # Book snapshots (depth-5)
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="BINANCE-FUTURES",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="BINANCE-SPOT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="OKX-FUTURES",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="OKX-SPOT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="OKX-SWAP",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="COINBASE-SPOT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="UPBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="BYBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="DERIBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        liquidity_cutoff_usd=5_000.0,
    ),
    # ── L2 microstructure data_types (Phase D P2) ────────────────────────
    # MTDS-COMPUTED from the canonical ``book_snapshot_5`` (L5 book), the SAME
    # feed in batch (Tardis archive) and live (venue WebSocket). batch==live: one
    # ``CanonicalBookMicrostructure`` shape both modes emit. SOURCE_PRIORITY for
    # these data_types resolves via ``(cefi, book_snapshot)`` (the upstream L5
    # book): tardis BATCH + the venue live/replay override — identical to how
    # ``book_snapshot_5`` itself resolves source. NOT added to SOURCE_PRIORITY as
    # raw vendor rows (they are computed-service outputs, like greeks_snapshot).
    #
    # ``order_flow_imbalance`` RETIRED (2026-07-08) — zero real consumers, zero
    # production rows ever captured; duplicated market-data-processing-service's
    # imbalance_ratio feature family. MTDS deleted book_microstructure_handler.py's
    # order_flow_imbalance computation (market-tick-data-service@a4fb3d13); this
    # UAC capability declaration retired to match.
    # ``depth_of_book_10`` (L10 ladder) — raw-captured directly by a WS connector
    # (mirrors book_snapshot_5's connector pattern, NOT computed from it). Live
    # WS feeds now genuinely exist for 5 venues
    # (market-tick-data-service@15f5657b): COINBASE-SPOT, BYBIT, DERIBIT,
    # BINANCE-FUTURES, OKX-SWAP. The remaining 4 (BINANCE-SPOT, OKX-FUTURES,
    # OKX-SPOT, UPBIT) have NO live book_snapshot_5 at all (trades-only /
    # batch-only) — see
    # plans/active/issues/l2_book_depth10_missing_l5_prerequisite_venues_2026_07_13.md
    # — stay honest-absent. No batch/replay path built (live-only todo).
    *(
        DataTypeCapability(
            asset_group=AssetGroup.CEFI,
            data_type="depth_of_book_10",
            venue=_venue,
            instrument_type="",
            live_capable=True,
            batch_capable=False,
            streaming_protocol="ws",
            sources=("market_tick_data_service/live/connectors/",),
            notes="Live L10 WS feed (extends the existing book_snapshot_5 connector per venue).",
        )
        for _venue in ("COINBASE-SPOT", "BYBIT", "DERIBIT", "BINANCE-FUTURES", "OKX-SWAP")
    ),
    *(
        DataTypeCapability(
            asset_group=AssetGroup.CEFI,
            data_type="depth_of_book_10",
            venue=_venue,
            instrument_type="",
            live_capable=False,
            batch_capable=False,
            streaming_protocol="ws",
            sources=("market_tick_data_service/live/connectors/",),
            notes="No live book_snapshot_5 for this venue at all (trades-only/batch-only) — honest gap.",
        )
        for _venue in ("BINANCE-SPOT", "OKX-FUTURES", "OKX-SPOT", "UPBIT")
    ),
    # ``queue_position`` (per-level resting queue) — COMPUTED, not raw-captured
    # (unlike depth_of_book_10 above). `compute_book_microstructure`
    # (market_tick_data_service/derived/book_microstructure_compute.py) is now
    # dispatched by `BookMicrostructureHandler`
    # (market_tick_data_service/cli/handlers/book_microstructure_handler.py,
    # `--operation collect-book-microstructure --mode batch`), which reads
    # already-captured depth_of_book_10 rows and writes queue_position via
    # record_captured(source="mtds_microstructure") — closing the gap the
    # deleted pre-retirement handler (a4fb3d13) left open. live_capable=True
    # (not batch_capable) mirrors depth_of_book_10's own flip: the derivation
    # is fundamentally bound to the live-only depth_of_book_10 upstream — no
    # independent historical batch/replay source exists — so history before
    # each venue's depth_of_book_10 connector went live stays an honest gap.
    *(
        DataTypeCapability(
            asset_group=AssetGroup.CEFI,
            data_type="queue_position",
            venue=_venue,
            instrument_type="",
            live_capable=True,
            batch_capable=False,
            streaming_protocol="ws",
            sources=("market_tick_data_service/cli/handlers/book_microstructure_handler.py",),
            notes=(
                "BookMicrostructureHandler derives this from already-captured "
                "depth_of_book_10 rows via compute_book_microstructure(); honest "
                "gap for any day before this venue's depth_of_book_10 connector "
                "went live (no independent batch/replay source)."
            ),
        )
        for _venue in ("COINBASE-SPOT", "BYBIT", "DERIBIT", "BINANCE-FUTURES", "OKX-SWAP")
    ),
    *(
        DataTypeCapability(
            asset_group=AssetGroup.CEFI,
            data_type="queue_position",
            venue=_venue,
            instrument_type="",
            live_capable=False,
            batch_capable=False,
            streaming_protocol="ws",
            sources=("market_tick_data_service/derived/book_microstructure_compute.py",),
            notes=(
                "No live depth_of_book_10 feed for this venue at all "
                "(see the depth_of_book_10 honest-gap entry above) — "
                "nothing for compute_book_microstructure() to derive from."
            ),
        )
        for _venue in (
            "BINANCE-SPOT",
            "OKX-FUTURES",
            "OKX-SPOT",
            "UPBIT",
        )
    ),
    # Derivative ticker — folds funding_rate, mark_price, index_price, OI
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="derivative_ticker",
        venue="BINANCE-FUTURES",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        notes="Includes funding_rate + mark_price + index_price + OI",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="derivative_ticker",
        venue="OKX-SWAP",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="derivative_ticker",
        venue="BYBIT",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="derivative_ticker",
        venue="DERIBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    # Liquidations
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="liquidations",
        venue="BINANCE-FUTURES",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="liquidations",
        venue="BYBIT",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="liquidations",
        venue="OKX-SWAP",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    # Options chain — LIVE-CAPABLE crypto options (Deribit public REST, no creds).
    # Live (real-time) chain source for the VOL_* engine family. The
    # instruments-service DeribitOptionsReferenceDataAdapter enumerates
    # strikes/expiries -> CanonicalOptionsChain + venue mark IV; Tardis is the
    # historical-crypto-options source (BLOCKED-CREDENTIALS scaffold). Same
    # canonical options_chain data_type the TradFi CME row carries — batch==live.
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="options_chain",
        venue="DERIBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("instruments_service/reference_data/adapters/cefi/deribit_options_adapter.py",),
        notes=(
            "Deribit public REST option chains + mark IV (live, no creds); "
            "Tardis = historical-crypto source (BLOCKED-CREDENTIALS scaffold). "
            "Greeks computed in-house by greeks-service -> greeks_snapshot / "
            "implied_vol_surface (below)."
        ),
    ),
    # greeks_snapshot — per-leg in-house greeks (delta/gamma/vega/theta/rho + IV)
    # computed by greeks-service from the canonical options_chain. Live-capable:
    # rides the same live chain feed (batch==live, identical shape both modes).
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="greeks_snapshot",
        venue="DERIBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("greeks_service/kernels/black_scholes.py",),
        notes="In-house BS greeks per option leg; CanonicalGreeksSnapshot wire shape.",
    ),
    # implied_vol_surface — assembled IV-by-(strike/moneyness)x(expiry/tenor)
    # surface from the canonical options_chain (venue mark IV, else BS-fitted).
    # Live-capable: same live chain feed (batch==live).
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="implied_vol_surface",
        venue="DERIBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("greeks_service/kernels/iv_surface.py",),
        notes="CanonicalImpliedVolSurface of CanonicalIVSurfacePoint; honest-absence empty surface.",
    ),
    # volatility_index — Deribit DVOL implied-vol index, public REST history
    # (``/public/get_volatility_index_data``), no credentials. REST-polled, not
    # a WS stream — live_capable=True still holds (a live consumer can re-poll
    # the same endpoint for the current value), so no ``streaming_protocol`` is
    # declared (mirrors the ``prediction_canonical_question_group`` REST-derived
    # pattern below). Feeds the DVOL-backtestable VOL_CARRY / VOL_ARB_RV_IV
    # engines (``vol_dvol_backtestable_engines_2026_07_13.md`` Todo 1 — registry
    # only; the MTDS capture handler + historical pull are that plan's separate,
    # not-yet-built Todo 2/3 — no handler file exists yet, so no ``sources``
    # entry is cited here until one lands).
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="volatility_index",
        venue="DERIBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        notes="Deribit BTC/ETH DVOL implied-vol index OHLC; public REST, no creds.",
    ),
    # Futures chain bundle
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="futures_chain",
        venue="BINANCE-FUTURES",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="futures_chain",
        venue="BYBIT",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    # ── CeFi venues added 2026-06-23 (cefi full-catalogue dispatch) ───────
    # The full-universe IS catalogue (18 venues / 230k rows) surfaced these
    # venues with EMPTY ``venue_data_types`` in the per-venue CSV export
    # because they had no rows here. Populate the data_types we ACTUALLY
    # capture per venue, by source, so the data_type axis is non-empty for
    # EVERY cefi venue (operator 2026-06-23: incl HL/ASTER + small DEX-perps,
    # even though they are NOT sourced from Tardis). SSOT for the per-venue
    # capture map: plans/active/issues/cefi_hl_aster_batch_data_gaps_2026_06_22.md
    # + cefi_universe_capture_rule_2026_06_23.md.
    #
    # ── Tardis CEX SPOT venues (KRAKEN-SPOT / BITGET-SPOT / BITFINEX-SPOT) ─
    # Same Tardis spot capture surface as COINBASE-SPOT/UPBIT above: trades +
    # book_snapshot_5 (order_flow_imbalance RETIRED 2026-07-08 — see the L2
    # microstructure section above). The two deeper-book data_types stay
    # honest-absent (depth_of_book_10 / queue_position need an L10/full-L2
    # capture, like every existing venue).
    *(
        DataTypeCapability(
            asset_group=AssetGroup.CEFI,
            data_type=_dt,
            venue=_venue,
            instrument_type="",
            live_capable=True,
            batch_capable=True,
            streaming_protocol="ws",
            sources=("market_tick_data_service/market_interface/adapters/cefi/tardis_shared.py",),
        )
        # BYBIT-SPOT added 2026-06-23 (cefi_universe_capture_rule): distinct
        # canonical venue for the Tardis ``bybit-spot`` endpoint, same spot
        # capture surface; pairs with BYBIT perps on the entity prefix.
        for _venue in ("KRAKEN-SPOT", "BITGET-SPOT", "BITFINEX-SPOT", "BYBIT-SPOT")
        for _dt in ("trades", "book_snapshot_5")
    ),
    # ── Tardis CEX PERP/FUTURES venues (KRAKEN-FUTURES / BITGET-FUTURES /
    # BITFINEX-FUTURES) — the derivatives complex. Same as the spot surface
    # PLUS derivative_ticker (funding/mark/index/OI) + liquidations
    # (Tardis ``liquidations`` channel) + futures_chain (dated quarterlies).
    # BITFINEX-FUTURES is the canonical venue for the Tardis
    # ``bitfinex-derivatives`` exchange (parallel to KRAKEN-FUTURES =
    # ``cryptofacilities``; -FUTURES is the convention-consistent suffix —
    # see venue_mapping.tardis_to_venue).
    *(
        DataTypeCapability(
            asset_group=AssetGroup.CEFI,
            data_type=_dt,
            venue=_venue,
            instrument_type=_itype,
            live_capable=True,
            batch_capable=True,
            streaming_protocol="ws",
            sources=("market_tick_data_service/market_interface/adapters/cefi/tardis_shared.py",),
        )
        # COINBASE-FUTURES added 2026-06-23 (cefi_universe_capture_rule): Coinbase
        # Derivatives (perps) via Tardis ``coinbase-international``; same perp
        # capture surface; pairs with COINBASE-SPOT on the entity prefix.
        for _venue in ("KRAKEN-FUTURES", "BITGET-FUTURES", "BITFINEX-FUTURES", "COINBASE-FUTURES")
        for _dt, _itype in (
            ("trades", ""),
            ("book_snapshot_5", ""),
            # order_flow_imbalance RETIRED 2026-07-08 — see the L2 microstructure
            # section above.
            ("derivative_ticker", "perpetual"),
            ("liquidations", "perpetual"),
            ("futures_chain", ""),
        )
    ),
    # ── HYPERLIQUID derivative_ticker (S3 archive ``asset_ctxs`` =
    # funding/OI; trades + book_snapshot_5 already declared above). HL
    # publishes NO liquidation feed anywhere → no liquidations row (DROPPED
    # as a hard system constraint, BUG#4(A) cefi_hl_aster gaps).
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="derivative_ticker",
        venue="HYPERLIQUID",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/hyperliquid/",),
        notes="HL S3 asset_ctxs = funding + open_interest. HL has NO liquidation feed (dropped).",
    ),
    # ── ASTER (Astherus) — Binance-Futures-compatible. NOT Tardis-sourced:
    # batch-historical REST (``fapi`` ``fundingRate`` + ``aggTrades``) serves
    # derivative_ticker + trades; book_snapshot_5 + liquidations are
    # LIVE-ONLY via the native asterdex WS (``@depth5@100ms`` +
    # ``!forceOrder@arr``) — historical REST cannot serve them
    # (live_capable=True, batch_capable=False). cefi_hl_aster_batch_data_gaps
    # BUG#4(A): KEEP as live-only, never a batch empty cell.
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="derivative_ticker",
        venue="ASTER",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/cefi/aster_rest.py",),
        notes="ASTER fapi fundingRate (Binance-compat) = funding/mark. Batch REST + live WS.",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="ASTER",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/cefi/aster_rest.py",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="ASTER",
        instrument_type="",
        live_capable=True,
        batch_capable=False,
        streaming_protocol="ws",
        sources=("market_tick_data_service/live/connectors/aster_book_liq_ws.py",),
        notes="LIVE-ONLY: asterdex WS @depth5@100ms. Binance-compat REST has no historical depth.",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="liquidations",
        venue="ASTER",
        instrument_type="perpetual",
        live_capable=True,
        batch_capable=False,
        streaming_protocol="ws",
        sources=("market_tick_data_service/live/connectors/aster_book_liq_ws.py",),
        notes="LIVE-ONLY: asterdex WS !forceOrder@arr. No historical liquidation REST.",
    ),
    # ── Small DEX-perp venues (on-chain CLOBs, treated as cefi). Native APIs
    # (NOT Tardis except LIGHTER post-2026-04-17): trades + book_snapshot_5 +
    # derivative_ticker (perp funding). Minimum perp surface so the data_type
    # axis is non-empty (operator 2026-06-23: all venues incl small DEX-perps
    # are in scope). DERIBIT-COMBO rides Deribit's multi-leg combo feed.
    # EXTENDED-STARKNET + LIGHTER-ZKSYNC (like HYPERLIQUID + ASTER above): the
    # standalone ``perp_funding`` data_type was RETIRED for these venues
    # (2026-07-08, operator-approved) in favor of this derivative_ticker row's
    # embedded funding_rate field — a live-fetch probe confirmed byte-identical/
    # same-source funding data for both. derivative_ticker IS the funding source
    # here; no separate perp_funding capability declaration exists or is needed.
    # (PACIFICA (Solana) was a third venue in this loop until removed entirely
    # 2026-07-16 — operator ruling: all Solana perp DEXes dropped except
    # Jupiter, not integrated.)
    *(
        DataTypeCapability(
            asset_group=AssetGroup.CEFI,
            data_type=_dt,
            venue=_venue,
            instrument_type=_itype,
            live_capable=True,
            batch_capable=True,
            streaming_protocol="ws",
        )
        for _venue in ("EXTENDED-STARKNET", "LIGHTER-ZKSYNC")
        for _dt, _itype in (
            ("trades", ""),
            ("book_snapshot_5", ""),
            ("derivative_ticker", "perpetual"),
        )
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="trades",
        venue="DERIBIT-COMBO",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        notes="Deribit multi-leg combo/spread instruments (distinct venue from DERIBIT).",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.CEFI,
        data_type="book_snapshot_5",
        venue="DERIBIT-COMBO",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    # =====================================================================
    # DeFi
    # =====================================================================
    # Wire-format note (reconciled 2026-06-02, A11c — defi-canonical-naming-ssot.md):
    # DeFi handlers NOW write canonical data_types to the manifest
    # (`dex_pool_state` / `dex_pool_swaps` / `lending_indices` / `lst_rates` /
    # `oracle_prices` / `perp_funding`, operator-locked + shipped via C0-CN2);
    # the earlier "EMPTY data_type / data-type axis unused" wording was the
    # pre-canonicalisation state and is now stale. These rows are still keyed by
    # venue alone (one DataTypeCapability per protocol) — populating the full
    # per-(venue, data_type) capability matrix with the canonical names is the
    # larger follow-up tracked in
    # `plans/active/issues/defi_coverage_capability_alignment_2026_05_22.md`;
    # the expected-coverage DENOMINATOR (`expected_coverage._DEFI` +
    # `market_data_categories` + `defi_venue_capabilities`) is already canonical.
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="AAVE_V3",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        sources=("market_tick_data_service/market_interface/adapters/defi/aave/",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="UNISWAP_V3",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        liquidity_cutoff_usd=1_000_000.0,
        sources=("market_tick_data_service/market_interface/adapters/defi/uniswap_v3_adapter.py",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="UNISWAP_V2",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="CURVE",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="BALANCER",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="COMPOUND_V3",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="LIDO",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="ETHENA",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="MORPHO",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="",
        venue="EIGENLAYER",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="rewards",
        venue="EIGENLAYER",
        instrument_type="staking",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        notes="Eigenlayer restaking rewards stream — only DeFi tuple with a non-empty data_type today",
    ),
    # aggregator_route — DEX aggregator quote capture for batch replay via AggregatorRouteMatcher.
    # Captured at decision time; route_json holds the full RouteLeg list.
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="aggregator_route",
        venue="JUPITER",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=False,
        notes="Jupiter aggregator (Solana) — REST quote-API; RouteLeg list serialized to route_json",
        sources=("execution_service/matching_engine/aggregator.py",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="aggregator_route",
        venue="1INCH",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        notes="1inch aggregator (EVM) — REST quote-API; requires API key for production rate limits",
        sources=("execution_service/matching_engine/aggregator.py",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="aggregator_route",
        venue="0X",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        notes="0x aggregator (EVM) — REST quote-API; requires API key",
        sources=("execution_service/matching_engine/aggregator.py",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.DEFI,
        data_type="aggregator_route",
        venue="PARASWAP",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=False,
        notes="ParaSwap aggregator (EVM) — REST quote-API; public endpoint available",
        sources=("execution_service/matching_engine/aggregator.py",),
    ),
    # =====================================================================
    # ── TradFi (verified 2026-04-30 against availability_index.parquet) ─
    # venues=CME/ICE/CBOE/NYSE/NASDAQ/FX; data_types=ohlcv_{1m,24h,15m},
    # trades, tbbo, options_chain; instrument_types=future/equity/spot_pair/
    # options_chain/combo (or empty).
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_1m",
        venue="CME",
        instrument_type="future",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_1m",
        venue="ICE",
        instrument_type="future",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_1m",
        venue="NYSE",
        instrument_type="equity",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_1m",
        venue="NASDAQ",
        instrument_type="equity",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_24h",
        venue="FX",
        instrument_type="spot_pair",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_15m",
        venue="CBOE",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
    # CBOE VX FUTURES — ohlcv_1s + ohlcv_1m via Databento XCBF.PITCH (operator's
    # "CFE" subscription, 2026-06-19). Distinct from the ohlcv_15m VIX cash index.
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_1s",
        venue="CBOE",
        instrument_type="future",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_1m",
        venue="CBOE",
        instrument_type="future",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="trades",
        venue="CME",
        instrument_type="future",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="trades",
        venue="ICE",
        instrument_type="future",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="trades",
        venue="NYSE",
        instrument_type="equity",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="trades",
        venue="NASDAQ",
        instrument_type="equity",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="tbbo",
        venue="CME",
        instrument_type="future",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="tbbo",
        venue="NYSE",
        instrument_type="equity",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="tbbo",
        venue="NASDAQ",
        instrument_type="equity",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="options_chain",
        venue="CME",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        ttm_cutoff_days=365,
        sources=("market_tick_data_service/market_interface/adapters/tradfi/databento_opra_converter.py",),
    ),
    # ETF daily OHLCV (NYSE / NASDAQ / ARCA) — capability stubs.
    #
    # ARCHITECTURAL NOTE (2026-04-30 correction): venue and data source
    # are distinct axes. SPY's venue is NYSE Arca; QQQ's is NASDAQ. yfinance
    # is a DATA SOURCE we fetch from, not a venue. The legacy
    # ``YAHOO_FINANCE`` venue token in some other registries (expected_coverage,
    # data_availability) is a stop-gap that conflates the two — new code
    # should avoid it.
    #
    # These capability rows will render ⚪ in the catalogue until either
    # (a) the Databento equity adapter ships (currently NotImplementedError
    # per its own docstring) — writes ETF ohlcv_24h to venue=NYSE/NASDAQ, or
    # (b) the Yahoo adapter is taught to classify symbol → venue and write
    # under the correct exchange token.
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_24h",
        venue="NYSE",
        instrument_type="etf",
        live_capable=False,
        batch_capable=True,
        notes="SPY / IVV / VOO / IWM / DIA / GLD / SLV / USO / TLT / IEF / SHY / HYG / LQD / EEM / EFA / sector SPDRs",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.TRADFI,
        data_type="ohlcv_24h",
        venue="NASDAQ",
        instrument_type="etf",
        live_capable=False,
        batch_capable=True,
        notes="QQQ / IBIT / FBTC / ARKB / ETHA / FETH",
    ),
    # ── Prediction (verified 2026-04-30 against availability_index.parquet) ─
    # POLYMARKET writes data_type=trades (instrument_type=prediction_market) AND
    # data_type=prediction_trades (per-underlying instrument_type tokens BTC/ETH/
    # XRP/SOL/SPX/DJIA/NDX/SILVER/GOLD/CRUDE_OIL/...) AND
    # data_type=prediction_canonical_question_group (bundled CQG bucket derived
    # by the writer — one row per canonical group x day). KALSHI excluded — no US
    # account yet. POLYMARKET book_snapshot / market_metadata excluded — adapters
    # do not yet write those data_types to the manifest.
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="trades",
        venue="POLYMARKET",
        instrument_type="prediction_market",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        sources=("market_tick_data_service/market_interface/adapters/prediction/polymarket_adapter.py",),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="BTC",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        notes="Per-underlying prediction trades — one capability per underlying token",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="ETH",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="SOL",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="XRP",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="SPX",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="DJIA",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="NDX",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="GOLD",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="SILVER",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="CRUDE_OIL",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_trades",
        venue="POLYMARKET",
        instrument_type="OTHER",
        live_capable=True,
        batch_capable=True,
        streaming_protocol="ws",
        notes="Long-tail / uncategorised prediction-trades bucket",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.PREDICTION,
        data_type="prediction_canonical_question_group",
        venue="POLYMARKET",
        instrument_type="",
        live_capable=True,
        batch_capable=True,
        notes=(
            "Bundled CQG bucket: writer groups prediction_trades rows by "
            "canonical question group (BTC_UP_DOWN_DAILY, OTHER, ...) x day. "
            "Declaring this capability removes the deployment-ui 'out of scope' "
            "badge for POLYMARKET on this data_type (badge = manifest data_type "
            "not in VENUE_DATA_TYPE_CAPABILITIES). Added 2026-06-16."
        ),
    ),
    # =====================================================================
    # Sports
    # =====================================================================
    # Wire-format SSOT verified 2026-04-30. The sports manifest has 2M+
    # rows in instruments-store-sports — most rows have empty venue
    # (sports captures source-by-day, not by-venue). Only ODDS_API odds
    # rows (17282) and API_FOOTBALL FIXTURE_STATS rows (5858) carry an
    # explicit venue token. Most-prolific empty-venue data_types:
    # STANDINGS / FIXTURES / INJURIES / FIXTURE_STATS / FIXTURE_EVENTS /
    # FIXTURE_LINEUPS / PLAYER_STATS / WEATHER / PREDICTIONS / ODDS /
    # MATCHES / XG / TRANSFERMARKT_LEAGUES.
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="FIXTURES",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        notes="Empty venue — sports captures by source-name, not venue",
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="ODDS",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        notes=(
            "Bulk ODDS captures (105K+ rows in prod) write to the manifest "
            "with empty venue — the source axis (footystats_odds, "
            "mdps_odds_horizon_bucket) is recorded inside the parquet path, "
            "not as the manifest venue token. SSOT: "
            "unified_api_contracts.sports.SOURCE_COVERAGE_START."
        ),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="ODDS",
        venue="ODDS_API",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
        retention_days=730,
        notes=(
            "Explicit ODDS_API venue tag (~17K rows in prod). The bulk of "
            "ODDS data is at empty venue — see the empty-venue capability "
            "above."
        ),
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="FIXTURE_EVENTS",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="FIXTURE_STATS",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
        requires_credentials=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="FIXTURE_LINEUPS",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="STANDINGS",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="INJURIES",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="PLAYER_STATS",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="WEATHER",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="PREDICTIONS",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="MATCHES",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
    DataTypeCapability(
        asset_group=AssetGroup.SPORTS,
        data_type="XG",
        venue="",
        instrument_type="",
        live_capable=False,
        batch_capable=True,
    ),
)


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------


def find_capability(
    asset_group: AssetGroup | str,
    data_type: str,
    venue: str,
    instrument_type: str | None = None,
) -> DataTypeCapability | None:
    """Return the matching capability or ``None``.

    ``instrument_type=None`` matches the first row with the same
    (asset_group, data_type, venue) regardless of instrument_type — useful
    when the caller doesn't have an instrument_type axis (e.g. the venue
    has only one).
    """
    ag = AssetGroup(asset_group) if not isinstance(asset_group, AssetGroup) else asset_group
    for cap in DATA_TYPE_CAPABILITY_REGISTRY:
        if cap.asset_group != ag:
            continue
        if cap.data_type != data_type:
            continue
        if cap.venue != venue:
            continue
        if instrument_type is not None and cap.instrument_type != instrument_type:
            continue
        return cap
    return None


def capabilities_for_asset_group(
    asset_group: AssetGroup | str,
) -> tuple[DataTypeCapability, ...]:
    """Return all capability rows for an asset group."""
    ag = AssetGroup(asset_group) if not isinstance(asset_group, AssetGroup) else asset_group
    return tuple(c for c in DATA_TYPE_CAPABILITY_REGISTRY if c.asset_group == ag)


__all__ = [
    "DATA_TYPE_CAPABILITY_REGISTRY",
    "DataTypeCapability",
    "capabilities_for_asset_group",
    "find_capability",
]
