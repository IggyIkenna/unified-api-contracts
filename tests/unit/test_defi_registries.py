"""Tests for DeFi registry modules — token wrapping, venue collateral, rewards, major assets, share class,
reward position, client config, E-Mode, max underlying moves."""

from __future__ import annotations

from decimal import Decimal

from unified_api_contracts.canonical.crosscutting.share_class import (
    SHARE_CLASS_BASE_ASSETS,
    ShareClass,
)
from unified_api_contracts.internal.domain.strategy_service.client_config import (
    ClientStrategyOverride,
)
from unified_api_contracts.internal.positions.reward_position import RewardPosition
from unified_api_contracts.registry.defi_major_assets import (
    DEFI_MAJOR_ASSET_ADDRESSES,
    DEFI_MAJOR_ASSET_SYMBOLS,
)
from unified_api_contracts.registry.defi_reserve_params import (
    AAVE_V3_EMODE_CATEGORIES,
    AAVE_V3_ETHEREUM_RESERVES,
    _extract_asset_symbol,
    compute_health_factor,
    get_emode_category,
    get_emode_params,
    get_reserve_params,
)
from unified_api_contracts.registry.max_underlying_moves import (
    MAX_UNDERLYING_MOVES,
    compute_max_leverage_from_outright_move,
    compute_max_leverage_from_spread_move,
    get_max_move,
)
from unified_api_contracts.registry.reward_schedules import REWARD_SCHEDULES
from unified_api_contracts.registry.token_wrapping import (
    get_balance_tracking_form,
    get_lst_base_asset,
    get_protocol_token,
    get_unwrapped_form,
    get_wrapped_form,
    is_lst,
    lst_adjusted_value,
    needs_unwrapping,
    needs_wrapping,
)
from unified_api_contracts.registry.venue_collateral import (
    get_accepted_collateral,
    get_collateral_haircut,
    venue_accepts_collateral,
)

# ---------------------------------------------------------------------------
# Token Wrapping
# ---------------------------------------------------------------------------


class TestTokenWrapping:
    """Token wrapping rules for DeFi protocols."""

    def test_eth_needs_wrapping_for_aavev3(self) -> None:
        wrap, target = needs_wrapping("ETH", "AAVEV3")
        assert wrap is True
        assert target == "WETH"

    def test_eth_needs_wrapping_for_uniswapv3(self) -> None:
        wrap, target = needs_wrapping("ETH", "UNISWAPV3")
        assert wrap is True
        assert target == "WETH"

    def test_eeth_needs_wrapping_for_aavev3(self) -> None:
        wrap, target = needs_wrapping("eETH", "AAVEV3")
        assert wrap is True
        assert target == "weETH"

    def test_steth_needs_wrapping_for_aavev3(self) -> None:
        wrap, target = needs_wrapping("stETH", "AAVEV3")
        assert wrap is True
        assert target == "wstETH"

    def test_weth_does_not_need_wrapping_for_aavev3(self) -> None:
        wrap, target = needs_wrapping("WETH", "AAVEV3")
        assert wrap is False
        assert target is None

    def test_usdc_does_not_need_wrapping_for_aavev3(self) -> None:
        wrap, target = needs_wrapping("USDC", "AAVEV3")
        assert wrap is False
        assert target is None

    def test_eth_does_not_need_wrapping_for_etherfi(self) -> None:
        wrap, target = needs_wrapping("ETH", "ETHERFI")
        assert wrap is False
        assert target is None

    def test_get_protocol_token_returns_correct_wrapped_form(self) -> None:
        assert get_protocol_token("ETH", "AAVEV3") == "WETH"
        assert get_protocol_token("eETH", "AAVEV3") == "weETH"
        assert get_protocol_token("stETH", "AAVEV3") == "wstETH"
        assert get_protocol_token("ETH", "UNISWAPV3") == "WETH"

    def test_unknown_protocol_returns_token_unchanged(self) -> None:
        assert get_protocol_token("ETH", "UNKNOWN_PROTOCOL") == "ETH"
        assert get_protocol_token("USDC", "NONEXISTENT") == "USDC"


# ---------------------------------------------------------------------------
# Token Unwrapping
# ---------------------------------------------------------------------------


