"""Restaking reward economics — 3-layer model + per-LST reward stream registry.

For restaking-eligible LSTs (weETH, pufETH, ankrETH, ETHx) and Solana
restaking equivalents (jitoSOL, mSOL, bSOL), total realised yield decomposes
into three on-chain-discoverable layers, each with its own data source,
cadence, and reward-token mix:

    Total LST yield = base_apy(exchange_rate)                 # layer 1 — in lst_rates
                    + avs_continuous_apy_per_token            # layer 2 — in eigenlayer_rewards
                    + issuer_seasonal_apy_per_token           # layer 3 — NEW: in lst_seasonal_rewards

The v0 ``_eigenlayer_aggregate_apy`` collapsed all three into a single
ETH-equivalent number, which:

  * masked per-LST attribution differences (weETH gets ETHFI seasonal
    drops; pufETH gets PUFFER foundation drops; they shouldn't share),
  * masked illiquidity haircuts (ARPA reward token at $1 USD-mid != $1
    realised after slippage),
  * missed lump-sum issuer-side seasonal rewards (Ether.fi merkle
    distributor claims, ~quarterly, not in the continuous stream).

This module names the layers, registers per-LST reward streams, indexes
on-chain distributor addresses for discovery, and provides the schema for
:mod:`unified_api_contracts.internal.architecture_v2.dust_conversion`'s
``ConvertDustInstruction`` to realise reward dust into a target denomination
(ETH for ETH-side LSTs, SOL for SOL-side, USD for fund-level NAV).

PnL attribution: each realised reward is tagged with its ``RewardPnLLayer``
so strategy-service/pnl can decompose the CARRY factor into
CARRY_BASE / CARRY_AVS_CONTINUOUS / CARRY_ISSUER_SEASONAL, plus a separate
REWARD_REALISATION_SLIPPAGE factor capturing the dust-conversion cost.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from unified_api_contracts.internal.architecture_v2.enums import (
    InstructionActionV2,
)
from unified_api_contracts.internal.architecture_v2.schemas import (
    StrategyInstructionEnvelope,
)


class RewardPnLLayer(StrEnum):
    """The 3-layer decomposition for restaking-eligible LST rewards.

    Maps 1:1 to PnL attribution sub-factors under the CARRY parent factor.
    Each LST holding accrues yield from up to all three layers
    simultaneously; strategy-service/pnl produces one row per (holding,
    layer, token) tuple per accrual period.
    """

    CARRY_BASE = "CARRY_BASE"
    """Exchange-rate appreciation of the LST itself. Sourced from
    ``lst-rates`` parquet. Continuous, in the LST's quote asset (ETH for
    stETH/weETH/rETH/etc., SOL for jitoSOL/mSOL, USDe for sUSDe). One per
    LST per period."""

    CARRY_AVS_CONTINUOUS = "CARRY_AVS_CONTINUOUS"
    """EigenLayer / Karak / Symbiotic continuous AVS rewards,
    paid per-token (EIGEN, KARAK, ARPA, AVS-specific tokens) and indexed
    to AVS-protocol-level reward distributions. Sourced from
    ``eigenlayer_rewards`` parquet today; per-AVS sources to be added.
    Cadence: per-block accrual, settled on claim. One per (LST, token,
    AVS) triple per period."""

    CARRY_ISSUER_SEASONAL = "CARRY_ISSUER_SEASONAL"
    """LST-issuer-side episodic distributions: Ether.fi quarterly Season
    drops, Puffer foundation airdrops, Ankr direct rebates, Stader SD
    emissions, Karak per-season unlocks, EigenPie / Kelp distributor
    claims. Sourced from a NEW ``lst_seasonal_rewards`` parquet collected
    by features-onchain-service via ``Transfer(from=registered_distributor)``
    event scans. Cadence: episodic (quarterly, monthly, ad-hoc). One per
    (LST, token, issuer-distributor) triple per claim event."""


class RewardTokenEconomics(BaseModel):
    """Per-reward-token realisation economics.

    Used by the dust-conversion router and strategy-service/pnl to
    convert raw token amounts to target-denomination values WITHOUT
    pre-baking a haircut: the router quotes the actual conversion route
    through existing market data (Binance spot ticks, Uniswap V3 pools,
    Jupiter aggregator quotes) and reports the realised slippage as a
    separate PnL factor (REWARD_REALISATION_SLIPPAGE).

    The v0 fields here are observability hints — venues and pools the
    router should consider — not hardcoded haircuts. The actual
    realisation cost comes from simulating the conversion path through
    the matching engine on stored tick data.
    """

    token_symbol: str
    token_address: str
    chain: str
    decimals: int = 18

    cex_listings: list[str] = Field(
        default_factory=list,
        description=(
            "Centralised venues that list this token (e.g. ['BINANCE', "
            "'COINBASE-SPOT', 'BYBIT']). Router considers each for conversion "
            "quotes via market-tick-data-service spot tick feeds. Empty "
            "list = no CEX listing yet (points / pre-TGE)."
        ),
    )
    primary_dex_pools: list[str] = Field(
        default_factory=list,
        description=(
            "Pool keys (e.g. ['UNISWAP_V3-ETHEREUM:WETH-ETHFI:0x...', "
            "'CURVE-ETHEREUM:USDC-ETHFI:0x...']) the router should consider "
            "for on-chain conversion. Resolved via instruments-service. "
            "Empty list = no liquid DEX pool (points / pre-TGE)."
        ),
    )
    is_pre_tge_points: bool = Field(
        default=False,
        description=(
            "True for pre-TGE points / illiquid airdrop tokens "
            "(KING, MILES, EigenPie points, season-N points pre-token). "
            "PnL attribution treats these as accrued-but-unrealisable until "
            "TGE; pnl-attribution emits CARRY_ISSUER_SEASONAL rows with "
            "value_eth=0 and ``points_pending`` flag set."
        ),
    )
    expected_vesting_months: int | None = Field(
        default=None,
        description=(
            "Expected vesting cliff in months. None = liquid on receipt. "
            "Non-None values feed the strategy's discount rate when the "
            "strategy chooses NOT to convert immediately (controller "
            "honours strategy preference via ``hold_until_vested`` flag)."
        ),
    )


class LSTRewardStream(BaseModel):
    """One reward stream feeding a restaking-eligible LST.

    A single LST may receive multiple streams across the 3 layers; the
    full list per LST is the registry's ``LST_REWARD_STREAMS`` mapping.

    On-chain discovery: each stream names the distributor contract
    address (Merkle distributor, treasury multisig, or AVS rewards
    contract) so features-onchain-service can index
    ``Transfer(from=distributor_address, to=*)`` events into the
    ``lst_seasonal_rewards`` parquet.
    """

    lst_symbol: str
    """The LST receiving this stream (e.g. 'weETH', 'pufETH', 'jitoSOL')."""

    issuer: str
    """Issuer label: 'ether.fi' / 'puffer' / 'ankr' / 'stader' / 'karak'
    / 'eigenlayer' / 'jito' / 'marinade' / etc. Used for grouping in
    pnl-attribution output."""

    layer: RewardPnLLayer
    """Which of the 3 layers this stream belongs to. CARRY_BASE has one
    entry per LST (the exchange_rate appreciation); the other two layers
    have N entries per LST (one per reward token / distributor)."""

    distributor_address: str | None = Field(
        default=None,
        description=(
            "On-chain address of the rewards distributor for "
            "Transfer-event discovery. None for layer 1 (no distributor "
            "— rewards accrue in exchange_rate). Required for layer 2 + 3."
        ),
    )
    distributor_chain: str | None = Field(
        default=None,
        description="Chain the distributor lives on (ETHEREUM / SOLANA / etc.)",
    )
    distributor_kind: Literal["merkle", "direct_transfer", "claim_function", "exchange_rate"] = Field(
        default="merkle",
        description=(
            "How rewards are paid out: 'merkle' = Merkle proof claim "
            "(Ether.fi seasons, Karak); 'direct_transfer' = direct "
            "ERC20 Transfer (Ankr rebates, Puffer airdrops); "
            "'claim_function' = stake-pool claim() call (legacy); "
            "'exchange_rate' = no separate distribution (layer 1)."
        ),
    )
    reward_token_symbol: str
    """ETHFI / EIGEN / PUFFER / ANKR / SD / KARAK / JTO / MNDE / etc.
    For CARRY_BASE this is the LST's quote asset (ETH / SOL / USDe)."""

    cadence: Literal["continuous", "quarterly", "monthly", "ad_hoc"] = Field(
        default="continuous",
        description=(
            "Expected payout cadence. continuous = per-block accrual; "
            "quarterly = ~3 months between epochs (Ether.fi seasons); "
            "monthly = monthly emissions (some AVSs); ad_hoc = "
            "unpredictable foundation drops."
        ),
    )

    expected_share_pct: Decimal = Field(
        default=Decimal("0"),
        description=(
            "Expected share of the LST's reward economics this stream "
            "represents (0-100). Used by the rebalancer's carry_quality "
            "estimator. Calibrated from historical data; refined over time."
        ),
    )


