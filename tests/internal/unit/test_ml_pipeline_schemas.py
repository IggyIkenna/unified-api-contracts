"""Tests for the uniform ML pipeline schemas."""

from __future__ import annotations

from unified_api_contracts.internal.domain.ml import schemas as domain_ml_schemas
from unified_api_contracts.internal.domain.ml.schemas import (
    BacktestExperimentConfig,
    BacktestFixedConfig,
    GridDimensions,
    ModelVariantConfig,
    TargetTypeParams,
)
from unified_api_contracts.internal.domain.strategy_service import StrategyModeParams
from unified_api_contracts.internal.ml import (
    CatBoostHyperparams,
    EnsembleConfig,
    EnsembleMember,
    HuberHyperparams,
    LightGBMHyperparams,
    ModelType,
    PoissonGLMHyperparams,
    RidgeHyperparams,
    TargetType,
    TrainingPhase,
    TrainingPipelineConfig,
    XGBoostHyperparams,
)
from unified_api_contracts.internal.modes import MockScenario
from unified_api_contracts.internal.testing.scenario_config import FaultConfig, ScenarioConfig


class TestTrainingPhase:
    def test_all_phases_exist(self) -> None:
        assert TrainingPhase.FEATURE_SELECTION == "feature_selection"
        assert TrainingPhase.HYPERPARAMETER_TUNING == "hyperparameter_tuning"
        assert TrainingPhase.BASE_RESULTS == "base_results"
        assert TrainingPhase.META_LEARNING == "meta_learning"
        assert TrainingPhase.META_RESULTS == "meta_results"
        assert TrainingPhase.CROSS_PIPELINE == "cross_pipeline"


class TestSportsTargetTypes:
    def test_sports_targets_exist(self) -> None:
        assert TargetType.CLV == "clv"
        assert TargetType.XG == "xg"
        assert TargetType.HT_DELTA == "ht_delta"
        assert TargetType.CLV_META == "clv_meta"
        assert TargetType.XG_META == "xg_meta"


class TestSportsModelTypes:
    def test_sports_model_types_exist(self) -> None:
        assert ModelType.CATBOOST == "catboost"
        assert ModelType.HUBER == "huber"
        assert ModelType.POISSON_GLM == "poisson_glm"
        assert ModelType.RIDGE == "ridge"


class TestHyperparameterConfigs:
    def test_lightgbm_to_dict(self) -> None:
        hp = LightGBMHyperparams(n_estimators=200)
        d = hp.to_dict()
        assert d["n_estimators"] == 200
        assert "model_type" not in d

    def test_xgboost_to_dict(self) -> None:
        hp = XGBoostHyperparams(max_depth=8)
        d = hp.to_dict()
        assert d["max_depth"] == 8
        assert "model_type" not in d

    def test_catboost_to_dict(self) -> None:
        hp = CatBoostHyperparams(depth=8, iterations=500)
        d = hp.to_dict()
        assert d["depth"] == 8
        assert "model_type" not in d

    def test_huber_to_dict(self) -> None:
        hp = HuberHyperparams(max_iter=1000, alpha=0.5)
        d = hp.to_dict()
        assert d["max_iter"] == 1000
        assert "model_type" not in d

    def test_poisson_glm_to_dict(self) -> None:
        hp = PoissonGLMHyperparams(alpha=0.2, max_iter=500)
        d = hp.to_dict()
        assert d["alpha"] == 0.2
        assert "model_type" not in d

    def test_ridge_to_dict(self) -> None:
        hp = RidgeHyperparams(alpha=2.0)
        d = hp.to_dict()
        assert d["alpha"] == 2.0
        assert "model_type" not in d


class TestEnsembleConfig:
    def test_ensemble_config_construction(self) -> None:
        ec = EnsembleConfig(
            members=[
                EnsembleMember(
                    model_type=ModelType.LIGHTGBM,
                    weight=0.5,
                    hyperparameters=LightGBMHyperparams(),
                ),
                EnsembleMember(
                    model_type=ModelType.RIDGE,
                    weight=0.5,
                    hyperparameters=RidgeHyperparams(),
                ),
            ],
            stacking_enabled=True,
            meta_model_type=ModelType.RIDGE,
            meta_model_hyperparameters=RidgeHyperparams(),
        )
        assert len(ec.members) == 2
        assert ec.stacking_enabled is True


