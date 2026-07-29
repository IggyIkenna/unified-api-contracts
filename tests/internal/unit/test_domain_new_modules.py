"""Coverage tests for new domain/ sub-packages — import + instantiation.

Importing each module covers class/enum definitions (the bulk of each file).
Targeted instantiation tests exercise validator logic and model construction.
"""

from __future__ import annotations

import importlib
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

UNCOVERED_MODULES = [
    "unified_api_contracts.internal.domain.analytics",
    "unified_api_contracts.internal.domain.analytics.factor_exposure",
    "unified_api_contracts.internal.domain.cefi_accounts",
    "unified_api_contracts.internal.domain.cefi_accounts.schemas",
    "unified_api_contracts.internal.domain.cicd",
    "unified_api_contracts.internal.domain.deployment_service",
    "unified_api_contracts.internal.domain.deployment_service.deployment",
    "unified_api_contracts.internal.domain.derivatives",
    "unified_api_contracts.internal.domain.derivatives.options",
    "unified_api_contracts.internal.domain.events_service",
    "unified_api_contracts.internal.domain.events_service.lifecycle",
    "unified_api_contracts.internal.domain.execution_service.cex_withdrawals",
    "unified_api_contracts.internal.domain.features_commodity.commodity_feature_request",
    "unified_api_contracts.internal.domain.features_commodity.commodity_signal",
    "unified_api_contracts.internal.domain.features_cross_instrument.cross_instrument",
    "unified_api_contracts.internal.domain.features_delta_one.feature_record",
    "unified_api_contracts.internal.domain.features_multi_timeframe.cross_timeframe",
    "unified_api_contracts.internal.domain.features_onchain.eth_transfers",
    "unified_api_contracts.internal.domain.features_onchain.onchain_feature",
    "unified_api_contracts.internal.domain.features_onchain.protocol_params",
    "unified_api_contracts.internal.domain.features_sports.storage",
    "unified_api_contracts.internal.domain.features_volatility.records",
    "unified_api_contracts.internal.domain.health",
    "unified_api_contracts.internal.domain.health.service_health",
    "unified_api_contracts.internal.domain.matching_engine",
    "unified_api_contracts.internal.domain.ml",
    "unified_api_contracts.internal.domain.ml.schemas",
    "unified_api_contracts.internal.domain.ml_inference_service.feature_snapshot",
    "unified_api_contracts.internal.domain.pubsub_service",
    "unified_api_contracts.internal.domain.pubsub_service.pubsub",
    "unified_api_contracts.internal.domain.risk_service",
    "unified_api_contracts.internal.domain.risk_service.risk",
    "unified_api_contracts.internal.domain.prediction_market",
    "unified_api_contracts.internal.domain.prediction_market.prediction_market_arb",
    "unified_api_contracts.internal.domain.websocket",
    "unified_api_contracts.internal.domain.websocket.lifecycle",
    "unified_api_contracts.internal.env_canon",
]


@pytest.mark.timeout(120)  # trivial import; 2x buffer against xdist worker contention on the full-suite run
@pytest.mark.parametrize("module_path", UNCOVERED_MODULES)
def test_module_importable(module_path: str) -> None:
    mod = importlib.import_module(module_path)
    assert mod is not None


class TestAnalyticsInstantiation:
    def test_factor_exposure(self) -> None:
        from unified_api_contracts.internal.domain.analytics.factor_exposure import (
            FactorAttributionModel,
            FactorAttributionRecord,
            FactorExposure,
            FactorType,
        )

        assert FactorType.MOMENTUM is not None
        exp = FactorExposure(factor=FactorType.MOMENTUM, beta=0.8)
        assert exp.factor == FactorType.MOMENTUM
        rec = FactorAttributionRecord(date=date(2026, 1, 1), total_return=0.05)
        assert rec.total_return == 0.05
        model = FactorAttributionModel(model_id="m1", model_name="3-factor", factors=[FactorType.MOMENTUM])
        assert model.model_id == "m1"


