"""Tests for the cross-asset-group partition-path SSOT."""

from __future__ import annotations

import datetime as _dt

import pytest

from unified_api_contracts._instrument_enums import InstrumentType
from unified_api_contracts.gcs_paths import (
    ASSET_GROUP_HIVE_KEY,
    AssetGroup,
    build_cefi_partition_path,
    build_defi_partition_path,
    build_prediction_partition_path,
    build_tradfi_partition_path,
    candidate_parquet_paths,
)

DAY = _dt.date(2026, 4, 17)


def test_asset_group_hive_key_is_canonical() -> None:
    assert ASSET_GROUP_HIVE_KEY == "asset_group"


# ---------------------------------------------------------------------------
# DeFi
# ---------------------------------------------------------------------------


def test_defi_partition_path_canonical() -> None:
    path = build_defi_partition_path(
        venue="aave_v3",
        chain="ethereum",
        instrument_type=InstrumentType.A_TOKEN,
        data_type="lending_indices",
        day=DAY,
        file_name="aUSDC.parquet",
    )
    assert path == (
        "raw_tick_data/by_date/day=2026-04-17/asset_group=defi/venue=AAVE_V3/chain=ETHEREUM/"
        "instrument_type=a_token/data_type=lending_indices/aUSDC.parquet"
    )


def test_defi_partition_path_uppercases_venue_and_chain() -> None:
    path = build_defi_partition_path(
        venue="uniswap_v3",
        chain="arbitrum",
        instrument_type=InstrumentType.POOL,
        data_type="dex_pool_state",
        day=DAY,
        file_name="USDC-WETH.parquet",
    )
    assert "/venue=UNISWAP_V3/" in path
    assert "/chain=ARBITRUM/" in path


def test_defi_partition_path_rejects_empty_chain() -> None:
    with pytest.raises(ValueError, match="chain"):
        build_defi_partition_path(
            venue="AAVE_V3",
            chain="",
            instrument_type=InstrumentType.A_TOKEN,
            data_type="lending_indices",
            day=DAY,
            file_name="aUSDC.parquet",
        )


# ---------------------------------------------------------------------------
# CeFi
# ---------------------------------------------------------------------------


def test_cefi_partition_path_canonical() -> None:
    path = build_cefi_partition_path(
        venue="binance",
        instrument_type=InstrumentType.PERPETUAL,
        data_type="trades",
        day=DAY,
        file_name="BTC-USDT.parquet",
    )
    assert path == (
        "raw_tick_data/by_date/day=2026-04-17/asset_group=cefi/venue=BINANCE/"
        "instrument_type=perpetual/data_type=trades/BTC-USDT.parquet"
    )


def test_cefi_v6_chain_bundle_layout() -> None:
    """v6 CHAIN bundle: instrument_type=options_chain + all v6 axes populated."""
    path = build_cefi_partition_path(
        venue="deribit",
        instrument_type="options_chain",
        data_type="trades",
        day=DAY,
        file_name="ignored.parquet",
        underlying="btc",
        quote_asset="usdc",
        margin_type="USDC",
    )
    assert path == (
        "raw_tick_data/by_date/day=2026-04-17/asset_group=cefi/venue=DERIBIT/"
        "instrument_type=options_chain/data_type=trades/"
        "underlying=BTC/quote=USDC/margin=usdc/ticks.parquet"
    )


def test_cefi_v6_falls_back_to_v5_for_single_symbol() -> None:
    """instrument_type=perpetual is per-symbol, not CHAIN — v6 axes ignored."""
    path = build_cefi_partition_path(
        venue="binance",
        instrument_type=InstrumentType.PERPETUAL,
        data_type="trades",
        day=DAY,
        file_name="BTC-USDT.parquet",
        underlying="BTC",
        quote_asset="USDT",
        margin_type="USDT",
    )
    assert "underlying=" not in path
    assert path.endswith("/data_type=trades/BTC-USDT.parquet")


def test_cefi_v6_chain_without_all_axes_falls_back_to_v5() -> None:
    """CHAIN instrument_type but missing margin_type → v5 layout."""
    path = build_cefi_partition_path(
        venue="deribit",
        instrument_type="options_chain",
        data_type="trades",
        day=DAY,
        file_name="BTC.parquet",
        underlying="BTC",
        quote_asset="USDC",
    )
    assert "underlying=" not in path
    assert path.endswith("/data_type=trades/BTC.parquet")