class TestTokenUnwrapping:
    """Token unwrapping rules for DeFi exit flows."""

    def test_weth_can_be_unwrapped_to_eth(self) -> None:
        can_unwrap, unwrapped = needs_unwrapping("WETH")
        assert can_unwrap is True
        assert unwrapped == "ETH"

    def test_weeth_can_be_unwrapped_to_eeth(self) -> None:
        can_unwrap, unwrapped = needs_unwrapping("weETH")
        assert can_unwrap is True
        assert unwrapped == "eETH"

    def test_wsteth_can_be_unwrapped_to_steth(self) -> None:
        can_unwrap, unwrapped = needs_unwrapping("wstETH")
        assert can_unwrap is True
        assert unwrapped == "stETH"

    def test_usdc_cannot_be_unwrapped(self) -> None:
        can_unwrap, unwrapped = needs_unwrapping("USDC")
        assert can_unwrap is False
        assert unwrapped is None

    def test_eth_cannot_be_unwrapped(self) -> None:
        """ETH is already unwrapped -- it is the unwrapped form of WETH."""
        can_unwrap, unwrapped = needs_unwrapping("ETH")
        assert can_unwrap is False
        assert unwrapped is None

    def test_get_wrapped_form_eth_to_weth(self) -> None:
        assert get_wrapped_form("ETH") == "WETH"

    def test_get_wrapped_form_eeth_to_weeth(self) -> None:
        assert get_wrapped_form("eETH") == "weETH"

    def test_get_unwrapped_form_weth_to_eth(self) -> None:
        assert get_unwrapped_form("WETH") == "ETH"

    def test_get_unwrapped_form_weeth_to_eeth(self) -> None:
        assert get_unwrapped_form("weETH") == "eETH"

    def test_get_wrapped_form_unknown_returns_itself(self) -> None:
        assert get_wrapped_form("SHIB") == "SHIB"

    def test_get_unwrapped_form_unknown_returns_itself(self) -> None:
        assert get_unwrapped_form("SHIB") == "SHIB"


# ---------------------------------------------------------------------------
# LST Helpers
# ---------------------------------------------------------------------------


class TestLSTHelpers:
    """Liquid staking token detection and price helpers."""

    def test_is_lst_weeth(self) -> None:
        assert is_lst("weETH") is True

    def test_is_lst_wsteth(self) -> None:
        assert is_lst("wstETH") is True

    def test_is_lst_weth_false(self) -> None:
        """WETH is wrapped ETH, NOT a liquid staking token."""
        assert is_lst("WETH") is False

    def test_is_lst_eth_false(self) -> None:
        assert is_lst("ETH") is False

    def test_is_lst_usdc_false(self) -> None:
        assert is_lst("USDC") is False

    def test_get_lst_base_asset_weeth(self) -> None:
        assert get_lst_base_asset("weETH") == "ETH"

    def test_get_lst_base_asset_wsteth(self) -> None:
        assert get_lst_base_asset("wstETH") == "ETH"

    def test_get_lst_base_asset_weth_none(self) -> None:
        assert get_lst_base_asset("WETH") is None

    def test_lst_adjusted_value_weeth(self) -> None:
        """10 weETH at $3165/weETH with ETH@$3000 => ($31,650, 10.55 ETH-eq)."""
        usd_val, base_eq = lst_adjusted_value(Decimal("10"), Decimal("3165"), Decimal("3000"), "weETH")
        assert usd_val == Decimal("31650")
        assert abs(base_eq - Decimal("10.55")) < Decimal("0.001")

    def test_lst_adjusted_value_weth_not_lst(self) -> None:
        """10 WETH at $3000 with ETH@$3000 => ($30,000, 10.0) -- WETH is not an LST."""
        usd_val, base_eq = lst_adjusted_value(Decimal("10"), Decimal("3000"), Decimal("3000"), "WETH")
        assert usd_val == Decimal("30000")
        assert base_eq == Decimal("10")

    def test_lst_adjusted_value_usdc_not_lst(self) -> None:
        """100 USDC at $1 with ETH@$3000 => ($100, 100) -- USDC is not an LST."""
        usd_val, base_eq = lst_adjusted_value(Decimal("100"), Decimal("1"), Decimal("3000"), "USDC")
        assert usd_val == Decimal("100")
        assert base_eq == Decimal("100")


# ---------------------------------------------------------------------------
# Balance Tracking Form
# ---------------------------------------------------------------------------


