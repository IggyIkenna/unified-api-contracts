"""Unit tests for the canonical possible-manifest registry (CF-15 / V0).

Covers the four public primitives — ``canonical_path_templates`` (the Axis-10
de-scatter SSOT), ``is_valid_shard_key`` (the orphan validator), ``enumerate_possible_
shard_keys`` (the could-exist generator), and ``get_possible_manifest_spec`` (the
per-AG authority object) — plus the regression guard that the generated path templates
remain a superset of the shapes the phantom reconciler / orphan sweep must probe.
"""

from __future__ import annotations

from typing import ClassVar

import pytest

from unified_api_contracts import (
    POSSIBLE_MANIFEST_ASSET_GROUPS,
    CatalogueLeaf,
    PossibleManifestSpec,
    ShardKey,
    canonical_path_templates,
    enumerate_possible_shard_keys,
    external_batch_sources_for_asset_group,
    get_possible_manifest_spec,
    is_valid_shard_key,
)

# The pipeline_mode batch sources every AG's raw-tick corpus physically uses. This
# is the durable in-repo regression guard for the de-scatter: if a consumer ever
# loses a source from its hand-list (the Axis-10 bug), this set still names it, and
# the generated templates must carry every one. Sourced from the migrated phantom
# reconciler ``prefix_tpls`` ground truth (2026-06-10).
_EXPECTED_BATCH_SOURCES = {
    "cefi": {"databento", "tardis", "hyperliquid"},
    "defi": {
        "onchain_rpc",
        "onchain_subgraph",
        "hyperliquid",
        "chainlink",
        "pyth_hermes",
        "helius_rpc",
        "solana_rpc",
    },
    "tradfi": {"databento", "massive", "yahoo", "eia"},  # barchart retired 2026-06-24
    "prediction": {"polymarket_clob", "polymarket_gamma_api", "kalshi"},
}

# Legacy/transitional pipeline_mode tokens that coexist on disk and MUST still be
# probed until the gated migrator rewrites them.
_EXPECTED_LEGACY_SOURCES = {"cefi": {"hyperliquid_rest"}, "defi": {"hyperliquid_rest"}}