class ConvertDustInstruction(StrategyInstructionEnvelope):
    """Generic dust-conversion instruction — any strategy issues one of
    these to realise a basket of reward tokens into a target denomination.

    Now extends ``StrategyInstructionEnvelope`` (the v2 envelope base shared
    with TradeInstruction / SwapInstruction / etc.) so the orchestrator's
    emit list is uniformly typed and downstream routing on
    ``action == InstructionActionV2.CONVERT_DUST`` works the same way as
    every other instruction kind. The strategy_instance_id is recovered
    from ``self.identity.strategy_instance_id`` (was a redundant top-level
    field in the v0 BaseModel form).

    Replaces hardcoded liquidity haircuts with actual route simulation:
    the dust-conversion router (execution-service algo_library) routes
    each token through the best CEX or DEX path, simulates fills via the
    existing matching engine, and returns realised target-denomination
    value with explicit slippage. Same code path batch + live (per
    Batch=Live), so live execution cost == batch backtest prediction.

    Use cases (all use the same primitive):
      - Restaking LST reward realisation: convert (EIGEN, ETHFI, ANKR,
        PUFFER, SD, KARAK, KING, MILES, ARPA, ...) -> ETH
      - Solana restaking reward realisation: convert (JTO, MNDE, BONK,
        SAYER, ...) -> SOL via Jupiter aggregator
      - Market-making rebate realisation: convert venue-token rebates
        (e.g. dYdX DYDX rebates) -> USDC
      - Liquidity-mining realisation: convert farming rewards (CRV, BAL,
        BANANA, JUP) -> ETH or SOL
      - Sports/prediction stake-back-token realisation: convert venue-
        specific bonus tokens -> USDC

    PnL attribution: the router emits one PnLAttribution row per
    converted token with factors split into:
      - DELTA: change in value at conversion vs receipt mark
      - REWARD_REALISATION_SLIPPAGE: realised vs mid-price slippage
      - FEES: protocol/exchange fees on the conversion
      - GAS: on-chain gas (DEX) or transfer fee (CEX withdrawal)
    """

    action: Literal[InstructionActionV2.CONVERT_DUST] = InstructionActionV2.CONVERT_DUST
    target_denomination: Literal["ETH", "SOL", "USDC", "USDT", "DAI"]
    """ETH for ETH-side restaking realisation, SOL for Solana,
    USDC/USDT/DAI for fund NAV-level realisation."""

    input_tokens: list[DustToken]
    """The basket to convert. Multiple tokens consolidate into one
    AtomicInstruction with sub-legs; the router orders them by liquidity
    + slippage to minimise total realisation cost."""

    max_total_slippage_bps: int = Field(
        default=200,
        description=(
            "Per-route slippage cap in basis points. Router skips legs "
            "that would exceed this and reports them as ``deferred`` in "
            "the result. Default 2.00% — generous enough for the long "
            "tail (ARPA, KING) at small notionals."
        ),
    )
    route_hint: Literal["AUTO", "CEX_ONLY", "DEX_ONLY", "AGGREGATOR"] = Field(
        default="AUTO",
        description=(
            "AUTO (default) = router picks per token. CEX_ONLY restricts "
            "to centralised venues (faster but requires deposit/withdraw "
            "wiring). DEX_ONLY restricts to on-chain. AGGREGATOR uses "
            "Jupiter / 1inch quote APIs only — best for thin tokens."
        ),
    )
    hold_until_vested_tokens: list[str] = Field(
        default_factory=list,
        description=(
            "Token symbols the strategy wants to HOLD rather than "
            "convert immediately (e.g. EIGEN with 4-yr vesting cliff -> "
            "strategy may want to defer realisation until vest). Router "
            "skips these and reports as ``held``."
        ),
    )
    pnl_layer_attribution: RewardPnLLayer | None = Field(
        default=None,
        description=(
            "Source layer that emitted these dust tokens — used by "
            "strategy-service/pnl to tag the resulting realised PnL "
            "rows with the right CARRY sub-factor. None means "
            "pnl-attribution will fall back to per-token-stream lookup."
        ),
    )