class TestBalanceTrackingForm:
    """Balance tracking form for token wrapping rules."""

    def test_eth_tracked_as_wrapped(self) -> None:
        assert get_balance_tracking_form("ETH") == "wrapped"

    def test_eeth_tracked_as_wrapped(self) -> None:
        assert get_balance_tracking_form("eETH") == "wrapped"

    def test_steth_tracked_as_wrapped(self) -> None:
        assert get_balance_tracking_form("stETH") == "wrapped"

    def test_weth_tracked_as_wrapped(self) -> None:
        assert get_balance_tracking_form("WETH") == "wrapped"

    def test_weeth_tracked_as_wrapped(self) -> None:
        assert get_balance_tracking_form("weETH") == "wrapped"

    def test_usdc_defaults_to_wrapped(self) -> None:
        """USDC has no wrapping rule -- defaults to 'wrapped'."""
        assert get_balance_tracking_form("USDC") == "wrapped"


# ---------------------------------------------------------------------------
# Venue Collateral
# ---------------------------------------------------------------------------


class TestVenueCollateral:
    """Venue collateral acceptance matrix tests."""

    def test_hyperliquid_accepts_usdc(self) -> None:
        assert venue_accepts_collateral("HYPERLIQUID", "USDC") is True

    def test_hyperliquid_rejects_eth(self) -> None:
        assert venue_accepts_collateral("HYPERLIQUID", "ETH") is False

    def test_hyperliquid_rejects_weth(self) -> None:
        assert venue_accepts_collateral("HYPERLIQUID", "WETH") is False

    def test_hyperliquid_rejects_weeth(self) -> None:
        assert venue_accepts_collateral("HYPERLIQUID", "weETH") is False

    def test_aavev3_ethereum_accepts_weth(self) -> None:
        assert venue_accepts_collateral("AAVEV3-ETHEREUM", "WETH") is True

    def test_aavev3_ethereum_accepts_weeth(self) -> None:
        assert venue_accepts_collateral("AAVEV3-ETHEREUM", "weETH") is True

    def test_aavev3_ethereum_accepts_wsteth(self) -> None:
        assert venue_accepts_collateral("AAVEV3-ETHEREUM", "wstETH") is True

    def test_aavev3_ethereum_accepts_usdc(self) -> None:
        assert venue_accepts_collateral("AAVEV3-ETHEREUM", "USDC") is True

    def test_aavev3_ethereum_accepts_usdt(self) -> None:
        assert venue_accepts_collateral("AAVEV3-ETHEREUM", "USDT") is True

    def test_aavev3_ethereum_accepts_wbtc(self) -> None:
        assert venue_accepts_collateral("AAVEV3-ETHEREUM", "WBTC") is True

    def test_aavev3_ethereum_rejects_eth(self) -> None:
        """ETH must be wrapped to WETH before use on Aave V3."""
        assert venue_accepts_collateral("AAVEV3-ETHEREUM", "ETH") is False

    def test_binance_accepts_usdt(self) -> None:
        assert venue_accepts_collateral("BINANCE", "USDT") is True

    def test_binance_accepts_btc(self) -> None:
        assert venue_accepts_collateral("BINANCE", "BTC") is True

    def test_binance_accepts_eth(self) -> None:
        assert venue_accepts_collateral("BINANCE", "ETH") is True

    def test_okx_accepts_usdt(self) -> None:
        assert venue_accepts_collateral("OKX", "USDT") is True

    def test_okx_accepts_btc(self) -> None:
        assert venue_accepts_collateral("OKX", "BTC") is True

    def test_okx_accepts_eth(self) -> None:
        assert venue_accepts_collateral("OKX", "ETH") is True

    def test_haircut_weeth_on_aave(self) -> None:
        haircut = get_collateral_haircut("AAVEV3-ETHEREUM", "weETH")
        assert haircut == Decimal("0.275")

    def test_haircut_weth_on_aave(self) -> None:
        haircut = get_collateral_haircut("AAVEV3-ETHEREUM", "WETH")
        assert haircut == Decimal("0.175")

    def test_haircut_unknown_token_returns_none(self) -> None:
        haircut = get_collateral_haircut("AAVEV3-ETHEREUM", "SHIB")
        assert haircut is None

    def test_accepted_collateral_hyperliquid(self) -> None:
        accepted = get_accepted_collateral("HYPERLIQUID")
        assert accepted == ["USDC"]

    def test_accepted_collateral_binance(self) -> None:
        accepted = get_accepted_collateral("BINANCE")
        assert set(accepted) == {"USDT", "BTC", "ETH"}

    def test_accepted_perp_collateral_filters_to_perp_kinds(self) -> None:
        from unified_api_contracts.registry import accepted_perp_collateral

        assert accepted_perp_collateral("HYPERLIQUID") == ["USDC"]
        assert set(accepted_perp_collateral("BINANCE")) == {"USDT", "BTC", "ETH"}

    def test_accepted_perp_collateral_excludes_lending(self) -> None:
        from unified_api_contracts.registry import accepted_perp_collateral

        assert accepted_perp_collateral("AAVEV3-ETHEREUM") == []

    def test_accepted_perp_collateral_excludes_staking(self) -> None:
        from unified_api_contracts.registry import accepted_perp_collateral

        assert accepted_perp_collateral("LIDO") == []
        assert accepted_perp_collateral("ETHERFI") == []

    def test_accepted_perp_collateral_unknown_venue(self) -> None:
        from unified_api_contracts.registry import accepted_perp_collateral

        assert accepted_perp_collateral("DOES_NOT_EXIST") == []

    def test_venue_kind_field_populated_on_every_row(self) -> None:
        from unified_api_contracts.registry.venue_collateral import VENUE_COLLATERAL_MATRIX

        for entry in VENUE_COLLATERAL_MATRIX:
            assert entry.venue_kind in {"PERP_CEX", "PERP_DEX", "LENDING", "STAKING"}, (
                f"row {entry.venue}/{entry.token} has invalid venue_kind={entry.venue_kind!r}"
            )


