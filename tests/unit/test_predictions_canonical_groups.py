"""Unit tests for the predictions canonical-question-group SSOT.

Predictions plan
``predictions_canonical_question_group_polymarket_migration_2026_05_06.md``
Phase 1A.
"""

from __future__ import annotations

import datetime as _dt

from unified_api_contracts.canonical.crosscutting.honest_coverage import (
    BUNDLED_DATA_TYPES,
    DATA_TYPE_TO_CLUSTER_REGISTRY,
    PREDICTION_GROUPS,
)
from unified_api_contracts.predictions import (
    CANONICAL_GROUP_METADATA,
    CLASSIFIER_STABILITY_HASH,
    KALSHI_TICKER_TO_GROUP,
    POLYMARKET_CONDITION_ID_TO_GROUP,
    CanonicalGroupMetadata,
    CanonicalQuestionGroup,
    MarketLifecycle,
    classify_kalshi_to_canonical_group,
    classify_polymarket_to_canonical_group,
    expected_market_ids_for_canonical_group,
    is_market_active_at,
)

# ---------------------------------------------------------------------------
# CanonicalQuestionGroup + CanonicalGroupMetadata
# ---------------------------------------------------------------------------


def test_every_canonical_group_has_metadata() -> None:
    """Every enum member is keyed in CANONICAL_GROUP_METADATA."""
    for group in CanonicalQuestionGroup:
        assert group in CANONICAL_GROUP_METADATA
        meta = CANONICAL_GROUP_METADATA[group]
        assert isinstance(meta, CanonicalGroupMetadata)
        assert meta.group == group
        assert meta.expected_market_ids_per_day >= 0


def test_metadata_cadence_lit_set() -> None:
    """Cadence values are within the documented literal set."""
    valid = {"hourly", "daily", "weekly", "monthly", "irregular", "single"}
    for meta in CANONICAL_GROUP_METADATA.values():
        assert meta.cadence in valid


def test_hourly_groups_expect_24_per_day() -> None:
    assert CANONICAL_GROUP_METADATA[CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY].expected_market_ids_per_day == 24
    assert CANONICAL_GROUP_METADATA[CanonicalQuestionGroup.ETH_UP_DOWN_HOURLY].expected_market_ids_per_day == 24


def test_daily_groups_expect_1_per_day() -> None:
    for group in (
        CanonicalQuestionGroup.BTC_UP_DOWN_DAILY,
        CanonicalQuestionGroup.ETH_UP_DOWN_DAILY,
        CanonicalQuestionGroup.SPX_UP_DOWN_DAILY,
    ):
        assert CANONICAL_GROUP_METADATA[group].expected_market_ids_per_day == 1


# ---------------------------------------------------------------------------
# Classifier — rule-based mapping for the canonical happy paths
# ---------------------------------------------------------------------------


def test_classify_btc_hourly_range_bracket() -> None:
    """``btc-up-or-down-hourly-april-15`` slug maps to BTC_UP_DOWN_HOURLY."""
    group = classify_polymarket_to_canonical_group(
        title="Will BTC be up or down at 12pm UTC?",
        slug="btc-up-or-down-hourly-april-15",
        event_slug="btc-price-hourly",
        outcome="Up",
    )
    assert group == CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY


def test_classify_eth_daily_range_bracket() -> None:
    """``eth-up-or-down-daily`` slug maps to ETH_UP_DOWN_DAILY."""
    group = classify_polymarket_to_canonical_group(
        title="Will ETH be up or down today?",
        slug="eth-up-or-down-daily",
        event_slug="eth-price-daily",
        outcome="Down",
    )
    assert group == CanonicalQuestionGroup.ETH_UP_DOWN_DAILY