class DustToken(BaseModel):
    """One reward token in the dust basket."""

    token_symbol: str
    token_address: str
    chain: str
    amount: Decimal
    """Native token amount (decimal-adjusted, not raw uint256)."""
    source_wallet: str
    """Wallet/account holding the token. Router uses to plan transfer/
    withdrawal legs if needed (e.g. on-chain wallet -> CEX deposit
    address before CEX conversion)."""
    received_at_utc: str
    """ISO-8601 timestamp the token was received (for benchmark mark
    in the SLIPPAGE attribution: realised_value vs received-mark)."""
    received_at_mark_price_eth: Decimal | None = Field(
        default=None,
        description=(
            "ETH-equivalent value at receipt timestamp from market data. "
            "Used as the benchmark for SLIPPAGE attribution: positive "
            "slippage = realised more than mark; negative = paid the "
            "haircut. Resolved by features-onchain at receipt time."
        ),
    )


class DustConversionResult(BaseModel):
    """What the router returns after conversion attempt."""

    instruction_id: str
    realised_target_amount: Decimal
    """Total target-denomination amount realised across all converted
    legs. Excludes ``held`` and ``deferred`` tokens."""

    converted: list[ConvertedTokenLeg]
    held: list[str] = Field(default_factory=list)
    """Token symbols the strategy elected to hold (from
    hold_until_vested_tokens)."""
    deferred: list[DeferredTokenLeg] = Field(default_factory=list)
    """Tokens skipped because no acceptable route was found within the
    slippage cap. Strategy can retry with a relaxed cap or different
    route_hint."""


