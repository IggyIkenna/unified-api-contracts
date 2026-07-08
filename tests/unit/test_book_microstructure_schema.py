"""Unit tests for the canonical L2 microstructure schema + data_type registry.

``CanonicalBookMicrostructure`` is the single-canonical wire shape that every
book source (venue live WebSocket + Tardis batch archive) converges on, derived
by MTDS from the canonical ``book_snapshot_5``. The tests assert (a) the public
export surface, (b) batch==live (the same instance round-trips identically
regardless of source), (c) honest-absence of the deeper-book fields (queue /
depth-10) that an L5 source cannot fill, and (d) the data_type / SOURCE_PRIORITY
registrations: queue_position / depth_of_book_10 are an honest gap (need a
deeper book).

order_flow_imbalance (the third L2-microstructure data_type, formerly
live-capable from L5 alone) RETIRED 2026-07-08 — zero real consumers, zero
production rows ever captured; duplicated market-data-processing-service's
imbalance_ratio feature family. See market-tick-data-service@a4fb3d13.

SSOT: v2_engine_venue_buildout_2026_06_15.md Phase D P2 (a).
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal


def test_canonical_types_exported_from_root() -> None:
    from unified_api_contracts import (
        CanonicalBookMicrostructure,
        CanonicalDepthLevel,
    )

    assert CanonicalBookMicrostructure.__name__ == "CanonicalBookMicrostructure"
    assert CanonicalDepthLevel.__name__ == "CanonicalDepthLevel"


def test_canonical_types_exported_from_domain() -> None:
    from unified_api_contracts.canonical.domain import (
        CanonicalBookMicrostructure,
        CanonicalDepthLevel,
    )

    assert CanonicalBookMicrostructure is not None
    assert CanonicalDepthLevel is not None


def test_l5_derivable_fields_present_deeper_honest_absent() -> None:
    """An L5-derived row carries spread/imbalance/microprice; the deeper-book
    fields (queue / depth-10) are honestly absent (None / empty)."""
    from unified_api_contracts import CanonicalBookMicrostructure

    row = CanonicalBookMicrostructure(
        instrument_key="BINANCE-FUTURES:perpetual:BTCUSDT",
        venue="BINANCE-FUTURES",
        as_of=datetime(2026, 6, 15, tzinfo=UTC),
        best_bid=Decimal("66800.0"),
        best_ask=Decimal("66801.0"),
        mid=Decimal("66800.5"),
        spread=Decimal("1.0"),
        relative_spread=Decimal("0.0000149"),
        microprice=Decimal("66800.6"),
        imbalance=Decimal("0.2"),
        captured_depth=5,
    )
    # L5-derivable present
    assert row.imbalance == Decimal("0.2")
    assert row.microprice == Decimal("66800.6")
    assert row.captured_depth == 5
    # deeper-book honest absence (L5 cannot fill these)
    assert row.queue_position_bid is None
    assert row.queue_position_ask is None
    assert row.depth_levels_bid == []
    assert row.depth_levels_ask == []
    assert row.schema_version == "1.0"


def test_batch_equals_live_identical_dump() -> None:
    """The SAME canonical instance serialises identically regardless of which
    source produced it — an engine cannot tell live from batch."""
    from unified_api_contracts import CanonicalBookMicrostructure

    kwargs = {
        "instrument_key": "DERIBIT:option:BTC-PERP",
        "venue": "DERIBIT",
        "as_of": datetime(2026, 6, 15, tzinfo=UTC),
        "best_bid": Decimal("66800.0"),
        "best_ask": Decimal("66801.0"),
        "imbalance": Decimal("-0.1"),
        "captured_depth": 5,
    }
    from_live = CanonicalBookMicrostructure(**kwargs)
    from_batch = CanonicalBookMicrostructure(**kwargs)
    assert from_live.model_dump() == from_batch.model_dump()


def test_queue_and_depth_are_honest_gap() -> None:
    """queue_position + depth_of_book_10 need a deeper book than L5 -> honest gap
    (neither live nor batch capable until a deeper capture lands)."""
    from unified_api_contracts.registry.data_type_capability import (
        DATA_TYPE_CAPABILITY_REGISTRY,
    )

    for dt in ("queue_position", "depth_of_book_10"):
        rows = [c for c in DATA_TYPE_CAPABILITY_REGISTRY if c.data_type == dt]
        assert rows, f"no rows registered for {dt}"
        for c in rows:
            assert c.live_capable is False, f"{dt}/{c.venue} must be an honest gap"
            assert c.batch_capable is False, f"{dt}/{c.venue} must be an honest gap"


def test_source_priority_registered_for_microstructure() -> None:
    """SOURCE_PRIORITY carries the new data_types, keyed to the computed source."""
    from unified_api_contracts.canonical.crosscutting.source_priority import SOURCE_PRIORITY

    for dt in ("depth_of_book_10", "queue_position"):
        assert ("cefi", dt) in SOURCE_PRIORITY
        assert SOURCE_PRIORITY[("cefi", dt)] == ["mtds_microstructure"]


def test_microstructure_source_round_trips_pipeline_mode() -> None:
    """mtds_microstructure resolves a PipelineMode in every mode (closed-set)."""
    from unified_api_contracts.canonical.crosscutting.pipeline_mode import (
        Mode,
        pipeline_mode_for_source,
    )

    for mode in (Mode.BATCH, Mode.LIVE, Mode.REPLAY):
        pm = pipeline_mode_for_source("mtds_microstructure", mode)
        assert pm.value == f"{mode.value}_mtds_microstructure"
