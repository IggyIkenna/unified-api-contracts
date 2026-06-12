"""Governance-parameter parquet schema — time-versioned UAC contract.

Covers on-chain lending protocol governance parameters (LTV, liquidation threshold,
rate-curve kinks, borrow/supply caps) emitted by the Phase 1 event listener and
consumed by the features-onchain APR calculator + strategy-service sizing.

GCS path layout (SSOT: defi_governance_params_refresh_2026_06_20.md Phase 2):
    gs://{market-data-tick-defi-bucket}/governance_params/by_protocol/
        protocol={p}/chain={c}/by_date/day={d}/<uuid>.parquet

Asof reads: UTL ``read_governance_params_asof(protocol, chain, asset, asof)``.
``LookaheadBiasError`` is raised by the reader when any candidate row carries
``asof_timestamp > requested asof`` — future-dated writes are a data-integrity error.
"""

from __future__ import annotations

from datetime import date as date_type

from pydantic import AwareDatetime, ConfigDict

from .._base import CanonicalBase


class GovernanceParamsRow(CanonicalBase):
    """Single governance-parameter observation — one parquet row.

    Each row represents the value of one protocol parameter (``param_name``) for a
    specific (``protocol``, ``chain``, ``asset``) tuple at a given on-chain block.
    Multiple rows with the same tuple but different ``asof_block`` values represent
    the parameter history over time; asof lookups return the row with the highest
    ``asof_timestamp`` that does not exceed the requested ``asof`` datetime.

    Schema SSOT: ``defi_governance_params_refresh_2026_06_20.md`` Phase 2.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    protocol: str
    """Protocol identifier — lowercase snake_case (e.g. ``'aave_v3'``, ``'compound_v3'``,
    ``'morpho_blue'``). Matches the ``protocol=`` hive partition key in the GCS path."""

    chain: str
    """EVM chain name in uppercase (e.g. ``'ETHEREUM'``, ``'ARBITRUM'``, ``'BASE'``).
    Matches the ``chain=`` hive partition key in the GCS path."""

    asset: str
    """Asset symbol in uppercase (e.g. ``'WETH'``, ``'USDC'``, ``'WSTETH'``).
    Matches the governance asset in the on-chain event (collateral asset for LTV/threshold
    params; base asset for rate-curve / borrow-cap params)."""

    param_name: str
    """Parameter identifier (e.g. ``'max_ltv'``, ``'liquidation_threshold'``,
    ``'borrow_cap_tokens'``, ``'reserve_factor'``, ``'base_variable_borrow_rate'``).
    Consumers cast ``param_value`` to ``Decimal`` for ratio and rate params, ``int`` for
    token-denominated caps."""

    param_value: str
    """Parameter value serialised as a string to avoid precision loss across both
    ratio params (0.80, 0.005) and large-integer borrow-cap tokens (e.g. 2_000_000_000).
    Consumers are responsible for casting to the appropriate numeric type."""

    asof_block: int
    """Block number at which this parameter took effect on-chain."""

    asof_timestamp: AwareDatetime
    """UTC datetime derived from the block timestamp at which this parameter took effect.
    Used as the PIT lookup key: ``asof_timestamp <= requested_asof`` is the filter condition.
    Must never exceed the write timestamp; future-dated rows are a data-integrity violation."""

    governance_tx_hash: str
    """Transaction hash of the governance action (Aave proposal execution / Compound governor
    call / Morpho curator set-params tx) that set this parameter value.
    Empty string for bootstrap rows seeded at discovery time (no originating tx)."""


def governance_params_gcs_prefix(protocol: str, chain: str, day: date_type) -> str:
    """Return the bucket-relative GCS prefix for one (protocol, chain, day) partition.

    Prefix is relative to the bucket root — no ``gs://`` scheme, no bucket name.
    The caller supplies the bucket (resolved via
    ``resolve_bucket_name(cloud="gcp", kind="tick-data", asset_group="defi")``).

    Path shape::

        governance_params/by_protocol/protocol={p}/chain={c}/by_date/day={d}/

    Args:
        protocol: Protocol identifier (e.g. ``'aave_v3'``).
        chain: Chain name (e.g. ``'ETHEREUM'``).
        day: The date partition.

    Returns:
        Bucket-relative prefix string ending with ``/``, e.g.
        ``governance_params/by_protocol/protocol=aave_v3/chain=ETHEREUM/by_date/day=2026-05-01/``.

    Example:
        >>> from datetime import date
        >>> governance_params_gcs_prefix("aave_v3", "ETHEREUM", date(2026, 5, 1))
        'governance_params/by_protocol/protocol=aave_v3/chain=ETHEREUM/by_date/day=2026-05-01/'
    """
    return f"governance_params/by_protocol/protocol={protocol}/chain={chain}/by_date/day={day.isoformat()}/"