class ConvertedTokenLeg(BaseModel):
    token_symbol: str
    input_amount: Decimal
    target_amount_realised: Decimal
    target_amount_at_mark: Decimal
    """What the router would have realised at the mid-price quote (no
    slippage). Realised - at_mark = REWARD_REALISATION_SLIPPAGE factor."""
    route_taken: list[str]
    """Ordered hop list, e.g. ['BINANCE:ETHFI-USDC', 'UNISWAP_V3-ETHEREUM:USDC-WETH']
    or ['JUPITER:JTO-SOL']."""
    fees_paid_target: Decimal
    """Total fees in target denomination (exchange + gas + protocol)."""
    pnl_layer: RewardPnLLayer | None = None


class DeferredTokenLeg(BaseModel):
    token_symbol: str
    amount: Decimal
    reason: Literal["slippage_cap_exceeded", "no_market", "below_dust_threshold", "venue_offline"]


class DustRouterResult(BaseModel):
    """Output of one runner-side ``DustRouterAdapter.maybe_realise`` invocation.

    Cross-repo contract type — strategy-service ``V2EngineOrchestrator``
    calls into the runner-injected adapter, the adapter routes the
    basket via ``execution_service.algo_library.dust_conversion_router.convert_dust``,
    builds per-token ``RewardAttributionRow`` rows + wraps the
    ``ConvertDustInstruction`` in a ``StrategyInstructionEnvelope``, and
    returns this aggregate.

    Lives in UAC (not in the consumer or producer service) because both
    sides need to refer to it: strategy-service's
    ``DustRouterAdapter`` Protocol declares this as the return type, and
    execution-service's concrete ``DustRouterRunner`` constructs it.

    Fields:
      instructions: zero or more ``StrategyInstructionEnvelope`` wrapping
        ``ConvertDustInstruction`` legs the orchestrator forwards to the
        execution path. Empty when no tokens were converted (all held or
        deferred).
      realised_target_amount: total target-denomination amount realised
        across all converted tokens (excludes held + deferred). Forwarded
        to ``LeveragedLegController.compute_drift(reward_inflow_target=...)``
        on the next leg-controller fire so the LST leg's equity bumps
        before cash-sweep preserves target_net_delta.
      leg_id_hint: which ``LegPortfolioState.legs[*].leg_id`` should
        receive the equity bump. ``None`` for strategies without
        leg-controller wiring.
      reward_attribution_rows: per-token detail rows for
        strategy-service/pnl. One row per converted token tagged with
        the matching ``RewardPnLLayer`` from
        ``LST_REWARD_STREAMS``.
    """

    model_config = ConfigDict(arbitrary_types_allowed=True)

    instructions: list[StrategyInstructionEnvelope] = Field(default_factory=list)
    """``ConvertDustInstruction`` envelopes (now a ``StrategyInstructionEnvelope``
    subclass with ``action=CONVERT_DUST``) the orchestrator forwards to the
    execution path. Empty when no tokens were converted (all held or deferred)."""

    realised_target_amount: Decimal = Decimal("0")
    leg_id_hint: str | None = None
    reward_attribution_rows: list[object] = Field(default_factory=list)
    """``RewardAttributionRow`` objects — typed as ``object`` to avoid the
    circular import with ``internal.domain.strategy_service.pnl`` (that
    module already imports ``RewardPnLLayer`` from this package).
    Consumers (strategy-service/pnl ``attribute_reward_realisation_from_rows``)
    cast at the import boundary."""


