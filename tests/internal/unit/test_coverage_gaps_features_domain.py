"""Tests to close coverage gaps — features domain schemas.

Covers:
- unified_api_contracts.internal/domain/features_commodity/__init__.py
  (COMMODITY_FEATURES_SCHEMA, FACTOR_GROUPS, SUPPORTED_COMMODITIES, get_commodity_features_schema)
- unified_api_contracts.internal/domain/features_sports/__init__.py
  (HalfTimeFeatureRecord, SeasonContextFeatureRecord, VenueContextFeatureRecord,
   RefereeFeatureRecord, SportsMLPredictionRecord)
"""

from __future__ import annotations

from datetime import UTC, datetime

# ---------------------------------------------------------------------------
# domain/features_commodity/__init__.py
# ---------------------------------------------------------------------------


class TestFeaturesCommoditySchema:
    def test_commodity_features_schema_name(self) -> None:
        from unified_api_contracts.internal.domain.features_commodity import COMMODITY_FEATURES_SCHEMA

        assert COMMODITY_FEATURES_SCHEMA.name == "features_commodity"
        assert COMMODITY_FEATURES_SCHEMA.version == "1.0"

    def test_commodity_features_schema_columns(self) -> None:
        from unified_api_contracts.internal.domain.features_commodity import COMMODITY_FEATURES_SCHEMA

        col_names = [c.name for c in COMMODITY_FEATURES_SCHEMA.columns]
        assert "timestamp" in col_names
        assert "commodity" in col_names
        assert "factor_group" in col_names
        assert "raw_value" in col_names
        assert "normalized_value" in col_names
        assert "weight" in col_names
        assert "staleness_seconds" in col_names
        assert "master_signal" in col_names
        assert "regime" in col_names
        assert "regime_confidence" in col_names

    def test_commodity_features_schema_dimension_keys(self) -> None:
        from unified_api_contracts.internal.domain.features_commodity import COMMODITY_FEATURES_SCHEMA

        assert "commodity" in COMMODITY_FEATURES_SCHEMA.dimension_keys
        assert "factor_group" in COMMODITY_FEATURES_SCHEMA.dimension_keys

    def test_get_commodity_features_schema_returns_singleton(self) -> None:
        from unified_api_contracts.internal.domain.features_commodity import (
            COMMODITY_FEATURES_SCHEMA,
            get_commodity_features_schema,
        )

        schema = get_commodity_features_schema()
        assert schema is COMMODITY_FEATURES_SCHEMA

    def test_factor_groups_completeness(self) -> None:
        from unified_api_contracts.internal.domain.features_commodity import FACTOR_GROUPS

        assert "storage_alpha" in FACTOR_GROUPS
        assert "weather_delta" in FACTOR_GROUPS
        assert "cot_positioning" in FACTOR_GROUPS
        assert "rig_count" in FACTOR_GROUPS
        assert "price_momentum" in FACTOR_GROUPS
        assert len(FACTOR_GROUPS) == 5

    def test_supported_commodities(self) -> None:
        from unified_api_contracts.internal.domain.features_commodity import SUPPORTED_COMMODITIES

        assert "NG" in SUPPORTED_COMMODITIES
        assert "CL" in SUPPORTED_COMMODITIES
        assert len(SUPPORTED_COMMODITIES) == 2

    def test_all_exports_importable(self) -> None:
        import unified_api_contracts.internal.domain.features_commodity as m
        from unified_api_contracts.internal.domain.features_commodity import __all__

        for name in __all__:
            assert hasattr(m, name)

    def test_nullable_optional_columns(self) -> None:
        from unified_api_contracts.internal.domain.features_commodity import COMMODITY_FEATURES_SCHEMA

        # master_signal, regime, regime_confidence should be nullable
        nullable_names = {c.name for c in COMMODITY_FEATURES_SCHEMA.columns if c.nullable}
        assert "master_signal" in nullable_names
        assert "regime" in nullable_names
        assert "regime_confidence" in nullable_names

    def test_required_columns_not_nullable(self) -> None:
        from unified_api_contracts.internal.domain.features_commodity import COMMODITY_FEATURES_SCHEMA

        # Core fields should not be nullable
        non_nullable = {c.name for c in COMMODITY_FEATURES_SCHEMA.columns if not c.nullable}
        assert "timestamp" in non_nullable
        assert "commodity" in non_nullable
        assert "factor_group" in non_nullable
        assert "raw_value" in non_nullable
        assert "normalized_value" in non_nullable


# ---------------------------------------------------------------------------
# domain/features_sports/__init__.py
# ---------------------------------------------------------------------------


