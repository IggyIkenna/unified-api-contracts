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
    ACCOUNT_STATE_FRESHNESS,
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
            "execution",
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
    # Consolidated from 8 features-{family}-service entries; one canonical contract.
    ("features-service", "feature", 300, 150, 60, "critical"),
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
    assert len(FEATURE_FRESHNESS) == 1


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
    expected_count = (
        len(MARKET_TICK_FRESHNESS) + len(FEATURE_FRESHNESS) + len(ML_FRESHNESS) + len(ACCOUNT_STATE_FRESHNESS)
    )
    assert len(ALL_FRESHNESS_CONTRACTS) == expected_count


def test_all_freshness_contracts_no_duplicates() -> None:
    # Each source key should appear in exactly one of the sub-dicts
    market_keys = set(MARKET_TICK_FRESHNESS)
    feature_keys = set(FEATURE_FRESHNESS)
    ml_keys = set(ML_FRESHNESS)
    account_keys = set(ACCOUNT_STATE_FRESHNESS)
    assert market_keys.isdisjoint(feature_keys)
    assert market_keys.isdisjoint(ml_keys)
    assert market_keys.isdisjoint(account_keys)
    assert feature_keys.isdisjoint(ml_keys)
    assert feature_keys.isdisjoint(account_keys)
    assert ml_keys.isdisjoint(account_keys)


def test_all_freshness_contracts_contains_known_sources() -> None:
    for key in ("binance", "features-service", "ml-inference-api", "account_snapshot"):
        assert key in ALL_FRESHNESS_CONTRACTS


# ---------------------------------------------------------------------------
# refetch_action — Phase-2 self-healing binding (optional, defaults None)
# ---------------------------------------------------------------------------


def test_refetch_action_defaults_none() -> None:
    c = DataFreshnessContract(
        source="x",
        asset_group="crypto_cefi",
        max_age_seconds=10,
        warn_age_seconds=5,
        expected_cadence_seconds=1,
        criticality="critical",
    )
    assert c.refetch_action is None


def test_refetch_action_settable() -> None:
    c = DataFreshnessContract(
        source="x",
        asset_group="execution",
        max_age_seconds=120,
        warn_age_seconds=60,
        expected_cadence_seconds=60,
        criticality="critical",
        refetch_action="refetch-feed:account_snapshot",
    )
    assert c.refetch_action == "refetch-feed:account_snapshot"


# ---------------------------------------------------------------------------
# refetch_action binding contract (Phase-2 self-healing)
#
# Binding scheme: every critical/important feed binds to a stable action id
# ``refetch-feed:<source>``; informational feeds leave it None (no automated
# re-fetch path). The deployment-service ``refetch-feed`` Layer-0 action keys
# off this id (it parses ``<source>`` back out and looks up ALL_FRESHNESS_CONTRACTS).
# ---------------------------------------------------------------------------


def test_every_critical_or_important_feed_has_refetch_action() -> None:
    missing = [
        key
        for key, c in ALL_FRESHNESS_CONTRACTS.items()
        if c.criticality in ("critical", "important") and c.refetch_action is None
    ]
    assert missing == [], f"critical/important feeds missing refetch_action: {missing}"


def test_informational_feeds_have_no_refetch_action() -> None:
    bound = [
        key
        for key, c in ALL_FRESHNESS_CONTRACTS.items()
        if c.criticality == "informational" and c.refetch_action is not None
    ]
    assert bound == [], f"informational feeds must NOT bind a refetch_action: {bound}"


@pytest.mark.parametrize(
    "key,contract",
    sorted(ALL_FRESHNESS_CONTRACTS.items()),
)
def test_refetch_action_id_scheme_matches_source(key: str, contract: DataFreshnessContract) -> None:
    # Bound feeds use the canonical ``refetch-feed:<source>`` id so the Layer-0
    # action can round-trip <source> back to ALL_FRESHNESS_CONTRACTS[key].
    if contract.refetch_action is None:
        return
    assert contract.refetch_action == f"refetch-feed:{contract.source}"
    assert contract.source == key


# ---------------------------------------------------------------------------
# ACCOUNT_STATE_FRESHNESS — the critical account/position/recon feeds
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("source", ["account_snapshot", "positions_snapshot", "reconciliation_age"])
def test_account_state_feeds_are_critical_execution(source: str) -> None:
    c = ACCOUNT_STATE_FRESHNESS[source]
    assert c.source == source
    assert c.asset_group == "execution"
    assert c.criticality == "critical"
    # warn must precede max for a meaningful staleness band
    assert c.warn_age_seconds < c.max_age_seconds


def test_reconciliation_age_bands_match_sev_thresholds() -> None:
    # warn = SEV1 (20min), max = SEV0 (40min) — mirrors the shipped recon-age escalation
    recon = ACCOUNT_STATE_FRESHNESS["reconciliation_age"]
    assert recon.warn_age_seconds == 1200
    assert recon.max_age_seconds == 2400


def test_execution_asset_group_accepted() -> None:
    c = DataFreshnessContract(
        source="positions_snapshot",
        asset_group="execution",
        max_age_seconds=120,
        warn_age_seconds=60,
        expected_cadence_seconds=60,
        criticality="critical",
    )
    assert c.asset_group == "execution"


# ---------------------------------------------------------------------------
# UIC top-level __init__ re-exports
# ---------------------------------------------------------------------------


def test_uic_init_exports_data_freshness_contract() -> None:
    from unified_api_contracts.internal import DataFreshnessContract as ImportedContract

    assert ImportedContract is DataFreshnessContract


def test_uic_init_exports_dicts() -> None:
    from unified_api_contracts.internal import (
        ACCOUNT_STATE_FRESHNESS as ASF,
    )
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
    assert ASF is ACCOUNT_STATE_FRESHNESS