def test_classify_cme_linked_groups_daily() -> None:
    """7 CME-linked groups (predictions_master Phase 5) classify from real Polymarket slugs."""
    cases: list[tuple[str, str, str, str, CanonicalQuestionGroup]] = [
        # (title, slug, event_slug, outcome, expected_group)
        (
            "Will NDX be up or down today?",
            "ndx-daily-up-or-down",
            "ndx-price-daily",
            "Up",
            CanonicalQuestionGroup.NDX_UP_DOWN_DAILY,
        ),
        (
            "Will DJIA be up or down today?",
            "dow-jones-daily-up-or-down",
            "djia-price-daily",
            "Down",
            CanonicalQuestionGroup.DJIA_UP_DOWN_DAILY,
        ),
        (
            "Will Russell 2000 be up or down?",
            "rut-daily-up-or-down",
            "rut-price-daily",
            "Up",
            CanonicalQuestionGroup.RUT_UP_DOWN_DAILY,
        ),
        (
            "Will Gold be up or down today?",
            "gold-daily-up-or-down",
            "gold-price-daily",
            "Up",
            CanonicalQuestionGroup.GOLD_UP_DOWN_DAILY,
        ),
        (
            "Will Crude Oil be up or down today?",
            "crude-oil-daily-up-or-down",
            "oil-price-daily",
            "Down",
            CanonicalQuestionGroup.CRUDE_OIL_UP_DOWN_DAILY,
        ),
        (
            "Will Natural Gas be up or down today?",
            "nat-gas-daily-up-or-down",
            "natgas-price-daily",
            "Up",
            CanonicalQuestionGroup.NATGAS_UP_DOWN_DAILY,
        ),
        (
            "Will EUR/USD be up or down today?",
            "eur-usd-daily-up-or-down",
            "eurusd-price-daily",
            "Down",
            CanonicalQuestionGroup.EUR_UP_DOWN_DAILY,
        ),
    ]
    for title, slug, event_slug, outcome, expected in cases:
        group = classify_polymarket_to_canonical_group(
            title=title,
            slug=slug,
            event_slug=event_slug,
            outcome=outcome,
        )
        assert group == expected, f"Expected {expected} for slug={slug!r}, got {group!r}"


def test_classify_russell_2000_slug_variant() -> None:
    """russell-2000- slug prefix also maps to RUT_UP_DOWN_DAILY."""
    group = classify_polymarket_to_canonical_group(
        title="Will Russell 2000 be up or down at close?",
        slug="russell-2000-daily-up-or-down",
        event_slug="russell-2000-price-daily",
        outcome="Up",
    )
    assert group == CanonicalQuestionGroup.RUT_UP_DOWN_DAILY


def test_classify_eth_monthly_returns_none_no_canonical_group() -> None:
    """Monthly resolution period has no canonical group → None.

    The canonical group enum only covers HOURLY + DAILY range-bracket
    cadences for crypto-up-down markets; MONTHLY markets exist on
    Polymarket but don't yet have a canonical group seeded. Caller
    routes such markets to ``attempted_failed[reason=ClassifierConfidenceLow]``.
    """
    group = classify_polymarket_to_canonical_group(
        title="Will ETH be up or down by end of April?",
        slug="eth-up-or-down-april",
        event_slug="eth-monthly",
        outcome="Up",
    )
    assert group is None


def test_classify_unknown_returns_none() -> None:
    """A slug the rule classifier can't map → None (caller flags low confidence)."""
    group = classify_polymarket_to_canonical_group(
        title="Will Mars be colonised by 2030?",
        slug="mars-colonised-by-2030",
        event_slug="space-colonisation",
        outcome="Yes",
    )
    assert group is None


def test_classify_polymarket_condition_id_override_wins() -> None:
    """A conditionId in the override dict bypasses rule-classification."""
    fake_id = "0xfake_condition_id_for_btc_up_down_hourly_test"
    POLYMARKET_CONDITION_ID_TO_GROUP[fake_id] = CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY
    try:
        group = classify_polymarket_to_canonical_group(
            title="totally unrelated question",
            slug="something-else-entirely",
            event_slug="off-topic",
            outcome="Yes",
            condition_id=fake_id,
        )
        assert group == CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY
    finally:
        del POLYMARKET_CONDITION_ID_TO_GROUP[fake_id]


def test_classify_kalshi_unknown_returns_none() -> None:
    assert classify_kalshi_to_canonical_group(ticker="UNKNOWN-TICKER-001") is None


