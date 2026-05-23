"""Synthetic-data generator taxonomy — closed-set workspace SSOT for the mock-data benchmark harness.

Phase 1.A-1.D of ``mock_data_pipeline_benchmarking_2026_05_10.md``
(``unified-trading-pm/plans/active/``). Defines the canonical generator
taxonomy that UTL ``synthetic/{generator,harness,profile}.py`` consumes when
driving the full cutover-archetype pipeline (MTDS read → MDPS compute →
features → ML inference → strategy → matching engine) on synthetic input so
per-stage CPU / memory / IO / wall-clock can be profiled 2 weeks before real
backfills complete.

Five orthogonal axes per generator declaration:

1. :class:`SyntheticGeneratorId` — closed-set identifier (regex
   ``[a-z][a-z0-9_]+``), one per ``(asset_group, data_type)`` the cutover
   archetypes consume.
2. :class:`SyntheticDataDomain` — high-level shape family (CEFI_TICK /
   CEFI_DERIVATIVES / DEFI_ONCHAIN / DEFI_RATES / DEFI_DEX / DEFI_ORACLE /
   TRADFI_OHLCV) — lets consumers dispatch a shape-family writer without
   re-deriving from the id.
3. :class:`SyntheticRealismAxis` — how faithful the synthetic rows are.
   Axis 1-3 (cardinality / parquet byte-size / shard count) is sufficient
   for bottleneck measurement; axis 4 (calibrated GBM / SDEs for value
   correctness) is DEFERRED post-cutover per the plan non-goals.
4. :class:`SyntheticShardLayout` — how the generator splits output across
   parquet shards (must match the prod reader's shard atom per the
   "Shard-granularity SSOT" rule in CLAUDE.md so the harness reads it back
   through prod reader paths with no schema-drift error).
5. :class:`SyntheticParams` — a concrete generation request (a
   :class:`SyntheticGeneratorId` + date range + cardinality knobs +
   output URI + RNG seed).

Per CLAUDE.md "Live = batch" rule: the harness rides the SAME prod
codepaths as live + batch — only the *input source* is the synthetic
generator instead of a venue adapter / GCS reader.

§ SSOT reconciliation seam
--------------------------

- :class:`SyntheticShardLayout.shard_key_axes` is the SAME shard atom the
  ``ManifestWriter`` row key + data-status display + downstream pre-flight
  gate use (per CLAUDE.md "Shard-granularity SSOT (CRITICAL)"). A generator
  whose ``shard_key_axes`` disagrees with the per-asset_group matrix is
  review-blocking.
- :class:`SyntheticRealismAxis` is orthogonal to
  ``scenario_overlay.ScenarioCategory`` — realism axis describes how close
  to real *baseline* data the synthetic rows are; scenario category
  describes the *adversarial mutation* layered on top. The benchmark
  harness uses synthetic generators with NO scenario overlay; the scenario
  matrix harness (``simulation_scenarios_topology_price_shocks_2026_05_09``)
  composes scenario overlays ON TOP of these generators.
- :class:`SyntheticOutputManifest` is distinct from the on-disk
  availability manifest — it is an *ephemeral* per-run artefact the harness
  reads to verify the generator wrote what it promised before kicking the
  pipeline; it never replaces ``ManifestWriter`` output (the synthetic
  pipeline run writes a real availability manifest of its own).

Adding a new generator
----------------------

1. Append the identifier to :class:`SyntheticGeneratorId` (it is an
   explicit :class:`enum.StrEnum`, not a regex — closed set).
2. Add a :class:`SyntheticGeneratorSpec` entry to the per-asset_group
   registry seed under ``unified_api_contracts/registry/generators/<asset_group>.py``;
   it self-registers via :func:`register_generator`.
3. Implement the per-data_type writer in UTL ``synthetic/generator.py`` in
   the SAME logical unit (per Citadel-Grade Pre-Audit — workspace-grep
   every existing reader of that ``(asset_group, data_type)``).
4. Update the codex doc per ``mock_data_pipeline_benchmarking_2026_05_10``
   Phase 7.

Compressed-scope status (2026-05-12 slot 7)
-------------------------------------------

Per the plan body's "In scope" section, the pre-cutover ship covers ONLY
the two cutover archetypes:

- ``carry_staked_basis`` (DeFi lead) — :data:`DEFI_GENERATORS` (gas, LST
  rates, lending indices, DEX pool states, oracle feeds).
- ``leveraged_funding_arb`` / ``ARBITRAGE_PRICE_DISPERSION`` (CeFi hedge
  +arb leg) — :data:`CEFI_GENERATORS` (trades, ohlcv_1m, ohlcv_15m,
  funding_rate, open_interest, liquidations).
- TradFi OHLCV (:data:`TRADFI_GENERATORS`) — included for the
  cross-asset hedge-overlay path the work-split scope names ("DeFi + CeFi
  + TradFi simulation paths"); minimal axis-1 coverage.

Deferred to a post-cutover successor sub-plan (per the plan's "Deferred
work" table): sports / prediction generators, realism axis 4 (calibrated
dynamics), full per-asset_group coverage beyond cutover archetypes,
continuous-benchmark cron.
"""