class TestTrainingPipelineConfig:
    def test_sports_config(self) -> None:
        pc = TrainingPipelineConfig(
            pipeline_id="sports-clv",
            category="sports",
            asset="FOOTBALL",
            target_type=TargetType.CLV,
            task_type="regression",
            multi_model=True,
            split_strategy="season",
            pool_horizons=True,
            time_horizons=["T-24h", "T-12h"],
            validation_granularity="seasonal",
            evaluation_metrics=["poisson_nll", "rps"],
        )
        assert pc.category == "sports"
        assert pc.pool_horizons is True
        assert pc.task_type == "regression"

    def test_financial_config(self) -> None:
        pc = TrainingPipelineConfig(
            pipeline_id="cefi-btc-swing",
            category="cefi",
            asset="BTC",
            target_type=TargetType.SWING_HIGH,
            task_type="classification",
            multi_model=False,
        )
        assert pc.multi_model is False
        assert pc.split_strategy == "date"

    def test_cross_pipeline_deps(self) -> None:
        pc = TrainingPipelineConfig(
            pipeline_id="sports-xg-cross",
            category="sports",
            asset="FOOTBALL",
            target_type=TargetType.XG,
            pipeline_dependencies=["sports-clv"],
        )
        assert pc.pipeline_dependencies == ["sports-clv"]


class TestTargetTypeParams:
    def test_construction(self) -> None:
        tp = TargetTypeParams(
            target_type="swing_high",
            params={"swing_lookback_window": 10, "std_dev_threshold": 1.5},
        )
        assert tp.target_type == "swing_high"
        assert tp.params["swing_lookback_window"] == 10

    def test_frozen(self) -> None:
        tp = TargetTypeParams(target_type="clv", params={"odds_time_bucket": "pre_match"})
        try:
            tp.target_type = "xg"  # type: ignore[misc]
            msg = "Should be frozen"
            raise AssertionError(msg)
        except Exception:
            pass

    def test_empty_params(self) -> None:
        tp = TargetTypeParams(target_type="direction")
        assert tp.params == {}


class TestStrategyModeParams:
    def test_construction(self) -> None:
        sp = StrategyModeParams(
            strategy_mode="momentum",
            params={"prediction_threshold": 0.55, "stop_loss_pct": 0.02},
        )
        assert sp.strategy_mode == "momentum"
        assert sp.params["prediction_threshold"] == 0.55

    def test_value_betting(self) -> None:
        sp = StrategyModeParams(
            strategy_mode="value_betting",
            params={"min_edge_pct": 0.03, "stake_sizing": "kelly"},
        )
        assert sp.params["stake_sizing"] == "kelly"


class TestBacktestFixedConfig:
    def test_defaults(self) -> None:
        fc = BacktestFixedConfig(
            instrument_id="BTC-USDT",
            timeframe="1h",
            target_type=TargetType.SWING_HIGH,
        )
        assert fc.pipeline_depth == 3
        assert fc.cv_strategy == "date"
        assert fc.strategy_mode == "momentum"

    def test_sports_config(self) -> None:
        fc = BacktestFixedConfig(
            instrument_id="SPORTS:FOOTBALL:39",
            timeframe="seasonal",
            target_type=TargetType.CLV,
            cv_strategy="seasonal",
            strategy_mode="value_betting",
        )
        assert fc.cv_strategy == "seasonal"


class TestGridDimensions:
    def test_target_type_params_grid(self) -> None:
        gd = GridDimensions(
            target_type_params={
                "swing_lookback_window": [5, 10, 20],
                "std_dev_threshold": [1.5, 2.0],
            }
        )
        assert len(gd.target_type_params["swing_lookback_window"]) == 3

    def test_strategy_mode_params_grid(self) -> None:
        gd = GridDimensions(
            strategy_mode_params={
                "prediction_threshold": [0.55, 0.6, 0.65],
                "stop_loss_pct": [0.02, 0.03],
            }
        )
        assert len(gd.strategy_mode_params["prediction_threshold"]) == 3


class TestBacktestExperimentConfig:
    def test_full_construction(self) -> None:
        ec = BacktestExperimentConfig(
            fixed=BacktestFixedConfig(
                instrument_id="BTC-USDT",
                timeframe="1h",
                target_type=TargetType.SWING_HIGH,
            ),
            grid=GridDimensions(
                target_type_params={
                    "swing_lookback_window": [5, 10],
                    "std_dev_threshold": [1.5, 2.0],
                },
            ),
            walk_forward_folds=5,
        )
        assert ec.fixed.target_type == TargetType.SWING_HIGH
        assert len(ec.grid.target_type_params) == 2


class TestModelVariantConfigBackwardsCompat:
    def test_flat_to_target_params_migration(self) -> None:
        mvc = ModelVariantConfig.model_validate(
            {
                "instrument_id": "BTC-USDT",
                "timeframe": "1h",
                "target_type": "swing_high",
                "swing_lookback_window": 10,
                "std_dev_threshold": 1.5,
            }
        )
        assert mvc.target_params["swing_lookback_window"] == 10
        assert mvc.target_params["std_dev_threshold"] == 1.5

    def test_get_target_param(self) -> None:
        mvc = ModelVariantConfig(
            instrument_id="BTC-USDT",
            timeframe="1h",
            target_type=TargetType.SWING_HIGH,
            target_params={"swing_lookback_window": 5},
        )
        assert mvc.get_target_param("swing_lookback_window") == 5
        assert mvc.get_target_param("nonexistent", 99) == 99