class TestCanonicalPathTemplates:
    @pytest.mark.parametrize("asset_group", ["cefi", "defi", "tradfi", "prediction"])
    def test_every_known_batch_source_yields_a_pipeline_mode_prefix(self, asset_group: str) -> None:
        """Axis-10 regression guard: every known batch source for the AG appears as a
        ``pipeline_mode=batch_<source>/asset_group=<ag>/`` prefix in the templates."""
        templates = canonical_path_templates(asset_group)
        joined = "\n".join(templates)
        for source in _EXPECTED_BATCH_SOURCES[asset_group] | _EXPECTED_LEGACY_SOURCES.get(asset_group, set()):
            needle = f"pipeline_mode=batch_{source}/asset_group={asset_group}/"
            assert needle in joined, f"{asset_group}: template set missing {needle}"

    @pytest.mark.parametrize("asset_group", ["cefi", "defi", "tradfi", "prediction"])
    def test_live_pipeline_mode_prefixes_present(self, asset_group: str) -> None:
        """CF-15 (2026-07-11): the phantom-existence probe must ALSO enumerate
        ``pipeline_mode=live_<source>/`` — a ``captured`` cell has data whether written by
        the batch backfill or the live writer (live=batch spine; CF-12). Batch-only
        templates false-phantomed 13,292 LIVE-captured prediction cells."""
        from unified_api_contracts.canonical.crosscutting.pipeline_mode import Mode, pipeline_mode_for_source

        joined = "\n".join(canonical_path_templates(asset_group))
        for source in _EXPECTED_BATCH_SOURCES[asset_group]:
            try:
                live_val = pipeline_mode_for_source(source, Mode.LIVE).value
            except ValueError:
                continue  # source has no live pipeline_mode (e.g. polymarket_gamma_api)
            needle = f"pipeline_mode={live_val}/asset_group={asset_group}/"
            assert needle in joined, f"{asset_group}: template set missing live prefix {needle}"

    @pytest.mark.parametrize("asset_group", ["cefi", "defi", "tradfi", "prediction"])
    def test_legacy_hive_shapes_present(self, asset_group: str) -> None:
        """Bare ``asset_group=`` (no pipeline_mode), legacy ``category=`` hive, and the
        top-level ``day=`` shapes must all be probed (pre-migration on-disk shapes)."""
        joined = "\n".join(canonical_path_templates(asset_group))
        assert f"raw_tick_data/by_date/day={{date}}/asset_group={asset_group}/" in joined
        assert f"raw_tick_data/by_date/day={{date}}/category={asset_group}/" in joined
        assert f"day={{date}}/asset_group={asset_group}/" in joined

    def test_cefi_tradfi_segment_shape(self) -> None:
        """CeFi/TradFi carry venue -> instrument_type -> data_type segments."""
        for ag in ("cefi", "tradfi"):
            joined = "\n".join(canonical_path_templates(ag))
            assert "venue={venue}/instrument_type={instrument_type}/data_type={data_type}/" in joined

    def test_defi_segment_shape_includes_chain(self) -> None:
        joined = "\n".join(canonical_path_templates("defi"))
        assert "venue={venue}/chain={chain}/instrument_type={instrument_type}/data_type={data_type}/" in joined
        # combined venue-chain legacy overload (EIGENLAYER restaking)
        assert "venue={venue}-{chain}/" in joined

    def test_prediction_union_live_prefixes_enumerated(self) -> None:
        """§5 UNION (prediction_consolidated_closeout_2026_07_18, operator 2026-07-18):
        a batch prediction manifest row is satisfied by live-only object evidence, so
        the probe set MUST enumerate ``live_kalshi`` / ``live_polymarket_clob`` /
        ``live_polymarket_gamma_api`` — including ``polymarket_gamma_api``, which is
        registered BATCH-only in ``SOURCE_MODE_CAPABILITY`` (no ``LIVE_`` enum member)
        so the capability-derived batch+live loop cannot emit it. The prefix is added
        as a prediction-scoped probe WITHOUT claiming gamma_api is live-capable."""
        joined = "\n".join(canonical_path_templates("prediction"))
        for live_val in ("live_kalshi", "live_polymarket_clob", "live_polymarket_gamma_api"):
            needle = f"pipeline_mode={live_val}/asset_group=prediction/"
            assert needle in joined, f"prediction: template set missing UNION live prefix {needle}"

    def test_extra_live_probe_sources_do_not_leak_cross_ag(self) -> None:
        """RULE 11 cross-AG guard (relaxed 2026-07-19, operator-ruled): the
        ``_EXTRA_LIVE_PROBE_SOURCES_BY_AG`` mechanism is now used by BOTH prediction
        (kalshi / polymarket_*) AND cefi (binance/bybit/kraken/okx live-WS CEX venues whose
        batch source is tardis) — the earlier "prediction-scoped only" baseline was incidental
        (prediction was just the only AG that needed it then). The REAL invariant: each AG's
        extra-probe sources appear ONLY in that AG's templates, never leaking into another AG;
        each AG's pipeline_mode-prefix count = capability-derived baseline + its own extra-probe."""
        # cefi 16→17 (2026-07-18: +batch_lighter_api); 17→21 (2026-07-19: +4 live_ CEX probes
        # binance/bybit/kraken/okx). defi 15→16 (2026-07-21: +batch_aave — AAVE on-chain
        # oracle, lst_rate_honest_coverage plan Phase 1); 16→17 (2026-07-26: +batch_defillama
        # — solana_lst_archival.py Tier-4 historical price-ratio proxy,
        # defi_satellite_ao_dispatch_batch1_2026_07_25.md lst_rates_handler.py sub-item (a)).
        # 2026-07-27: `_canonical_pipeline_mode_prefixes` gained a `Mode.REPLAY` leg
        # (defi_satellite_ao_dispatch_batch1_2026_07_25.md) — every REPLAY-capable batch
        # source (per SOURCE_MODE_CAPABILITY) now also emits a `replay_<source>/` prefix.
        # cefi 21→27 (+6: aster/databento/deribit/extended/hyperliquid/kalshi_perp — tardis
        # and lighter_api stay BATCH-only). defi 17→24 (+7: chainlink/helius_rpc/
        # hyperliquid/onchain_rpc/onchain_subgraph/pyth_hermes/solana_rpc — aave/defillama
        # stay BATCH-only). tradfi 6→9 (+3: databento/eia/massive — yahoo stays BATCH-only);
        # 9→12 (2026-07-29: +fred/ecb/ofr — round-3 TRADFI
        # gcs_path_resolution_centralization_audit_2026_07_28.md pipeline_mode
        # provenance-fallback fix, SOURCE_PRIORITY[("tradfi","yield_curve"/"ohlcv_1d"/
        # "cds_spread")] now registers fred/ecb/ofr; all three are BATCH-only, so each
        # contributes exactly one prefix, same as yahoo's existing single-BATCH-prefix
        # pattern above).
        # Other AGs stay at their capability-derived baseline.
        expected_pipeline_mode_counts = {"cefi": 27, "defi": 24, "tradfi": 12, "sports": 0}
        for ag, expected in expected_pipeline_mode_counts.items():
            templates = canonical_path_templates(ag)
            pmode = [t for t in templates if "pipeline_mode=" in t]
            assert len(pmode) == expected, f"{ag}: pipeline_mode prefix count changed ({len(pmode)} != {expected})"
        # Cross-AG leak guard: a source in one AG's extra-probe must NOT appear in any other AG.
        # Match the EXACT pipeline_mode segment (trailing '/') so live_kalshi (prediction) does not
        # false-match cefi's legitimate live_kalshi_perp.
        owner_sources = {
            "prediction": ("polymarket_gamma_api", "kalshi"),
            "cefi": ("binance", "kraken", "okx"),
        }
        for owner_ag, sources in owner_sources.items():
            for other_ag in ("cefi", "defi", "tradfi", "sports", "prediction"):
                if other_ag == owner_ag:
                    continue
                templates = canonical_path_templates(other_ag)
                for src in sources:
                    seg = f"pipeline_mode=live_{src}/"
                    assert not any(seg in t for t in templates), (
                        f"{owner_ag} extra-probe source live_{src} leaked into {other_ag} templates"
                    )

    def test_prediction_templates_have_no_duplicate_prefixes(self) -> None:
        """The append-if-absent extra-probe must not duplicate the LIVE-capable
        (kalshi / polymarket_clob) live prefixes the batch+live loop already emits."""
        templates = canonical_path_templates("prediction")
        assert len(templates) == len(set(templates))

    def test_sports_has_no_inline_templates(self) -> None:
        """Sports dispatches to its own UAC ``candidate_parquet_paths`` SSOT — the
        possible-manifest registry returns an empty template list (NOT 'no paths')."""
        assert canonical_path_templates("sports") == []

    def test_templates_carry_only_known_placeholders(self) -> None:
        allowed = {"date", "venue", "chain", "instrument_type", "data_type"}
        import re

        for ag in POSSIBLE_MANIFEST_ASSET_GROUPS:
            for tpl in canonical_path_templates(ag):
                for ph in re.findall(r"\{(\w+)\}", tpl):
                    assert ph in allowed, f"{ag}: unexpected placeholder {{{ph}}} in {tpl}"