# ---------------------------------------------------------------------------
# Reward Schedules
# ---------------------------------------------------------------------------


class TestRewardSchedules:
    """Reward schedule registry tests."""

    def test_eigenlayer_entry_exists_with_weekly_frequency(self) -> None:
        eigen_entries = [e for e in REWARD_SCHEDULES if e.protocol == "EIGENLAYER"]
        assert len(eigen_entries) == 1
        assert eigen_entries[0].frequency == "WEEKLY"

    def test_etherfi_entry_exists_with_quarterly_frequency(self) -> None:
        etherfi_entries = [e for e in REWARD_SCHEDULES if e.protocol == "ETHERFI"]
        assert len(etherfi_entries) == 1
        assert etherfi_entries[0].frequency == "QUARTERLY"

    def test_reward_schedule_entries_have_required_fields(self) -> None:
        for entry in REWARD_SCHEDULES:
            assert entry.protocol, "protocol must be non-empty"
            assert entry.reward_token, "token must be non-empty"
            assert entry.sell_venue, "sell_venue must be non-empty"
            assert entry.sell_pair, "sell_pair must be non-empty"
            assert entry.description, "description must be non-empty"


# ---------------------------------------------------------------------------
# DeFi Major Assets
# ---------------------------------------------------------------------------


class TestDefiMajorAssets:
    """DeFi major asset symbols and addresses."""

    def test_eigen_in_major_assets(self) -> None:
        assert "EIGEN" in DEFI_MAJOR_ASSET_SYMBOLS

    def test_ethfi_in_major_assets(self) -> None:
        assert "ETHFI" in DEFI_MAJOR_ASSET_SYMBOLS

    def test_core_tokens_in_major_assets(self) -> None:
        for token in ("ETH", "WETH", "USDC", "USDT"):
            assert token in DEFI_MAJOR_ASSET_SYMBOLS, f"{token} missing from DEFI_MAJOR_ASSET_SYMBOLS"

    def test_eigen_contract_address(self) -> None:
        assert DEFI_MAJOR_ASSET_ADDRESSES["EIGEN"] == "0xec53bF9167f50cDEB3Ae105f56099aaaB9061F83"

    def test_ethfi_contract_address(self) -> None:
        assert DEFI_MAJOR_ASSET_ADDRESSES["ETHFI"] == "0xFe0c30065B384F05761f15d0CC899D4F9F9Cc0eB"


# ---------------------------------------------------------------------------
# Share Class
# ---------------------------------------------------------------------------


class TestShareClass:
    """Share class enum and base asset mapping."""

    def test_share_class_has_usdt(self) -> None:
        assert ShareClass.USDT == "USDT"

    def test_share_class_has_eth(self) -> None:
        assert ShareClass.ETH == "ETH"

    def test_share_class_has_btc(self) -> None:
        assert ShareClass.BTC == "BTC"

    def test_share_class_base_assets_usdt(self) -> None:
        assert "USDT" in SHARE_CLASS_BASE_ASSETS["USDT"]
        assert "USDC" in SHARE_CLASS_BASE_ASSETS["USDT"]
        assert "DAI" in SHARE_CLASS_BASE_ASSETS["USDT"]

    def test_share_class_base_assets_eth(self) -> None:
        assert "ETH" in SHARE_CLASS_BASE_ASSETS["ETH"]
        assert "WETH" in SHARE_CLASS_BASE_ASSETS["ETH"]

    def test_share_class_base_assets_btc(self) -> None:
        assert "BTC" in SHARE_CLASS_BASE_ASSETS["BTC"]
        assert "WBTC" in SHARE_CLASS_BASE_ASSETS["BTC"]