class TestHalfTimeFeatureRecord:
    def _make_minimal(self) -> object:
        from unified_api_contracts.internal.domain.features_sports import HalfTimeFeatureRecord

        return HalfTimeFeatureRecord(
            fixture_id="PL_2024_f1",
            timestamp=datetime.now(UTC),
        )

    def test_create_minimal(self) -> None:
        record = self._make_minimal()
        assert record.fixture_id == "PL_2024_f1"  # type: ignore[union-attr]
        assert record.feature_group == "ht_features"  # type: ignore[union-attr]

    def test_defaults_are_none(self) -> None:
        record = self._make_minimal()
        assert record.home_ht_goals_avg is None  # type: ignore[union-attr]
        assert record.ht_state is None  # type: ignore[union-attr]
        assert record.ht_performance_shots_home is None  # type: ignore[union-attr]
        assert record.ht_delta_goals is None  # type: ignore[union-attr]
        assert record.ht_momentum_home is None  # type: ignore[union-attr]
        assert record.ht_odds_home_implied is None  # type: ignore[union-attr]

    def test_create_with_all_fields(self) -> None:
        from unified_api_contracts.internal.domain.features_sports import HalfTimeFeatureRecord

        ts = datetime.now(UTC)
        record = HalfTimeFeatureRecord(
            fixture_id="PL_2024_f2",
            timestamp=ts,
            home_ht_goals_avg=0.9,
            home_ht_win_rate=0.45,
            home_ht_comeback_rate=0.22,
            pred_2h_home_goals=1.2,
            pred_2h_away_goals=0.8,
            pred_comeback_probability=0.3,
            ht_state="LEAD_HOME",
            ht_performance_shots_home=7.0,
            ht_performance_shots_away=4.0,
            ht_performance_possession_home=58.0,
            ht_performance_possession_away=42.0,
            ht_performance_xg_home=0.95,
            ht_performance_xg_away=0.4,
            ht_delta_goals=1.0,
            ht_delta_possession=16.0,
            ht_delta_xg=0.55,
            ht_momentum_home=0.72,
            ht_momentum_away=-0.72,
            ht_odds_home_implied=0.55,
            ht_odds_draw_implied=0.25,
            ht_odds_away_implied=0.20,
        )
        assert record.ht_state == "LEAD_HOME"
        assert record.home_ht_goals_avg == 0.9
        assert record.ht_momentum_home == 0.72
        assert record.ht_odds_home_implied == 0.55

    def test_feature_group_literal(self) -> None:
        from unified_api_contracts.internal.domain.features_sports import HalfTimeFeatureRecord

        record = HalfTimeFeatureRecord(
            fixture_id="f1",
            timestamp=datetime.now(UTC),
            feature_group="ht_features",
        )
        assert record.feature_group == "ht_features"


class TestSeasonContextFeatureRecord:
    def test_create_minimal(self) -> None:
        from unified_api_contracts.internal.domain.features_sports import SeasonContextFeatureRecord

        record = SeasonContextFeatureRecord(
            fixture_id="PL_2024_f10",
            timestamp=datetime.now(UTC),
        )
        assert record.fixture_id == "PL_2024_f10"
        assert record.feature_group == "season_context"
        assert record.round_name is None
        assert record.matchday is None

    def test_create_with_all_fields(self) -> None:
        from unified_api_contracts.internal.domain.features_sports import SeasonContextFeatureRecord

        record = SeasonContextFeatureRecord(
            fixture_id="PL_2024_f10",
            timestamp=datetime.now(UTC),
            round_name="Regular Season - 10",
            matchday=10,
            competition_phase="regular",
            is_promotion_relegation=True,
            games_remaining=28,
            points_at_stake=84,
        )
        assert record.round_name == "Regular Season - 10"
        assert record.matchday == 10
        assert record.competition_phase == "regular"
        assert record.is_promotion_relegation is True
        assert record.games_remaining == 28
        assert record.points_at_stake == 84


class TestVenueContextFeatureRecord:
    def test_create_minimal(self) -> None:
        from unified_api_contracts.internal.domain.features_sports import VenueContextFeatureRecord

        record = VenueContextFeatureRecord(
            fixture_id="CL_2024_f5",
            timestamp=datetime.now(UTC),
        )
        assert record.fixture_id == "CL_2024_f5"
        assert record.feature_group == "venue_context"
        assert record.home_advantage_pct is None
        assert record.travel_distance_km is None

    def test_create_with_all_fields(self) -> None:
        from unified_api_contracts.internal.domain.features_sports import VenueContextFeatureRecord

        record = VenueContextFeatureRecord(
            fixture_id="CL_2024_f5",
            timestamp=datetime.now(UTC),
            home_advantage_pct=0.62,
            travel_distance_km=1200.5,
            altitude_m=620.0,
            stadium_capacity=75000,
            surface_type="grass",
            is_neutral_venue=False,
        )
        assert record.home_advantage_pct == 0.62
        assert record.travel_distance_km == 1200.5
        assert record.altitude_m == 620.0
        assert record.stadium_capacity == 75000
        assert record.surface_type == "grass"
        assert record.is_neutral_venue is False

    def test_neutral_venue(self) -> None:
        from unified_api_contracts.internal.domain.features_sports import VenueContextFeatureRecord

        record = VenueContextFeatureRecord(
            fixture_id="WC_2026_f1",
            timestamp=datetime.now(UTC),
            is_neutral_venue=True,
        )
        assert record.is_neutral_venue is True


