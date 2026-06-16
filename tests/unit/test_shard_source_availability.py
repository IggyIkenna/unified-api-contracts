"""Unit tests for the per-shard source-availability registry + ``could_exist`` (M3).

Asserts :func:`could_exist` is ``True`` for a genuinely-possible
``(asset_group, data_type, mode)`` and ``False`` for an impossible one (a
batch-only source asked for ``LIVE``, or a shard with no registered sources).
"""

from __future__ import annotations

from unified_api_contracts import could_exist as could_exist_facade
from unified_api_contracts.canonical.crosscutting.pipeline_mode import Mode
from unified_api_contracts.canonical.crosscutting.shard_source_availability import (
    could_exist,
    sources_for_shard,
)
from unified_api_contracts.canonical.crosscutting.source_priority import modes_for_source

# ---------------------------------------------------------------------------
# Import-surface facade
# ---------------------------------------------------------------------------


def test_could_exist_importable_from_root_facade() -> None:
    """``from unified_api_contracts import could_exist`` works (import-surface rule)."""
    assert could_exist_facade is could_exist


# ---------------------------------------------------------------------------
# sources_for_shard
# ---------------------------------------------------------------------------


def test_sources_for_shard_cefi_trades_unions_batch_and_live_venues() -> None:
    """A CeFi trades shard carries the BATCH source (tardis) AND the live venues."""
    sources = sources_for_shard("cefi", "trades")
    assert "tardis" in sources  # batch (SOURCE_PRIORITY)
    assert "binance" in sources  # live/replay overlay (CEFI_LIVE_VENUES)
    assert "deribit" in sources


def test_sources_for_shard_unregistered_is_empty() -> None:
    """An unregistered shard yields no sources (non-raising soft guardrail)."""
    assert sources_for_shard("tradfi", "no_such_data_type") == frozenset()


def test_sources_for_shard_non_cefi_has_no_venue_overlay() -> None:
    """The CeFi venue overlay must NOT leak into non-cefi shards."""
    sources = sources_for_shard("tradfi", "trades")
    assert sources == frozenset({"massive", "databento"})
    assert "binance" not in sources


# ---------------------------------------------------------------------------
# could_exist — POSSIBLE combinations -> True
# ---------------------------------------------------------------------------


def test_could_exist_cefi_trades_batch_is_true() -> None:
    """CeFi trades x BATCH is possible (tardis is a batch source)."""
    assert could_exist("cefi", "trades", Mode.BATCH) is True


def test_could_exist_cefi_trades_live_is_true() -> None:
    """CeFi trades x LIVE is possible (the exchange venues stream live)."""
    assert could_exist("cefi", "trades", Mode.LIVE) is True


def test_could_exist_tradfi_trades_replay_is_true() -> None:
    """TradFi trades x REPLAY is possible (massive/databento are replay-capable)."""
    assert could_exist("tradfi", "trades", Mode.REPLAY) is True


# ---------------------------------------------------------------------------
# could_exist — IMPOSSIBLE combinations -> False
# ---------------------------------------------------------------------------


def test_could_exist_batch_only_source_live_is_false() -> None:
    """A batch-only-source shard asked for LIVE is impossible.

    ``understat`` is ``{BATCH, REPLAY}`` (no LIVE), so ``(sports, UNDERSTAT_XG)``
    cannot run LIVE — an honest absence, not a decision.
    """
    assert Mode.LIVE not in modes_for_source("understat")
    assert could_exist("sports", "UNDERSTAT_XG", Mode.LIVE) is False


def test_could_exist_unregistered_shard_is_false_for_every_mode() -> None:
    """A shard with no registered source can run no mode."""
    for mode in Mode:
        assert could_exist("tradfi", "no_such_data_type", mode) is False


# ---------------------------------------------------------------------------
# could_exist — per-(source, data_type) refinement (M2-REFINEMENT). The same
# shard reads a DIFFERENT mode set per data_type now that could_exist composes
# modes_for(source, data_type) (not the coarse modes_for_source).
# ---------------------------------------------------------------------------


def test_could_exist_cefi_funding_rates_live_is_false() -> None:
    """No CeFi source STREAMS funding live (none declares a ``ws_funding*`` op): the
    exchange venues only batch/REST-archive it and tardis is batch-only. The coarse
    per-source answer would (wrongly) say the live venues make LIVE reachable — the
    refinement makes this an honest ``False``.
    """
    assert could_exist("cefi", "funding_rates", Mode.LIVE) is False


def test_could_exist_cefi_funding_rates_batch_is_true() -> None:
    """Funding IS batch-capturable for cefi (hyperliquid REST-archives it) — only the
    LIVE axis is narrowed, never the BATCH floor."""
    assert could_exist("cefi", "funding_rates", Mode.BATCH) is True


def test_could_exist_cefi_trades_still_live_after_refinement() -> None:
    """The refinement must NOT break a genuinely-live data_type: trades stays LIVE
    (the venues declare ``ws_trades``)."""
    assert could_exist("cefi", "trades", Mode.LIVE) is True
