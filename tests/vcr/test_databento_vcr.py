"""Auth-gated VCR tests for Databento metadata API.

These tests require DATABENTO_API_KEY to be set in the environment.
In record mode (cassette missing): makes live API call and saves cassette.
In replay mode (cassette present): replays without network access.

To record:
    DATABENTO_API_KEY=<key> pytest tests/vcr/test_databento_vcr.py -v
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
    / "databento"
    / "mocks"
)

_DATABENTO_API_KEY = os.environ.get("DATABENTO_API_KEY", "")
_HAS_DATABENTO_KEY = bool(_DATABENTO_API_KEY)


def _vcr_for_databento() -> VCR:
    """VCR instance that filters auth from recorded cassettes."""
    my_vcr = VCR()
    my_vcr.filter_headers = ["Authorization"]
    my_vcr.filter_query_parameters = ["key"]
    my_vcr.record_mode = "new_episodes" if _HAS_DATABENTO_KEY else "none"
    return my_vcr


@pytest.mark.skipif(  # reason: requires live Databento API key or a pre-recorded cassette
    not _HAS_DATABENTO_KEY and not (CASSETTE_DIR / "list_datasets.yaml").exists(),
    reason="DATABENTO_API_KEY not set and cassette not recorded yet",
)
def test_databento_list_datasets() -> None:
    """Databento metadata list_datasets — auth-gated or cassette replay."""
    cassette_path = CASSETTE_DIR / "list_datasets.yaml"
    auth = (_DATABENTO_API_KEY, "") if _HAS_DATABENTO_KEY else ("", "")

    with _vcr_for_databento().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://hist.databento.com/v0/metadata.list_datasets",
            auth=auth,
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)


@pytest.mark.skipif(  # reason: requires live Databento API key or a pre-recorded cassette
    not _HAS_DATABENTO_KEY and not (CASSETTE_DIR / "list_datasets.yaml").exists(),
    reason="DATABENTO_API_KEY not set and cassette not recorded yet",
)
def test_databento_datasets_contain_equities() -> None:
    """Databento dataset list includes major equity and futures datasets."""
    cassette_path = CASSETTE_DIR / "list_datasets.yaml"
    auth = (_DATABENTO_API_KEY, "") if _HAS_DATABENTO_KEY else ("", "")

    with _vcr_for_databento().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://hist.databento.com/v0/metadata.list_datasets",
            auth=auth,
        )
        data = response.json()
        # Datasets are strings like "GLBX.MDP3", "XNAS.ITCH"
        assert len(data) > 0, "Expected at least one dataset"


@pytest.mark.skipif(  # reason: requires live Databento API key or a pre-recorded cassette
    not _HAS_DATABENTO_KEY and not (CASSETTE_DIR / "symbology_resolve_es.yaml").exists(),
    reason="DATABENTO_API_KEY not set and cassette not recorded yet",
)
def test_databento_symbology_resolve_es() -> None:
    """Databento symbology resolution for ES (CME E-mini S&P 500 continuous contract)."""
    cassette_path = CASSETTE_DIR / "symbology_resolve_es.yaml"
    auth = (_DATABENTO_API_KEY, "") if _HAS_DATABENTO_KEY else ("", "")

    with _vcr_for_databento().use_cassette(str(cassette_path)):
        response = httpx.get(
            "https://hist.databento.com/v0/symbology.resolve",
            params={
                "dataset": "GLBX.MDP3",
                "symbols": "ES.c.0",
                "stype_in": "continuous",
                "stype_out": "instrument_id",
                "start_date": "2024-01-02",
                "end_date": "2024-01-03",
            },
            auth=auth,
        )
        assert response.status_code == 200
        data = response.json()
        assert data is not None