class LstSeasonalRewardRow(BaseModel):
    """One row of the ``lst_seasonal_rewards`` features-onchain parquet.

    Output of the features-onchain ``lst_seasonal_rewards`` collector which
    scans Transfer events with ``from`` matching a registered distributor in
    ``LST_REWARD_STREAMS``. Each row represents one realised reward
    distribution: a token transfer from a distributor to a wallet that
    holds the corresponding LST.

    Pure transform contract — same row shape in batch (replay historical
    Transfer events from MTDS / GCS) and live (subscribe to RPC event filter
    and stream) modes per the workspace Batch=Live invariant.

    Downstream consumers:
      - strategy-service: archetypes holding restaking-eligible LSTs
        consume these rows as ``lst_seasonal_rewards_<token>_amount``
        features and emit ``ConvertDustInstruction`` once-per-epoch.
      - strategy-service/pnl: tags rows with the source ``RewardPnLLayer``
        for the CARRY decomposition.
    """

    block_number: int
    block_timestamp_utc: datetime
    tx_hash: str
    chain: str
    """Chain the distribution happened on (ETHEREUM / BASE / ARBITRUM /
    SOLANA / etc.)."""

    lst_symbol: str
    """Which LST this stream feeds (weETH / pufETH / ETHx / etc.)."""

    issuer: str
    """Issuer label from the matching ``LSTRewardStream`` (ether.fi /
    puffer / ankr / stader / karak / eigenlayer / jito / marinade)."""

    layer: RewardPnLLayer
    """Source layer for PnL attribution. CARRY_AVS_CONTINUOUS or
    CARRY_ISSUER_SEASONAL — CARRY_BASE doesn't emit Transfer events."""

    reward_token_symbol: str
    """Token paid (ETHFI / EIGEN / PUFFER / ANKR / SD / KARAK / KING / etc.)."""

    reward_token_address: str
    """ERC20 contract address of the reward token."""

    distributor_address: str
    """The ``from`` address of the Transfer event — the registered
    distributor contract from ``LSTRewardStream.distributor_address``."""

    distributor_kind: Literal["merkle", "direct_transfer", "claim_function", "exchange_rate"]
    """How rewards were paid out — propagated from the matching stream."""

    recipient_address: str
    """The ``to`` address of the Transfer event — the wallet that received
    the rewards. Strategy-service joins on this to attribute rewards to
    the right strategy_instance_id (one wallet per strategy instance)."""

    amount_raw: Decimal
    """Raw ERC20 ``value`` field from the Transfer event (uint256, in the
    token's native decimal units)."""

    amount_decimal: Decimal
    """Decimals-adjusted amount: ``amount_raw / 10**reward_token_decimals``.
    Used directly by ``DustToken.amount`` when emitting ``ConvertDustInstruction``."""


# ---------------------------------------------------------------------------
# Per-LST reward stream registry — the v0 mapping. Calibration of
# expected_share_pct comes from historical data; this is the structural
# claim about which streams exist, used by features-onchain to know which
# distributors to scan and by pnl-attribution to tag layers.
# ---------------------------------------------------------------------------

