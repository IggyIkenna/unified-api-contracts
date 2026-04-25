"""Unit tests for DataFreshnessContract and all freshness contract dicts.

Covers:
- Model instantiation and field validation
- Parametrized asset class thresholds for each dict
- ALL_FRESHNESS_CONTRACTS aggregate
- Top-level UIC __init__ re-exports
"""

from __future__ import annotations

import pytest

from unified_api_contracts.internal.reference.data_freshness import (
    ALL_FRESHNESS_CONTRACTS,
    FEATURE_FRESHNESS,
    MARKET_TICK_FRESHNESS,
    ML_FRESHNESS,
    DataFreshnessContract,
)

# ---------------------------------------------------------------------------
# DataFreshnessContract model validation
# ---------------------------------------------------------------------------


class TestDataFreshnessContractModel:
    def test_valid_contract_instantiation(self) -> None:
        c = DataFreshnessContract(
            source="test_source",
            asset_group="crypto_cefi",
            max_age_seconds=10,
            warn_age_seconds=5,
            expected_cadence_seconds=1,
            criticality="critical",
        )
        assert c.source == "test_source"
        assert c.max_age_seconds == 10
        assert c.warn_age_seconds == 5
        assert c.expected_cadence_seconds == 1
        assert c.criticality == "critical"

    def test_invalid_asset_group_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DataFreshnessContract(
                source="x",
                asset_group="unknown_class",  # type: ignore[arg-type]
                max_age_seconds=10,
                warn_age_seconds=5,
                expected_cadence_seconds=1,
                criticality="critical",
            )

    def test_invalid_criticality_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DataFreshnessContract(
                source="x",
                asset_group="crypto_cefi",
                max_age_seconds=10,
                warn_age_seconds=5,
                expected_cadence_seconds=1,
                criticality="unknown",  # type: ignore[arg-type]
            )

    def test_zero_max_age_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DataFreshnessContract(
                source="x",
                asset_group="crypto_cefi",
                max_age_seconds=0,
                warn_age_seconds=5,
                expected_cadence_seconds=1,
                criticality="critical",
            )

    def test_zero_warn_age_raises(self) -> None:
        from pydantic import ValidationError

        with pytest.raises(ValidationError):
            DataFreshnessContract(
                source="x",
                asset_group="crypto_cefi",
                max_age_seconds=10,
                warn_age_seconds=0,
                expected_cadence_seconds=1,
                criticality="critical",
            )

    def test_all_asset_groupes_valid(self) -> None:
        asset_groupes = [
            "crypto_cefi",
            "crypto_defi",
            "tradfi",
            "onchain",
            "sports",
            "feature",
            "ml",
        ]
        for ac in asset_groupes:
            c = DataFreshnessContract(
                source="test",
                asset_group=ac,  # type: ignore[arg-type]
                max_age_seconds=60,
                warn_age_seconds=30,
                expected_cadence_seconds=10,
                criticality="informational",
            )
            assert c.asset_group == ac

    def test_all_criticality_levels_valid(self) -> None:
        for crit in ("critical", "important", "informational"):
            c = DataFreshnessContract(
                source="test",
                asset_group="feature",
                max_age_seconds=60,
                warn_age_seconds=30,
                expected_cadence_seconds=10,
                criticality=crit,  # type: ignore[arg-type]
            )
            assert c.criticality == crit


# ---------------------------------------------------------------------------
# MARKET_TICK_FRESHNESS — parametrized per venue
# ---------------------------------------------------------------------------

_EXPECTED_MARKET_VENUES = [
    # (key, asset_group, max_age, warn_age, cadence, criticality)
    ("binance", "crypto_cefi", 5, 2, 1, "critical"),
    ("bybit", "crypto_cefi", 5, 2, 1, "critical"),
    ("okx", "crypto_cefi", 5, 2, 1, "critical"),
    ("coinbase", "crypto_cefi", 5, 2, 1, "critical"),
    ("hyperliquid", "crypto_cefi", 5, 2, 1, "critical"),
    ("deribit", "crypto_cefi", 10, 3, 1, "critical"),
    ("uniswap_v3", "crypto_defi", 15, 6, 12, "critical"),
    ("aave_v3", "crypto_defi", 15, 6, 12, "critical"),
    ("curve", "crypto_defi", 15, 6, 12, "critical"),
    ("balancer", "crypto_defi", 15, 6, 12, "critical"),
    ("databento_intraday", "tradfi", 60, 30, 60, "important"),
    ("databento_eod", "tradfi", 86400, 43200, 86400, "important"),
    ("yahoo_finance", "tradfi", 86400, 43200, 86400, "important"),
    ("openbb", "tradfi", 86400, 43200, 86400, "informational"),
    ("fred", "tradfi", 86400, 43200, 86400, "informational"),
    ("ecb", "tradfi", 86400, 43200, 86400, "informational"),
    ("ofr", "tradfi", 86400, 43200, 86400, "informational"),
    ("pinnacle", "sports", 300, 60, 30, "important"),
    ("odds_api", "sports", 300, 60, 30, "important"),
    ("betfair", "sports", 60, 15, 5, "important"),
    ("glassnode", "onchain", 3600, 1800, 3600, "important"),
    ("coinglass", "onchain", 3600, 1800, 3600, "important"),
]


