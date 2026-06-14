"""Signal-variant → ML target map: exhaustiveness + structural invariants.

Guarantees every ``signal_variant`` carried by the archetype capability
registry is CLASSIFIED (predictive or deterministic) — so a new signal added
to an archetype cell forces a classification decision here rather than silently
dropping out of the capability graph's ``uses_model`` derivation.
"""

from __future__ import annotations

from unified_api_contracts.internal.architecture_v2.archetype_capability import (
    ARCHETYPE_CAPABILITY_REGISTRY,
)
from unified_api_contracts.internal.architecture_v2.ml_signal_targets import (
    NON_ML_SIGNAL_VARIANTS,
    SIGNAL_VARIANT_ML_TARGETS,
    is_classified_signal,
    ml_targets_for_signal,
)

# The ml-service target universe (config_schema.VALID_TARGET_TYPES + the DeFi
# target-builder keys). Mirrored here as strings — UAC does not import ml-service.
_VALID_TARGETS = frozenset(
    {
        "swing_high",
        "swing_low",
        "direction",
        "volatility",
        "cross_venue_spread",
        "clv",
        "xg",
        "ht_delta",
        "clv_meta",
        "xg_meta",
        "funding_rate",
        "lending_rate",
        "impermanent_loss",
    }
)


def _observed_signal_variants() -> set[str]:
    observed: set[str] = set()
    for entry in ARCHETYPE_CAPABILITY_REGISTRY:
        for cell in entry.cells:
            observed.update(cell.signal_variants)
    return observed


def test_every_observed_signal_is_classified() -> None:
    unclassified = sorted(s for s in _observed_signal_variants() if not is_classified_signal(s))
    assert not unclassified, f"unclassified signal_variants (add to predictive or non-ML): {unclassified}"


def test_predictive_and_non_ml_are_disjoint() -> None:
    assert not (set(SIGNAL_VARIANT_ML_TARGETS) & NON_ML_SIGNAL_VARIANTS)


def test_predictive_targets_are_valid_and_non_empty() -> None:
    for signal, targets in SIGNAL_VARIANT_ML_TARGETS.items():
        assert targets, f"{signal} maps to no targets — make it deterministic instead"
        unknown = sorted(set(targets) - _VALID_TARGETS)
        assert not unknown, f"{signal} maps to unknown target(s): {unknown}"


def test_deterministic_signals_yield_no_targets() -> None:
    for signal in NON_ML_SIGNAL_VARIANTS:
        assert ml_targets_for_signal(signal) == ()


def test_odds_covers_the_sports_targets() -> None:
    assert set(ml_targets_for_signal("odds")) == {"clv", "xg", "ht_delta", "clv_meta", "xg_meta"}
