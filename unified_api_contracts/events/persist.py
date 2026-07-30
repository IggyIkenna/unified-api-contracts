"""Canonical persist/message envelope for the central event-log spine.

Every event published to the Pub/Sub central log carries this envelope.
Producers (MTDS / MDPS / features / execution) publish one envelope per
window; consumers (hot-path services, GCS warm sink, BQ external table)
all subscribe to the same topic.

Key invariants:
* Exactly one of ``payload_inline`` / ``payload_pointer`` is set.
  ``payload_inline`` carries the JSON-encoded bar/aggregate for hot-path
  delivery (well under the 10 MB Pub/Sub cap). ``payload_pointer`` carries a
  GCS blob path for large payloads (analytics-only, never hot path — D4).
* ``retention_class`` drives the lifecycle via
  :data:`~unified_api_contracts.events.sink_matrix.SINK_MATRIX`.
* ``schema_version`` is pinned to ``"1"`` for this generation; bump on a
  breaking field change (use the same versioning discipline as UAC contract
  schema versions).

Plan: ``live_data_persistence_central_event_log_2026_06_25.md`` Plan 01.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, Field, model_validator

from unified_api_contracts.canonical.crosscutting.pipeline_mode import PipelineMode
from unified_api_contracts.canonical.gcs_paths import AssetGroup


class RetentionClass(StrEnum):
    """Retention classification for a persisted shard.

    Drives the ``SINK_MATRIX`` lifecycle (TTL vs keep-forever).

    * ``REPRODUCIBLE`` — re-fetchable externally OR re-derivable from a
      retained upstream + pinned logic (Databento OHLCV; MDPS candles;
      features with pinned ``formula_version``; ML preds with pinned
      model+features). Cold GCS gets a TTL; re-derive/backfill beyond.
    * ``STREAM_ONLY`` — no external backfill and/or system-of-record
      state we ourselves emitted (execution fills/positions/PnL; paper
      ledger). Cold GCS = **forever, no TTL** — losing it means losing
      audit history.
    """

    REPRODUCIBLE = "REPRODUCIBLE"
    STREAM_ONLY = "STREAM_ONLY"


class CanonicalPersistEnvelope(BaseModel):
    """Canonical envelope published to the Pub/Sub central event log.

    Every service in the live pipeline publishes exactly this shape.
    The UTL ``publish()`` facade builds and sends it; the UTL ``read()``
    facade deserialises it back — consumers never touch Pub/Sub directly.

    Payload contract (D4):

    * ``payload_inline`` — JSON-encoded bar/aggregate (OHLCV row, feature
      dict, fill record). Must be set for hot-path shards (hot=True in
      SINK_MATRIX). Size MUST be well under the 10 MB Pub/Sub message cap;
      the UTL facade chunks anything close to the limit across ordered
      messages.
    * ``payload_pointer`` — GCS blob path for large/analytics-only payloads
      that are not on the hot path. Exactly one of these two must be set.
    """

    schema_version: Literal["1"] = "1"
    asset_group: AssetGroup
    data_type: str
    pipeline_mode: PipelineMode | None = None
    period_start: datetime = Field(description="UTC, aligned to the window boundary.")
    period_end: datetime = Field(description="UTC, aligned (period_start + window).")
    source: str = Field(
        description=(
            "Emitting service tag. Closed set: 'MTDS' / 'MDPS' / 'features' / "
            "'ml' / 'execution' / 'strategy'. Used by the read() facade for provenance routing."
        ),
    )
    available_at: datetime = Field(
        description="When the emitting service finalised the window (= period_end + latency).",
    )
    retention_class: RetentionClass

    # Payload discriminator — exactly one must be set (validated below)
    payload_inline: str | None = Field(
        default=None,
        description="JSON-encoded payload for hot-path delivery. Set for hot=True shards.",
    )
    payload_pointer: str | None = Field(
        default=None,
        description="GCS blob path for large/analytics-only payloads (hot=False shards).",
    )

    # Shard key dimensions — nullable when the envelope covers all instruments in a shard
    venue: str | None = None
    chain: str | None = None
    instrument_id: str | None = None
    instrument_type: str | None = None

    # Operational metadata
    correlation_id: str
    vm_name: str

    @model_validator(mode="after")
    def _check_payload_xor(self) -> CanonicalPersistEnvelope:
        has_inline = self.payload_inline is not None
        has_pointer = self.payload_pointer is not None
        if has_inline == has_pointer:
            raise ValueError(
                "Exactly one of payload_inline or payload_pointer must be set; "
                f"got inline={has_inline}, pointer={has_pointer}."
            )
        return self


__all__ = [
    "CanonicalPersistEnvelope",
    "RetentionClass",
]
