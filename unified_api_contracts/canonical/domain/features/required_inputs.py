"""SSOT for the ``feature_group -> required_inputs`` DAG.

Single declaration consumed by:

* writegate's ``LookaheadBiasError.assert_no_lookahead(...)`` — every input
  row consumed by a feature compute must satisfy
  ``input.available_at <= target_ts - horizon``. The DAG drives the check.
* deployment-api ``data_status`` denominator — when the UI asks
  "is feature_group X covered for date D?", the denominator is
  ``required_inputs(X)`` clipped to source-coverage windows.
* features-* phantom audit — denominator + per-feature_group probe.

Today the DAG is inlined per-service across features-onchain, features-sports,
and features-delta-one (their respective ``feature_builder_registry.py``
modules). Per writegate's "Temporary states" table, those inlined DAGs
are the temporary state and this module is the named successor.

Layer discipline (CLAUDE.md "Shard-granularity SSOT"):

* **[UAC]** — this module declares WHAT inputs each feature_group requires.
* **[UTL]** — ``LookaheadBiasError`` reads this declaration.
* **[per-service]** — feature_builder_registry imports from here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
from typing import Final

from unified_api_contracts.canonical.crosscutting.availability_semantics import (
    AVAILABILITY_AT_SEMANTICS,
    AvailabilitySemantic,
)


@dataclass(frozen=True)
class InputReq:
    """A single ``(asset_group, data_type)`` input requirement for a feature_group.

    The ``available_at_rule`` mirrors writegate's ``AVAILABILITY_AT_SEMANTICS``
    taxonomy — it MUST equal ``AVAILABILITY_AT_SEMANTICS[(asset_group, data_type)]``
    or the lookahead-bias check will use the wrong stamping rule. Validation
    is enforced by ``validate_required_inputs()`` and the UAC test suite.

    ``source`` is optional. Set it when the feature group is bound to a
    specific adapter (e.g. ``"lido_api"`` for Lido LST yields, or
    ``"defillama_api"`` for DefiLlama TVL); leave it ``None`` for inputs
    that may come from any source for the ``(asset_group, data_type)``
    pair (e.g. CeFi ``ohlcv_1m`` from Tardis OR Databento).

    ``horizon`` is the lookahead buffer. ``timedelta(0)`` means "available
    by the target timestamp itself"; positive means "available at least
    ``horizon`` before target." Sports features use ``timedelta(hours=24)``
    or larger to model the kickoff-time lookahead window.
    """

    asset_group: str
    data_type: str
    available_at_rule: AvailabilitySemantic
    horizon: timedelta = field(default_factory=lambda: timedelta(0))
    source: str | None = None


# ---------------------------------------------------------------------------
# Registry — feature_group -> list[InputReq]
# ---------------------------------------------------------------------------
#
# Populated for feature_groups whose ``(asset_group, data_type)`` inputs are
# already registered in ``AVAILABILITY_AT_SEMANTICS``. Feature groups whose
# upstream data_types are not yet in availability_semantics (defi
# ``lending_indices`` / ``risk_params`` / ``rewards`` / ``flash_loan_events``
# / ``eigenlayer_rewards``; sports ``required_inputs`` reference-entity-name
# vocabulary) are deliberately omitted from this dict for now. They appear
# in ``EXPECTED_FEATURE_GROUPS_BY_SERVICE`` (denominator coverage), but the
# lookahead-bias check skips groups absent here. See
# ``## Temporary states + their canonical follow-up plans`` in
# ``feature_dag_uac_ssot_and_features_coverage_2026_05_06.plan.md``.

FEATURE_REQUIRED_INPUTS: Final[dict[str, list[InputReq]]] = {
    # ---- features-onchain (defi) ----------------------------------------
    # Two of the 12 calculators have AVAILABILITY_AT_SEMANTICS coverage today;
    # the other 10 are blocked behind the defi data_type vocabulary alignment
    # follow-up (lending_indices / risk_params / rewards / flash_loan_events
    # / eigenlayer_rewards need entries in availability_semantics). Once that
    # ships, lift the remaining 10 here in the same Phase 1A.2 commit.
    "lst_staking_yields": [
        InputReq(
            asset_group="defi",
            data_type="lst_yields",
            available_at_rule="tick_timestamp",
            source=None,  # multi-source: lido_api + etherfi_contract + jito_solana
        ),
    ],
    "defillama_tvl": [
        InputReq(
            asset_group="defi",
            data_type="liquidity",
            available_at_rule="tick_timestamp",
            source="defillama_api",
        ),
    ],
    # ---- features-delta-one (cefi / tradfi candle-derived) --------------
    # Price-based feature groups all read ohlcv_1m. We use ohlcv_1m as the
    # canonical base data_type (other timeframes derive from it via
    # resampling — same available_at semantic).
    "technical_indicators": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "moving_averages": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "oscillators": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "volatility_realized": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "momentum": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "volume_analysis": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "vwap": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "candlestick_patterns": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "market_structure": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "returns": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "round_numbers": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "streaks": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "targets": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "swing_outcome_targets": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    # Microstructure pulls book + tbbo (tradfi only — book_snapshot is a
    # CeFi-only AVAILABILITY_AT_SEMANTICS entry; tradfi uses tbbo).
    "microstructure": [
        InputReq(asset_group="cefi", data_type="book_snapshot", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="tbbo", available_at_rule="tick_timestamp"),
    ],
    "liquidations": [
        InputReq(asset_group="cefi", data_type="liquidations", available_at_rule="tick_timestamp"),
    ],
    "volume_flow": [
        InputReq(asset_group="cefi", data_type="trades", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="trades", available_at_rule="tick_timestamp"),
    ],
    # S/R + enrichment groups all read ohlcv_1m.
    "supply_demand_zones": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "fibonacci": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "level_confluence": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "market_structure_sequence": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "sr_memory": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "signal_confirmation": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "statistical_anomaly": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "order_flow_inference": [
        InputReq(asset_group="cefi", data_type="trades", available_at_rule="tick_timestamp"),
        InputReq(asset_group="cefi", data_type="book_snapshot", available_at_rule="tick_timestamp"),
    ],
    "return_kurtosis": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "polynomial_trendlines": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "risk_reward": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "wedge_quality": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
    "confluence": [
        InputReq(asset_group="cefi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
        InputReq(asset_group="tradfi", data_type="ohlcv_1m", available_at_rule="tick_timestamp"),
    ],
}
"""Registry — feature_group -> list of upstream input requirements.

