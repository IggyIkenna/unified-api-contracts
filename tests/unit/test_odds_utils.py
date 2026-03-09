from datetime import UTC, datetime
from decimal import Decimal

from unified_api_contracts import (
    CanonicalComboBet,
    CanonicalComboLeg,
    OddsFormat,
    american_to_decimal,
    decimal_to_american,
)


def test_american_to_decimal_positive():
    assert american_to_decimal(100) == Decimal("2.0")


def test_american_to_decimal_negative():
    result = american_to_decimal(-110)
    assert abs(result - Decimal("1.9090909090909090")) < Decimal("0.001")


def test_decimal_to_american_ge2():
    assert decimal_to_american(Decimal("2.0")) == 100


def test_decimal_to_american_lt2():
    assert decimal_to_american(Decimal("1.5")) == -200


def test_combo_bet_negative_net_premium():
    """net_premium on CanonicalComboBet may be negative (options combos)."""
    leg = CanonicalComboLeg(
        venue="DERIBIT",
        market_id="BTC-CALL-50000",
        selection_id="sel1",
        side="back",
        decimal_odds=Decimal("2.0"),
        stake=Decimal("100"),
    )
    bet = CanonicalComboBet(
        venue="DERIBIT",
        order_id="ord1",
        legs=(leg,),
        combined_decimal_odds=Decimal("2.0"),
        total_stake=Decimal("100"),
        net_premium=Decimal("-5.50"),  # negative premium — short leg > long leg
        status="OPEN",
        timestamp=datetime.now(UTC),
    )
    assert bet.net_premium == Decimal("-5.50")


def test_odds_format_enum():
    leg = CanonicalComboLeg(
        venue="BETFAIR",
        market_id="m1",
        selection_id="s1",
        side="back",
        decimal_odds=Decimal("1.91"),
        stake=Decimal("10"),
        odds_format=OddsFormat.DECIMAL,
    )
    assert leg.odds_format == OddsFormat.DECIMAL