# ---------------------------------------------------------------------------
# Reward Position
# ---------------------------------------------------------------------------


class TestRewardPosition:
    """Reward position model instantiation and defaults."""

    def test_instantiates_with_required_fields(self) -> None:
        pos = RewardPosition(protocol="EIGENLAYER", reward_token="EIGEN")
        assert pos.protocol == "EIGENLAYER"
        assert pos.reward_token == "EIGEN"

    def test_defaults_are_sensible(self) -> None:
        pos = RewardPosition(protocol="ETHERFI", reward_token="ETHFI")
        assert pos.accrued_amount == Decimal("0")
        assert pos.claimed_amount == Decimal("0")
        assert pos.sold_amount == Decimal("0")
        assert pos.accrued_value_usd == Decimal("0")
        assert pos.claimed_value_usd == Decimal("0")
        assert pos.last_claim_timestamp is None
        assert pos.next_expected_claim is None


# ---------------------------------------------------------------------------
# Client Config
# ---------------------------------------------------------------------------


class TestClientStrategyOverride:
    """Client strategy override configuration."""

    def test_instantiates_with_defaults(self) -> None:
        override = ClientStrategyOverride(client_id="c1", strategy_id="s1")
        assert override.client_id == "c1"
        assert override.strategy_id == "s1"
        assert override.multi_coin_rotation is True
        assert override.dynamic_venue_weighting is True
        assert override.strategy_rotation is False
        assert override.allowed_perp_venues is None
        assert override.allowed_spot_venues is None
        assert override.allowed_lending_venues is None
        assert override.fixed_basis_coin is None
        assert override.fixed_venue_weights is None
        assert override.max_leverage is None
        assert override.max_position_usd is None

    def test_venue_restrictions_filter(self) -> None:
        override = ClientStrategyOverride(
            client_id="c1",
            strategy_id="s1",
            allowed_perp_venues=["BINANCE", "OKX"],
        )
        candidate_venues = ["BINANCE", "OKX", "BYBIT", "DERIBIT"]
        filtered = [v for v in candidate_venues if v in override.allowed_perp_venues]  # type: ignore[operator]
        assert filtered == ["BINANCE", "OKX"]

    def test_fixed_coins_override(self) -> None:
        override = ClientStrategyOverride(
            client_id="c1",
            strategy_id="s1",
            fixed_basis_coin="ETH",
            multi_coin_rotation=False,
        )
        assert override.fixed_basis_coin == "ETH"
        assert override.multi_coin_rotation is False


# ---------------------------------------------------------------------------
# E-Mode Categories
# ---------------------------------------------------------------------------