Feature groups absent here are *not* unsupported; they're feature groups
whose upstream ``(asset_group, data_type)`` is not yet in
``AVAILABILITY_AT_SEMANTICS``. The lookahead-bias check skips them rather
than asserting against an unregistered semantic. See module docstring +
the named successor plan.

Derived feature groups (e.g. ``aave_rate_impact``, ``onchain_regime``,
``confluence``, ``risk_reward``) declare the TRANSITIVE upstream inputs
as if they were leaf inputs — the orchestrator's topological sort handles
the inter-feature_group dependency separately. This keeps lookahead-bias
checks simple: every feature_group's input list is the closure over
external data_types.
"""


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def get_required_inputs(feature_group: str) -> list[InputReq]:
    """Return the list of upstream inputs declared for ``feature_group``.

    Args:
        feature_group: A feature_group name (e.g. ``"lst_staking_yields"``,
            ``"technical_indicators"``).

    Returns:
        The list of ``InputReq`` declarations. Returns an empty list when
        the feature_group is unregistered — callers should treat this as
        "no lookahead-bias enforcement on this group" until the registry
        is filled in.
    """
    return FEATURE_REQUIRED_INPUTS.get(feature_group, [])


def has_required_inputs(feature_group: str) -> bool:
    """Return ``True`` iff ``feature_group`` has a non-empty input declaration."""
    return bool(FEATURE_REQUIRED_INPUTS.get(feature_group))


def list_feature_groups() -> list[str]:
    """Return the sorted list of feature_groups with declared input requirements."""
    return sorted(FEATURE_REQUIRED_INPUTS)


def validate_required_inputs() -> list[str]:
    """Validate the registry. Returns a list of human-readable issues.

    Empty list = registry is internally consistent. Used by the UAC test
    suite (``tests/test_feature_dag_ssot.py``).

    Checks:

    1. Every ``(asset_group, data_type)`` in ``FEATURE_REQUIRED_INPUTS``
       MUST be a key in ``AVAILABILITY_AT_SEMANTICS``.
    2. Every ``InputReq.available_at_rule`` MUST equal
       ``AVAILABILITY_AT_SEMANTICS[(asset_group, data_type)]``.
    3. Every ``feature_group`` key MUST have at least one ``InputReq``
       (no empty lists — omit the key instead).
    """
    issues: list[str] = []
    for feature_group, reqs in FEATURE_REQUIRED_INPUTS.items():
        if not reqs:
            issues.append(
                f"feature_group {feature_group!r} has empty required_inputs list — "
                "omit the key instead of declaring an empty list"
            )
            continue
        for req in reqs:
            key = (req.asset_group, req.data_type)
            registered = AVAILABILITY_AT_SEMANTICS.get(key)
            if registered is None:
                issues.append(
                    f"feature_group {feature_group!r} declares input "
                    f"asset_group={req.asset_group!r}, data_type={req.data_type!r} "
                    "but no AVAILABILITY_AT_SEMANTICS entry exists for that pair"
                )
                continue
            if registered != req.available_at_rule:
                issues.append(
                    f"feature_group {feature_group!r} declares "
                    f"available_at_rule={req.available_at_rule!r} for "
                    f"({req.asset_group}, {req.data_type}), but "
                    f"AVAILABILITY_AT_SEMANTICS says {registered!r}"
                )
    return issues


__all__ = [
    "FEATURE_REQUIRED_INPUTS",
    "InputReq",
    "get_required_inputs",
    "has_required_inputs",
    "list_feature_groups",
    "validate_required_inputs",
]
