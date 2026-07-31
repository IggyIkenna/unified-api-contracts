"""Execution fidelity capability — item 001 in
``plans/active/execution_fidelity_tiers_uac_governed_2026_06_28.md``.

UAC is the SSOT for **what execution matching fidelity is possible** for a
given ``(asset_group, venue, instrument_type)`` cell and ``mode``
(live / batch). The execution-service matching engine reads this capability
to pick its matcher tier (L2 book walk vs. candle+book-cols vs. plain OHLC
bar) instead of hard-mapping by domain — so a strategy may request a max
tier and execution clamps to what the data supports.

The three tiers (in descending fidelity):

==========================  ==========================================  =======================================
Tier                        Data required                               Matcher
==========================  ==========================================  =======================================
``L2_TICK``                 ``trades + book_snapshot_5`` ticks          full L2 book walk (L2_MBP)
``CANDLE_BOOK_COLS``        Plan-1 candle with intra-bar book columns   fill at time-weighted spread, slippage
                                                                        off mean depth
``OHLC_BAR``                plain ``ohlcv_1m`` candle                   OHLC-endpoint / close fill (L1-style;
                                                                        the e2e 1m determinism spine)
==========================  ==========================================  =======================================

Decision table — applied to the MVP_SCOPE data_type set for the cell
(resolved via :func:`unified_api_contracts.is_mvp`'s resolution order:
per-venue override → per-instrument_type override → flat ``data_types``):

* ``book_snapshot_5`` ∈ data_types   → ``L2_TICK``     (CeFi standard venues
                                                       across PERPETUAL /
                                                       SPOT_PAIR / FUTURE /
                                                       EQUITY_PERP)
* AMM pool state (``dex_pool_state``  → ``CANDLE_BOOK_COLS`` (POOL / DEX_POOL
  AND ``dex_pool_swaps``)              cells — the on-chain reserves +
                                       swap stream is the book-equivalent;
                                       the Plan-1 candle carries pool-reserve
                                       columns for the matcher)
* anything else                       → ``OHLC_BAR``   (TradFi ``ohlcv_1m``;
                                       CeFi COINBASE ``{trades}``-only;
                                       Deribit OPTION ``{options_chain}``;
                                       DeFi LST/LENDING reference-rate cells)

``mode`` is currently a future-proof axis: for today's MVP the data_types a
cell carries are the same in live and batch, so both modes resolve to the
same tier. The parameter exists so a future cell that diverges
(e.g. a venue that ships book ticks live but only candles in batch) can be
expressed without changing the function signature.

``sports`` and ``prediction`` raise — sports has no execution model
(non-tradable odds), and prediction's CLOB execution model is out of scope
for the item-001 capability (the perp/spot representative selectors are
also restricted to the three market-data AGs that share a
``(venue, instrument_type)`` grain).
"""

from __future__ import annotations

from enum import StrEnum
from typing import Final, Literal

from unified_api_contracts.canonical.crosscutting.mvp_scope import (
    MVP_SCOPE,
    CeFiMvpRule,
    DeFiMvpRule,
    TradFiMvpRule,
    mdps_mvp_universe,
)


class ExecutionFidelityTier(StrEnum):
    """The three execution matching fidelities the engine supports.

    Ordering: ``L2_TICK`` > ``CANDLE_BOOK_COLS`` > ``OHLC_BAR``. A strategy
    may request a max tier and the engine clamps DOWN to what
    :func:`execution_fidelity` returns for the cell. There is no
    "L1_TICK" (trade-tape-only) tier — without book state, the matcher
    falls back to candle/bar fill (``OHLC_BAR``), which is what CeFi
    COINBASE ``{trades}``-only venues resolve to.
    """

    L2_TICK = "L2_TICK"
    CANDLE_BOOK_COLS = "CANDLE_BOOK_COLS"
    OHLC_BAR = "OHLC_BAR"


ExecutionMode = Literal["live", "batch"]
"""Mode the matching engine runs in.

``live`` — real-time stream; the matcher consumes the active data feed.
``batch`` — historical backtest; the matcher consumes persisted parquet.

For today's MVP_SCOPE the per-cell data_types are identical live vs. batch
(capture-driven), so the mode parameter does not change the resolution.
Reserved for future divergence (e.g. a vendor that streams book ticks live
but only ships candles in batch, or vice versa).
"""


# --- Sentinel tier-resolution markers --------------------------------------
# Membership-only frozensets — kept module-level so the resolution function
# stays a pure lookup over MVP_SCOPE's data_type set (no per-call object
# construction inside the hot path).

_L2_TICK_DATA_TYPES: Final[frozenset[str]] = frozenset({"book_snapshot_5"})
"""Data types whose presence is sufficient for L2_TICK matching.

Today this is just ``book_snapshot_5`` — the CeFi venues with the per-tick
order book snapshots in MVP_SCOPE (Binance, Bybit, OKX, Deribit perp/future,
Hyperliquid, Aster, Kraken). When a venue's per-venue or per-instrument_type
override drops ``book_snapshot_5`` (e.g. COINBASE = ``{trades}``,
Deribit OPTION = ``{options_chain}``), the cell falls down to OHLC_BAR.
"""