@pytest.mark.parametrize(
    "key,asset_group,max_age,warn_age,cadence,criticality",
    _EXPECTED_MARKET_VENUES,
)
def test_market_tick_freshness_entry(
    key: str,
    asset_group: str,
    max_age: int,
    warn_age: int,
    cadence: int,
    criticality: str,
) -> None:
    assert key in MARKET_TICK_FRESHNESS, f"Missing venue: {key}"
    c = MARKET_TICK_FRESHNESS[key]
    assert c.source == key
    assert c.asset_group == asset_group
    assert c.max_age_seconds == max_age
    assert c.warn_age_seconds == warn_age
    assert c.expected_cadence_seconds == cadence
    assert c.criticality == criticality


def test_market_tick_freshness_count() -> None:
    assert len(MARKET_TICK_FRESHNESS) == len(_EXPECTED_MARKET_VENUES)


# ---------------------------------------------------------------------------
# FEATURE_FRESHNESS — parametrized per service
# ---------------------------------------------------------------------------

_EXPECTED_FEATURE_SERVICES = [
    ("features-delta-one-service", "feature", 120, 60, 60, "critical"),
    ("features-volatility-service", "feature", 300, 150, 60, "critical"),
    ("features-onchain-service", "feature", 600, 300, 300, "important"),
    ("features-calendar-service", "feature", 86400, 43200, 3600, "informational"),
    ("features-commodity-service", "feature", 3600, 1800, 3600, "informational"),
    ("features-cross-instrument-service", "feature", 300, 150, 60, "important"),
    ("features-multi-timeframe-service", "feature", 300, 150, 60, "critical"),
    ("features-sports-service", "feature", 300, 60, 60, "important"),
]


@pytest.mark.parametrize(
    "key,asset_group,max_age,warn_age,cadence,criticality",
    _EXPECTED_FEATURE_SERVICES,
)
def test_feature_freshness_entry(
    key: str,
    asset_group: str,
    max_age: int,
    warn_age: int,
    cadence: int,
    criticality: str,
) -> None:
    assert key in FEATURE_FRESHNESS, f"Missing feature service: {key}"
    c = FEATURE_FRESHNESS[key]
    assert c.source == key
    assert c.asset_group == asset_group
    assert c.max_age_seconds == max_age
    assert c.warn_age_seconds == warn_age
    assert c.expected_cadence_seconds == cadence
    assert c.criticality == criticality


def test_feature_freshness_count() -> None:
    assert len(FEATURE_FRESHNESS) == 8


# ---------------------------------------------------------------------------
# ML_FRESHNESS — parametrized per API
# ---------------------------------------------------------------------------

_EXPECTED_ML_ENTRIES = [
    ("ml-inference-api", "ml", 120, 60, 60, "critical"),
    ("ml-training-api", "ml", 604800, 259200, 86400, "informational"),
]


@pytest.mark.parametrize(
    "key,asset_group,max_age,warn_age,cadence,criticality",
    _EXPECTED_ML_ENTRIES,
)
def test_ml_freshness_entry(
    key: str,
    asset_group: str,
    max_age: int,
    warn_age: int,
    cadence: int,
    criticality: str,
) -> None:
    assert key in ML_FRESHNESS, f"Missing ML entry: {key}"
    c = ML_FRESHNESS[key]
    assert c.source == key
    assert c.asset_group == asset_group
    assert c.max_age_seconds == max_age
    assert c.warn_age_seconds == warn_age
    assert c.expected_cadence_seconds == cadence
    assert c.criticality == criticality


def test_ml_freshness_count() -> None:
    assert len(ML_FRESHNESS) == 2


# ---------------------------------------------------------------------------
# ALL_FRESHNESS_CONTRACTS — aggregate
# ---------------------------------------------------------------------------


def test_all_freshness_contracts_is_union() -> None:
    expected_count = len(MARKET_TICK_FRESHNESS) + len(FEATURE_FRESHNESS) + len(ML_FRESHNESS)
    assert len(ALL_FRESHNESS_CONTRACTS) == expected_count


def test_all_freshness_contracts_no_duplicates() -> None:
    # Each source key should appear in exactly one of the three sub-dicts
    market_keys = set(MARKET_TICK_FRESHNESS)
    feature_keys = set(FEATURE_FRESHNESS)
    ml_keys = set(ML_FRESHNESS)
    assert market_keys.isdisjoint(feature_keys)
    assert market_keys.isdisjoint(ml_keys)
    assert feature_keys.isdisjoint(ml_keys)


def test_all_freshness_contracts_contains_known_sources() -> None:
    for key in ("binance", "features-delta-one-service", "ml-inference-api"):
        assert key in ALL_FRESHNESS_CONTRACTS


# ---------------------------------------------------------------------------
# UIC top-level __init__ re-exports
# ---------------------------------------------------------------------------


def test_uic_init_exports_data_freshness_contract() -> None:
    from unified_api_contracts.internal import DataFreshnessContract as ImportedContract

    assert ImportedContract is DataFreshnessContract


def test_uic_init_exports_dicts() -> None:
    from unified_api_contracts.internal import (
        ALL_FRESHNESS_CONTRACTS as AFC,
    )
    from unified_api_contracts.internal import (
        FEATURE_FRESHNESS as FF,
    )
    from unified_api_contracts.internal import (
        MARKET_TICK_FRESHNESS as MTF,
    )
    from unified_api_contracts.internal import (
        ML_FRESHNESS as MLF,
    )

    assert MTF is MARKET_TICK_FRESHNESS
    assert FF is FEATURE_FRESHNESS
    assert MLF is ML_FRESHNESS
    assert AFC is ALL_FRESHNESS_CONTRACTS
