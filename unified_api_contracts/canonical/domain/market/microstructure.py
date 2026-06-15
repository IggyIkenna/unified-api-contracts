"""Canonical L2 order-book microstructure schemas (single-canonical).

These are the ONE wire/manifest shape that every source maps to — the live
venue-WebSocket book feed (Binance / OKX / Bybit / Deribit / Coinbase / Upbit)
AND the Tardis historical book archive. Per the workspace "Live = batch / Batch =
Live" rule an engine reading ``order_flow_imbalance`` / ``queue_position`` /
``depth_of_book_10`` MUST NOT be able to tell live from batch: same fields, same
units, ``available_at`` stamped per-row at write-time, no live-only field set, no
read-time derivation.

Derivation provenance (single-canonical, mirrors the greeks.py pattern)
-----------------------------------------------------------------------
The microstructure rows are MTDS-computed from the canonical ``book_snapshot_5``
(``OrderBookSnapshot5``) — the SAME book feed in batch (Tardis archive) and live
(venue WebSocket). The depth at which each field is *derivable* differs:

* **``order_flow_imbalance``** + **microprice** — derivable from the L5 book
  (``book_snapshot_5``) ALONE. Top-of-book and L5-aggregated bid/ask sizes give
  the imbalance ratio + the size-weighted microprice. These ship now.
* **``depth_of_book_10``** — requires an L10 (depth-10) book capture; the L5
  snapshot only carries 5 levels per side, so levels 6-10 are honestly absent
  (``None``) until a deeper book is captured. The field set is canonical either
  way; honest-absence omits the deeper levels rather than synthesising them.
* **``queue_position``** — requires per-price-level queue / order-by-order (full
  L2) capture that the aggregated L5 snapshot does not carry. Honest absence
  (``None``) until the deeper book lands. NEVER invented.

``imbalance`` is ``(bid_qty - ask_qty) / (bid_qty + ask_qty)`` over the captured
depth (∈ [-1, 1]); ``microprice`` = size-weighted top-of-book mid
``(bid_px·ask_qty + ask_px·bid_qty) / (bid_qty + ask_qty)``; ``spread`` =
``ask_px_0 - bid_px_0``; ``relative_spread`` = ``spread / mid``. All datetimes
are UTC-aware.

SSOT: codex/04-architecture/market-microstructure-feed.md § "Microstructure
snapshot canonical schema".
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import AwareDatetime, Field

from .._base import CanonicalBase


class CanonicalDepthLevel(CanonicalBase):
    """One price level of the depth-of-book ladder (bid or ask side).

    ``rank`` is 0-indexed from top-of-book. Carries the canonical per-level
    queue size; ``order_count`` is the number of resting orders at the level
    when the venue exposes it (full-L2 only — honest absence otherwise).
    """

    rank: int = Field(ge=0, description="0 = top-of-book; ascending into the book")
    price: Decimal
    size: Decimal = Field(description="Aggregate resting size at this level")
    order_count: int | None = Field(
        default=None, description="Resting order count at the level (full-L2 venues only; else honest-absent)"
    )


class CanonicalBookMicrostructure(CanonicalBase):
    """L2 order-book microstructure snapshot — the ``order_flow_imbalance`` /
    ``depth_of_book_10`` / ``queue_position`` data_type row.

    One row per (venue, instrument) at one snapshot time. The L5-derivable
    fields (``spread`` / ``relative_spread`` / ``imbalance`` / ``microprice``)
    are computed from the canonical ``book_snapshot_5``; the deeper-book fields
    (``depth_levels_bid`` / ``depth_levels_ask`` beyond rank 4,
    ``queue_position_bid`` / ``queue_position_ask``) are honestly absent
    (empty / ``None``) until an L10 / full-L2 capture exists. Identical shape
    regardless of source (venue live WS / Tardis batch) — batch == live.
    """

    instrument_key: str = Field(description="Canonical instrument key VENUE:TYPE:SYMBOL")
    venue: str
    as_of: AwareDatetime = Field(description="Snapshot time (UTC)")

    # ---- L5-derivable (always present when the L5 book is present) ----
    best_bid: Decimal | None = Field(default=None, description="Top-of-book bid price")
    best_ask: Decimal | None = Field(default=None, description="Top-of-book ask price")
    mid: Decimal | None = Field(default=None, description="(best_bid + best_ask) / 2")
    spread: Decimal | None = Field(default=None, description="best_ask - best_bid (absolute)")
    relative_spread: Decimal | None = Field(default=None, description="spread / mid (fractional)")
    microprice: Decimal | None = Field(
        default=None,
        description="Size-weighted TOB mid (bid_px*ask_qty + ask_px*bid_qty)/(bid_qty+ask_qty)",
    )
    imbalance: Decimal | None = Field(
        default=None, description="(bid_qty - ask_qty)/(bid_qty + ask_qty) over captured depth, in [-1, 1]"
    )
    captured_depth: int = Field(
        ge=0, description="Number of book levels per side this row was derived from (5 for an L5 source)"
    )

    # ---- Deeper-book fields — honest absence when only L5 is captured ----
    depth_levels_bid: list[CanonicalDepthLevel] = Field(
        default_factory=list,
        description="Bid ladder (rank 0..N). >5 levels need an L10 capture; honest-absent on L5.",
    )
    depth_levels_ask: list[CanonicalDepthLevel] = Field(
        default_factory=list,
        description="Ask ladder (rank 0..N). >5 levels need an L10 capture; honest-absent on L5.",
    )
    queue_position_bid: Decimal | None = Field(
        default=None,
        description="Aggregate resting size ahead at the best bid (full-L2 only; honest-absent on L5).",
    )
    queue_position_ask: Decimal | None = Field(
        default=None,
        description="Aggregate resting size ahead at the best ask (full-L2 only; honest-absent on L5).",
    )

    schema_version: str = "1.0"


__all__ = [
    "CanonicalBookMicrostructure",
    "CanonicalDepthLevel",
]