class TestDiscriminatedUnionDeserialization:
    def test_lightgbm_round_trip(self) -> None:
        from pydantic import TypeAdapter

        from unified_api_contracts.internal.ml import HyperparameterConfigUnion

        ta = TypeAdapter(HyperparameterConfigUnion)
        hp = ta.validate_python({"model_type": "lightgbm", "num_leaves": 64})
        assert isinstance(hp, LightGBMHyperparams)
        assert hp.num_leaves == 64

    def test_catboost_round_trip(self) -> None:
        from pydantic import TypeAdapter

        from unified_api_contracts.internal.ml import HyperparameterConfigUnion

        ta = TypeAdapter(HyperparameterConfigUnion)
        hp = ta.validate_python({"model_type": "catboost", "depth": 4})
        assert isinstance(hp, CatBoostHyperparams)
        assert hp.depth == 4

    def test_ridge_round_trip(self) -> None:
        from pydantic import TypeAdapter

        from unified_api_contracts.internal.ml import HyperparameterConfigUnion

        ta = TypeAdapter(HyperparameterConfigUnion)
        hp = ta.validate_python({"model_type": "ridge", "alpha": 0.5})
        assert isinstance(hp, RidgeHyperparams)
        assert hp.alpha == 0.5


class TestNewMockScenarios:
    def test_new_scenario_values(self) -> None:
        assert MockScenario.BAD_SCHEMA == "bad_schema"
        assert MockScenario.ERROR_STORM == "error_storm"
        assert MockScenario.FLASH_CRASH == "flash_crash"
        assert MockScenario.HIGH_LATENCY == "high_latency"

    def test_load_bad_schema_yaml(self) -> None:
        cfg = ScenarioConfig.load(MockScenario.BAD_SCHEMA)
        assert cfg.name == MockScenario.BAD_SCHEMA
        assert cfg.fault is not None
        assert cfg.fault.corrupt_schema_rate == 0.1

    def test_load_error_storm_yaml(self) -> None:
        cfg = ScenarioConfig.load(MockScenario.ERROR_STORM)
        assert cfg.fault is not None
        assert cfg.fault.error_rate == 1.0
        assert cfg.fault.error_burst_duration_s == 30

    def test_load_flash_crash_yaml(self) -> None:
        cfg = ScenarioConfig.load(MockScenario.FLASH_CRASH)
        assert cfg.fault is not None
        assert cfg.fault.price_drop_pct == 0.5
        assert cfg.fault.recovery_minutes == 5

    def test_load_high_latency_yaml(self) -> None:
        cfg = ScenarioConfig.load(MockScenario.HIGH_LATENCY)
        assert cfg.delay_ms == 3500
        assert cfg.fault is not None
        assert cfg.fault.latency_ms == 3500


class TestFaultConfigExtended:
    def test_default_new_fields(self) -> None:
        fc = FaultConfig()
        assert fc.corrupt_schema_rate == 0.0
        assert fc.error_burst_duration_s == 0
        assert fc.price_drop_pct == 0.0
        assert fc.recovery_minutes == 0


class TestSyntheticDataFaultInjection:
    """Test that FaultConfig fields actually affect data generation."""

    def _make_generator(self, scenario_name: str) -> object:
        from unified_api_contracts.internal.testing.scenario_config import ScenarioConfig
        from unified_api_contracts.internal.testing.synthetic import SyntheticDataGenerator

        cfg = ScenarioConfig.load(MockScenario(scenario_name))
        spec = {"gbm_params": {"BTC/USDT": {"vol": 0.5, "drift": 0.05, "base_price": 50000.0}}}
        return SyntheticDataGenerator(spec, scenario=cfg)

    def test_bad_schema_corrupts_data(self) -> None:
        from datetime import date

        gen = self._make_generator("bad_schema")
        df = gen.generate_ohlcv("BTC/USDT", "binance", date(2025, 1, 1), date(2025, 1, 10), "1h")
        # BAD_SCHEMA has corrupt_schema_rate=0.1, so ~10% of rows should have NaN
        nan_rows = df.isnull().any(axis=1).sum()
        assert nan_rows > 0, "BAD_SCHEMA scenario should corrupt some rows"

    def test_flash_crash_drops_price(self) -> None:
        from datetime import date

        gen = self._make_generator("flash_crash")
        df = gen.generate_ohlcv("BTC/USDT", "binance", date(2025, 1, 1), date(2025, 1, 10), "1h")
        # FLASH_CRASH has price_drop_pct=0.5, so mid-series should have a significant dip
        closes = df["close"].values
        mid = len(closes) // 2
        # The crash should create a dip around the midpoint
        min_price = closes[max(0, mid - 10) : min(len(closes), mid + 10)].min()
        max_price = max(closes[0], closes[-1])
        assert min_price < max_price * 0.8, "FLASH_CRASH should create a significant price dip"

    def test_normal_scenario_no_corruption(self) -> None:
        from datetime import date

        gen = self._make_generator("normal")
        df = gen.generate_ohlcv("BTC/USDT", "binance", date(2025, 1, 1), date(2025, 1, 10), "1h")
        nan_rows = df.isnull().any(axis=1).sum()
        assert nan_rows == 0, "NORMAL scenario should not corrupt any rows"