class TestExternalBatchSources:
    @pytest.mark.parametrize("asset_group", ["cefi", "defi", "tradfi", "prediction"])
    def test_known_sources_are_a_subset_of_derived(self, asset_group: str) -> None:
        derived = set(external_batch_sources_for_asset_group(asset_group))
        assert _EXPECTED_BATCH_SOURCES[asset_group] <= derived

    def test_sports_sources_excluded_from_path_templates(self) -> None:
        # sports has external sources (api_football etc.) but no inline pipeline_mode
        # path templates — they live in the sports candidate_parquet_paths SSOT.
        assert canonical_path_templates("sports") == []


class TestIsValidShardKey:
    def test_valid_cefi_perp_trades(self) -> None:
        key = ShardKey("cefi", "BINANCE-FUTURES", "", "perpetual", "trades")
        assert is_valid_shard_key("cefi", key) is True

    def test_invalid_data_type_for_instrument_type(self) -> None:
        # spot_pair cannot carry derivative_ticker (a perp-only data_type)
        key = ShardKey("cefi", "BINANCE-SPOT", "", "spot_pair", "derivative_ticker")
        assert is_valid_shard_key("cefi", key) is False

    def test_unmapped_instrument_type_admitted(self) -> None:
        # an unknown instrument_type must NOT be silently rejected
        key = ShardKey("cefi", "BINANCE-SPOT", "", "some_new_shape", "trades")
        assert is_valid_shard_key("cefi", key) is True

    def test_empty_data_type_rejected(self) -> None:
        key = ShardKey("cefi", "BINANCE-SPOT", "", "spot_pair", "")
        assert is_valid_shard_key("cefi", key) is False

    def test_unknown_asset_group_rejected(self) -> None:
        key = ShardKey("shared", "X", "", "spot_pair", "trades")
        assert is_valid_shard_key("shared", key) is False

    def test_prediction_data_type_grain(self) -> None:
        key = ShardKey("prediction", "POLYMARKET", "", "", "trades")
        assert is_valid_shard_key("prediction", key) is True


