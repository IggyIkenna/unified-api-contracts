"""DeFi protocol pause windows — DETECTOR-POPULATED (NOT operator-typed).

Operator directive 2026-05-20 round 4: "I can't just tell you when protocols
are out — it needs to be understood from data. Isn't that something
instruments-service can understand OR a script per chain which checks for
when outages occur using governance or otherwise?"

The right answer: outages are DERIVED FROM ON-CHAIN DATA, not operator-typed
into a static dict. This module is the **consumer-side cache** read by the
oracle; the writer is a detector pipeline (item R-NEW-6 in mega-audit
delegation SSOT).

## Architecture (target — implementation pending under R-NEW-6)

```
                              ┌─────────────────────────────────────┐
                              │  Sources of truth (on-chain)        │
                              │                                     │
  Existing in workspace:      │  • Aave/Compound/Uniswap governance │
  governance_events           │    events via The Graph subgraphs   │
  data_type per protocol      │    (MTDS handler:                   │
  (MTDS                       │    governance_events_handler.py)    │
  governance_events_          │  • Aave V3/Compound V3/Spark/Lido   │
  handler.py)                 │    proposals via Snapshot GraphQL   │
                              │    (MTDS handler:                   │
                              │    governance_proposals_handler.py) │
                              │  • Per-chain block-time anomalies   │
                              │    via RPC eth_getBlock              │
                              │    (not yet built — R-NEW-6)        │
                              └────────────────┬────────────────────┘
                                               │
                                               ▼
                              ┌─────────────────────────────────────┐
                              │  Detector pipeline (R-NEW-6)        │
                              │                                     │
                              │  • Filter governance_events for     │
                              │    Pause/Freeze action types        │
                              │    (ReserveFrozen, ReservePaused,   │
                              │    PauseAction, PoolPaused, etc.)   │
                              │  • Compute pause windows from       │
                              │    (start_event, end_event) pairs   │
                              │  • Per-chain: detect block-time     │
                              │    gaps > threshold (e.g. >1h on    │
                              │    Solana, >30min on EVM)           │
                              │  • Output: protocol_outages         │
                              │    data_type parquets per           │
                              │    (protocol, chain)                │
                              └────────────────┬────────────────────┘
                                               │
                                               ▼
                              ┌─────────────────────────────────────┐
                              │  This module (consumer-side cache)  │
                              │                                     │
                              │  PROTOCOL_PAUSE_WINDOWS dict is     │
                              │  REFRESHED periodically from the    │
                              │  detector's parquet output (e.g.    │
                              │  daily cron rebuilds the dict from  │
                              │  protocol_outages.parquet).         │
                              │                                     │
                              │  Empty initial state — populates    │
                              │  programmatically as detector       │
                              │  pipeline lands.                    │
                              └────────────────┬────────────────────┘
                                               │
                                               ▼
                              ┌─────────────────────────────────────┐
                              │  Oracle consumer                    │
                              │  (expected_coverage.py gate fires   │
                              │  EXPECTED_PROTOCOL_PAUSED when      │
                              │  is_protocol_paused returns True)   │
                              └─────────────────────────────────────┘
```

## Why detector-derived, not operator-typed

Per CLAUDE.md `External Data Is Always Available — Never Silently Defer
Adapters`: the data exists on-chain (governance events) + via chain RPC
(block-time anomalies). Operator typing in static dates would:

- Drift from on-chain truth as new pauses happen
- Mix operator judgment with data fact
- Bias the audit (operator can't enumerate every protocol-pause they don't
  remember)

The detector pipeline reads canonical sources, applies a deterministic
algorithm, outputs a deterministic registry. Operator role = approve the
detector's output spot-checks, not type dates.

## Outage-vs-pause distinction (HARD RULE for the detector)

Two genuinely different categories with different encoding rules:

- Chain-level outage (Solana 2022-09-30, Polygon Bor halts, Arbitrum
  sequencer down): hours to <1 day. Detector encodes? NO by default —
  flag operator-review-required if multi-protocol-multi-bucket impact.
  Too short to safely encode; high false-positive vs adapter bugs /
  rate limits / wrong sources. Single-day outages should surface as
  `DIVERGENT_EMPTY` → operator decides per-incident.
- Protocol pause (Aave V2 freeze, Curve emergency-pause, multi-day
  governance pauses): days to months; on-chain governance event source.
  Detector encodes? YES when governance event clearly fires
  Pause/Freeze + Unpause/Unfreeze pair. Officially documented;
  multi-day; on-chain provable; benefit of honest-down outweighs FP risk.

The detector defaults to **conservative** — only encode pauses where:

1. There is an on-chain governance event (ProposalExecuted with Pause action OR
   direct admin call to `setReserveFreeze(true)` / `_setPauseGuardian` / etc.).
2. The pause lasts ≥ 24 hours (operator-tunable threshold).
3. The end-event (Unpause/Unfreeze) is observed OR the pause extends past
   the audit window.

## Module contract

This module exposes:

- `PROTOCOL_PAUSE_WINDOWS: dict[tuple[str, str], list[tuple[date, date | None]]]`
  keyed by `(protocol, chain)` (workspace-canonical UPPERCASE tokens). Read
  by the oracle. Loaded from `registry/data/protocol_pause_windows_cache.json`
  at import time; **empty initial state** until detector first runs.
- `is_protocol_paused(protocol, chain, target_date) -> tuple[bool, str | None]`.
  Oracle calls this; returns (paused, human-readable-window-description).
  Ongoing windows (``end_date=None``) are treated as extending to the present.

Detector implementation lives in a separate slot per R-NEW-6 — see
`plans/audit/results/mega_audit_phase_a_issues_human_readable_2026_05_20.md`
§ Section 6.5 for the full owner/plan/verification spec.

Until the detector lands, this registry stays empty — the oracle gate
exists but never fires, which is the honest default (don't encode pauses
we can't prove from data).
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any, cast

# JSON cache written by market-tick-data-service scripts/refresh_protocol_pause_windows.py
# after each daily detect-protocol-outages batch run. Falls back to empty on first boot.
_CACHE_PATH = Path(__file__).parent / "data" / "protocol_pause_windows_cache.json"


def _load_cache() -> dict[tuple[str, str], list[tuple[date, date | None]]]:
    """Load protocol pause windows from the JSON cache. Returns empty dict if absent."""
    if not _CACHE_PATH.exists():
        return {}
    try:
        raw = cast(dict[str, Any], json.loads(_CACHE_PATH.read_text()))
        raw_windows = cast(dict[str, Any], raw.get("windows", {}))  # noqa: qg-empty-fallback
        result: dict[tuple[str, str], list[tuple[date, date | None]]] = {}
        for key_str, wins_raw in raw_windows.items():  # type: ignore[reportAny]
            wins_list = cast(list[dict[str, Any]], wins_raw)
            if "|" not in key_str:
                continue
            protocol, chain = key_str.split("|", 1)
            parsed: list[tuple[date, date | None]] = []
            for w_dict in wins_list:
                if not w_dict.get("start_date"):
                    continue
                start_date_raw = cast(str, w_dict["start_date"])
                start = date.fromisoformat(start_date_raw)
                end_raw = w_dict.get("end_date")
                end: date | None = date.fromisoformat(cast(str, end_raw)) if end_raw else None
                parsed.append((start, end))
            if parsed:
                result[(protocol, chain)] = parsed
        return result
    except Exception:
        return {}


# Detector-populated — DO NOT manually edit. Refreshed daily by
# refresh_protocol_pause_windows.py from GCS protocol_outages parquets.
# Empty initial state is correct + honest until the detector first runs.
PROTOCOL_PAUSE_WINDOWS: dict[tuple[str, str], list[tuple[date, date | None]]] = _load_cache()


def is_protocol_paused(protocol: str, chain: str, target_date: date) -> tuple[bool, str | None]:
    """Return (is_paused, window_description).

    Consumer interface — read by `expected_coverage()` oracle gate. Returns
    True when `target_date` falls inside a detector-confirmed pause window
    for `(protocol, chain)`. Ongoing windows (end_date=None) are treated as
    extending to the present. Detector refreshes the registry daily from
    on-chain governance events + chain RPC block-time anomalies.
    """
    key = (protocol.upper(), chain.upper())
    windows = PROTOCOL_PAUSE_WINDOWS.get(key)
    if not windows:
        return False, None
    for start, end in windows:
        end_check = end if end is not None else date.today()
        if start <= target_date <= end_check:
            end_desc = end.isoformat() if end is not None else "ongoing"
            return True, f"{protocol}-{chain} paused {start.isoformat()} → {end_desc} (detector-confirmed)"
    return False, None


__all__ = ["PROTOCOL_PAUSE_WINDOWS", "is_protocol_paused"]