class TestDomainMLSchemasCoverage:
    """Ensure domain/ml/schemas.py to_dict() methods are exercised."""

    def test_lightgbm_domain_to_dict(self) -> None:
        hp = domain_ml_schemas.LightGBMHyperparams(n_estimators=50)
        d = hp.to_dict()
        assert d["n_estimators"] == 50
        assert "model_type" not in d

    def test_xgboost_domain_to_dict(self) -> None:
        hp = domain_ml_schemas.XGBoostHyperparams(max_depth=4)
        d = hp.to_dict()
        assert d["max_depth"] == 4
        assert "model_type" not in d

    def test_catboost_domain_to_dict(self) -> None:
        hp = domain_ml_schemas.CatBoostHyperparams(depth=3)
        d = hp.to_dict()
        assert d["depth"] == 3
        assert "model_type" not in d

    def test_huber_domain_to_dict(self) -> None:
        hp = domain_ml_schemas.HuberHyperparams(alpha=0.3)
        d = hp.to_dict()
        assert d["alpha"] == 0.3
        assert "model_type" not in d

    def test_poisson_domain_to_dict(self) -> None:
        hp = domain_ml_schemas.PoissonGLMHyperparams(alpha=0.5)
        d = hp.to_dict()
        assert d["alpha"] == 0.5
        assert "model_type" not in d

    def test_ridge_domain_to_dict(self) -> None:
        hp = domain_ml_schemas.RidgeHyperparams(alpha=3.0)
        d = hp.to_dict()
        assert d["alpha"] == 3.0
        assert "model_type" not in d

    def test_hyperparameter_config_domain(self) -> None:
        hp = domain_ml_schemas.HyperparameterConfig(num_leaves=64)
        d = hp.to_dict()
        assert d["num_leaves"] == 64
        hp2 = domain_ml_schemas.HyperparameterConfig.from_dict({"num_leaves": 32, "unknown_key": True})
        assert hp2.num_leaves == 32

    def test_pipeline_config_validator(self) -> None:
        pc = domain_ml_schemas.TrainingPipelineConfig(
            pipeline_id="test",
            category="cefi",
            asset="BTC",
            target_type=domain_ml_schemas.TargetType.SWING_HIGH,
            pipeline_dependencies=["other"],
        )
        assert pc.pipeline_dependencies == ["other"]

    def test_model_variant_config_domain_compat(self) -> None:
        mvc = domain_ml_schemas.ModelVariantConfig.model_validate(
            {
                "instrument_id": "ETH-USDT",
                "timeframe": "4h",
                "target_type": "swing_low",
                "swing_lookback_window": 5,
            }
        )
        assert mvc.target_params["swing_lookback_window"] == 5

    def test_model_metadata_domain_compat(self) -> None:
        mm = domain_ml_schemas.ModelMetadata.model_validate(
            {
                "model_id": "m1",
                "model_version": "v1",
                "instrument_id": "BTC-USDT",
                "symbol": "BTC",
                "category": "cefi",
                "timeframe": "1h",
                "target_type": "swing_high",
                "model_type": "lightgbm",
                "feature_count": 10,
                "feature_names": "a,b",
                "hyperparameters": "{}",
                "performance_metrics": "{}",
                "training_timestamp": "2026-01-01T00:00:00Z",
                "training_duration_seconds": 1.0,
                "swing_lookback_window": 10,
            }
        )
        assert mm.target_params["swing_lookback_window"] == 10

    def test_ml_config_dict_domain_compat(self) -> None:
        cfg = domain_ml_schemas.MLConfigDict.model_validate(
            {
                "model_id": "m1",
                "model_version": "v1",
                "category": "cefi",
                "asset": "BTC",
                "target_type": "swing_high",
                "model_type": "lightgbm",
                "timeframe": "1h",
                "features_config": {},
                "hyperparameters": {},
                "training_period": {"start": "2025-01-01", "end": "2025-12-31"},
                "training_cutoff_date": "2025-12-31",
                "performance_metrics": {},
                "feature_names": [],
                "swing_lookback_window": 20,
            }
        )
        assert cfg.target_params["swing_lookback_window"] == 20