class TestCefiAccountsInstantiation:
    def test_schemas(self) -> None:
        from unified_api_contracts.internal.domain.cefi_accounts.schemas import (
            DepositAddress,
            DepositRecord,
            ExchangeFeeSchedule,
            InternalTransfer,
            PortfolioMarginAccount,
            SubAccount,
            WithdrawalRecord,
        )

        DepositAddress(network="BTC", address="bc1q...")
        DepositRecord(status="completed", amount=Decimal("1.0"), asset="ETH", network="ETH")
        WithdrawalRecord(status="pending", amount=Decimal("100"), asset="USDT", network="TRX")
        InternalTransfer(fromAccountType="SPOT", toAccountType="MARGIN", asset="BTC", amount=Decimal("0.1"))
        SubAccount(id="sub1")
        ExchangeFeeSchedule(tier=1, makerRate=Decimal("0.001"), takerRate=Decimal("0.001"))
        PortfolioMarginAccount(
            totalEquity=Decimal("100000"),
            actualEquity=Decimal("90000"),
            availableBalance=Decimal("80000"),
        )


class TestCicdInstantiation:
    def test_github_workflow_event(self) -> None:
        from unified_api_contracts.internal.domain.cicd import GitHubWorkflowEvent

        GitHubWorkflowEvent(
            repo_name="pm",
            workflow_name="qg",
            run_id=1,
            run_url="https://...",
            conclusion="success",
            triggered_by="push",
            branch="main",
            commit_sha="abc123",
            duration_seconds=30.0,
            timestamp=datetime.now(UTC),
        )


class TestDeploymentInstantiation:
    def test_deployment(self) -> None:
        from unified_api_contracts.internal.domain.deployment_service.deployment import (
            DeploymentState,
            DeploymentStatus,
            ShardEvent,
            VMEventType,
        )

        assert DeploymentStatus.RUNNING is not None
        ShardEvent(deployment_id="d1", shard_id="s1", event_type=VMEventType.JOB_STARTED, message="ok")
        DeploymentState(
            deployment_id="d1",
            service="mtds",
            status=DeploymentStatus.RUNNING,
            tag="v0.5.0",
            region="us-central1",
            created_at="2026-01-01",
            updated_at="2026-01-01",
            total_shards=2,
            completed_shards=1,
            failed_shards=0,
        )


class TestDerivativesInstantiation:
    def test_options(self) -> None:
        from unified_api_contracts.internal.domain.derivatives.options import (
            OptionContract,
            OptionGreeks,
            OptionsChain,
            SettlementPrice,
        )

        SettlementPrice(
            venue="deribit",
            symbol="BTC-PERPETUAL",
            price=Decimal("50000"),
            settlement_time=datetime.now(UTC),
        )
        greeks = OptionGreeks(delta=Decimal("0.5"), gamma=Decimal("0.01"), theta=Decimal("-0.05"), vega=Decimal("0.2"))
        assert greeks.delta == Decimal("0.5")
        OptionContract(
            strike=Decimal("100000"),
            option_type="call",
            bid=Decimal("0.05"),
            ask=Decimal("0.06"),
            last=Decimal("0.055"),
            volume=Decimal("100"),
            open_interest=Decimal("500"),
            implied_volatility=Decimal("0.65"),
            greeks=greeks,
        )
        OptionsChain(venue="deribit", underlying="BTC", expiry=datetime.now(UTC))


class TestEventsLifecycleInstantiation:
    def test_lifecycle_key_types(self) -> None:
        from unified_api_contracts.internal.domain.events_service.lifecycle import (
            AuthFailureDetails,
            ConfigChangedDetails,
            DataBroadcastDetails,
            DataIngestionCompletedDetails,
            DataIngestionDetails,
            EventMetadata,
            EventSeverity,
            FailedDetails,
            LifecycleEventEnvelope,
            LifecycleEventType,
            PersistenceCompletedDetails,
            PersistenceStartedDetails,
            ProcessingCompletedDetails,
            ProcessingStartedDetails,
            SecretAccessedDetails,
            ServiceMode,
            StartedDetails,
            StoppedDetails,
            ValidationCompletedDetails,
            ValidationStartedDetails,
        )

        assert LifecycleEventType.STARTED is not None
        assert EventSeverity.INFO is not None
        assert ServiceMode.LIVE is not None
        StartedDetails(service_name="svc", mode="batch")
        ValidationStartedDetails(service_name="svc", validator_count=5)
        ValidationCompletedDetails(service_name="svc", passed=3, failed=0, skipped=0)
        DataIngestionDetails(service_name="svc", source="binance", data_type="trades")
        DataIngestionCompletedDetails(service_name="svc", source="binance", records_ingested=100)
        ProcessingStartedDetails(service_name="svc", step="calc")
        ProcessingCompletedDetails(service_name="svc", step="calc", records_processed=50)
        DataBroadcastDetails(service_name="svc", topic="features", record_count=10)
        PersistenceStartedDetails(service_name="svc", target="gcs")
        PersistenceCompletedDetails(service_name="svc", target="gcs", records_persisted=10)
        StoppedDetails(service_name="svc")
        FailedDetails(service_name="svc", error="boom", error_type="RuntimeError")
        AuthFailureDetails(service_name="svc", venue="binance", error="401")
        ConfigChangedDetails(service_name="svc", key="batch_size", old_value="10", new_value="20")
        SecretAccessedDetails(service_name="svc", secret_name="api_key", caller_identity="agent")
        meta = EventMetadata(service_name="svc", event_type=LifecycleEventType.STARTED, timestamp=datetime.now(UTC))
        LifecycleEventEnvelope(
            event=LifecycleEventType.STARTED,
            service="svc",
            timestamp=datetime.now(UTC),
            metadata=meta,
        )