class TestEModeCategories:
    """Aave V3 E-Mode: elevated LTV when collateral+debt in same category."""

    def test_eth_correlated_category_exists(self) -> None:
        eth_cat = next(c for c in AAVE_V3_EMODE_CATEGORIES if c.label == "ETH_CORRELATED")
        assert eth_cat.max_ltv == Decimal("0.93")
        assert eth_cat.liquidation_threshold == Decimal("0.95")
        assert "WETH" in eth_cat.assets
        assert "WEETH" in eth_cat.assets
        assert "WSTETH" in eth_cat.assets
        assert "CBETH" in eth_cat.assets

    def test_stablecoin_category_exists(self) -> None:
        stable_cat = next(c for c in AAVE_V3_EMODE_CATEGORIES if c.label == "STABLECOIN")
        assert stable_cat.max_ltv == Decimal("0.97")
        assert "USDC" in stable_cat.assets
        assert "USDT" in stable_cat.assets
        assert "DAI" in stable_cat.assets

    def test_get_emode_category_weth(self) -> None:
        cat = get_emode_category("WETH")
        assert cat is not None
        assert cat.label == "ETH_CORRELATED"

    def test_get_emode_category_weeth(self) -> None:
        cat = get_emode_category("WEETH")
        assert cat is not None
        assert cat.label == "ETH_CORRELATED"

    def test_get_emode_category_usdc(self) -> None:
        cat = get_emode_category("USDC")
        assert cat is not None
        assert cat.label == "STABLECOIN"

    def test_get_emode_category_unknown_returns_none(self) -> None:
        assert get_emode_category("LINK") is None
        assert get_emode_category("AAVE") is None

    def test_get_emode_category_case_insensitive(self) -> None:
        cat = get_emode_category("weeth")
        assert cat is not None
        assert cat.label == "ETH_CORRELATED"

    def test_emode_params_same_category_eth(self) -> None:
        """weETH collateral + WETH debt → ETH_CORRELATED E-Mode."""
        emode = get_emode_params("WEETH", "WETH")
        assert emode is not None
        assert emode.label == "ETH_CORRELATED"
        assert emode.max_ltv == Decimal("0.93")
        assert emode.liquidation_threshold == Decimal("0.95")

    def test_emode_params_wsteth_weth(self) -> None:
        """wstETH collateral + WETH debt → ETH_CORRELATED E-Mode."""
        emode = get_emode_params("WSTETH", "WETH")
        assert emode is not None
        assert emode.label == "ETH_CORRELATED"

    def test_emode_params_stablecoin_pair(self) -> None:
        """USDC collateral + USDT debt → STABLECOIN E-Mode."""
        emode = get_emode_params("USDC", "USDT")
        assert emode is not None
        assert emode.label == "STABLECOIN"

    def test_emode_params_cross_category_returns_none(self) -> None:
        """weETH collateral + USDC debt → no E-Mode (different categories)."""
        assert get_emode_params("WEETH", "USDC") is None

    def test_emode_params_unknown_asset_returns_none(self) -> None:
        assert get_emode_params("LINK", "WETH") is None
        assert get_emode_params("WEETH", "LINK") is None

    def test_emode_ltv_much_higher_than_standard(self) -> None:
        """E-Mode LTV (93%) must be significantly higher than standard (72.5% for weETH)."""
        standard = AAVE_V3_ETHEREUM_RESERVES["WEETH"]
        emode = get_emode_params("WEETH", "WETH")
        assert emode is not None
        assert emode.max_ltv > standard.max_ltv + Decimal("0.15")  # 93% vs 72.5%

    def test_emode_liquidation_bonus_lower(self) -> None:
        """E-Mode has lower liquidation bonus (1% vs 7.5%) — less penalty for same-category pairs."""
        standard = AAVE_V3_ETHEREUM_RESERVES["WEETH"]
        emode = get_emode_params("WEETH", "WETH")
        assert emode is not None
        assert emode.liquidation_bonus < standard.liquidation_bonus


class TestEModeHealthFactor:
    """Health factor computation with E-Mode parameters."""

    def test_health_factor_standard_mode(self) -> None:
        """Without E-Mode, weETH collateral uses standard 77.5% liq threshold."""
        collateral = [("AAVEV3-ETHEREUM:A_TOKEN:AWEETH@ETHEREUM", Decimal("10"), Decimal("3000"))]
        debt = [("AAVEV3-ETHEREUM:DEBT_TOKEN:DEBTWETH@ETHEREUM", Decimal("8"), Decimal("3000"))]
        hf, _ltv = compute_health_factor(collateral, debt)
        # HF = (10 * 3000 * 0.775) / (8 * 3000) = 23250 / 24000 ≈ 0.969
        assert hf < Decimal("1.0")  # Under-collateralized at standard params

    def test_health_factor_emode(self) -> None:
        """With E-Mode, weETH collateral uses elevated 95% liq threshold."""
        emode = get_emode_params("WEETH", "WETH")
        collateral = [("AAVEV3-ETHEREUM:A_TOKEN:AWEETH@ETHEREUM", Decimal("10"), Decimal("3000"))]
        debt = [("AAVEV3-ETHEREUM:DEBT_TOKEN:DEBTWETH@ETHEREUM", Decimal("8"), Decimal("3000"))]
        hf, _ltv = compute_health_factor(collateral, debt, emode_category=emode)
        # HF = (10 * 3000 * 0.95) / (8 * 3000) = 28500 / 24000 = 1.1875
        assert hf > Decimal("1.0")  # Safe with E-Mode!
        assert abs(hf - Decimal("1.1875")) < Decimal("0.001")

    def test_health_factor_emode_vs_standard_significant_difference(self) -> None:
        """E-Mode HF must be meaningfully higher than standard for same positions."""
        emode = get_emode_params("WEETH", "WETH")
        collateral = [("AAVEV3-ETHEREUM:A_TOKEN:AWEETH@ETHEREUM", Decimal("10"), Decimal("3000"))]
        debt = [("AAVEV3-ETHEREUM:DEBT_TOKEN:DEBTWETH@ETHEREUM", Decimal("7"), Decimal("3000"))]
        hf_standard, _ = compute_health_factor(collateral, debt)
        hf_emode, _ = compute_health_factor(collateral, debt, emode_category=emode)
        assert hf_emode > hf_standard + Decimal("0.2")  # E-Mode gives ~0.25 extra HF

    def test_health_factor_no_debt_returns_infinity(self) -> None:
        """Lending-only (no debt) → HF is Infinity (no liquidation risk), LTV is 0."""
        collateral = [("WETH", Decimal("10"), Decimal("3000"))]
        hf, ltv = compute_health_factor(collateral, [])
        assert hf == Decimal("Infinity")
        assert ltv == Decimal("0")