from __future__ import annotations

import hashlib
import json
from decimal import Decimal
from enum import StrEnum
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

# ---------------------------------------------------------------------------
# Closed-set enums (Phase 1.A)
# ---------------------------------------------------------------------------


class SyntheticDataDomain(StrEnum):
    """High-level shape family for a synthetic generator.

    Closed-set 8. Lets UTL ``synthetic/generator.py`` dispatch a
    shape-family writer (each family shares a parquet column skeleton +
    cardinality model) without re-deriving from the id.
    """

    CEFI_TICK = "CEFI_TICK"
    """CeFi trade / orderbook tick rows (per-event grain)."""
    CEFI_OHLCV = "CEFI_OHLCV"
    """CeFi bar rows (ohlcv_1m / ohlcv_15m / ohlcv_1h / ohlcv_24h)."""
    CEFI_DERIVATIVES = "CEFI_DERIVATIVES"
    """CeFi funding-rate / open-interest / liquidation rows."""
    DEFI_ONCHAIN = "DEFI_ONCHAIN"
    """On-chain primitives — block gas / priority fee / base fee per chain-slot."""
    DEFI_RATES = "DEFI_RATES"
    """LST exchange rates + lending-protocol supply/borrow indices."""
    DEFI_DEX = "DEFI_DEX"
    """DEX pool-state snapshots (reserves, sqrtPriceX96, tick, liquidity)."""
    DEFI_ORACLE = "DEFI_ORACLE"
    """Oracle-feed rows (Pyth Hermes batches, Chainlink aggregator rounds)."""
    TRADFI_OHLCV = "TRADFI_OHLCV"
    """TradFi bar rows (Databento / Barchart equities + futures + index)."""


class SyntheticGeneratorId(StrEnum):
    """Closed-set generator identifier — one per ``(asset_group, data_type)`` a cutover archetype consumes.

    Naming: ``<asset_group>_<data_type>`` (snake_case ASCII). Reviewers
    reject a :class:`SyntheticGeneratorSpec` whose ``generator_id`` is not a
    member here. Extending the set requires the 4-step "Adding a new
    generator" workflow in the module docstring.

    Pre-cutover members cover the 2 cutover archetypes only (DeFi
    ``carry_staked_basis`` lead + CeFi ``leveraged_funding_arb`` /
    ``ARBITRAGE_PRICE_DISPERSION``) plus a minimal TradFi-OHLCV path for
    the cross-asset hedge overlay.
    """

    # ----- CeFi (leveraged_funding_arb / ARBITRAGE_PRICE_DISPERSION) ---------
    CEFI_TRADES = "cefi_trades"
    CEFI_OHLCV_1M = "cefi_ohlcv_1m"
    CEFI_OHLCV_15M = "cefi_ohlcv_15m"
    CEFI_FUNDING_RATE = "cefi_funding_rate"
    CEFI_OPEN_INTEREST = "cefi_open_interest"
    CEFI_LIQUIDATIONS = "cefi_liquidations"

    # ----- DeFi (carry_staked_basis) ----------------------------------------
    DEFI_GAS = "defi_gas"
    DEFI_LST_RATES = "defi_lst_rates"
    DEFI_LENDING_INDICES = "defi_lending_indices"
    DEFI_DEX_POOL_STATE = "defi_dex_pool_state"
    DEFI_ORACLE_FEEDS = "defi_oracle_feeds"

    # ----- TradFi (cross-asset hedge overlay) -------------------------------
    TRADFI_OHLCV_1M = "tradfi_ohlcv_1m"
    TRADFI_OHLCV_1D = "tradfi_ohlcv_1d"