# ---------------------------------------------------------------------------
# TradFi
# ---------------------------------------------------------------------------


def test_tradfi_partition_path_canonical() -> None:
    path = build_tradfi_partition_path(
        venue="fred",
        instrument_type=InstrumentType.BOND,
        data_type="series_dgs10",
        day=DAY,
        file_name="DGS10.parquet",
    )
    assert path == (
        "raw_tick_data/by_date/day=2026-04-17/asset_group=tradfi/venue=FRED/"
        "instrument_type=bond/data_type=series_dgs10/DGS10.parquet"
    )


# ---------------------------------------------------------------------------
# Prediction
# ---------------------------------------------------------------------------


def test_prediction_partition_path_canonical() -> None:
    """Verified 2026-04-29 against MTDS orchestrator + polymarket_adapter."""
    cid = "0x1234abcd"
    path = build_prediction_partition_path(
        venue="polymarket",
        condition_id=cid,
        data_type="trades",
        day=DAY,
    )
    # condition_id is the FILENAME, not a partition segment.
    assert path == (
        f"raw_tick_data/by_date/day=2026-04-17/asset_group=prediction/venue=POLYMARKET/"
        f"instrument_type=prediction_market/data_type=trades/{cid}.parquet"
    )


def test_prediction_default_instrument_type() -> None:
    """Default instrument_type is prediction_market — matches production."""
    path = build_prediction_partition_path(
        venue="kalshi",
        condition_id="EVENT-2026-Q4",
        data_type="trades",
        day=DAY,
    )
    assert "/instrument_type=prediction_market/" in path


def test_prediction_sanitizes_slash_in_condition_id() -> None:
    """`/` in condition_id replaced with `_` to keep filename flat."""
    path = build_prediction_partition_path(
        venue="polymarket",
        condition_id="market/with/slashes",
        data_type="trades",
        day=DAY,
    )
    assert path.endswith("/market_with_slashes.parquet")


def test_prediction_rejects_empty_condition_id() -> None:
    with pytest.raises(ValueError, match="condition_id"):
        build_prediction_partition_path(
            venue="polymarket",
            condition_id="",
            data_type="trades",
            day=DAY,
        )


# ---------------------------------------------------------------------------
# Cross-asset-group dispatcher
# ---------------------------------------------------------------------------


def test_dispatcher_routes_defi() -> None:
    paths = candidate_parquet_paths(
        AssetGroup.DEFI,
        "lending_indices",
        DAY,
        venue="AAVE_V3",
        chain="ETHEREUM",
        instrument_type="a_token",
        file_name="aUSDC.parquet",
    )
    assert len(paths) == 1
    assert paths[0] == (
        "raw_tick_data/by_date/day=2026-04-17/asset_group=defi/venue=AAVE_V3/chain=ETHEREUM/"
        "instrument_type=a_token/data_type=lending_indices/aUSDC.parquet"
    )


def test_dispatcher_routes_sports_to_domain_module() -> None:
    """SPORTS dispatches to the domain-co-located sports SSOT."""
    paths = candidate_parquet_paths(
        AssetGroup.SPORTS,
        "FIXTURES",
        DAY,
        league_id="EPL",
    )
    # Sports returns ordered candidates: per-league subpartition first, then bare path.
    assert len(paths) == 2
    assert "league=EPL" in paths[0]
    assert "/league=EPL/" not in paths[1]


def test_dispatcher_string_asset_group_accepted() -> None:
    """Lowercase string token works as well as enum."""
    paths = candidate_parquet_paths(
        "cefi",
        "trades",
        DAY,
        venue="BINANCE",
        instrument_type="perpetual",
        file_name="BTC.parquet",
    )
    assert len(paths) == 1
    assert "asset_group=cefi" in paths[0]


def test_dispatcher_routes_prediction() -> None:
    """Prediction dispatcher uses condition_id as filename, no file_name kwarg."""
    paths = candidate_parquet_paths(
        AssetGroup.PREDICTION,
        "trades",
        DAY,
        venue="POLYMARKET",
        condition_id="0xabc123",
    )
    assert len(paths) == 1
    assert paths[0] == (
        "raw_tick_data/by_date/day=2026-04-17/asset_group=prediction/venue=POLYMARKET/"
        "instrument_type=prediction_market/data_type=trades/0xabc123.parquet"
    )