class TestCexWithdrawalsInstantiation:
    def test_all_venues(self) -> None:
        from unified_api_contracts.internal.domain.execution_service.cex_withdrawals import (
            BinanceWithdrawRequest,
            BinanceWithdrawResponse,
            BybitWithdrawRequest,
            BybitWithdrawResponse,
            CoinbaseWithdrawRequest,
            CoinbaseWithdrawResponse,
            OKXWithdrawRequest,
            OKXWithdrawResponse,
            UpbitWithdrawRequest,
            UpbitWithdrawResponse,
        )

        BinanceWithdrawRequest(coin="BTC", address="bc1q...", amount="0.1")
        BinanceWithdrawResponse(id="w1")
        OKXWithdrawRequest(ccy="ETH", amt="1.0", dest="4", toAddr="0x...")
        OKXWithdrawResponse()
        BybitWithdrawRequest(coin="USDT", chain="TRX", address="T...", amount="100")
        BybitWithdrawResponse()
        UpbitWithdrawRequest(currency="BTC", amount="0.01")
        UpbitWithdrawResponse()
        CoinbaseWithdrawRequest(to="0x...", amount="0.5", currency="ETH")
        CoinbaseWithdrawResponse()


class TestManualInstructionInstantiation:
    def test_manual_instruction(self) -> None:
        from unified_api_contracts.internal.execution import ManualInstruction

        ManualInstruction(
            instruction_id="i1",
            submitted_by="t@ex.com",
            venue="binance",
            account_id="a1",
            instrument_key="BINANCE:SPOT:BTCUSDT",
            side="BUY",
            order_type="MARKET",
            quantity=Decimal("0.1"),
            submitted_at=datetime.now(UTC),
        )


class TestFeaturesCommodityInstantiation:
    def test_commodity_models(self) -> None:
        from unified_api_contracts.internal.domain.features_commodity.commodity_feature_request import (
            CommodityFeatureRequest,
        )
        from unified_api_contracts.internal.domain.features_commodity.commodity_signal import (
            CommoditySignal,
            FactorValue,
            RegimeState,
        )

        assert RegimeState.TRENDING is not None
        CommodityFeatureRequest(commodity="CL", factor_values=[])
        FactorValue(factor_id="mom", raw_value=0.8, normalized_value=0.6, weight=0.3)
        CommoditySignal(commodity="CL", master_signal=0.65, signal_timestamp=datetime.now(UTC))


class TestFeaturesCrossInstrumentInstantiation:
    def test_cross_instrument(self) -> None:
        from unified_api_contracts.internal.domain.features_cross_instrument.cross_instrument import (
            CrossInstrumentFeatures,
            PairSpreadFeatureRecord,
        )

        CrossInstrumentFeatures(
            timestamp=datetime.now(UTC),
            timestamp_out=datetime.now(UTC),
            instrument_id_primary="BINANCE:SPOT:BTCUSDT",
            feature_category="spread",
        )
        PairSpreadFeatureRecord(
            instrument_key_a="BINANCE:SPOT:BTCUSDT",
            instrument_key_b="BINANCE:SPOT:ETHUSDT",
            spread_value=Decimal("0.05"),
            spread_zscore=1.2,
            hedge_ratio=Decimal("15.5"),
            cointegration_score=0.85,
            half_life_bars=20,
            ou_mean_reversion_speed=0.05,
            spread_velocity=0.01,
            timestamp=1710000000,
        )


