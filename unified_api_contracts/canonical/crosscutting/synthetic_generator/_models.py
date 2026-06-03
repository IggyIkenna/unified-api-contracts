"""Synthetic generator Pydantic models."""

from __future__ import annotations

import hashlib
import json

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from ._enums import SHARD_AXIS_PATTERN, SyntheticGeneratorId, SyntheticRealismAxis


class SyntheticShardLayout(BaseModel):
    """How a generator splits its per-day output across parquet shards."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    shard_key_axes: tuple[str, ...] = Field(min_length=1)
    shards_per_day: int = Field(gt=0)
    partition_template: str = Field(min_length=1)

    @field_validator("shard_key_axes")
    @classmethod
    def _validate_axes(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        bad = [a for a in v if a not in SHARD_AXIS_PATTERN]
        if bad:
            raise ValueError(
                f"shard_key_axes {bad!r} not in the closed shard-atom set "
                f"{sorted(SHARD_AXIS_PATTERN)!r} (CLAUDE.md Shard-granularity SSOT)",
            )
        if len(set(v)) != len(v):
            raise ValueError(f"shard_key_axes {v!r} contains duplicates")
        return v


class SyntheticParams(BaseModel):
    """A concrete synthetic-data generation request."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    generator_id: SyntheticGeneratorId
    asset_group: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    date_start: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    date_end: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    row_count_per_day: int = Field(gt=0)
    schema_version: str = Field(min_length=1)
    realism_axis: SyntheticRealismAxis = SyntheticRealismAxis.SHARD_COUNT
    shard_layout: SyntheticShardLayout
    output_uri: str = Field(min_length=1)
    venues: tuple[str, ...] = Field(default=())
    instruments: tuple[str, ...] = Field(default=())
    chains: tuple[str, ...] = Field(default=())
    protocols: tuple[str, ...] = Field(default=())
    seed: int = Field(default=20260512, ge=0)

    @model_validator(mode="after")
    def _validate_dates(self) -> SyntheticParams:
        if self.date_end < self.date_start:
            raise ValueError(f"date_end {self.date_end} < date_start {self.date_start}")
        return self

    @model_validator(mode="after")
    def _validate_fanout_matches_layout(self) -> SyntheticParams:
        axes = set(self.shard_layout.shard_key_axes)
        if "venue" in axes and not self.venues:
            raise ValueError(f"shard layout keys on 'venue' but no venues provided for {self.generator_id}")
        if "chain" in axes and not self.chains:
            raise ValueError(f"shard layout keys on 'chain' but no chains provided for {self.generator_id}")
        if "protocol" in axes and not self.protocols:
            raise ValueError(f"shard layout keys on 'protocol' but no protocols provided for {self.generator_id}")
        if "instrument" in axes and not self.instruments:
            raise ValueError(f"shard layout keys on 'instrument' but no instruments provided for {self.generator_id}")
        return self

    def params_hash(self) -> str:
        """Stable short hash of the request — used in the run_id + as the
        idempotency key for the output manifest."""
        payload = self.model_dump(mode="json")
        blob = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return hashlib.sha256(blob).hexdigest()[:16]


__all__ = [
    "SyntheticParams",
    "SyntheticShardLayout",
]
