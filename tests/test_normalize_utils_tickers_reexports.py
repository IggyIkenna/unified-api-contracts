"""Regression guard for normalize_utils/tickers.py re-export surface.

The file was once a 10-line stub with all 15 ticker re-exports missing —
causing ImportError on `normalize_aster_ticker` at every UAC consumer import
(workspace-wide outage; UAC@f008af9 fix 2026-05-13). This test locks the
re-export surface so any future deletion is caught at PR time.
"""

from __future__ import annotations

import importlib


def test_all_14_venue_ticker_normalizers_reexported():
    """The 14 expected venue ticker normalizers must be importable from
    normalize_utils.tickers.

    If a new venue ticker is added (or one removed), update both this list
    AND the `__all__` in tickers.py — they must stay in sync.
    """
    expected = {
        "normalize_aster_ticker",
        "normalize_binance_ticker",
        "normalize_bitget_ticker",
        "normalize_bybit_ticker",
        "normalize_ccxt_ticker",
        "normalize_coinbase_ticker",
        "normalize_deribit_ticker",
        "normalize_hyperliquid_ticker",
        "normalize_ibkr_ticker",
        "normalize_kalshi_ticker",
        "normalize_kucoin_ticker",
        "normalize_mexc_ticker",
        "normalize_okx_ticker",
        "normalize_upbit_ticker",
    }
    tickers_mod = importlib.import_module("unified_api_contracts.normalize_utils.tickers")
    for name in expected:
        assert hasattr(tickers_mod, name), (
            f"normalize_utils.tickers is missing re-export {name!r}. "
            f"See UAC@f008af9 incident — every consumer ImportError-fails when this regresses."
        )


def test_tickers_all_is_complete():
    """__all__ in tickers.py must list every re-exported symbol — keeps the
    module's public surface explicit + drives basedpyright unused-import
    suppression."""
    tickers_mod = importlib.import_module("unified_api_contracts.normalize_utils.tickers")
    assert hasattr(tickers_mod, "__all__"), "tickers.py must declare __all__"
    declared = set(tickers_mod.__all__)
    expected_min = {
        "normalize_aster_ticker",
        "normalize_binance_ticker",
        "normalize_bitget_ticker",
        "normalize_bybit_ticker",
        "normalize_ccxt_ticker",
        "normalize_coinbase_ticker",
        "normalize_deribit_ticker",
        "normalize_hyperliquid_ticker",
        "normalize_ibkr_ticker",
        "normalize_kalshi_ticker",
        "normalize_kucoin_ticker",
        "normalize_mexc_ticker",
        "normalize_okx_ticker",
        "normalize_upbit_ticker",
    }
    missing = expected_min - declared
    assert not missing, f"tickers.py __all__ missing entries: {sorted(missing)}"