class TestFeaturesDeltaOneInstantiation:
    def test_feature_record(self) -> None:
        from unified_api_contracts.internal.domain.features_delta_one.feature_record import (
            DeltaOneFeatureRecord,
        )

        DeltaOneFeatureRecord(
            instrument_id="BINANCE:SPOT:BTCUSDT",
            timestamp=datetime.now(UTC),
            timestamp_out=datetime.now(UTC),
        )


class TestFeaturesMultiTimeframeInstantiation:
    def test_cross_timeframe(self) -> None:
        from unified_api_contracts.internal.domain.features_multi_timeframe.cross_timeframe import (
            CrossTimeframeFeatures,
        )

        CrossTimeframeFeatures(
            instrument_id="BINANCE:SPOT:BTCUSDT",
            timestamp=datetime.now(UTC),
            timestamp_out=datetime.now(UTC),
            feature_category="mtf",
        )


class TestFeaturesOnchainInstantiation:
    def test_all_types(self) -> None:
        from unified_api_contracts.internal.domain.features_onchain.eth_transfers import (
            EthSendRawTransactionRequest,
        )
        from unified_api_contracts.internal.domain.features_onchain.onchain_feature import (
            OnchainFeatureRecord,
        )
        from unified_api_contracts.internal.domain.features_onchain.protocol_params import (
            AaveBorrowParams,
            CurveDepositParams,
        )

        EthSendRawTransactionRequest(id=1, params=["0xabc"])
        pass  # Erc20TransferCalldata is a TypedDict, covered by import
        OnchainFeatureRecord(timestamp=datetime.now(UTC), instrument_key="ETHEREUM:DEFI:AAVE")
        AaveBorrowParams(asset="0x...", amount="1000")
        CurveDepositParams(amounts=["1000", "0"])


class TestFeaturesSportsStorageInstantiation:
    def test_storage_records(self) -> None:
        from unified_api_contracts.internal.domain.features_sports.storage import (
            CoachRecord,
            FixtureEventsRecord,
            FixtureLineupsRecord,
            FixturePlayerStatsRecord,
            FixtureRecord,
            FixtureStatsRecord,
            InjuryRecord,
            LeagueRecord,
            PlayerRecord,
            RefereeRecord,
            RoundRecord,
            StandingsRecord,
            TeamRecord,
            VenueRecord,
        )

        LeagueRecord(league_id=1, name="EPL", country="England", season=2025)
        TeamRecord(team_id=1, name="Arsenal", league_id=1)
        VenueRecord(venue_id=1, name="Emirates", city="London")
        PlayerRecord(player_id=1, name="Saka", team_id=1)
        CoachRecord(coach_id=1, name="Arteta", team_id=1)
        RefereeRecord(referee_id=1, name="Oliver")
        FixtureRecord(fixture_id=1, league_id=1, home_team_id=1, away_team_id=2, date="2026-01-01")
        FixtureStatsRecord(fixture_id=1, team_id=1)
        FixtureEventsRecord(fixture_id=1)
        FixtureLineupsRecord(fixture_id=1, team_id=1)
        FixturePlayerStatsRecord(fixture_id=1, player_id=1, team_id=1)
        InjuryRecord(player_id=1, team_id=1, league_id=1)
        StandingsRecord(league_id=1, season=2025, team_id=1, rank=1)
        RoundRecord(league_id=1, season=2025, round_name="Matchday 1")


class TestFeaturesVolatilityInstantiation:
    def test_records(self) -> None:
        from unified_api_contracts.internal.domain.features_volatility.records import (
            FuturesTermStructureRecord,
            OptionsIvRecord,
            VolSurfaceTermStructureRecord,
        )

        OptionsIvRecord(
            timestamp=datetime.now(UTC),
            timestamp_out=datetime.now(UTC),
            venue="deribit",
            underlying_symbol="BTC",
        )
        FuturesTermStructureRecord(
            timestamp=datetime.now(UTC),
            timestamp_out=datetime.now(UTC),
            venue="binance",
            underlying_symbol="BTC",
            spot_price=Decimal("50000"),
        )
        VolSurfaceTermStructureRecord(
            venue="deribit",
            underlying="BTC",
            timestamp=1710000000,
            underlying_price=Decimal("50000"),
        )


class TestHealthInstantiation:
    def test_service_health(self) -> None:
        from unified_api_contracts.internal.domain.health.service_health import ServiceHealthResponse

        ServiceHealthResponse(service_name="test", status="healthy", version="0.1.0")