def test_classify_kalshi_override_wins() -> None:
    fake_ticker = "FAKEFEDDEC25"
    KALSHI_TICKER_TO_GROUP[fake_ticker] = CanonicalQuestionGroup.FED_RATE_DECISION_PER_FOMC
    try:
        assert (
            classify_kalshi_to_canonical_group(ticker=fake_ticker) == CanonicalQuestionGroup.FED_RATE_DECISION_PER_FOMC
        )
    finally:
        del KALSHI_TICKER_TO_GROUP[fake_ticker]


# ---------------------------------------------------------------------------
# Stability hash
# ---------------------------------------------------------------------------


def test_classifier_stability_hash_is_deterministic() -> None:
    """Re-import yields the same hash (regex + override sources unchanged)."""
    from unified_api_contracts.predictions import (
        CLASSIFIER_STABILITY_HASH as SECOND_READ,
    )

    assert SECOND_READ == CLASSIFIER_STABILITY_HASH


def test_classifier_stability_hash_is_hex() -> None:
    """SHA-256 truncated hexdigest — 16 lowercase hex characters."""
    assert len(CLASSIFIER_STABILITY_HASH) == 16
    int(CLASSIFIER_STABILITY_HASH, 16)  # raises ValueError if non-hex


# ---------------------------------------------------------------------------
# Lifecycle helpers
# ---------------------------------------------------------------------------


_UTC = _dt.UTC


def _make_lifecycle(
    *,
    market_id: str = "MKT-1",
    canonical_group: CanonicalQuestionGroup = CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY,
    created: _dt.datetime,
    resolved: _dt.datetime,
    settled: _dt.datetime,
    status: str = "active",
) -> MarketLifecycle:
    return MarketLifecycle(
        market_id=market_id,
        venue="POLYMARKET",
        canonical_group=canonical_group,
        market_created_at=created,
        resolution_time=resolved,
        settlement_time=settled,
        current_status=status,  # pyright: ignore[reportArgumentType]
    )


def test_is_market_active_at_during_window() -> None:
    lc = _make_lifecycle(
        created=_dt.datetime(2026, 5, 6, 10, 0, tzinfo=_UTC),
        resolved=_dt.datetime(2026, 5, 6, 11, 0, tzinfo=_UTC),
        settled=_dt.datetime(2026, 5, 6, 13, 0, tzinfo=_UTC),
    )
    assert is_market_active_at(lc, _dt.datetime(2026, 5, 6, 10, 30, tzinfo=_UTC))


def test_is_market_active_at_before_creation() -> None:
    lc = _make_lifecycle(
        created=_dt.datetime(2026, 5, 6, 10, 0, tzinfo=_UTC),
        resolved=_dt.datetime(2026, 5, 6, 11, 0, tzinfo=_UTC),
        settled=_dt.datetime(2026, 5, 6, 13, 0, tzinfo=_UTC),
    )
    assert not is_market_active_at(lc, _dt.datetime(2026, 5, 6, 9, 59, tzinfo=_UTC))


def test_is_market_active_at_after_settlement() -> None:
    lc = _make_lifecycle(
        created=_dt.datetime(2026, 5, 6, 10, 0, tzinfo=_UTC),
        resolved=_dt.datetime(2026, 5, 6, 11, 0, tzinfo=_UTC),
        settled=_dt.datetime(2026, 5, 6, 13, 0, tzinfo=_UTC),
    )
    assert not is_market_active_at(lc, _dt.datetime(2026, 5, 6, 13, 1, tzinfo=_UTC))