_AMM_POOL_DATA_TYPES: Final[frozenset[str]] = frozenset({"dex_pool_state", "dex_pool_swaps"})
"""Data types whose JOINT presence resolves to CANDLE_BOOK_COLS.

Plan-1 introduced book_summary columns on the candle artifact derived from
order-book ticks; DeFi POOL / DEX_POOL cells get the analogue (pool reserve
columns + swap-event derived volume/spread) on the candle. Both ``state``
(the reserves) AND ``swaps`` (the events) need to be in scope for the
matcher to have something to fill against — a state-only cell (e.g. a
hypothetical snapshot-only protocol) would fall through to OHLC_BAR.
"""

_AMM_INSTRUMENT_TYPES: Final[frozenset[str]] = frozenset({"POOL", "DEX_POOL"})
"""DeFi instrument_types where the AMM-pool tier applies.

The DeFi MVP rule's flat ``data_types`` is the UNION of every data_type in
scope across all DeFi instrument_types (``dex_pool_state`` + ``lst_rates`` +
``lending_indices`` + …), so a naive "is the data_type set superset of
``{dex_pool_state, dex_pool_swaps}``?" check would wrongly classify an
``LST`` or ``LENDING`` cell as CANDLE_BOOK_COLS. The DeFi rule does not
encode per-instrument_type data_type subsets, so the AMM check is gated on
the instrument_type matching one of the actual AMM types here. LST + LENDING
are reference-rate cells (``lst_rates`` / ``lending_indices``) — they fall
to OHLC_BAR.
"""


# ---------------------------------------------------------------------------
# Internal data-type resolution — mirror is_mvp's resolution order for the
# three supported AGs (cefi / defi / tradfi). Sports + prediction never
# reach the resolver because they are rejected upstream.
# ---------------------------------------------------------------------------


def _cefi_data_types_for_cell(venue: str, instrument_type: str, rule: CeFiMvpRule) -> frozenset[str]:
    """Resolve the MVP data_type set for a CeFi ``(venue, instrument_type)``.

    Resolution order mirrors :func:`unified_api_contracts.is_mvp`:

    1. Per-venue override (``venue_data_types``) — highest priority. When a
       venue declares its own set (e.g. ``COINBASE-SPOT → {trades}``), that
       set applies to ALL instrument_types at that venue. The map key is
       matched on the EXACT venue string first, then the base token before
       the first ``-`` (so ``COINBASE-SPOT`` resolves whether the key is
       ``COINBASE-SPOT`` or bare ``COINBASE``).
    2. Per-instrument_type override (``instrument_type_data_types``) —
       applies when the venue has no override. Today only
       ``OPTION → {options_chain}`` (a Deribit option's bulk-chain bundle).
    3. Flat ``data_types`` — default
       (``{trades, book_snapshot_5, derivative_ticker, funding_rate}``).
    """
    venue_norm = (venue or "").strip().upper()
    if rule.venue_data_types:
        if venue_norm in rule.venue_data_types:
            return rule.venue_data_types[venue_norm]
        venue_base = venue_norm.split("-", 1)[0]
        if venue_base and venue_base != venue_norm and venue_base in rule.venue_data_types:
            return rule.venue_data_types[venue_base]
    instrument_type_norm = (instrument_type or "").strip().upper()
    return rule.instrument_type_data_types.get(instrument_type_norm, rule.data_types)


# ---------------------------------------------------------------------------
# Public capability function
# ---------------------------------------------------------------------------


