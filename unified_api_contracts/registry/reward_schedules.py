"""Reward schedule registry — protocol reward token metadata and sell routing."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class RewardScheduleEntry:
    """A single protocol reward schedule entry."""

    protocol: str
    reward_token: str
    reward_token_address: str
    frequency: str  # WEEKLY, QUARTERLY, CONTINUOUS
    description: str
    sell_venue: str
    sell_pair: str


REWARD_SCHEDULES: list[RewardScheduleEntry] = [
    RewardScheduleEntry(
        protocol="EIGENLAYER",
        reward_token="EIGEN",
        reward_token_address="0xec53bF9167f50cDEB3Ae105f56099aaaB9061F83",
        frequency="WEEKLY",
        description="EigenLayer restaking rewards via RewardsCoordinator",
        sell_venue="BINANCE",
        sell_pair="EIGEN-USDT",
    ),
    RewardScheduleEntry(
        protocol="ETHERFI",
        reward_token="ETHFI",
        reward_token_address="0xFe0c30065B384F05761f15d0CC899D4F9F9Cc0eB",
        frequency="QUARTERLY",
        description="EtherFi seasonal loyalty rewards",
        sell_venue="BINANCE",
        sell_pair="ETHFI-USDT",
    ),
]
