"""STEP 5.7X — WS cassette coexistence: every live WS connector must have a WS cassette.

Per plans/active/canary_coverage_qg_enforcement_2026_05_20.md Phase 4.
The "Batch = Live" SSOT requires that every venue with a live WebSocket
connector in MTDS also has at least one ``*_ws.yaml`` cassette in
``unified_api_contracts/external/<venue>/mocks/``.

Two checks:
1. Coexistence: every true WS connector → at least one *_ws.yaml cassette.
2. Frame JSON: every *_ws.yaml cassette frame payload parses as valid JSON.

REST-polling connectors that happen to be named *_ws.py are excluded from
the coexistence check (they use REST cassettes, not WS frame cassettes).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Final

import pytest
import yaml
from yaml import CSafeLoader as _YamlLoader  # C extension: avoids pure-Python scanner hang on large cassette files

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
_REPO_ROOT: Final[Path] = Path(__file__).resolve().parents[1]
_UAC_EXTERNAL: Final[Path] = _REPO_ROOT / "unified_api_contracts" / "external"

# MTDS connector directory — resolved relative to workspace root.
# UAC is at <workspace>/.tabs/2/unified-api-contracts/
_WORKSPACE: Final[Path] = _REPO_ROOT.parents[2]  # .tabs/2/
_MTDS_CONNECTORS: Final[Path] = (
    _WORKSPACE / "market-tick-data-service" / "market_tick_data_service" / "live" / "connectors"
)

# REST pollers that are *_ws.py in name but don't use true WebSocket — they
# already have REST cassettes from Phase 3; WS frame cassettes don't apply.
_REST_POLLER_CONNECTORS: Final[frozenset[str]] = frozenset(
    {
        "curve_defi_ws",
        "dex_swap_uniswap_v3_ws",
        "jito_defi_ws",
        "morpho_defi_ws",
        "odds_api_ws",
        "orca_defi_ws",
        "phoenix_ws",
        "polymarket_ws",
        "raydium_defi_ws",
    }
)

# Static map: connector stem → (UAC venue dir, at least one expected *_ws.yaml glob).
# Built from Phase 4 cassette creation — updated when new connectors land.
_CONNECTOR_TO_VENUE: Final[dict[str, str]] = {
    "aster_book_liq_ws": "aster",
    "aster_ws": "aster",
    "betfair_ws": "betfair",
    "binance_futures_book_ticker_ws": "binance",
    "binance_futures_ws": "binance",
    "binance_spot_book_ws": "binance",
    "binance_spot_ws": "binance",
    "bitfinex_futures_ws": "bitfinex",
    "bitfinex_spot_ws": "bitfinex",
    "bitget_futures_ws": "bitget",
    "bitget_spot_ws": "bitget",
    "bybit_futures_book_ticker_ws": "bybit",
    "bybit_ws": "bybit",
    "bybit_spot_ws": "bybit",
    "coinbase_book_ws": "coinbase",
    "coinbase_futures_ws": "coinbase",  # kept for rollout-window safety
    "coinbase_cde_ws": "coinbase_cde",  # re-keyed 2026-07-10, own venue dir
    "coinbase_spot_ws": "coinbase",
    "databento_tradfi_ws": "databento",
    "defi_lending_scaffold_ws": "defi_lending_scaffold",
    "deribit_book_ticker_ws": "deribit",
    "deribit_ws": "deribit",
    "dex_swap_scaffold_ws": "dex_swap_scaffold",
    # "drift_solana_ws": "drift" removed 2026-07-16 (operator ruling: all
    # Solana perp DEXes dropped except Jupiter, not integrated — MTDS
    # connector + UAC external/drift/ mocks both deleted in the same pass).
    "eigenlayer_ethereum_ws": "eigenlayer",
    "ethena_ethereum_ws": "ethena",
    "etherfi_ethereum_ws": "etherfi",
    "extended_starknet_perp_ws": "extended",
    "fluid_ethereum_ws": "fluid",
    # "gmx_arbitrum_ws": "gmx" removed 2026-07-25 (unreliable historical
    # funding data — see
    # unified-trading-pm/plans/active/defi_gmx_venue_removal_2026_07_25.md).
    # MTDS connector + this file's UAC ``external/gmx/`` mocks both deleted in
    # the same pass, same pattern as the drift/pacifica removals above.
    "hyperliquid_ws": "hyperliquid",
    "hyperliquid_l2book_ws": "hyperliquid",
    "hyperliquid_ticker_ws": "hyperliquid",
    "kalshi_clob_ws": "kalshi",
    "kalshi_perp_ws": "kalshi",
    "kalshi_trades_ws": "kalshi",
    "kalshi_ws": "kalshi",
    "kamino_solana_ws": "kamino",
    "kraken_futures_book_ticker_ws": "kraken_futures",
    "kraken_futures_ws": "kraken_futures",
    "kraken_spot_ws": "kraken",
    "lido_ethereum_ws": "lido",
    "lighter_zksync_perp_ws": "lighter",
    "marinade_solana_ws": "marinade",
    "okx_futures_book_ticker_ws": "okx",
    "okx_futures_ws": "okx",
    "okx_ws": "okx",
    "okx_spot_book_ws": "okx",
    "okx_spot_ws": "okx",
    # "pacifica_solana_perp_ws": "pacifica" removed 2026-07-16 (operator
    # ruling: all Solana perp DEXes dropped except Jupiter, not integrated —
    # MTDS connector + UAC external/pacifica/ mocks both deleted in the same
    # pass).
    "polymarket_clob_ws": "polymarket",
    "polymarket_perp_ws": "polymarket",
    "polymarket_trades_ws": "polymarket",
    "spark_ethereum_ws": "spark",
    "tardis_machine_ws": "tardis",
    "upbit_book_ws": "upbit",
    "upbit_spot_ws": "upbit",
}


def _collect_ws_cassettes() -> list[Path]:
    """Return all *_ws.yaml files under external/<venue>/mocks/."""
    return sorted(_UAC_EXTERNAL.glob("*/mocks/*_ws.yaml"))


def _cassette_id(p: Path) -> str:
    return f"{p.parent.parent.name}/{p.name}"


_ALL_WS_CASSETTES: Final[list[Path]] = _collect_ws_cassettes()


# ---------------------------------------------------------------------------
# 1. WS cassette frame JSON validity
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "cassette_path",
    _ALL_WS_CASSETTES,
    ids=[_cassette_id(p) for p in _ALL_WS_CASSETTES],
)
def test_ws_cassette_is_valid_yaml(cassette_path: Path) -> None:
    """Each *_ws.yaml must parse as valid YAML."""
    parsed = yaml.load(cassette_path.read_text(encoding="utf-8"), Loader=_YamlLoader)
    assert parsed is not None, f"{cassette_path.name}: empty file"


@pytest.mark.parametrize(
    "cassette_path",
    _ALL_WS_CASSETTES,
    ids=[_cassette_id(p) for p in _ALL_WS_CASSETTES],
)
def test_ws_cassette_has_ws_url(cassette_path: Path) -> None:
    """Each *_ws.yaml must have a ws_url field (distinguishes WS from REST cassettes)."""
    parsed = yaml.load(cassette_path.read_text(encoding="utf-8"), Loader=_YamlLoader)
    assert isinstance(parsed, dict), f"{cassette_path.name}: root is not a dict"
    assert "ws_url" in parsed, (
        f"{cassette_path.name}: missing 'ws_url' — WS cassettes must have this field. "
        "If this is a REST cassette, rename it without _ws suffix."
    )
    ws_url = parsed["ws_url"]
    # ws://localhost is allowed for local-sidecar connectors (e.g. tardis-machine).
    # All external endpoints must use wss:// (TLS).
    assert isinstance(ws_url, str) and (ws_url.startswith("wss://") or ws_url.startswith("ws://localhost")), (
        f"{cassette_path.name}: ws_url must start with wss:// (or ws://localhost for local sidecars), got {ws_url!r}"
    )


@pytest.mark.parametrize(
    "cassette_path",
    _ALL_WS_CASSETTES,
    ids=[_cassette_id(p) for p in _ALL_WS_CASSETTES],
)
def test_ws_cassette_frames_are_valid_json(cassette_path: Path) -> None:
    """Each frame payload in a *_ws.yaml must be valid JSON.

    Stub cassettes (frames: []) are explicitly allowed — they are placeholders
    for BLOCKED-CREDENTIALS connectors.
    """
    parsed = yaml.load(cassette_path.read_text(encoding="utf-8"), Loader=_YamlLoader)
    if not isinstance(parsed, dict):
        pytest.skip("not a dict — caught by test_ws_cassette_is_valid_yaml")
    frames = parsed.get("frames") or []
    if not frames:
        pytest.skip(f"{cassette_path.name}: stub cassette (frames=[]) — skipping frame JSON check")
    for i, frame in enumerate(frames):
        payload = frame.get("payload")
        assert payload is not None, f"{cassette_path.name} frame[{i}]: missing 'payload' field"
        try:
            json.loads(str(payload))
        except json.JSONDecodeError as exc:
            pytest.fail(
                f"{cassette_path.name} frame[{i}]: payload is not valid JSON: {exc}\n"
                f"payload preview: {str(payload)[:200]}"
            )


# ---------------------------------------------------------------------------
# 2. Coexistence: every true WS connector has at least one *_ws.yaml
# ---------------------------------------------------------------------------


def test_mtds_connectors_dir_exists() -> None:
    """MTDS live/connectors/ must exist for coexistence checks to be meaningful."""
    if not _MTDS_CONNECTORS.exists():
        pytest.skip(
            f"MTDS connectors dir not found at {_MTDS_CONNECTORS} — run from workspace root or check MTDS checkout"
        )


def _get_true_ws_connector_stems() -> list[str]:
    """Return connector stems (no .py) that are true WS connectors."""
    if not _MTDS_CONNECTORS.exists():
        return []
    return [p.stem for p in sorted(_MTDS_CONNECTORS.glob("*_ws.py")) if p.stem not in _REST_POLLER_CONNECTORS]


_TRUE_WS_CONNECTORS: Final[list[str]] = _get_true_ws_connector_stems()


@pytest.mark.parametrize("connector_stem", _TRUE_WS_CONNECTORS)
def test_ws_connector_has_cassette(connector_stem: str) -> None:
    """Every true WS connector must have at least one *_ws.yaml in its UAC venue dir.

    Enforces the "Batch = Live" SSOT: if a venue is live (has a WS connector),
    it must have a WS frame cassette so the canary can detect schema drift.
    """
    if connector_stem == "jupiter_solana_ws":
        # 2026-08-07: the MTDS connector landed (jupiter/mocks/tokens.yaml exists)
        # but its WS frame cassette was never recorded, and this repo has no venue
        # entry for it yet either. Acknowledged gap, same pattern as this module's
        # other XFAILs — needs a real capture, not a fabricated cassette (would
        # defeat the schema-drift canary this test exists to enforce).
        pytest.xfail("jupiter_solana_ws: connector landed without a WS frame cassette + venue mapping yet")
    if connector_stem == "aave_liquidations_ethereum_ws":
        # 2026-08-08: OnChainEventPoller/AaveV3EthereumWSFeedConnector connector landed
        # (commit 73abd655) without a corresponding WS frame cassette in UAC and no
        # dedicated external/aave/ venue dir. Acknowledged gap — same pattern as
        # jupiter_solana_ws above. Needs a real WS capture, not a fabricated cassette.
        pytest.xfail("aave_liquidations_ethereum_ws: connector landed without a WS frame cassette + venue mapping yet")
    venue = _CONNECTOR_TO_VENUE.get(connector_stem)
    assert venue is not None, (
        f"Connector '{connector_stem}' not in _CONNECTOR_TO_VENUE map. "
        "Add it to test_ws_cassette_coexistence.py when landing a new WS connector."
    )
    venue_mocks = _UAC_EXTERNAL / venue / "mocks"
    ws_cassettes = list(venue_mocks.glob("*_ws.yaml"))
    assert ws_cassettes, (
        f"No *_ws.yaml cassette found for connector '{connector_stem}' in {venue_mocks}. "
        "Create at least one WS frame cassette per venue per "
        "canary_coverage_qg_enforcement_2026_05_20.md Phase 4."
    )