class SyntheticRealismAxis(StrEnum):
    """How faithful the synthetic rows are to real data.

    Closed-set 4 (ordered). The benchmark harness only needs axes 1-3 —
    bottleneck measurement is driven by *data shape* (row count, byte size,
    shard count), not *data value*. Axis 4 (calibrated dynamics for value
    correctness) is DEFERRED post-cutover; the cutover pipelines are
    shape-driven not value-driven.
    """

    CARDINALITY = "CARDINALITY"
    """Axis 1: correct row count per ``(generator, day, shard)``; values are
    cheap RNG fills with the right dtypes + monotone timestamps."""
    PARQUET_SIZE = "PARQUET_SIZE"
    """Axis 2: axis-1 + per-shard byte size within +/-20% of a real
    backfill sample (string-column width, dictionary-encoding ratio)."""
    SHARD_COUNT = "SHARD_COUNT"
    """Axis 3: axis-2 + correct shard fan-out (per-venue / per-instrument /
    per-chain) so GCS / S3 listing depth matches prod."""
    CALIBRATED_DYNAMICS = "CALIBRATED_DYNAMICS"
    """Axis 4 (DEFERRED post-cutover): axis-3 + calibrated GBM / SDE value
    paths for correctness benchmarking. Not shipped pre-cutover."""


# ---------------------------------------------------------------------------
# Shard layout (Phase 1.A)
# ---------------------------------------------------------------------------


_SHARD_AXIS_PATTERN: Final = frozenset(
    {"venue", "instrument", "chain", "protocol", "pool", "oracle_feed", "data_type", "day"},
)
"""The closed set of shard-key axes a synthetic generator may fan out on.

Must be a subset of the per-asset_group shard-atom matrix in
``plans/epics/infrastructure_master.md`` — drift between this
list and that matrix is a silent correctness bug per CLAUDE.md
"Shard-granularity SSOT (CRITICAL)".
"""