LST_REWARD_STREAMS: dict[str, list[LSTRewardStream]] = {
    # ─── ETH-side restaking-eligible LSTs ─────────────────────────────
    "weETH": [
        LSTRewardStream(
            lst_symbol="weETH",
            issuer="ether.fi",
            layer=RewardPnLLayer.CARRY_BASE,
            reward_token_symbol="ETH",
            distributor_kind="exchange_rate",
            cadence="continuous",
        ),
        LSTRewardStream(
            lst_symbol="weETH",
            issuer="eigenlayer",
            layer=RewardPnLLayer.CARRY_AVS_CONTINUOUS,
            reward_token_symbol="EIGEN",
            distributor_address="0x4665BAa5C19aaC6e3F1FcC1c20bE25d3a2c5D89B",
            distributor_chain="ETHEREUM",
            distributor_kind="claim_function",
            cadence="continuous",
        ),
        LSTRewardStream(
            lst_symbol="weETH",
            issuer="ether.fi",
            layer=RewardPnLLayer.CARRY_ISSUER_SEASONAL,
            reward_token_symbol="ETHFI",
            distributor_address="0x6Db24Ee656843E3fE03eb8762a54D86186bA6B64",
            distributor_chain="ETHEREUM",
            distributor_kind="merkle",
            cadence="quarterly",
        ),
    ],
    "pufETH": [
        LSTRewardStream(
            lst_symbol="pufETH",
            issuer="puffer",
            layer=RewardPnLLayer.CARRY_BASE,
            reward_token_symbol="ETH",
            distributor_kind="exchange_rate",
            cadence="continuous",
        ),
        LSTRewardStream(
            lst_symbol="pufETH",
            issuer="eigenlayer",
            layer=RewardPnLLayer.CARRY_AVS_CONTINUOUS,
            reward_token_symbol="EIGEN",
            distributor_kind="claim_function",
            cadence="continuous",
        ),
        LSTRewardStream(
            lst_symbol="pufETH",
            issuer="puffer",
            layer=RewardPnLLayer.CARRY_ISSUER_SEASONAL,
            reward_token_symbol="PUFFER",
            distributor_kind="merkle",
            cadence="ad_hoc",
        ),
        LSTRewardStream(
            lst_symbol="pufETH",
            issuer="puffer",
            layer=RewardPnLLayer.CARRY_ISSUER_SEASONAL,
            reward_token_symbol="CARROT",
            distributor_kind="merkle",
            cadence="ad_hoc",
        ),
    ],
    "ankrETH": [
        LSTRewardStream(
            lst_symbol="ankrETH",
            issuer="ankr",
            layer=RewardPnLLayer.CARRY_BASE,
            reward_token_symbol="ETH",
            distributor_kind="exchange_rate",
            cadence="continuous",
        ),
        LSTRewardStream(
            lst_symbol="ankrETH",
            issuer="ankr",
            layer=RewardPnLLayer.CARRY_ISSUER_SEASONAL,
            reward_token_symbol="ANKR",
            distributor_kind="direct_transfer",
            cadence="monthly",
        ),
    ],
    "ETHx": [
        LSTRewardStream(
            lst_symbol="ETHx",
            issuer="stader",
            layer=RewardPnLLayer.CARRY_BASE,
            reward_token_symbol="ETH",
            distributor_kind="exchange_rate",
            cadence="continuous",
        ),
        LSTRewardStream(
            lst_symbol="ETHx",
            issuer="eigenlayer",
            layer=RewardPnLLayer.CARRY_AVS_CONTINUOUS,
            reward_token_symbol="EIGEN",
            distributor_kind="claim_function",
            cadence="continuous",
        ),
        LSTRewardStream(
            lst_symbol="ETHx",
            issuer="stader",
            layer=RewardPnLLayer.CARRY_ISSUER_SEASONAL,
            reward_token_symbol="SD",
            distributor_kind="direct_transfer",
            cadence="monthly",
        ),
    ],
    # ─── Solana-side restaking equivalents (same architecture) ────────
    "jitoSOL": [
        LSTRewardStream(
            lst_symbol="jitoSOL",
            issuer="jito",
            layer=RewardPnLLayer.CARRY_BASE,
            reward_token_symbol="SOL",
            distributor_kind="exchange_rate",
            cadence="continuous",
        ),
        LSTRewardStream(
            lst_symbol="jitoSOL",
            issuer="jito",
            layer=RewardPnLLayer.CARRY_ISSUER_SEASONAL,
            reward_token_symbol="JTO",
            distributor_chain="SOLANA",
            distributor_kind="merkle",
            cadence="ad_hoc",
        ),
    ],
    "mSOL": [
        LSTRewardStream(
            lst_symbol="mSOL",
            issuer="marinade",
            layer=RewardPnLLayer.CARRY_BASE,
            reward_token_symbol="SOL",
            distributor_kind="exchange_rate",
            cadence="continuous",
        ),
        LSTRewardStream(
            lst_symbol="mSOL",
            issuer="marinade",
            layer=RewardPnLLayer.CARRY_ISSUER_SEASONAL,
            reward_token_symbol="MNDE",
            distributor_chain="SOLANA",
            distributor_kind="direct_transfer",
            cadence="monthly",
        ),
    ],
}


# ---------------------------------------------------------------------------
# Per-reward-token economics registry — feeds the dust-conversion router's
# market-data lookups. v0 entries are skeleton; primary_dex_pools and
# cex_listings get populated as instruments-service registers each token's
# market venue presence.
# ---------------------------------------------------------------------------

