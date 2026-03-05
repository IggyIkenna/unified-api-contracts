"""Auth-gated VCR tests for Tardis historical data endpoints.

These tests require TARDIS_API_KEY to be set in the environment.
In record mode (cassette missing): makes live API call and saves cassette.
In replay mode (cassette present): replays without network access.

To record:
    TARDIS_API_KEY=<key> pytest tests/vcr/test_tardis_auth_vcr.py -v
"""

from __future__ import annotations

import os
from pathlib import Path

import httpx
import pytest
from vcr import VCR

CASSETTE_DIR = (
    Path(__file__).parent.parent.parent
    / "unified_api_contracts"
    / "unified_api_contracts_external"
    / "tardis"
    / "mocks"
)

_TARDIS_API_KEY = os.environ.get("TARDIS_API_KEY", "")
_HAS_TARDIS_KEY = bool(_TARDIS_API_KEY)


def _vcr_for_tardis() -> VCR:
    """VCR instance that filters the Authorization header from recorded cassettes."""
    my_vcr = VCR()
    my_vcr.filter_headers = ["Authorization"]
    my_vcr.record_mode = "new_episodes" if _HAS_TARDIS_KEY else "none"
    return my_vcr


@pytest.mark.skipif(  # reason: requires live Tardis API key or a pre-recorded cassette
    not _HAS_TARDIS_KEY and not (CASSETTE_DIR / "instruments_binance_futures.yaml").exists(),
    reason="TARDIS_API_KEY not set and cassette not recorded yet",
)
def test_tardis_instruments_binance_futures() -> None:
    """Tardis instruments for binance-futures — auth-gated or cassette replay."""
    cassette_path = CASSETTE_DIR / "instruments_binance_futures.yaml"
    headers = {"Authorization": f"Bearer {_TARDIS_API_KEY}"} if _HAS_TARDIS_KEY else {}

    with _vcr_for_tardis().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://api.tardis.dev/v1/instruments/binance-futures",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) and len(data) > 0


@pytest.mark.skipif(  # reason: requires live Tardis API key or a pre-recorded cassette
    not _HAS_TARDIS_KEY and not (CASSETTE_DIR / "instruments_binance_futures.yaml").exists(),
    reason="TARDIS_API_KEY not set and cassette not recorded yet",
)
def test_tardis_instruments_fields() -> None:
    """Tardis instrument records have required fields."""
    from unified_api_contracts.tardis.schemas import TardisInstrument

    cassette_path = CASSETTE_DIR / "instruments_binance_futures.yaml"
    headers = {"Authorization": f"Bearer {_TARDIS_API_KEY}"} if _HAS_TARDIS_KEY else {}

    with _vcr_for_tardis().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://api.tardis.dev/v1/instruments/binance-futures",
            headers=headers,
        )
        data = response.json()
        for raw in data[:5]:
            instrument = TardisInstrument.model_validate(raw)
            assert instrument.symbol is not None or instrument.exchange is not None


@pytest.mark.skipif(  # reason: requires live Tardis API key or a pre-recorded cassette
    not _HAS_TARDIS_KEY and not (CASSETTE_DIR / "instruments_deribit.yaml").exists(),
    reason="TARDIS_API_KEY not set and cassette not recorded yet",
)
def test_tardis_instruments_deribit() -> None:
    """Tardis instruments for Deribit — includes options and perpetuals."""
    cassette_path = CASSETTE_DIR / "instruments_deribit.yaml"
    headers = {"Authorization": f"Bearer {_TARDIS_API_KEY}"} if _HAS_TARDIS_KEY else {}

    with _vcr_for_tardis().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://api.tardis.dev/v1/instruments/deribit",
            headers=headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list) and len(data) > 0
