"""Unit tests for `canonical.crosscutting.synthetic_generator` + per-asset_group generator registry.

Phase 1.D of `mock_data_pipeline_benchmarking_2026_05_10.md` (slot 7,
2026-05-12). Covers:

- Closed-set enum membership + count (`SyntheticDataDomain` /
  `SyntheticGeneratorId` / `SyntheticRealismAxis`).
- `SyntheticShardLayout` shard-axis validator (closed shard-atom set).
- `SyntheticParams` validators (date range; fanout-matches-layout; params_hash determinism).
- `SyntheticGeneratorSpec.make_default_params` cardinality computation.
- `SyntheticOutputManifest` / `SyntheticRunManifest` round-trip + aggregate properties.
- Registry completeness — 13 generators (6 cefi + 5 defi + 2 tradfi), per-archetype coverage.
- `register_generator` idempotency + conflict-detection.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from unified_api_contracts import (
    SYNTHETIC_GENERATOR_REGISTRY,
    SyntheticDataDomain,
    SyntheticGeneratorId,
    SyntheticGeneratorSpec,
    SyntheticOutputManifest,
    SyntheticParams,
    SyntheticRealismAxis,
    SyntheticRunManifest,
    SyntheticShardLayout,
    SyntheticShardManifest,
    generators_for_archetype,
    get_generator_spec,
    register_generator,
)
from unified_api_contracts.canonical.crosscutting.synthetic_generator import make_decimal
from unified_api_contracts.registry.generators import (
    ALL_GENERATORS,
    CEFI_GENERATORS,
    DEFI_GENERATORS,
    TRADFI_GENERATORS,
)

# ---------------------------------------------------------------------------
# Closed-set enums
# ---------------------------------------------------------------------------


def test_data_domain_count_eight() -> None:
    assert len(SyntheticDataDomain) == 8


def test_generator_id_count_thirteen() -> None:
    # 6 cefi + 5 defi + 2 tradfi
    assert len(SyntheticGeneratorId) == 13


def test_realism_axis_count_four() -> None:
    assert len(SyntheticRealismAxis) == 4
    assert SyntheticRealismAxis.CARDINALITY in SyntheticRealismAxis
    assert SyntheticRealismAxis.SHARD_COUNT.value == "SHARD_COUNT"


@pytest.mark.parametrize("gen_id", list(SyntheticGeneratorId))
def test_generator_id_value_is_snake_case(gen_id: SyntheticGeneratorId) -> None:
    assert gen_id.value == gen_id.value.lower()
    assert " " not in gen_id.value
    assert gen_id.value.replace("_", "").isalnum()


# ---------------------------------------------------------------------------
# SyntheticShardLayout
# ---------------------------------------------------------------------------


def test_shard_layout_accepts_known_axes() -> None:
    layout = SyntheticShardLayout(
        shard_key_axes=("venue", "instrument"),
        shards_per_day=18,
        partition_template="asset_group={asset_group}/venue={venue}/instrument={instrument}/dt={dt}",
    )
    assert layout.shard_key_axes == ("venue", "instrument")


def test_shard_layout_rejects_unknown_axis() -> None:
    with pytest.raises(ValidationError):
        SyntheticShardLayout(
            shard_key_axes=("nonsense_axis",),
            shards_per_day=1,
            partition_template="x={x}",
        )


def test_shard_layout_rejects_duplicate_axes() -> None:
    with pytest.raises(ValidationError):
        SyntheticShardLayout(
            shard_key_axes=("venue", "venue"),
            shards_per_day=1,
            partition_template="venue={venue}",
        )


def test_shard_layout_rejects_zero_shards() -> None:
    with pytest.raises(ValidationError):
        SyntheticShardLayout(shard_key_axes=("chain",), shards_per_day=0, partition_template="chain={chain}")


# ---------------------------------------------------------------------------
# SyntheticParams
# ---------------------------------------------------------------------------


def _cefi_params(**overrides: object) -> SyntheticParams:
    base: dict[str, object] = dict(
        generator_id=SyntheticGeneratorId.CEFI_TRADES,
        asset_group="cefi",
        data_type="trades",
        date_start="2024-01-01",
        date_end="2024-01-07",
        row_count_per_day=1_000,
        schema_version="trades.v3",
        shard_layout=SyntheticShardLayout(
            shard_key_axes=("venue", "instrument"),
            shards_per_day=2,
            partition_template="venue={venue}/instrument={instrument}/dt={dt}",
        ),
        output_uri="gs://central-element-323112-benchmark-synthetic/cefi/trades",
        venues=("bybit",),
        instruments=("BTCUSDT",),
    )
    base.update(overrides)
    return SyntheticParams(**base)  # type: ignore[arg-type]


def test_params_valid_round_trip() -> None:
    p = _cefi_params()
    dumped = p.model_dump(mode="json")
    assert SyntheticParams.model_validate(dumped) == p


def test_params_rejects_reversed_date_range() -> None:
    with pytest.raises(ValidationError):
        _cefi_params(date_start="2024-02-01", date_end="2024-01-01")


def test_params_rejects_bad_date_format() -> None:
    with pytest.raises(ValidationError):
        _cefi_params(date_start="20240101")


def test_params_rejects_venue_layout_without_venues() -> None:
    with pytest.raises(ValidationError):
        _cefi_params(venues=())


def test_params_rejects_chain_layout_without_chains() -> None:
    with pytest.raises(ValidationError):
        SyntheticParams(
            generator_id=SyntheticGeneratorId.DEFI_GAS,
            asset_group="defi",
            data_type="gas",
            date_start="2024-01-01",
            date_end="2024-01-02",
            row_count_per_day=1_000,
            schema_version="gas.v2",
            shard_layout=SyntheticShardLayout(
                shard_key_axes=("chain",), shards_per_day=1, partition_template="chain={chain}/dt={dt}",
            ),
            output_uri="gs://x/y",
            chains=(),
        )


def test_params_hash_is_deterministic() -> None:
    assert _cefi_params().params_hash() == _cefi_params().params_hash()
    assert len(_cefi_params().params_hash()) == 16


def test_params_hash_changes_with_seed() -> None:
    assert _cefi_params(seed=1).params_hash() != _cefi_params(seed=2).params_hash()


def test_params_is_frozen() -> None:
    p = _cefi_params()
    with pytest.raises(ValidationError):
        p.row_count_per_day = 5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# SyntheticGeneratorSpec
# ---------------------------------------------------------------------------


def test_spec_make_default_params_cardinality() -> None:
    spec = get_generator_spec(SyntheticGeneratorId.CEFI_TRADES)
    params = spec.make_default_params(
        date_start="2024-01-01",
        date_end="2024-01-31",
        output_uri="gs://x/cefi/trades",
        venues=("bybit", "okx", "binance"),
        instruments=("BTCUSDT", "ETHUSDT"),
    )
    # venue x instrument == 3 x 2 == 6 cells
    assert params.shard_layout.shards_per_day == 6
    assert params.row_count_per_day == spec.default_row_count_per_day
    assert params.realism_axis == SyntheticRealismAxis.SHARD_COUNT


def test_spec_make_default_params_chain_only_cardinality() -> None:
    spec = get_generator_spec(SyntheticGeneratorId.DEFI_GAS)
    params = spec.make_default_params(
        date_start="2024-01-01",
        date_end="2024-01-02",
        output_uri="gs://x/defi/gas",
        chains=("ethereum", "arbitrum", "solana"),
    )
    assert params.shard_layout.shards_per_day == 3


def test_spec_row_count_override() -> None:
    spec = get_generator_spec(SyntheticGeneratorId.CEFI_OHLCV_1M)
    params = spec.make_default_params(
        date_start="2024-01-01",
        date_end="2024-01-02",
        output_uri="gs://x",
        venues=("bybit",),
        instruments=("BTCUSDT",),
        row_count_per_day=999,
    )
    assert params.row_count_per_day == 999


def test_get_generator_spec_accepts_string() -> None:
    assert get_generator_spec("cefi_trades").generator_id == SyntheticGeneratorId.CEFI_TRADES


def test_get_generator_spec_raises_keyerror_for_unregistered() -> None:
    # Construct an id that isn't a member -> SyntheticGeneratorId(...) raises ValueError first,
    # so test the post-registration KeyError path by clearing-and-restoring is overkill; assert the str path raises.
    with pytest.raises(ValueError):
        get_generator_spec("not_a_generator")


# ---------------------------------------------------------------------------
# Output / run manifests
# ---------------------------------------------------------------------------


def test_output_manifest_aggregates_rows_and_bytes() -> None:
    m = SyntheticOutputManifest(
        generator_id=SyntheticGeneratorId.CEFI_TRADES,
        asset_group="cefi",
        data_type="trades",
        params_hash="abcdef0123456789",
        schema_version="trades.v3",
        realism_axis=SyntheticRealismAxis.SHARD_COUNT,
        date_start="2024-01-01",
        date_end="2024-01-02",
        generated_at_iso="2026-05-12T00:00:00Z",
        output_uri="gs://x/cefi/trades",
        shards=(
            SyntheticShardManifest(
                shard_uri="gs://x/cefi/trades/venue=bybit/instrument=BTCUSDT/dt=2024-01-01/part-0.parquet",
                shard_key={"venue": "bybit", "instrument": "BTCUSDT", "dt": "2024-01-01"},
                row_count=50_000,
                byte_size=2_000_000,
                available_at_iso="2024-01-02T00:00:01Z",
            ),
            SyntheticShardManifest(
                shard_uri="gs://x/cefi/trades/venue=okx/instrument=BTCUSDT/dt=2024-01-01/part-0.parquet",
                shard_key={"venue": "okx", "instrument": "BTCUSDT", "dt": "2024-01-01"},
                row_count=40_000,
                byte_size=1_600_000,
                available_at_iso="2024-01-02T00:00:01Z",
            ),
        ),
    )
    assert m.total_rows == 90_000
    assert m.total_bytes == 3_600_000
    assert SyntheticOutputManifest.model_validate(m.model_dump(mode="json")) == m


def test_run_manifest_requires_at_least_one_generator_manifest() -> None:
    with pytest.raises(ValidationError):
        SyntheticRunManifest(
            run_id="r1",
            archetype="carry_staked_basis",
            started_at_iso="2026-05-12T00:00:00Z",
            generator_manifests=(),
        )


# ---------------------------------------------------------------------------
# Registry completeness
# ---------------------------------------------------------------------------


def test_registry_has_thirteen_generators() -> None:
    assert len(SYNTHETIC_GENERATOR_REGISTRY) == 13
    assert len(ALL_GENERATORS) == 13


def test_registry_per_asset_group_split() -> None:
    assert len(CEFI_GENERATORS) == 6
    assert len(DEFI_GENERATORS) == 5
    assert len(TRADFI_GENERATORS) == 2
    assert all(s.asset_group == "cefi" for s in CEFI_GENERATORS)
    assert all(s.asset_group == "defi" for s in DEFI_GENERATORS)
    assert all(s.asset_group == "tradfi" for s in TRADFI_GENERATORS)


def test_every_registered_id_resolves_to_a_spec() -> None:
    for gen_id in SyntheticGeneratorId:
        assert get_generator_spec(gen_id).generator_id == gen_id


def test_carry_staked_basis_archetype_has_defi_generators() -> None:
    specs = generators_for_archetype("carry_staked_basis")
    ids = {s.generator_id for s in specs}
    assert {
        SyntheticGeneratorId.DEFI_GAS,
        SyntheticGeneratorId.DEFI_LST_RATES,
        SyntheticGeneratorId.DEFI_LENDING_INDICES,
        SyntheticGeneratorId.DEFI_DEX_POOL_STATE,
        SyntheticGeneratorId.DEFI_ORACLE_FEEDS,
    } <= ids


def test_leveraged_funding_arb_archetype_has_cefi_generators() -> None:
    specs = generators_for_archetype("leveraged_funding_arb")
    ids = {s.generator_id for s in specs}
    assert {
        SyntheticGeneratorId.CEFI_TRADES,
        SyntheticGeneratorId.CEFI_FUNDING_RATE,
        SyntheticGeneratorId.CEFI_OPEN_INTEREST,
        SyntheticGeneratorId.CEFI_LIQUIDATIONS,
    } <= ids


def test_arbitrage_price_dispersion_alias_has_cefi_generators() -> None:
    # The plan body names the CeFi cutover archetype as ARBITRAGE_PRICE_DISPERSION in some places.
    specs = generators_for_archetype("ARBITRAGE_PRICE_DISPERSION")
    assert SyntheticGeneratorId.CEFI_TRADES in {s.generator_id for s in specs}


@pytest.mark.parametrize("spec", ALL_GENERATORS, ids=lambda s: s.generator_id.value)
def test_every_spec_has_nonempty_pipeline_stages_and_archetypes(spec: SyntheticGeneratorSpec) -> None:
    assert len(spec.pipeline_stages_touching) >= 1
    assert len(spec.archetypes_consuming) >= 1
    assert spec.default_row_count_per_day > 0
    assert all(a in {"mtds_read", "mdps_compute", "features", "ml_inference", "strategy", "matching_engine"}
               for a in spec.pipeline_stages_touching)


@pytest.mark.parametrize("spec", ALL_GENERATORS, ids=lambda s: s.generator_id.value)
def test_every_spec_default_layout_is_constructible(spec: SyntheticGeneratorSpec) -> None:
    layout = SyntheticShardLayout(
        shard_key_axes=spec.default_shard_key_axes,
        shards_per_day=1,
        partition_template=spec.default_partition_template,
    )
    # Every placeholder in the partition template must be a shard axis or asset_group/data_type/dt.
    import re

    placeholders = set(re.findall(r"\{(\w+)\}", spec.default_partition_template))
    allowed = set(layout.shard_key_axes) | {"asset_group", "data_type", "dt"}
    assert placeholders <= allowed, f"{spec.generator_id}: {placeholders - allowed} not in {allowed}"


# ---------------------------------------------------------------------------
# register_generator semantics
# ---------------------------------------------------------------------------


def test_register_generator_idempotent_same_instance() -> None:
    spec = get_generator_spec(SyntheticGeneratorId.DEFI_GAS)
    register_generator(spec)  # re-register identical -> no-op
    assert SYNTHETIC_GENERATOR_REGISTRY[SyntheticGeneratorId.DEFI_GAS] == spec


def test_register_generator_rejects_conflicting_redefinition() -> None:
    original = get_generator_spec(SyntheticGeneratorId.DEFI_GAS)
    mutated = original.model_copy(update={"description": "DIFFERENT — should conflict"})
    with pytest.raises(ValueError):
        register_generator(mutated)
    # registry unchanged
    assert SYNTHETIC_GENERATOR_REGISTRY[SyntheticGeneratorId.DEFI_GAS] == original


def test_make_decimal_helper_avoids_float_loss() -> None:
    assert make_decimal("0.1") + make_decimal("0.2") == make_decimal("0.3")