REWARD_TOKEN_ECONOMICS: dict[str, RewardTokenEconomics] = {
    "ETHFI": RewardTokenEconomics(
        token_symbol="ETHFI",
        token_address="0xfe0c30065B384F05761f15d0CC899D4F9F9Cc0eB",
        chain="ETHEREUM",
        cex_listings=["BINANCE", "COINBASE-SPOT", "BYBIT", "OKX"],
    ),
    "EIGEN": RewardTokenEconomics(
        token_symbol="EIGEN",
        token_address="0xec53bf9167f50cdeb3ae105f56099aaab9061f83",
        chain="ETHEREUM",
        cex_listings=["BINANCE", "COINBASE-SPOT", "BYBIT"],
        expected_vesting_months=48,
    ),
    "PUFFER": RewardTokenEconomics(
        token_symbol="PUFFER",
        token_address="0x4d1c297d39C5c1277964D0E3f8Aa901493664530",
        chain="ETHEREUM",
        cex_listings=["BINANCE", "BYBIT"],
    ),
    "ANKR": RewardTokenEconomics(
        token_symbol="ANKR",
        token_address="0x8290333ceF9e6D528dD5618Fb97a76f268f3EDD4",
        chain="ETHEREUM",
        cex_listings=["BINANCE", "COINBASE-SPOT", "OKX"],
    ),
    "SD": RewardTokenEconomics(
        token_symbol="SD",
        token_address="0x30D20208d987713f46DFD34EF128Bb16C404D10f",
        chain="ETHEREUM",
        cex_listings=["BINANCE", "BYBIT"],
    ),
    "KARAK": RewardTokenEconomics(
        token_symbol="KARAK",
        token_address="",
        chain="ETHEREUM",
        is_pre_tge_points=True,
    ),
    "CARROT": RewardTokenEconomics(
        token_symbol="CARROT",
        token_address="",
        chain="ETHEREUM",
        is_pre_tge_points=True,
    ),
    "KING": RewardTokenEconomics(
        token_symbol="KING",
        token_address="",
        chain="ETHEREUM",
        is_pre_tge_points=True,
    ),
    "MILES": RewardTokenEconomics(
        token_symbol="MILES",
        token_address="",
        chain="ETHEREUM",
        is_pre_tge_points=True,
    ),
    "ARPA": RewardTokenEconomics(
        token_symbol="ARPA",
        token_address="0xBA50933C268F567BDC86E1aC131BE072C6B0B71a",
        chain="ETHEREUM",
        cex_listings=["BINANCE", "OKX"],
    ),
    "JTO": RewardTokenEconomics(
        token_symbol="JTO",
        token_address="jtojtomepa8beP8AuQc6eXt5FriJwfFMwQx2v2f9mCL",
        chain="SOLANA",
        cex_listings=["BINANCE", "COINBASE-SPOT", "BYBIT"],
    ),
    "MNDE": RewardTokenEconomics(
        token_symbol="MNDE",
        token_address="MNDEFzGvMt87ueuHvVU9VcTqsAP5b3fTGPsHuuPA5ey",
        chain="SOLANA",
        cex_listings=["GATE"],
    ),
}


# ---------------------------------------------------------------------------
# Joined lookup helper — eliminates the per-token "unknown" + CARRY_BASE
# fallbacks that consumers fall back to when they only have the token symbol
# in hand.
#
# Both LST_REWARD_STREAMS and REWARD_TOKEN_ECONOMICS are needed to resolve
# (token_symbol) -> (layer, issuer, distributor_kind) for the dust-router's
# RewardAttributionRow construction, and (token_address) -> (issuer,
# lst_symbol, decimals) for the chain-event scanners' Transfer-event
# projection. Pre-resolver, both consumers hardcoded fallbacks; this
# class joins the two registries once and exposes total lookups.
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TokenStreamMetadata:
    """Joined view returned by ``RewardStreamRegistry.lookup_by_token_symbol``."""

    token_symbol: str
    token_address: str
    chain: str
    decimals: int
    is_pre_tge_points: bool
    layer: RewardPnLLayer
    issuer: str
    lst_symbol: str
    distributor_address: str | None
    distributor_chain: str | None
    distributor_kind: Literal["merkle", "direct_transfer", "claim_function", "exchange_rate"]


@dataclass(frozen=True)
class TokenAddressMetadata:
    """Joined view returned by ``RewardStreamRegistry.lookup_by_token_address`` —
    subset the chain-event scanners need."""

    token_symbol: str
    issuer: str
    lst_symbol: str
    decimals: int