class TestEnumeratePossibleShardKeys:
    def test_family_grain_cefi_nonempty_and_valid(self) -> None:
        keys = list(enumerate_possible_shard_keys("cefi"))
        assert keys, "cefi family-grain enumeration must be non-empty"
        # every emitted family-grain key is itself valid
        for k in keys[:200]:
            assert is_valid_shard_key("cefi", k)

    def test_unknown_asset_group_yields_nothing(self) -> None:
        assert list(enumerate_possible_shard_keys("shared")) == []

    def test_catalogue_grain_binds_instrument_id(self) -> None:
        leaves = [CatalogueLeaf("BTC-PERP", "perpetual", "BINANCE-FUTURES")]
        keys = list(enumerate_possible_shard_keys("cefi", catalogue=leaves))
        assert keys
        assert all(k.instrument_id == "BTC-PERP" for k in keys)
        assert {k.data_type for k in keys} <= {
            "trades",
            "book_snapshot_5",
            "derivative_ticker",
            "liquidations",
            "ohlcv_1m",
            # 2026-06-21: perp_funding added to cefi/perpetual for CFTC-regulated venues
            "perp_funding",
        }

    def test_option_leaf_rolls_up_to_one_bundle(self) -> None:
        """G1-ENUM bundle roll-up: many option leaves of one underlying collapse to a
        single per-underlying ``options_chain`` candidate (not one per contract)."""
        leaves = [
            CatalogueLeaf("BTC-29MAR24-50000-C", "option", "DERIBIT", underlying="BTC"),
            CatalogueLeaf("BTC-29MAR24-60000-C", "option", "DERIBIT", underlying="BTC"),
            CatalogueLeaf("BTC-29MAR24-50000-P", "option", "DERIBIT", underlying="BTC"),
        ]
        keys = list(enumerate_possible_shard_keys("cefi", catalogue=leaves))
        # all three leaves collapse to ONE underlying bundle
        assert {k.instrument_id for k in keys} == {"BTC"}
        assert {k.instrument_type for k in keys} == {"options_chain"}

    def test_prediction_family_grain_data_type_only(self) -> None:
        keys = list(enumerate_possible_shard_keys("prediction"))
        assert keys
        assert all(k.instrument_type == "" and k.venue == "" for k in keys)


class TestPossibleManifestSpec:
    @pytest.mark.parametrize("asset_group", list(POSSIBLE_MANIFEST_ASSET_GROUPS))
    def test_spec_builds_for_every_asset_group(self, asset_group: str) -> None:
        spec = get_possible_manifest_spec(asset_group)
        assert isinstance(spec, PossibleManifestSpec)
        assert spec.asset_group == asset_group
        assert isinstance(spec.shard_axes, tuple)
        # non-sports AGs must carry path templates
        if asset_group != "sports":
            assert spec.path_templates, f"{asset_group}: spec must carry path templates"

    def test_unknown_asset_group_raises(self) -> None:
        with pytest.raises(ValueError, match="unknown asset_group"):
            get_possible_manifest_spec("shared")

    def test_spec_methods_delegate(self) -> None:
        spec = get_possible_manifest_spec("cefi")
        key = ShardKey("cefi", "BINANCE-FUTURES", "", "perpetual", "trades")
        assert spec.is_valid(key) is True
        assert list(spec.enumerate_shard_keys())[:1]  # non-empty


class TestAxisCompleteness:
    """CF-15/CF-18 join: each AG's spec must declare every shard axis its data physically
    carries — no AG silently missing a dimension (e.g. DeFi must carry `chain`)."""

    # The shard axes each AG's raw-tick data physically carries (the market-tick-data
    # shard atom). A spec missing any of these would under-key the could-exist universe.
    _EXPECTED_AXES: ClassVar[dict[str, set[str]]] = {
        "cefi": {"venue", "data_type", "instrument_type", "instrument_id"},
        "tradfi": {"venue", "data_type", "instrument_type", "instrument_id"},
        "defi": {"venue", "chain", "data_type", "instrument_id"},
        "sports": {"data_type", "league_id"},
        "prediction": {"venue", "canonical_question_group", "data_type"},
    }

    @pytest.mark.parametrize("asset_group", list(POSSIBLE_MANIFEST_ASSET_GROUPS))
    def test_spec_declares_every_physical_axis(self, asset_group: str) -> None:
        spec = get_possible_manifest_spec(asset_group)
        expected = self._EXPECTED_AXES[asset_group]
        missing = expected - set(spec.shard_axes)
        assert not missing, f"{asset_group}: spec.shard_axes missing physical axes {missing}"

    def test_defi_carries_chain_axis(self) -> None:
        # the regression guard: DeFi's extra `chain` dimension must never be dropped
        spec = get_possible_manifest_spec("defi")
        assert "chain" in spec.shard_axes