class TestReserveParams:
    """Aave V3 reserve parameter lookups."""

    def test_get_weeth_params(self) -> None:
        params = get_reserve_params("WEETH")
        assert params is not None
        assert params.max_ltv == Decimal("0.725")
        assert params.liquidation_threshold == Decimal("0.775")

    def test_get_weth_params(self) -> None:
        params = get_reserve_params("WETH")
        assert params is not None
        assert params.max_ltv == Decimal("0.825")

    def test_get_params_from_instrument_id(self) -> None:
        params = get_reserve_params("AAVEV3-ETHEREUM:A_TOKEN:AWEETH@ETHEREUM")
        assert params is not None
        assert params.max_ltv == Decimal("0.725")

    def test_get_params_from_debt_instrument_id(self) -> None:
        params = get_reserve_params("AAVEV3-ETHEREUM:DEBT_TOKEN:DEBTWETH@ETHEREUM")
        assert params is not None
        assert params.max_ltv == Decimal("0.825")  # WETH params

    def test_get_params_unknown_returns_none(self) -> None:
        assert get_reserve_params("FAKECOIN") is None


class TestExtractAssetSymbol:
    """_extract_asset_symbol handles both colon and underscore instrument formats."""

    def test_colon_atoken_format(self) -> None:
        assert _extract_asset_symbol("AAVEV3-ETHEREUM:A_TOKEN:AWEETH@ETHEREUM") == "WEETH"

    def test_colon_debt_format(self) -> None:
        assert _extract_asset_symbol("AAVEV3-ETHEREUM:DEBT_TOKEN:DEBTWETH@ETHEREUM") == "WETH"

    def test_underscore_atoken_format(self) -> None:
        assert _extract_asset_symbol("AAVE_V3_WEETH_A_TOKEN") == "WEETH"

    def test_underscore_debt_token_format(self) -> None:
        assert _extract_asset_symbol("AAVE_V3_WETH_DEBT_TOKEN") == "WETH"

    def test_plain_symbol(self) -> None:
        assert _extract_asset_symbol("WETH") == "WETH"

    def test_underscore_usdc_atoken(self) -> None:
        assert _extract_asset_symbol("AAVE_V3_USDC_A_TOKEN") == "USDC"

    def test_case_insensitive(self) -> None:
        assert _extract_asset_symbol("aave_v3_weeth_a_token") == "WEETH"


class TestDepegSafeLeverage:
    """Depeg tolerance → max safe leverage calculation (tested via formula)."""

    def test_standard_weeth_2pct_depeg(self) -> None:
        """Standard weETH: liq=0.775, depeg=2% → max_lev ≈ 3.16x."""
        liq = Decimal("0.775")
        depeg = Decimal("0.02")
        max_lev = liq / (1 - liq + depeg)
        assert abs(max_lev - Decimal("3.163")) < Decimal("0.01")

    def test_standard_weeth_3pct_depeg(self) -> None:
        """Standard weETH: liq=0.775, depeg=3% → max_lev ≈ 3.04x."""
        liq = Decimal("0.775")
        depeg = Decimal("0.03")
        max_lev = liq / (1 - liq + depeg)
        assert abs(max_lev - Decimal("3.039")) < Decimal("0.01")

    def test_emode_weeth_2pct_depeg(self) -> None:
        """E-Mode weETH: liq=0.95, depeg=2% → max_lev ≈ 13.57x (massively higher)."""
        liq = Decimal("0.95")
        depeg = Decimal("0.02")
        max_lev = liq / (1 - liq + depeg)
        assert max_lev > Decimal("13")
        assert max_lev < Decimal("14")

    def test_emode_weeth_3pct_depeg(self) -> None:
        """E-Mode weETH: liq=0.95, depeg=3% → max_lev ≈ 11.875x."""
        liq = Decimal("0.95")
        depeg = Decimal("0.03")
        max_lev = liq / (1 - liq + depeg)
        assert abs(max_lev - Decimal("11.875")) < Decimal("0.01")

    def test_depeg_tolerance_must_reduce_leverage(self) -> None:
        """Higher depeg tolerance → lower max leverage (more conservative)."""
        liq = Decimal("0.95")
        lev_2pct = liq / (1 - liq + Decimal("0.02"))
        lev_5pct = liq / (1 - liq + Decimal("0.05"))
        assert lev_2pct > lev_5pct