class SyntheticShardLayout(BaseModel):
    """How a generator splits its per-day output across parquet shards.

    The ``shard_key_axes`` tuple is the SAME shard atom the
    ``ManifestWriter`` row key uses for that ``(asset_group, data_type)`` —
    see CLAUDE.md "Shard-granularity SSOT". The synthetic pipeline run
    writes a real availability manifest with this shard granularity, so the
    downstream pre-flight gate + data-status display see exactly what a real
    backfill would produce.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    shard_key_axes: tuple[str, ...] = Field(min_length=1)
    """Ordered shard-atom axes (e.g. ``("venue", "instrument")`` for CeFi
    tick, ``("chain",)`` for DeFi gas). Each must be in
    :data:`_SHARD_AXIS_PATTERN`."""

    shards_per_day: int = Field(gt=0)
    """How many parquet shards the generator writes per ``(generator,
    day)`` — i.e. the cardinality of the cross-product of the shard-key axes
    for the configured venue/instrument/chain set."""

    partition_template: str = Field(min_length=1)
    """Hive partition path template under the output URI prefix, e.g.
    ``asset_group={asset_group}/data_type={data_type}/venue={venue}/instrument={instrument}/dt={dt}``.
    Placeholders must be a subset of the shard-key axes plus ``asset_group``
    / ``data_type`` / ``dt``."""

    @field_validator("shard_key_axes")
    @classmethod
    def _validate_axes(cls, v: tuple[str, ...]) -> tuple[str, ...]:
        bad = [a for a in v if a not in _SHARD_AXIS_PATTERN]
        if bad:
            raise ValueError(
                f"shard_key_axes {bad!r} not in the closed shard-atom set "
                f"{sorted(_SHARD_AXIS_PATTERN)!r} (CLAUDE.md Shard-granularity SSOT)",
            )
        if len(set(v)) != len(v):
            raise ValueError(f"shard_key_axes {v!r} contains duplicates")
        return v


# ---------------------------------------------------------------------------
# Generation request (Phase 1.A)
# ---------------------------------------------------------------------------


class SyntheticParams(BaseModel):
    """A concrete synthetic-data generation request.

    Built by the benchmark CLI from a ``--synthetic-params <yaml>`` file (or
    a registry default via :func:`generator_default_params`) and handed to
    UTL ``synthetic.generator.generate(params)`` which produces parquets +
    a :class:`SyntheticOutputManifest`.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    generator_id: SyntheticGeneratorId
    asset_group: str = Field(min_length=1)
    """Lowercase asset-group key per CLAUDE.md vocab (``cefi`` / ``defi`` /
    ``tradfi``). Must match the registry spec's ``asset_group``."""
    data_type: str = Field(min_length=1)
    """Canonical data_type string (``trades`` / ``funding_rate`` / ``gas`` /
    ...). Must match the registry spec's ``data_type``."""

    date_start: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    date_end: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    """Inclusive ISO date range to generate (both ends)."""

    row_count_per_day: int = Field(gt=0)
    """Rows per ``(generator, day)`` SUMMED across all shards — the
    cardinality knob. Realism-axis-1 default comes from the registry spec;
    the CLI may scale it up for a stress run."""

    schema_version: str = Field(min_length=1)
    """The ``CANONICAL_*_VERSION`` / ``__schema_version__`` the generated
    parquet declares. Must match what the prod reader expects for that
    data_type so the harness reads it back with no schema-drift error."""

    realism_axis: SyntheticRealismAxis = SyntheticRealismAxis.SHARD_COUNT
    shard_layout: SyntheticShardLayout
    output_uri: str = Field(min_length=1)
    """Base URI prefix (``gs://...`` or ``s3://...``) the generator writes
    under, using :attr:`SyntheticShardLayout.partition_template`. Must be
    resolved by the caller via
    ``unified_trading_library.cloud_interface.bucket_naming.resolve_bucket_name``
    — this field is the already-resolved value."""

    venues: tuple[str, ...] = Field(default=())
    """Venue short-names (lowercase) the generator fans out across — CeFi /
    DeFi-DEX generators. Empty for chain-keyed or single-cell generators."""
    instruments: tuple[str, ...] = Field(default=())
    """Per-venue instrument symbols — CeFi generators."""
    chains: tuple[str, ...] = Field(default=())
    """Chain keys (lowercase: ``ethereum`` / ``arbitrum`` / ``solana`` /
    ...) — DeFi generators."""
    protocols: tuple[str, ...] = Field(default=())
    """Protocol keys (``aave_v3`` / ``morpho`` / ``marinade`` / ...) — DeFi
    rates / DEX generators."""

    seed: int = Field(default=20260512, ge=0)
    """Deterministic RNG seed — two runs with the same params produce
    byte-identical parquets (modulo parquet writer non-determinism, which
    we pin)."""

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


# ---------------------------------------------------------------------------
# Registry spec (Phase 1.B)
# ---------------------------------------------------------------------------