def test_expected_market_ids_for_canonical_group_overlap() -> None:
    """Lifecycle whose [created, settled) overlaps the day → market_id included."""
    day = _dt.date(2026, 5, 6)
    lifecycles = [
        _make_lifecycle(
            market_id="MKT-OVERLAP",
            created=_dt.datetime(2026, 5, 5, 23, 30, tzinfo=_UTC),
            resolved=_dt.datetime(2026, 5, 6, 0, 30, tzinfo=_UTC),
            settled=_dt.datetime(2026, 5, 6, 2, 30, tzinfo=_UTC),
        ),
        _make_lifecycle(
            market_id="MKT-BEFORE",
            created=_dt.datetime(2026, 5, 4, 10, 0, tzinfo=_UTC),
            resolved=_dt.datetime(2026, 5, 4, 11, 0, tzinfo=_UTC),
            settled=_dt.datetime(2026, 5, 5, 13, 0, tzinfo=_UTC),
        ),
        _make_lifecycle(
            market_id="MKT-AFTER",
            created=_dt.datetime(2026, 5, 7, 10, 0, tzinfo=_UTC),
            resolved=_dt.datetime(2026, 5, 7, 11, 0, tzinfo=_UTC),
            settled=_dt.datetime(2026, 5, 7, 13, 0, tzinfo=_UTC),
        ),
    ]
    result = expected_market_ids_for_canonical_group(CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY, day, lifecycles)
    assert result == {"MKT-OVERLAP"}


def test_expected_market_ids_filters_by_canonical_group() -> None:
    day = _dt.date(2026, 5, 6)
    lifecycles = [
        _make_lifecycle(
            market_id="BTC-MKT",
            canonical_group=CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY,
            created=_dt.datetime(2026, 5, 6, 10, 0, tzinfo=_UTC),
            resolved=_dt.datetime(2026, 5, 6, 11, 0, tzinfo=_UTC),
            settled=_dt.datetime(2026, 5, 6, 13, 0, tzinfo=_UTC),
        ),
        _make_lifecycle(
            market_id="ETH-MKT",
            canonical_group=CanonicalQuestionGroup.ETH_UP_DOWN_HOURLY,
            created=_dt.datetime(2026, 5, 6, 10, 0, tzinfo=_UTC),
            resolved=_dt.datetime(2026, 5, 6, 11, 0, tzinfo=_UTC),
            settled=_dt.datetime(2026, 5, 6, 13, 0, tzinfo=_UTC),
        ),
    ]
    btc_only = expected_market_ids_for_canonical_group(CanonicalQuestionGroup.BTC_UP_DOWN_HOURLY, day, lifecycles)
    assert btc_only == {"BTC-MKT"}


# ---------------------------------------------------------------------------
# PREDICTION_GROUPS registry consistency with CanonicalQuestionGroup
# ---------------------------------------------------------------------------


def test_prediction_groups_registry_keys_match_canonical_enum() -> None:
    """Every PREDICTION_GROUPS key matches an enum value (except OTHER)."""
    enum_values = {g.value for g in CanonicalQuestionGroup if g != CanonicalQuestionGroup.OTHER}
    registry_keys = set(PREDICTION_GROUPS.keys())
    # Registry keys must be a subset of enum values (OTHER intentionally absent).
    assert registry_keys <= enum_values


def test_prediction_canonical_question_group_in_bundled_data_types() -> None:
    """The bundled-data_type set names the prediction shard data_type."""
    assert "prediction_canonical_question_group" in BUNDLED_DATA_TYPES
    assert DATA_TYPE_TO_CLUSTER_REGISTRY["prediction_canonical_question_group"] == "PREDICTION_GROUPS"


def test_prediction_groups_have_per_market_min_rows() -> None:
    """Every populated PREDICTION_GROUPS entry carries the min-rows floor."""
    for group_name, registry in PREDICTION_GROUPS.items():
        assert "_per_market_min_rows" in registry, group_name
        assert registry["_per_market_min_rows"] > 0


# ---------------------------------------------------------------------------
# _MONTHLY_TOKENS bug fix — "may" full-name now in the set
# ---------------------------------------------------------------------------


def test_monthly_tokens_includes_may_full_name() -> None:
    """2026-05-06 bug fix: "may" was missing from the full-name set."""
    from unified_api_contracts.internal.schemas._prediction_market_taxonomy import (
        _MONTHLY_TOKENS,
    )

    assert "may" in _MONTHLY_TOKENS
    # Sanity: full names alongside "may"
    assert "april" in _MONTHLY_TOKENS
    assert "june" in _MONTHLY_TOKENS
