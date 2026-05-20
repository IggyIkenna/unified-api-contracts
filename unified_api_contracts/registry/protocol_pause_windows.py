"""DeFi protocol pause windows — operator-fillable SSOT.

For DeFi venues that were operational both before and after a documented
date range but PAUSED during it (intentional migration, chain-level outage,
governance pause). The oracle's `expected_coverage()` reads this registry
to honest-down those cells to `EXPECTED_PROTOCOL_PAUSED` rather than
flagging them as `MISSING_EXPECTED`.

Distinct from:

- ``capability_declarations._defi_coverage.EMPTY_OR_DEPRECATED_DEFI_VENUES``
  — venue-level permanent retirement (e.g. TRADER_JOEV2-AVALANCHE).
- ``EXPECTED_PRE_VENUE_LAUNCH`` / ``EXPECTED_PRE_GENESIS_CHAIN`` — date is
  before the venue / chain existed at all.
- ``EXPECTED_DEPRECATED_DATA_TYPE`` — data_type retired but venue still live.

This is **temporary pause with known resume**.

**Operator-fillable**: the initial registry is sparse — populate as new
pauses are discovered. Suggested seeds (operator to confirm exact windows):

- Aave V2 deprecation on Ethereum (~2024 Q1).
- Compound V2 wind-down on most chains (~late 2024).
- Solana chain-level outages (2022-09-30, 2023-02-25, etc.).
- Polygon Bor halts.
- Optimism / Arbitrum sequencer downtimes.

Mega-audit Phase A2 round 3 — closes R8 partial. CLAUDE.md "Data Pipeline
Correctness Is The Heartbeat" HARD RULE: only operator can populate this
registry; agents surface candidates via plan todos.
"""

from __future__ import annotations

from datetime import date


# Per (protocol_token, chain_token) → list of (start, end) inclusive date ranges.
# Tokens are workspace-canonical UPPERCASE (matching EXPECTED_COVERAGE_BY_ASSET_GROUP
# venue tokens — e.g. "AAVEV3-ETHEREUM" splits to ("AAVEV3", "ETHEREUM")).
#
# Initial seed: EMPTY — operator fills as candidates surface from A3 anomalies
# + on-chain research. Each addition MUST cite the source of truth
# (governance vote, official announcement, on-chain proof).
PROTOCOL_PAUSE_WINDOWS: dict[tuple[str, str], list[tuple[date, date]]] = {
    # Example shape (uncomment + edit when operator confirms a pause window):
    # ("AAVEV2", "ETHEREUM"): [
    #     (date(2024, 1, 1), date(2024, 3, 31)),  # V2→V3 deprecation period
    # ],
    # ("COMPOUNDV2", "ETHEREUM"): [
    #     (date(2024, 9, 1), date(2024, 12, 31)),  # V2 wind-down
    # ],
}


def is_protocol_paused(protocol: str, chain: str, target_date: date) -> tuple[bool, str | None]:
    """Return (is_paused, window_description).

    True if `target_date` falls inside a documented (protocol, chain) pause window.
    `window_description` is a human-readable annotation for the diagnostic field.
    """
    key = (protocol.upper(), chain.upper())
    windows = PROTOCOL_PAUSE_WINDOWS.get(key)
    if not windows:
        return False, None
    for start, end in windows:
        if start <= target_date <= end:
            return True, f"{protocol}-{chain} paused {start.isoformat()} → {end.isoformat()}"
    return False, None


__all__ = ["PROTOCOL_PAUSE_WINDOWS", "is_protocol_paused"]