class SyntheticGeneratorSpec(BaseModel):
    """Per-``(asset_group, data_type)`` generator declaration in the registry.

    Each entry in ``unified_api_contracts/registry/generators/<asset_group>.py``
    is a :class:`SyntheticGeneratorSpec` instance; it self-registers in
    :data:`SYNTHETIC_GENERATOR_REGISTRY` at import time via
    :func:`register_generator`.

    Reviewers cross-check that every cutover archetype's consumed
    ``(asset_group, data_type)`` set has a registered spec (Phase 1.D
    "per-archetype coverage" test).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    generator_id: SyntheticGeneratorId
    domain: SyntheticDataDomain
    asset_group: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    """Default ``CANONICAL_*_VERSION`` for generated parquet (the CLI may
    override per-run via :class:`SyntheticParams`)."""

    default_row_count_per_day: int = Field(gt=0)
    """Realism-axis-1 default per-day row count, calibrated to a real
    backfill sample where one exists (see plan § Audit findings 0.B), else
    a documented estimate."""

    default_shard_key_axes: tuple[str, ...] = Field(min_length=1)
    """The shard atom for this ``(asset_group, data_type)`` — SAME as the
    ManifestWriter row key (CLAUDE.md Shard-granularity SSOT)."""

    default_partition_template: str = Field(min_length=1)

    archetypes_consuming: frozenset[str] = Field(min_length=1)
    """Cutover-archetype ids that read this ``(asset_group, data_type)``
    (e.g. ``{"carry_staked_basis"}``). Free-form strings (not enum) per the
    same rationale as ``ScenarioOutcomeAssertion.archetype``."""

    pipeline_stages_touching: tuple[str, ...] = Field(min_length=1)
    """Ordered pipeline stage names that read/transform this data_type
    (subset of ``("mtds_read", "mdps_compute", "features", "ml_inference",
    "strategy", "matching_engine")``) — the harness profiles exactly these
    stages for a run keyed on this generator."""

    real_backfill_sample_uri: str = Field(default="")
    """Optional ``gs://...`` pointer to a real backfill sample the
    ``default_row_count_per_day`` + axis-2 byte-size targets were
    calibrated against. Empty = estimate (flagged in plan § Audit findings)."""

    description: str = Field(default="")

    def make_default_params(
        self,
        *,
        date_start: str,
        date_end: str,
        output_uri: str,
        venues: tuple[str, ...] = (),
        instruments: tuple[str, ...] = (),
        chains: tuple[str, ...] = (),
        protocols: tuple[str, ...] = (),
        realism_axis: SyntheticRealismAxis = SyntheticRealismAxis.SHARD_COUNT,
        row_count_per_day: int | None = None,
        seed: int = 20260512,
    ) -> SyntheticParams:
        """Build a :class:`SyntheticParams` from this spec's defaults."""
        cardinality = self._fanout_cardinality(
            venues=venues,
            instruments=instruments,
            chains=chains,
            protocols=protocols,
        )
        return SyntheticParams(
            generator_id=self.generator_id,
            asset_group=self.asset_group,
            data_type=self.data_type,
            date_start=date_start,
            date_end=date_end,
            row_count_per_day=row_count_per_day if row_count_per_day is not None else self.default_row_count_per_day,
            schema_version=self.schema_version,
            realism_axis=realism_axis,
            shard_layout=SyntheticShardLayout(
                shard_key_axes=self.default_shard_key_axes,
                shards_per_day=max(1, cardinality),
                partition_template=self.default_partition_template,
            ),
            output_uri=output_uri,
            venues=venues,
            instruments=instruments,
            chains=chains,
            protocols=protocols,
            seed=seed,
        )

    def _fanout_cardinality(
        self,
        *,
        venues: tuple[str, ...],
        instruments: tuple[str, ...],
        chains: tuple[str, ...],
        protocols: tuple[str, ...],
    ) -> int:
        axes = set(self.default_shard_key_axes)
        card = 1
        if "venue" in axes:
            card *= max(1, len(venues))
        if "instrument" in axes:
            card *= max(1, len(instruments))
        if "chain" in axes:
            card *= max(1, len(chains))
        if "protocol" in axes or "pool" in axes:
            card *= max(1, len(protocols))
        return card


# ---------------------------------------------------------------------------
# Per-run output manifest (Phase 1.C)
# ---------------------------------------------------------------------------


class SyntheticShardManifest(BaseModel):
    """One parquet shard the generator wrote — the harness verifies each."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    shard_uri: str = Field(min_length=1)
    shard_key: dict[str, str] = Field(default_factory=dict)
    """The shard-atom values for this shard (e.g. ``{"venue": "bybit",
    "instrument": "BTCUSDT", "dt": "2024-01-15"}``)."""
    row_count: int = Field(ge=0)
    byte_size: int = Field(ge=0)
    available_at_iso: str = Field(min_length=1)
    """Per-shard write-time ``available_at`` — equal to the live-pipeline
    arrival time of the SOURCE_PRIORITY top entry for this data_type, per
    CLAUDE.md "available_at is per-row, write-time"."""


class SyntheticOutputManifest(BaseModel):
    """Ephemeral per-generator-run manifest the harness reads before kicking the pipeline.

    Written next to the generated parquets at ``<output_uri>/_synthetic_manifest.json``.
    The harness loads it, asserts ``sum(shard.row_count) == params.row_count_per_day
    * n_days`` and every ``shard_uri`` exists, then proceeds. Distinct from
    the on-disk availability manifest the synthetic pipeline run itself
    writes (this is a generator-side receipt, not a coverage record).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    generator_id: SyntheticGeneratorId
    asset_group: str = Field(min_length=1)
    data_type: str = Field(min_length=1)
    params_hash: str = Field(min_length=8)
    schema_version: str = Field(min_length=1)
    realism_axis: SyntheticRealismAxis
    date_start: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    date_end: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    generated_at_iso: str = Field(min_length=1)
    output_uri: str = Field(min_length=1)
    shards: tuple[SyntheticShardManifest, ...] = Field(default=())

    @property
    def total_rows(self) -> int:
        return sum(s.row_count for s in self.shards)

    @property
    def total_bytes(self) -> int:
        return sum(s.byte_size for s in self.shards)


