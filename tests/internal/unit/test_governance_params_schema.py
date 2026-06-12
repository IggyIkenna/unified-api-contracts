"""Unit tests for GovernanceParamsRow schema and governance_params_gcs_prefix helper.

Validates: field types, frozen invariant, extra-fields rejection, path prefix format,
and the example in governance_params_gcs_prefix's docstring.
"""

from __future__ import annotations

from datetime import UTC, date
from datetime import datetime as dt

import pytest

from unified_api_contracts.canonical.domain.onchain import (
    GovernanceParamsRow,
    governance_params_gcs_prefix,
)


def _make_row(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "protocol": "aave_v3",
        "chain": "ETHEREUM",
        "asset": "WETH",
        "param_name": "max_ltv",
        "param_value": "0.825",
        "asof_block": 20_000_000,
        "asof_timestamp": dt(2026, 5, 1, 12, 0, 0, tzinfo=UTC),
        "governance_tx_hash": "0xabc123",
    }
    base.update(overrides)
    return base


class TestGovernanceParamsRowSchema:
    def test_valid_row_round_trips(self) -> None:
        row = GovernanceParamsRow(**_make_row())
        assert row.protocol == "aave_v3"
        assert row.chain == "ETHEREUM"
        assert row.asset == "WETH"
        assert row.param_name == "max_ltv"
        assert row.param_value == "0.825"
        assert row.asof_block == 20_000_000
        assert row.governance_tx_hash == "0xabc123"

    def test_empty_governance_tx_hash_allowed(self) -> None:
        row = GovernanceParamsRow(**_make_row(governance_tx_hash=""))
        assert row.governance_tx_hash == ""

    def test_frozen_rejects_mutation(self) -> None:
        row = GovernanceParamsRow(**_make_row())
        with pytest.raises(Exception):
            row.param_value = "0.90"  # type: ignore[misc]

    def test_extra_fields_rejected(self) -> None:
        with pytest.raises(Exception):
            GovernanceParamsRow(**_make_row(unexpected_field="boom"))  # type: ignore[call-overload]

    def test_requires_aware_datetime(self) -> None:
        with pytest.raises(Exception):
            GovernanceParamsRow(**_make_row(asof_timestamp=dt(2026, 5, 1, 12, 0, 0)))

    def test_large_borrow_cap_value_as_string(self) -> None:
        row = GovernanceParamsRow(**_make_row(param_name="borrow_cap_tokens", param_value="2000000000"))
        assert row.param_value == "2000000000"

    def test_zero_block_allowed(self) -> None:
        row = GovernanceParamsRow(**_make_row(asof_block=0))
        assert row.asof_block == 0


class TestGovernanceParamsGcsPrefix:
    def test_basic_path_shape(self) -> None:
        prefix = governance_params_gcs_prefix("aave_v3", "ETHEREUM", date(2026, 5, 1))
        assert prefix == "governance_params/by_protocol/protocol=aave_v3/chain=ETHEREUM/by_date/day=2026-05-01/"

    def test_ends_with_slash(self) -> None:
        prefix = governance_params_gcs_prefix("compound_v3", "BASE", date(2026, 6, 20))
        assert prefix.endswith("/")

    def test_contains_protocol_partition(self) -> None:
        prefix = governance_params_gcs_prefix("morpho_blue", "ARBITRUM", date(2026, 1, 15))
        assert "protocol=morpho_blue" in prefix

    def test_contains_chain_partition(self) -> None:
        prefix = governance_params_gcs_prefix("aave_v3", "POLYGON", date(2026, 3, 10))
        assert "chain=POLYGON" in prefix

    def test_contains_day_partition(self) -> None:
        prefix = governance_params_gcs_prefix("aave_v3", "ETHEREUM", date(2026, 12, 31))
        assert "day=2026-12-31" in prefix

    def test_no_gs_prefix(self) -> None:
        prefix = governance_params_gcs_prefix("aave_v3", "ETHEREUM", date(2026, 5, 1))
        assert not prefix.startswith("gs://")