def execution_fidelity(
    asset_group: str,
    venue: str,
    instrument_type: str,
    mode: ExecutionMode,
) -> ExecutionFidelityTier:
    """Return the maximum :class:`ExecutionFidelityTier` for the cell.

    The cell is the ``(asset_group, venue, instrument_type)`` grain — a
    projection of the ``(venue, instrument_type, data_type)`` triples
    ``mdps_mvp_universe`` returns (down to the two axes this gate checks) and
    the same grain ``is_mvp`` accepts. The resolution reads the cell's MVP
    data_types out of MVP_SCOPE (applying the v11 / v12 per-venue +
    per-instrument_type overrides), then projects onto the three-tier
    decision table documented in this module's docstring.

    Args:
        asset_group: One of ``cefi`` / ``defi`` / ``tradfi``. ``sports`` and
            ``prediction`` raise ``ValueError`` — they are not in the
            executable-instrument scope for item 001 of the plan.
        venue: Canonical venue identifier (e.g. ``BINANCE-FUTURES``,
            ``COINBASE-SPOT``, ``CME``, ``UNISWAP_V3-ETHEREUM``). The CeFi
            sub-venue resolution rule applies: a bare ``OKX`` resolves via
            ``_cefi_venue_in_rule``.
        instrument_type: Canonical instrument-type string (a
            :class:`~unified_api_contracts.InstrumentType` str value).
        mode: ``"live"`` or ``"batch"``. Reserved for future per-mode
            divergence; today both resolve identically.

    Returns:
        The highest :class:`ExecutionFidelityTier` the cell's data supports.

    Raises:
        ValueError: ``asset_group`` is unknown, is sports/prediction (no
            executable instrument grain in scope for item 001), or the
            ``(venue, instrument_type)`` cell is not declared in
            :data:`MVP_SCOPE` for the asset_group. The cell-not-in-MVP case
            is a fail-loud guard — execution must never silently fall back
            to OHLC for a venue/instrument_type that is not even in the
            capture universe.

    Example::

        from unified_api_contracts import (
            ExecutionFidelityTier,
            execution_fidelity,
        )

        # CeFi with trades + book ticks → full L2 walk
        assert execution_fidelity(
            "cefi", "BINANCE-FUTURES", "PERPETUAL", "batch"
        ) == ExecutionFidelityTier.L2_TICK

        # CeFi COINBASE — trades-only override → fall back to OHLC bar
        assert execution_fidelity(
            "cefi", "COINBASE-SPOT", "SPOT_PAIR", "batch"
        ) == ExecutionFidelityTier.OHLC_BAR

        # TradFi 1m bars — only ohlcv_1m in MVP → OHLC_BAR
        assert execution_fidelity(
            "tradfi", "CME", "FUTURE", "batch"
        ) == ExecutionFidelityTier.OHLC_BAR

        # DeFi AMM pool — pool state + swap events → candle+book-cols matcher
        assert execution_fidelity(
            "defi", "UNISWAP_V3-ETHEREUM", "POOL", "batch"
        ) == ExecutionFidelityTier.CANDLE_BOOK_COLS
    """
    # Reject the two non-executable asset_groups loudly. Sports has no
    # execution model; prediction's CLOB execution model is a separate plan.
    if asset_group in {"sports", "prediction"}:
        raise ValueError(
            f"execution_fidelity: asset_group {asset_group!r} is not in the executable-instrument "
            "scope for item 001 (sports has no execution model; prediction's CLOB execution is out "
            "of scope — supported: cefi / defi / tradfi)."
        )
    rule = MVP_SCOPE.get(asset_group)
    if rule is None:
        raise ValueError(f"execution_fidelity: unknown asset_group {asset_group!r} (not declared in MVP_SCOPE).")
    if not isinstance(rule, CeFiMvpRule | DeFiMvpRule | TradFiMvpRule):
        raise ValueError(
            f"execution_fidelity: asset_group {asset_group!r} has no executable-instrument rule "
            "(Phase-2 stub or non-market-data AG)."
        )

    # Cell must be in MVP. mdps_mvp_universe already encodes the tradfi
    # equity-basis carve-out, so this is a single membership check that
    # covers every supported AG. Project the (venue, instrument_type,
    # data_type) triples down to (venue, instrument_type) — this gate has no
    # data_type axis of its own (fidelity is checked per-instrument).
    mvp_cells = {(v, it) for v, it, _dt in mdps_mvp_universe(asset_group)}
    if (venue, instrument_type) not in mvp_cells:
        raise ValueError(
            f"execution_fidelity: ({venue!r}, {instrument_type!r}) is not an MVP cell for "
            f"asset_group {asset_group!r} — execution must not silently fall back for a cell that "
            "is not even in the capture universe. Add the cell to MVP_SCOPE first."
        )

    # Mode is reserved for future divergence; today both modes resolve to
    # the same data_type set. Touch it so static analysis sees the use.
    _ = mode

    # Resolve the data_types in scope for this cell.
    data_types = _data_types_for_cell(asset_group, venue, instrument_type, rule)

    # Decision table — apply the three tiers in descending fidelity.
    if data_types & _L2_TICK_DATA_TYPES:
        return ExecutionFidelityTier.L2_TICK
    if instrument_type in _AMM_INSTRUMENT_TYPES and _AMM_POOL_DATA_TYPES.issubset(data_types):
        return ExecutionFidelityTier.CANDLE_BOOK_COLS
    return ExecutionFidelityTier.OHLC_BAR


def _data_types_for_cell(
    asset_group: str,
    venue: str,
    instrument_type: str,
    rule: CeFiMvpRule | DeFiMvpRule | TradFiMvpRule,
) -> frozenset[str]:
    """Dispatch to the per-AG data_type resolver — mirrors :func:`is_mvp`."""
    if isinstance(rule, CeFiMvpRule):
        return _cefi_data_types_for_cell(venue, instrument_type, rule)
    # DeFi + TradFi have no per-venue / per-instrument_type overrides today;
    # the flat ``data_types`` set is the answer.
    return rule.data_types