class TestMatchingEngineInstantiation:
    def test_matching_types(self) -> None:
        from unified_api_contracts.internal.domain.matching_engine import (
            BookType,
            MatchingFeeType,
            OrderType,
        )

        assert OrderType.LIMIT is not None
        assert BookType.L1_MBP is not None
        assert MatchingFeeType.ASYMMETRIC is not None


class TestMLSchemasInstantiation:
    def test_ml_types(self) -> None:
        from unified_api_contracts.internal.domain.ml.schemas import (
            ModelType,
            TargetType,
        )

        assert TargetType.DIRECTION is not None
        assert ModelType.LIGHTGBM is not None


class TestFeatureSnapshotInstantiation:
    def test_feature_snapshot(self) -> None:
        from unified_api_contracts.internal.domain.ml_inference_service.feature_snapshot import (
            FeatureSnapshotRequest,
        )

        FeatureSnapshotRequest(
            instrument_id="BINANCE:SPOT:BTCUSDT",
            timestamp=datetime.now(UTC),
            swing_lookback_window=60,
        )


class TestPubSubServiceInstantiation:
    def test_pubsub_enums(self) -> None:
        from unified_api_contracts.internal.domain.pubsub_service.pubsub import InternalPubSubTopic

        assert InternalPubSubTopic.FILL_EVENTS is not None


class TestRiskServiceInstantiation:
    def test_risk_enums(self) -> None:
        from unified_api_contracts.internal.domain.risk_service.risk import (
            AlertType,
            PositionSide,
            RiskStatus,
        )

        assert RiskStatus.OK is not None
        assert AlertType.EXPOSURE_BREACH is not None
        assert PositionSide.LONG is not None


