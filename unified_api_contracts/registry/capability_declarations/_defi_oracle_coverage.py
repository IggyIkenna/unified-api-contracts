"""Oracle coverage windows for DeFi price feeds.

SSOT for archive-coverage-start dates per oracle source. Mirrors the role
``CHAIN_GENESIS_DATES`` / ``LST_TOKEN_GENESIS`` play for chains / LSTs:
clips pre-coverage days from the data-status panel's expected denominator
so pre-archive dates don't render as ``missing`` and downstream backfills
don't waste calls on 404-returning windows.

Per Tab 14 fork1 prep audit 2026-05-08
(``plans/archive/issues/defi_fork1_prep_audit_2026_05_08.md``):

* Pyth Hermes archive at https://hermes.pyth.network/v2/updates/price/{publish_time}
  starts returning data on or about 2023-10-01. Pre-2023-10-01 timestamps return
  ``Update data not found`` (verified live 2026-05-08 via probes at multiple
  unix timestamps spanning 2023-08 to 2023-11 for the SOL/USD feed).

* jitoSOL pre-archive gap (2022-11-01 to 2023-10-01) -- the Pyth Hermes archive
  does NOT cover the ~11-month window between jitoSOL token genesis (2022-11-01,
  see ``LST_TOKEN_GENESIS["jitoSOL"]``) and Hermes archive start. **RESOLVED
  2026-07-27** (``plans/active/defi_onchain_derivable_values_and_date_drift_2026_06_20.md``
  P1, operator-stated default): CLIP -- backtests involving jitoSOL start no
  earlier than ``ORACLE_COVERAGE_START["pyth_hermes"]`` (2023-10-01); the
  slower/costlier Pythnet-RPC replay backfill for the pre-archive window is
  NOT pursued. A consumer wiring this default into an actual backtest-window
  derivation is separate, cross-craft follow-on work (not yet built anywhere
  in the codebase -- see that plan's Progress Log).

Consumers:
* MTDS ``oracle_prices_handler`` -- short-circuit Hermes fetches for
  pre-archive dates instead of issuing 404-returning calls.
* deployment-api / data-status -- clip the expected-coverage start so
  pre-archive dates don't render as ``missing`` in the UI.
"""

from __future__ import annotations

# Per-oracle archive coverage start dates. ISO YYYY-MM-DD.
ORACLE_COVERAGE_START: dict[str, str] = {
    # Pyth Hermes archive -- verified 2026-05-08 via Tab 14 audit + Tab 1
    # sub-agent probes at /v2/updates/price/{ts} for SOL/USD feed.
    # Pre-2023-10-01 timestamps return ``Update data not found``.
    "pyth_hermes": "2023-10-01",
    # Chainlink aggregator feeds are read ON-CHAIN via RPC (no archive-API floor
    # like Hermes), so this is a global conservative floor composed with each
    # chain's CHAIN_GENESIS_DATES / PROTOCOL_LAUNCH_DATES via max() by consumers:
    # 2020-01-01 = Chainlink ETH data feeds live era; later-genesis chains (Base
    # 2023-08, Optimism 2021-12, Arbitrum 2021-08, Polygon 2020-05) clip further
    # forward through their per-chain launch floors. Added 2026-07-20 (DeFi
    # catalogue canonicalization) alongside the CHAINLINK-<chain> oracle venues.
    "chainlink": "2020-01-01",
    # AAVE on-chain oracle (AaveOracle.getAssetPrice, read ON-CHAIN via RPC, no
    # archive-API floor). This is a NEW collection surface (2026-07-21, the
    # RPC call was dormant/unwired until lst_rate_honest_coverage plan Phase 1)
    # with no historical data captured yet, so the coverage-start floor is set
    # conservative to the registration date rather than to the reserves' own
    # on-chain genesis — a real backfill-start audit can pull it earlier once
    # Phase 5 runs. See codex/02-data/lst-exchange-rate-surfaces.md surface #3.
    "aave_oracle": "2026-07-21",
}


def get_oracle_coverage_start(oracle_source: str) -> str | None:
    """Return ISO YYYY-MM-DD archive coverage start for an oracle source.

    Case-insensitive on ``oracle_source``. Returns ``None`` for unknown
    sources so callers can fall back to a wider expected-window when the
    oracle isn't yet declared in the SSOT (over-clipping toward chain /
    token genesis is the safe direction per CLAUDE.md "Honest absence vs
    fake placeholders" rule).
    """
    return ORACLE_COVERAGE_START.get(oracle_source.lower()) if oracle_source else None


__all__ = [
    "ORACLE_COVERAGE_START",
    "get_oracle_coverage_start",
]
