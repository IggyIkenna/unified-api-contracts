"""Baker Hughes North America Rotary Rig Count report schemas.

Source: https://rigcount.bakerhughes.com/na-rig-count
Format: Excel/HTML table, released every Friday ~13:00 ET.
Authentication: None required (public page scrape).

The rig count is a lagging indicator of upstream supply expectations.
A rising gas rig count signals increased future production (bearish for prices over 6-12 months).
features-commodity-service uses WoW gas rig change normalised by 52-week std.
"""

from __future__ import annotations

__api_version__ = "v1"

from dataclasses import dataclass
from datetime import date, datetime


@dataclass
class BakerHughesRigCount:
    """Weekly Baker Hughes North America rig count.

    report_date: Friday release date (data as of same Friday)
    gas_rigs: active rotary rigs drilling for natural gas
    oil_rigs: active rotary rigs drilling for oil
    total_rigs: gas_rigs + oil_rigs + miscellaneous
    gas_rigs_wow_change: gas_rigs - prior_week_gas_rigs
    oil_rigs_wow_change: oil_rigs - prior_week_oil_rigs
    """

    report_date: date
    gas_rigs: int
    oil_rigs: int
    total_rigs: int
    gas_rigs_wow_change: int
    oil_rigs_wow_change: int
    retrieved_at: datetime