class SyntheticRunManifest(BaseModel):
    """Aggregates the :class:`SyntheticOutputManifest` of every generator a single benchmark run drove.

    Written to ``gs://{pid}-benchmark-reports/{archetype}/{run_id}/synthetic_run_manifest.json``
    alongside the per-stage profile parquet. Lets a later report-aggregation
    pass tie a profile back to the exact synthetic input that produced it.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(min_length=1)
    archetype: str = Field(min_length=1)
    started_at_iso: str = Field(min_length=1)
    generator_manifests: tuple[SyntheticOutputManifest, ...] = Field(min_length=1)

    @property
    def total_input_rows(self) -> int:
        return sum(m.total_rows for m in self.generator_manifests)


# ---------------------------------------------------------------------------
# Module-level registry index (populated at module-load by registry/generators)
# ---------------------------------------------------------------------------


SYNTHETIC_GENERATOR_REGISTRY: Final[dict[SyntheticGeneratorId, SyntheticGeneratorSpec]] = {}
"""Global registry — populated at import time by ``registry/generators/__init__.py``.

Lookup: ``SYNTHETIC_GENERATOR_REGISTRY[SyntheticGeneratorId.CEFI_TRADES]``.
Reviewers reject a generator spec declared in a
``registry/generators/<asset_group>.py`` module that doesn't register
itself here.
"""


def register_generator(spec: SyntheticGeneratorSpec) -> None:
    """Register a generator spec in the global :data:`SYNTHETIC_GENERATOR_REGISTRY`.

    Idempotent — raises :class:`ValueError` on conflicting re-registration
    of the same ``generator_id``. Called by per-asset_group registry
    modules at module-load time.
    """
    existing = SYNTHETIC_GENERATOR_REGISTRY.get(spec.generator_id)
    if existing is not None:
        if existing == spec:
            return
        raise ValueError(
            f"conflicting re-registration of generator {spec.generator_id!r}: "
            f"existing={existing.description!r} vs new={spec.description!r}",
        )
    SYNTHETIC_GENERATOR_REGISTRY[spec.generator_id] = spec


def get_generator_spec(generator_id: SyntheticGeneratorId | str) -> SyntheticGeneratorSpec:
    """Look up a registered spec; raises :class:`KeyError` if absent."""
    key = generator_id if isinstance(generator_id, SyntheticGeneratorId) else SyntheticGeneratorId(generator_id)
    if key not in SYNTHETIC_GENERATOR_REGISTRY:
        raise KeyError(f"no registered synthetic generator spec for {key!r}")
    return SYNTHETIC_GENERATOR_REGISTRY[key]


def generators_for_archetype(archetype: str) -> tuple[SyntheticGeneratorSpec, ...]:
    """All registered specs a given cutover archetype consumes (sorted by id)."""
    return tuple(
        sorted(
            (s for s in SYNTHETIC_GENERATOR_REGISTRY.values() if archetype in s.archetypes_consuming),
            key=lambda s: s.generator_id.value,
        ),
    )


def make_decimal(value: float | int | str) -> Decimal:
    """Helper for registry modules: build a :class:`Decimal` from a literal without float-precision loss."""
    return Decimal(str(value))


__all__ = [
    "SYNTHETIC_GENERATOR_REGISTRY",
    "SyntheticDataDomain",
    "SyntheticGeneratorId",
    "SyntheticGeneratorSpec",
    "SyntheticOutputManifest",
    "SyntheticParams",
    "SyntheticRealismAxis",
    "SyntheticRunManifest",
    "SyntheticShardLayout",
    "SyntheticShardManifest",
    "generators_for_archetype",
    "get_generator_spec",
    "make_decimal",
    "register_generator",
]
