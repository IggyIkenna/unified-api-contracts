"""Public per-venue prediction-market trading fee model.

Kalshi and Polymarket charge per-trade fees that are distinct from the
per-client / prime-broker execution fees in
:mod:`unified_api_contracts.internal.reference.fee_schedule` (which models
maker/taker bps for CeFi venues). Prediction market fees are public, uniform,
and *price-dependent* (Kalshi) or zero (Polymarket), so they live here — in
the canonical predictions domain — as a versioned, capability-level constant.

Fee semantics (per YES share in probability/price units [0, 1])
--------------------------------------------------------------
* **Kalshi** — published general trading fee:
  ``fee = round_up( KALSHI_FEE_COEFF * C * P * (1 - P) )`` dollars for
  ``C`` contracts at YES price ``P``.  Per single contract (``C = 1``) the fee
  as a fraction of the $1 settlement notional is ``KALSHI_FEE_COEFF * P * (1 - P)``
  — a convex, mid-heavy curve (max ~1.75 ¢ at P=0.5, →0 at the tails).
* **Polymarket** — currently **0 trading fees** (maker and taker both 0;
  gas/relay is borne off-book).
* **Betfair** — sports *exchange* commission charged on **net winnings** of a
  winning bet (back or lay), not on stake/notional: ``fee = BETFAIR_COMMISSION_FRACTION * max(net_winnings, 0)``.
  The default 5% is the standard base rate; it is an operator-tunable model
  input (market-base rates vary and are reduced by loyalty discounts).

Versioning
----------
:data:`PREDICTION_VENUE_FEE_MODEL_VERSION` is stamped on every arb-store row
so a fee-schedule change is auditable across the stored corpus.  Bump the
constant whenever *any* coefficient below changes.

Source: ``help.kalshi.com`` fee schedule (accessed 2026-06).
"""

from __future__ import annotations

__all__ = [
    "BETFAIR_COMMISSION_FRACTION",
    "KALSHI_FEE_COEFF",
    "POLYMARKET_FEE_FRACTION",
    "PREDICTION_VENUE_FEE_MODEL_VERSION",
    "betfair_fee",
    "kalshi_fee",
    "net_edge_sell_kalshi",
    "net_edge_sell_polymarket",
    "polymarket_fee",
]

# Bump whenever a coefficient below changes; persisted per arb-store row.
PREDICTION_VENUE_FEE_MODEL_VERSION: str = "v2_public_2026_07_kalshi0.07_poly0_betfair0.05"

# Kalshi general trading fee coefficient (dimensionless): fee_per_contract = COEFF * P * (1 - P).
KALSHI_FEE_COEFF: float = 0.07
# Polymarket CLOB trading fee fraction (currently zero; both maker and taker).
POLYMARKET_FEE_FRACTION: float = 0.0
# Betfair exchange commission on NET winnings of a winning bet (base rate 5%);
# operator-tunable model input (see module docstring).
BETFAIR_COMMISSION_FRACTION: float = 0.05


def kalshi_fee(price: float) -> float:
    """Per-share Kalshi trading fee at YES execution ``price`` (price units [0, 1]).

    ``KALSHI_FEE_COEFF * P * (1 - P)`` — the published convex curve.
    Input is clamped to ``[0, 1]`` before applying the formula.
    """
    p = min(max(price, 0.0), 1.0)
    return KALSHI_FEE_COEFF * p * (1.0 - p)


def polymarket_fee(price: float) -> float:
    """Per-share Polymarket trading fee at YES execution ``price`` (currently 0)."""
    _ = price
    return POLYMARKET_FEE_FRACTION


def betfair_fee(net_winnings: float) -> float:
    """Betfair exchange commission on the ``net_winnings`` of a settled bet.

    ``BETFAIR_COMMISSION_FRACTION * max(net_winnings, 0)`` — commission is charged
    only on the *net* winnings of a *winning* bet (back or lay), never on stake or
    notional, so a losing/non-positive ``net_winnings`` yields ``0``. The 5%
    default is an operator-tunable model input (see module docstring).
    """
    return BETFAIR_COMMISSION_FRACTION * max(net_winnings, 0.0)


def net_edge_sell_kalshi(kalshi_yes_bid: float, polymarket_yes_ask: float) -> float:
    """Fee-net edge for SELL-YES-Kalshi / BUY-YES-Polymarket.

    ``raw = kalshi_bid - poly_ask``; subtract Kalshi fee on the bid leg
    (Polymarket fee is 0).
    """
    raw = kalshi_yes_bid - polymarket_yes_ask
    return raw - kalshi_fee(kalshi_yes_bid) - polymarket_fee(polymarket_yes_ask)


def net_edge_sell_polymarket(polymarket_yes_bid: float, kalshi_yes_ask: float) -> float:
    """Fee-net edge for SELL-YES-Polymarket / BUY-YES-Kalshi.

    ``raw = poly_bid - kalshi_ask``; Polymarket fee is 0, Kalshi fee on the
    ask leg.
    """
    raw = polymarket_yes_bid - kalshi_yes_ask
    return raw - polymarket_fee(polymarket_yes_bid) - kalshi_fee(kalshi_yes_ask)
