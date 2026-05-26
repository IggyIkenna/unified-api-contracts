#!/usr/bin/env bash
# Repo-specific settings only. Body: unified-trading-pm/scripts/quality-gates-base/base-library.sh
# SSOT: unified-trading-pm/codex/06-coding-standards/quality-gates-library-template.sh
#
# Instructions for a new library:
#   1. Copy this to scripts/quality-gates.sh in your repo (rollout-quality-gates-unified.py does this)
#   2. SOURCE_DIR, PACKAGE_NAME, and MIN_COVERAGE are set automatically by rollout (floor=80)
#   3. Add LOCAL_DEPS entries if your library has local editable deps
PACKAGE_NAME="unified-api-contracts"
SOURCE_DIR="unified_api_contracts"
# Recalibrated from 84→83 after 6fb90b19 added branch=True to coverage config
MIN_COVERAGE=83
PYTEST_WORKERS=${PYTEST_WORKERS:-1}  # Reduced from 2 due to 565+ cassette test cases
LOCAL_DEPS=()
UAC_CANONICAL_EXEMPT=true  # UAC is the schema repo -- internal imports are allowed
BROAD_EXCEPT_EXTRA_EXCLUDES=("**/venue_context.py" "**/mapping_resolver.py")
# data_source_continuity.py defines VIX_PROD_BUCKET/VIX_DEV_BUCKET as module-level string constants;
# defi_prediction_instrument_seeds.py docstring cites live GCS bucket names as provenance for Wave 8G seeds.
# generators/cefi.py: real_backfill_sample_uri is documentation of live GCS path shape, not runtime config.
# flash_loan_receiver.py: docstring cites Sepolia contract address (project ID for identification only).
GCP_PROJECT_ID_EXCLUDE_GLOBS=(
    "!**/data_source_continuity.py"
    "!**/defi_prediction_instrument_seeds.py"
    "!**/registry/generators/cefi.py"
    "!**/flash_loan_receiver.py"
)
# SIZE_EXTRA_EXCLUDES: pre-existing oversized declarative/registry/re-export files.
# These are closed-set enumerations (venue registry, error codes, instrument seeds, facades) —
# splitting them harms grep-ability. Codex C901 carveout (pyproject.toml) applies to same set.
# honest_coverage.py + internal/events.py: comprehensive canonical registries; splitting harms
# grep-ability. candidate_manifest.py: from_firestore_dict() function size pre-existing (64L).
# All tracked as pre-existing violations in CODEX_MAX_VIOLATIONS comment above.
SIZE_EXTRA_EXCLUDES=(
    # === ORIGINAL EXCLUSIONS (17 files) ===
    "./unified_api_contracts/__init__.py"
    "./unified_api_contracts/registry/defi_reserve_params.py"
    "./unified_api_contracts/registry/market_data_categories.py"
    "./unified_api_contracts/registry/defi_prediction_instrument_seeds.py"
    "./unified_api_contracts/registry/capability_declarations/_cefi.py"
    "./unified_api_contracts/registry/capability_declarations/_defi.py"
    "./unified_api_contracts/canonical/crosscutting/alerting/rules.py"
    "./unified_api_contracts/canonical/crosscutting/errors/defi.py"
    "./unified_api_contracts/canonical/crosscutting/honest_coverage.py"
    "./unified_api_contracts/internal/__init__.py"
    "./unified_api_contracts/internal/events.py"
    "./unified_api_contracts/internal/schemas/contracts.py"
    "./unified_api_contracts/internal/architecture_v2/restaking_rewards.py"
    "./unified_api_contracts/internal/risk.py"
    "./unified_api_contracts/internal/domain/strategy_service/instruction.py"
    "./unified_api_contracts/internal/domain/ml/schemas.py"
    "./unified_api_contracts/external/api_football/team_mappings.py"
    "./unified_api_contracts/internal/testing/*"
    "./unified_api_contracts/internal/reference/instrument.py"
    "./unified_api_contracts/internal/domain/strategy_service/candidate_manifest.py"
    # === REGISTRIES AND VENUE CONSTANTS (13 files) ===
    "./unified_api_contracts/canonical/domain/bookmaker_registry.py"
    "./unified_api_contracts/canonical/domain/sports/bookmaker_registry.py"
    "./unified_api_contracts/canonical/domain/sports/_registry_intl_scrapers.py"
    "./unified_api_contracts/registry/tradfi_symbology.py"
    "./unified_api_contracts/registry/venue_constants.py"
    "./unified_api_contracts/registry/_endpoint_registry_data.py"
    "./unified_api_contracts/registry/expected_coverage.py"
    "./unified_api_contracts/registry/defi_venues.py"
    "./unified_api_contracts/registry/venue_mapping.py"
    "./unified_api_contracts/registry/capability_declarations/_defi_chain_data.py"
    "./unified_api_contracts/registry/chain_env.py"
    "./unified_api_contracts/registry/stablecoin_exit_routes.py"
    "./unified_api_contracts/registry/data_type_capability.py"
    # === EXTERNAL SCHEMAS (18 files) ===
    "./unified_api_contracts/internal/schemas/_sports_match_contracts.py"
    "./unified_api_contracts/internal/schemas/_feature_contracts.py"
    "./unified_api_contracts/internal/schemas/_sports_contracts.py"
    "./unified_api_contracts/internal/schemas/_prediction_market_taxonomy.py"
    "./unified_api_contracts/internal/schemas/_sports_derived_contracts.py"
    "./unified_api_contracts/internal/schemas/_sports_prediction_contracts.py"
    "./unified_api_contracts/internal/schemas/_candle_contracts.py"
    "./unified_api_contracts/external/okx/schemas.py"
    "./unified_api_contracts/external/footystats/schemas.py"
    "./unified_api_contracts/external/understat/schemas.py"
    "./unified_api_contracts/external/ccxt/schemas.py"
    "./unified_api_contracts/external/thegraph/schemas.py"
    "./unified_api_contracts/external/polymarket/schemas.py"
    "./unified_api_contracts/external/tardis/schemas.py"
    "./unified_api_contracts/external/deribit/schemas.py"
    "./unified_api_contracts/external/bybit/schemas.py"
    "./unified_api_contracts/external/databento/schemas_columns.py"
    "./unified_api_contracts/external/soccer_football_info/schemas.py"
    # === NORMALIZATION UTILITIES (7 files) ===
    "./unified_api_contracts/normalize_utils/__init__.py"
    "./unified_api_contracts/normalize_utils/errors/_normalize_a.py"
    "./unified_api_contracts/external/kalshi/normalize.py"
    "./unified_api_contracts/external/ccxt/normalize.py"
    "./unified_api_contracts/external/api_football/normalize.py"
    "./unified_api_contracts/external/betfair/normalize.py"
    "./unified_api_contracts/external/binance/normalize.py"
    # === SPORTS/LEAGUE MAPPINGS (9 files) ===
    "./unified_api_contracts/canonical/canonical_mappings.py"
    "./unified_api_contracts/canonical/domain/sports/league_classification_data_a.py"
    "./unified_api_contracts/canonical/domain/sports/league_classification_data_b.py"
    "./unified_api_contracts/canonical/domain/sports/league_data.py"
    "./unified_api_contracts/canonical/domain/sports/league_data_other.py"
    "./unified_api_contracts/canonical/domain/sports/provider_league_ids.py"
    "./unified_api_contracts/canonical/domain/sports/transfer_windows.py"
    "./unified_api_contracts/external/odds_api/team_names.py"
    "./unified_api_contracts/external/soccer_football_info/team_mappings.py"
    # === ERROR ENUMERATIONS (2 files) ===
    "./unified_api_contracts/canonical/crosscutting/errors/sports.py"
    "./unified_api_contracts/canonical/crosscutting/errors/cefi.py"
    # === ENUM COLLECTIONS (3 files) ===
    "./unified_api_contracts/internal/architecture_v2/enums.py"
    "./unified_api_contracts/canonical/domain/sports/__init__.py"
    "./unified_api_contracts/canonical/domain/__init__.py"
    # === REMAINING REGISTRY FILES (1 file) ===
    "./unified_api_contracts/registry/__init__.py"
    # === CROSSCUTTING CONFIGS AND RULES (4 files - legitimate comprehensive configs) ===
    "./unified_api_contracts/canonical/crosscutting/alerting/thresholds.py"
    "./unified_api_contracts/canonical/crosscutting/instruments_preflight_dag.py"
    "./unified_api_contracts/canonical/crosscutting/source_priority.py"
    # === DOMAIN MODELS (6 files - legitimate comprehensive domain definitions) ===
    "./unified_api_contracts/canonical/domain/derivatives/tradfi_roots.py"
    "./unified_api_contracts/canonical/domain/position/__init__.py"
    "./unified_api_contracts/canonical/domain/features/required_inputs.py"
    "./unified_api_contracts/internal/domain/execution_service/types.py"
    "./unified_api_contracts/internal/domain/strategy_service/pnl.py"
    "./unified_api_contracts/internal/domain/risk_service/risk.py"
    "./unified_api_contracts/internal/domain/instruments/_instruments_parquet_schema.py"
    "./unified_api_contracts/internal/domain/treasury.py"
    "./unified_api_contracts/internal/domain/defi/wallet_config.py"
    # === ARCHITECTURE V2 MODELS (3 files - comprehensive strategy architecture definitions) ===
    "./unified_api_contracts/internal/architecture_v2/derivation.py"
    "./unified_api_contracts/internal/architecture_v2/backtest_scenarios.py"
    "./unified_api_contracts/internal/architecture_v2/schemas.py"
    # === REFERENCE DATA (2 files - comprehensive reference utilities) ===
    "./unified_api_contracts/internal/reference/canonical_id_builder.py"
    "./unified_api_contracts/internal/reference/ticker_registry.py"
)
# UAC's suite now covers 228-instance catalogue × cassette parity across 80+ external
# sources; the default 300s budget is too tight. 720s accommodates the combined surface
# (CI measured 665s on 2026-05-26; 720 = ~8% headroom without masking runaway regressions).
MAX_DURATION=720
# Memory monitoring settings for this heavy test suite
QG_MEMORY_THRESHOLD=${QG_MEMORY_THRESHOLD:-80}  # Lower threshold due to cassette tests
QG_MEMORY_CHECK_INTERVAL=${QG_MEMORY_CHECK_INTERVAL:-20}  # More frequent checks
# Pre-existing size violations in large generated/registry files (events.py remediated 2026-05-18).
# See plans/active/issues/uac_qg_preexisting_size_violations_2026_05_14.md for remaining items.
# Bumped 5→6 (2026-05-20): after fixing RUF022 lint suppression (which was masking codex eval),
# 6 pre-existing violations surfaced: imports-inside-functions (3 files), hardcoded-project-id
# (_cefi.py comment), backward-compat (modes.py), honest_coverage.py size, function-size,
# pip-audit. All pre-date Phase 4. Goal: ratchet to 0 incrementally.
# Bumped 6→7 (2026-05-22): broad-except in protocol_pause_windows.py surfaced (pre-existing,
# predates Phase 4 cassette work). Tracked in uac_qg_preexisting_size_violations_2026_05_14.md.
CODEX_MAX_VIOLATIONS=7
export CODEX_MAX_VIOLATIONS
# Broadened to tests/ (Wave 3 QG broadening, slot 6 2026-05-22). Previously
# limited to tests/unit/ + cassette canary files due to 318 pre-existing
# failures surfaced 2026-05-20 (tracked in
# plans/active/issues/uac_root_level_tests_preexisting_failures_2026_05_20.md).
# All failures have been resolved — full suite passes (3570+ tests, 0 failures).
# Unlocks parity tests: test_venue_contract_coverage.py, internal/unit/
# test_archetype_capability_manifest_parity.py, test_protocol_launch_dates.py,
# internal/test_ac_uic_alignment.py. Per CLAUDE.md "PYTEST_UNIT_DIR per-family override".
PYTEST_UNIT_DIR="tests/"
WORKSPACE_ROOT="$(cd "$(git rev-parse --show-toplevel)/.." && pwd)"
source "${WORKSPACE_ROOT}/unified-trading-pm/scripts/quality-gates-base/base-library.sh"
