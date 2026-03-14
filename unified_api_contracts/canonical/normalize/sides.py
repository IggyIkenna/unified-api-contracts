"""Side normalization — convert raw venue side strings/ints to canonical 'buy'/'sell'."""

from __future__ import annotations

from typing import Literal


def normalize_side(raw: str | int | None) -> Literal["buy", "sell"]:
    """Convert any venue side representation to lowercase canonical 'buy' or 'sell'.

    Handles:
    - String: "BUY", "buy", "B", "b", "bid", "long", "Long", "LONG" -> "buy"
    - String: "SELL", "sell", "S", "s", "ask", "short", "Short", "SHORT" -> "sell"
    - Integer: 1 -> "buy", 2 -> "sell" (Binance/Databento aggressor_side convention)
    - Integer: 0 -> "buy" (some venues use 0=buy)
    - Fallback: "buy"
    """
    if raw is None:
        return "buy"
    if isinstance(raw, int):
        return "sell" if raw == 2 else "buy"
    s = str(raw).strip().upper()
    if s in ("SELL", "S", "ASK", "SHORT", "SELLER", "SOLD", "2"):
        return "sell"
    return "buy"


__all__ = ["normalize_side"]