class RewardStreamRegistry:
    """Joined lookup over ``LST_REWARD_STREAMS`` + ``REWARD_TOKEN_ECONOMICS``.

    Build with ``RewardStreamRegistry.default()`` to use the as-shipped UAC
    registries; build with ``RewardStreamRegistry.from_streams(...)`` to
    inject test fixtures. All lookups are total — they never raise on
    missing keys, they return ``None`` so callers can decide on the
    sentinel value (preserves shard-level isolation).
    """

    def __init__(
        self,
        streams_by_lst: dict[str, list[LSTRewardStream]],
        token_economics: dict[str, RewardTokenEconomics],
    ) -> None:
        self._streams_by_lst = streams_by_lst
        self._token_economics = token_economics
        self._by_token_symbol: dict[str, TokenStreamMetadata] = {}
        self._by_token_address: dict[str, TokenAddressMetadata] = {}
        self._build_indexes()

    @classmethod
    def default(cls) -> RewardStreamRegistry:
        return cls(
            streams_by_lst=LST_REWARD_STREAMS,
            token_economics=REWARD_TOKEN_ECONOMICS,
        )

    @classmethod
    def from_streams(
        cls,
        streams_by_lst: dict[str, list[LSTRewardStream]],
        token_economics: dict[str, RewardTokenEconomics] | None = None,
    ) -> RewardStreamRegistry:
        return cls(
            streams_by_lst=streams_by_lst,
            token_economics=token_economics if token_economics is not None else {},
        )

    def _build_indexes(self) -> None:
        """Walk both registries once and populate the joined indexes."""
        best_stream = self._select_best_stream_per_token()
        for token_symbol, (lst_symbol, stream) in best_stream.items():
            self._register_token(token_symbol=token_symbol, lst_symbol=lst_symbol, stream=stream)

    def _select_best_stream_per_token(self) -> dict[str, tuple[str, LSTRewardStream]]:
        """Resolve duplicates: prefer non-CARRY_BASE; ties go to lexicographic
        lst_symbol. Base streams have no distributor (exchange_rate)."""
        best_stream: dict[str, tuple[str, LSTRewardStream]] = {}
        for lst_symbol in sorted(self._streams_by_lst.keys()):
            for stream in self._streams_by_lst[lst_symbol]:
                token = stream.reward_token_symbol
                if stream.layer is RewardPnLLayer.CARRY_BASE:
                    if token not in best_stream:
                        best_stream[token] = (lst_symbol, stream)
                    continue
                existing = best_stream.get(token)
                if existing is None or existing[1].layer is RewardPnLLayer.CARRY_BASE:
                    best_stream[token] = (lst_symbol, stream)
        return best_stream

    def _register_token(
        self,
        *,
        token_symbol: str,
        lst_symbol: str,
        stream: LSTRewardStream,
    ) -> None:
        """Project one (token, lst, stream) tuple into the two indexes."""
        econ = self._token_economics.get(token_symbol)
        if econ is None:
            token_address = ""
            chain = stream.distributor_chain or ""
            decimals = 18
            is_pre_tge_points = False
        else:
            token_address = econ.token_address
            chain = econ.chain
            decimals = econ.decimals
            is_pre_tge_points = econ.is_pre_tge_points
        self._by_token_symbol[token_symbol] = TokenStreamMetadata(
            token_symbol=token_symbol,
            token_address=token_address,
            chain=chain,
            decimals=decimals,
            is_pre_tge_points=is_pre_tge_points,
            layer=stream.layer,
            issuer=stream.issuer,
            lst_symbol=lst_symbol,
            distributor_address=stream.distributor_address,
            distributor_chain=stream.distributor_chain,
            distributor_kind=stream.distributor_kind,
        )
        if token_address:
            self._by_token_address[token_address.lower()] = TokenAddressMetadata(
                token_symbol=token_symbol,
                issuer=stream.issuer,
                lst_symbol=lst_symbol,
                decimals=decimals,
            )

    def lookup_by_token_symbol(self, token_symbol: str) -> TokenStreamMetadata | None:
        """Joined view by token symbol — used by dust-router runner for RAR rows."""
        return self._by_token_symbol.get(token_symbol)

    def lookup_by_token_address(self, token_address: str) -> TokenAddressMetadata | None:
        """Joined view by token address — used by chain-event scanners."""
        return self._by_token_address.get(token_address.lower())

    @property
    def all_token_symbols(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_token_symbol.keys()))

    @property
    def all_token_addresses(self) -> tuple[str, ...]:
        return tuple(sorted(self._by_token_address.keys()))


__all__ = [
    "LST_REWARD_STREAMS",
    "REWARD_TOKEN_ECONOMICS",
    "ConvertDustInstruction",
    "ConvertedTokenLeg",
    "DeferredTokenLeg",
    "DustConversionResult",
    "DustRouterResult",
    "DustToken",
    "LSTRewardStream",
    "LstSeasonalRewardRow",
    "RewardPnLLayer",
    "RewardStreamRegistry",
    "RewardTokenEconomics",
    "TokenAddressMetadata",
    "TokenStreamMetadata",
]
