"""CFTC Commitments of Traders (COT) report schemas.

Source: https://www.cftc.gov/MarketReports/CommitmentsofTraders/index.htm
Format: CSV, released every Friday ~15:30 ET for positions as of Tuesday.
Authentication: None required (public).

The Disaggregated COT report (used here) breaks positions into:
  Producer/Merchant/Processor/User, Swap Dealers, Managed Money, Other Reportables.
features-commodity-service uses the Managed Money category as the primary positioning signal.
"""

from __future__ import annotations

__api_version__ = "v1"

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class CFTCCOTReport:
    """Raw Disaggregated COT report row for a single commodity.

    commodity: CFTC commodity name (e.g. 'NATURAL GAS - NEW YORK MERCANTILE EXCHANGE')
    report_date: Tuesday as-of date (report released 3 days later on Friday)
    All long/short fields are number of contracts (open interest).
    """

    commodity: str
    report_date: date
    managed_money_long: int
    managed_money_short: int
    managed_money_net: int  # long - short
    managed_money_spreading: int  # spread positions (long one expiry, short another)
    producer_long: int
    producer_short: int
    swap_dealer_long: int
    swap_dealer_short: int
    other_reportable_long: int
    other_reportable_short: int
    open_interest_total: int
    retrieved_at: datetime


@dataclass
class CFTCManagedMoneyPosition:
    """Derived managed money positioning view with squeeze/momentum metrics.

    Derived from CFTCCOTReport; computed by features-commodity-service cot.py factor.
    net: managed_money_long - managed_money_short (current week)
    net_change_wow: net - prior_week_net
    squeeze_score: normalised net position in [-1.0, 1.0]
      +1.0 = maximally net-long (historically bullish signal)
      -1.0 = maximally net-short (historically bearish signal)
      normalisation: tanh(net / rolling_52wk_std_of_net)
    """

    commodity: str
    report_date: date
    net: int
    net_change_wow: int
    squeeze_score: float  # in [-1.0, 1.0]