class TestFixedGridConfig:
    """Tests for BacktestFixedConfig, GridDimensions, BacktestExperimentConfig."""

    def test_backtest_fixed_config(self) -> None:
        from unified_api_contracts.internal.domain.ml import BacktestFixedConfig

        cfg = BacktestFixedConfig(
            instrument_id="BTC-USDT",
            timeframe="1h",
            target_type="swing_high",
        )
        assert cfg.pipeline_depth == 3
        assert cfg.cv_strategy == "date"
        assert cfg.strategy_mode == "momentum"

    def test_grid_dimensions(self) -> None:
        from unified_api_contracts.internal.domain.ml import GridDimensions

        gd = GridDimensions(
            target_type_params={
                "swing_lookback_window": [5, 10, 20],
                "std_dev_threshold": [1.5, 2.0],
            },
            strategy_mode_params={
                "prediction_threshold": [0.55, 0.6],
            },
        )
        assert len(gd.target_type_params["swing_lookback_window"]) == 3
        assert len(gd.strategy_mode_params["prediction_threshold"]) == 2

    def test_backtest_experiment_config(self) -> None:
        from unified_api_contracts.internal.domain.ml import (
            BacktestExperimentConfig,
            BacktestFixedConfig,
            GridDimensions,
        )

        exp = BacktestExperimentConfig(
            fixed=BacktestFixedConfig(
                instrument_id="SPORTS:FOOTBALL:39",
                timeframe="seasonal",
                target_type="clv",
                cv_strategy="seasonal",
                strategy_mode="value_betting",
                pipeline_depth=5,
            ),
            grid=GridDimensions(
                target_type_params={
                    "odds_time_bucket": ["T-60m", "T-24h"],
                },
                strategy_mode_params={
                    "min_edge_pct": [3.0, 5.0, 7.0],
                },
            ),
            walk_forward_folds=3,
        )
        assert exp.fixed.target_type == "clv"
        assert exp.fixed.cv_strategy == "seasonal"
        assert len(exp.grid.target_type_params["odds_time_bucket"]) == 2
        assert len(exp.grid.strategy_mode_params["min_edge_pct"]) == 3

    def test_model_variant_config_backwards_compat(self) -> None:
        from unified_api_contracts.internal.domain.ml import ModelVariantConfig

        v = ModelVariantConfig(
            instrument_id="BTC",
            timeframe="1h",
            target_type="swing_high",
            swing_lookback_window=5,
            std_dev_threshold=1.5,
            breakout_threshold=1.0,
        )
        assert v.target_params["swing_lookback_window"] == 5
        assert v.target_params["std_dev_threshold"] == 1.5
        assert v.get_target_param("breakout_threshold", 0.0) == 1.0

    def test_model_variant_config_new_style(self) -> None:
        from unified_api_contracts.internal.domain.ml import ModelVariantConfig

        v = ModelVariantConfig(
            instrument_id="SPORTS:FOOTBALL:39",
            timeframe="seasonal",
            target_type="clv",
            target_params={"odds_time_bucket": "T-60m", "min_odds_bookmakers": 3},
        )
        assert v.target_params["odds_time_bucket"] == "T-60m"
        assert v.get_target_param("missing", 99) == 99

    def test_model_metadata_target_params(self) -> None:
        from unified_api_contracts.internal.domain.ml import ModelMetadata

        m = ModelMetadata(
            model_id="test",
            model_version="v1",
            instrument_id="BTC",
            symbol="BTC",
            category="cefi",
            timeframe="1h",
            target_type="swing_high",
            swing_lookback_window=10,
            std_dev_threshold=2.0,
            breakout_threshold=1.0,
            model_type="lightgbm",
            feature_count=100,
            feature_names="f1,f2",
            hyperparameters="{}",
            performance_metrics="{}",
            training_timestamp="2026-01-01T00:00:00Z",
            training_duration_seconds=60.0,
        )
        assert m.target_params["swing_lookback_window"] == 10

    def test_ml_py_model_variant_compat(self) -> None:
        """Test the ml.py mirror ModelVariantConfig backwards compat."""
        from unified_api_contracts.internal.ml import ModelVariantConfig as MlModuleVariant

        v = MlModuleVariant(
            instrument_id="BTC",
            timeframe="1h",
            target_type="swing_high",
            swing_lookback_window=5,
            std_dev_threshold=1.5,
            breakout_threshold=1.0,
        )
        assert v.target_params["swing_lookback_window"] == 5
        assert v.get_target_param("std_dev_threshold", 0.0) == 1.5

    def test_ml_py_model_metadata_compat(self) -> None:
        """Test the ml.py mirror ModelMetadata backwards compat."""
        from unified_api_contracts.internal.ml import ModelMetadata as MlModuleMetadata

        m = MlModuleMetadata(
            model_id="t",
            model_version="v1",
            instrument_id="BTC",
            symbol="BTC",
            category="cefi",
            timeframe="1h",
            target_type="swing_high",
            swing_lookback_window=10,
            std_dev_threshold=2.0,
            breakout_threshold=1.0,
            model_type="lightgbm",
            feature_count=100,
            feature_names="f1",
            hyperparameters="{}",
            performance_metrics="{}",
            training_timestamp="2026-01-01T00:00:00Z",
            training_duration_seconds=60.0,
        )
        assert m.target_params["swing_lookback_window"] == 10

    def test_ml_py_config_dict_compat(self) -> None:
        """Test the ml.py mirror MLConfigDict backwards compat."""
        from unified_api_contracts.internal.ml import MLConfigDict as MlModuleConfigDict
        from unified_api_contracts.internal.ml import TrainingPeriod

        c = MlModuleConfigDict(
            model_id="t",
            model_version="v1",
            category="cefi",
            asset="BTC",
            target_type="swing_high",
            model_type="lightgbm",
            timeframe="1h",
            features_config={},
            hyperparameters={},
            training_period=TrainingPeriod(start="2025-01-01", end="2025-12-31"),
            training_cutoff_date="2025-12-31",
            performance_metrics={},
            feature_names=[],
            swing_lookback_window=5,
            std_dev_threshold=1.5,
            breakout_threshold=1.0,
        )
        assert c.target_params["swing_lookback_window"] == 5

    def test_ml_config_dict_target_params(self) -> None:
        from unified_api_contracts.internal.domain.ml.schemas import MLConfigDict, TrainingPeriod

        c = MLConfigDict(
            model_id="test",
            model_version="v1",
            category="cefi",
            asset="BTC",
            target_type="swing_high",
            model_type="lightgbm",
            timeframe="1h",
            features_config={},
            hyperparameters={},
            training_period=TrainingPeriod(start="2025-01-01", end="2025-12-31"),
            training_cutoff_date="2025-12-31",
            performance_metrics={},
            feature_names=[],
            swing_lookback_window=5,
            std_dev_threshold=1.5,
            breakout_threshold=1.0,
        )
        assert c.target_params["swing_lookback_window"] == 5