class TestRefereeFeatureRecord:
    def test_create_minimal(self) -> None:
        from unified_api_contracts.internal.domain.features_sports import RefereeFeatureRecord

        record = RefereeFeatureRecord(
            fixture_id="PL_2024_f20",
            timestamp=datetime.now(UTC),
        )
        assert record.fixture_id == "PL_2024_f20"
        assert record.feature_group == "referee_features"
        assert record.referee_avg_cards is None
        assert record.referee_card_rate_band is None

    def test_create_with_all_fields(self) -> None:
        from unified_api_contracts.internal.domain.features_sports import RefereeFeatureRecord

        record = RefereeFeatureRecord(
            fixture_id="PL_2024_f20",
            timestamp=datetime.now(UTC),
            referee_avg_cards=3.8,
            referee_avg_fouls=22.5,
            referee_avg_penalties=0.4,
            referee_card_rate_band="high",
            referee_home_bias=0.05,
        )
        assert record.referee_avg_cards == 3.8
        assert record.referee_avg_fouls == 22.5
        assert record.referee_avg_penalties == 0.4
        assert record.referee_card_rate_band == "high"
        assert record.referee_home_bias == 0.05

    def test_negative_home_bias_allowed(self) -> None:
        from unified_api_contracts.internal.domain.features_sports import RefereeFeatureRecord

        record = RefereeFeatureRecord(
            fixture_id="PL_2024_f21",
            timestamp=datetime.now(UTC),
            referee_home_bias=-0.03,
        )
        assert record.referee_home_bias == -0.03


class TestSportsMLPredictionRecord:
    def test_create_minimal(self) -> None:
        from unified_api_contracts.internal.domain.features_sports import SportsMLPredictionRecord

        record = SportsMLPredictionRecord(
            fixture_id="PL_2024_f30",
            timestamp=datetime.now(UTC),
        )
        assert record.fixture_id == "PL_2024_f30"
        assert record.feature_group == "ml_predictions"
        assert record.model_version is None
        assert record.pred_home_win is None

    def test_create_with_probabilities(self) -> None:
        from unified_api_contracts.internal.domain.features_sports import SportsMLPredictionRecord

        record = SportsMLPredictionRecord(
            fixture_id="PL_2024_f30",
            timestamp=datetime.now(UTC),
            model_version="lgbm_v3.2.1",
            feature_vector_hash="sha256:abc123",
            pred_home_win=0.52,
            pred_draw=0.24,
            pred_away_win=0.24,
            pred_home_goals=1.6,
            pred_away_goals=1.1,
            pred_over_25=0.60,
            model_confidence=0.78,
        )
        assert record.pred_home_win == 0.52
        assert record.pred_draw == 0.24
        assert record.pred_away_win == 0.24
        assert record.pred_home_goals == 1.6
        assert record.pred_away_goals == 1.1
        assert record.pred_over_25 == 0.60
        assert record.model_confidence == 0.78
        assert record.model_version == "lgbm_v3.2.1"

    def test_probabilities_sum_to_one(self) -> None:
        from unified_api_contracts.internal.domain.features_sports import SportsMLPredictionRecord

        record = SportsMLPredictionRecord(
            fixture_id="PL_2024_f31",
            timestamp=datetime.now(UTC),
            pred_home_win=0.50,
            pred_draw=0.25,
            pred_away_win=0.25,
        )
        total = (record.pred_home_win or 0.0) + (record.pred_draw or 0.0) + (record.pred_away_win or 0.0)
        assert abs(total - 1.0) < 1e-9


class TestFeaturesSportsAllExports:
    def test_all_exports_importable(self) -> None:
        import unified_api_contracts.internal.domain.features_sports as m
        from unified_api_contracts.internal.domain.features_sports import __all__

        for name in __all__:
            assert hasattr(m, name)

    def test_all_exports_are_classes(self) -> None:
        from unified_api_contracts.internal.domain.features_sports import (
            HalfTimeFeatureRecord,
            RefereeFeatureRecord,
            SeasonContextFeatureRecord,
            SportsMLPredictionRecord,
            VenueContextFeatureRecord,
        )

        for cls in (
            HalfTimeFeatureRecord,
            SeasonContextFeatureRecord,
            VenueContextFeatureRecord,
            RefereeFeatureRecord,
            SportsMLPredictionRecord,
        ):
            assert isinstance(cls, type)