# ---------------------------------------------------------------------------
# Max Underlying Moves
# ---------------------------------------------------------------------------


class TestMaxUnderlyingMoves:
    """Dynamic leverage caps reverse-engineered from worst-case moves."""

    def test_eth_move_data_exists(self) -> None:
        move = get_max_move("ETH")
        assert move is not None
        assert move.max_outright_move == Decimal("0.30")
        assert move.max_spread_move == Decimal("0.03")

    def test_btc_move_data_exists(self) -> None:
        move = get_max_move("BTC")
        assert move is not None
        assert move.max_outright_move == Decimal("0.25")

    def test_sol_move_data_exists(self) -> None:
        move = get_max_move("SOL")
        assert move is not None
        assert move.max_outright_move == Decimal("0.40")

    def test_stablecoin_move_data(self) -> None:
        move = get_max_move("USDC")
        assert move is not None
        assert move.max_outright_move < Decimal("0.10")  # Stables much less volatile

    def test_unknown_currency_returns_none(self) -> None:
        assert get_max_move("DOGE") is None

    def test_case_insensitive(self) -> None:
        assert get_max_move("eth") is not None

    def test_outright_leverage_eth(self) -> None:
        """ETH 30% crash → max leverage ~3.17x (with 5% maintenance margin)."""
        lev = compute_max_leverage_from_outright_move("ETH")
        # (1 - 0.05) / 0.30 = 0.95 / 0.30 ≈ 3.17
        assert lev > Decimal("3.0")
        assert lev < Decimal("3.5")

    def test_outright_leverage_btc(self) -> None:
        """BTC 25% crash → max leverage ~3.8x."""
        lev = compute_max_leverage_from_outright_move("BTC")
        assert lev > Decimal("3.5")
        assert lev < Decimal("4.0")

    def test_outright_leverage_sol(self) -> None:
        """SOL 40% crash → max leverage ~2.375x (most conservative)."""
        lev = compute_max_leverage_from_outright_move("SOL")
        assert lev > Decimal("2.0")
        assert lev < Decimal("2.5")

    def test_outright_leverage_unknown_returns_1(self) -> None:
        assert compute_max_leverage_from_outright_move("DOGE") == Decimal("1")

    def test_spread_leverage_eth_emode(self) -> None:
        """ETH 3% spread + E-Mode 95% liq → ~11.875x."""
        lev = compute_max_leverage_from_spread_move("ETH", Decimal("0.95"))
        assert abs(lev - Decimal("11.875")) < Decimal("0.01")

    def test_spread_leverage_eth_standard(self) -> None:
        """ETH 3% spread + standard 77.5% liq → ~3.04x."""
        lev = compute_max_leverage_from_spread_move("ETH", Decimal("0.775"))
        assert abs(lev - Decimal("3.039")) < Decimal("0.02")

    def test_spread_leverage_sol(self) -> None:
        """SOL 5% spread + E-Mode-like 95% → 9.5x."""
        lev = compute_max_leverage_from_spread_move("SOL", Decimal("0.95"))
        assert abs(lev - Decimal("9.5")) < Decimal("0.01")

    def test_higher_move_lower_leverage(self) -> None:
        """SOL (40% outright) should have lower max leverage than BTC (25%)."""
        sol_lev = compute_max_leverage_from_outright_move("SOL")
        btc_lev = compute_max_leverage_from_outright_move("BTC")
        assert sol_lev < btc_lev

    def test_all_base_currencies_have_both_moves(self) -> None:
        """Every entry must have both outright and spread moves defined."""
        for currency, move in MAX_UNDERLYING_MOVES.items():
            assert move.max_outright_move > 0, f"{currency} missing outright move"
            assert move.max_spread_move > 0, f"{currency} missing spread move"
            assert move.timeframe_hours > 0, f"{currency} missing timeframe"

    def test_outright_always_larger_than_spread(self) -> None:
        """Outright moves should always be larger than spread moves."""
        for currency, move in MAX_UNDERLYING_MOVES.items():
            assert move.max_outright_move > move.max_spread_move, (
                f"{currency}: outright {move.max_outright_move} <= spread {move.max_spread_move}"
            )
