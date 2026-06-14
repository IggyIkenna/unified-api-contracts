"""Archetype signal-variant → ML prediction-target map (operator-authored SSOT).

The capability exporter derives archetype→``ml_model`` ``uses_model`` edges by
joining each archetype's REAL ``signal_variants`` (carried per
``ArchetypeCapabilityCell`` in ``archetype_capability_manifest.json``) to the
ML prediction targets those signals are trained against, then to the ml-service
model-variant registry. This module is the bridge: it classifies every
``signal_variant`` as EITHER predictive (maps to ≥1 ml-service ``target_type``)
OR deterministic (no trained ML target — honest absence).

Granularity rationale: a prior pass joined archetype→model purely on the
archetype's *asset group* (every DeFi archetype claimed every DeFi model). That
over-claimed — a pure-carry archetype whose only signal is ``staking_yield`` is
not ML-driven. This map tightens the join to the archetype's actual signal
expression, so a carry archetype gets NO ``uses_model`` edges and a swing
archetype gets only the swing/direction model targets.

SOURCING — each predictive mapping is grounded in the signal's meaning and a
REAL ml-service target builder; deterministic signals are left unmapped (never
invent a target). Targets reference ``ml_service.training.ml.config_schema``
``VALID_TARGET_TYPES`` (swing_high/swing_low/direction/volatility/
cross_venue_spread/clv/xg/ht_delta/clv_meta/xg_meta) + the DeFi target builders
(``funding_rate``/``lending_rate``/``impermanent_loss``) — strings only, no
import (UAC does not depend on ml-service).

PREDICTIVE (signal → trained ML target_types):
  - ``price`` / ``momentum_ranking`` / ``zscore_reversion`` → directional &
    swing-point prediction (``direction`` / ``swing_high`` / ``swing_low``):
    a price-level / momentum-rank / mean-reversion signal IS a model predicting
    the next directional move or swing reversal.
  - ``vol_metric`` / ``iv_dispersion`` → ``volatility``: realised/implied vol
    signals are the volatility target.
  - ``spread_capture`` → ``cross_venue_spread``: cross-venue spread capture is
    the cross_venue_spread target.
  - ``funding_rate`` → ``funding_rate`` (DeFi builder): identity — a funding
    signal predicts the funding rate.
  - ``odds`` → the sports targets (``clv`` / ``xg`` / ``ht_delta`` /
    ``clv_meta`` / ``xg_meta``): the sports odds signal IS the sports ML stack.

DETERMINISTIC — no trained ML target (honest absence, NOT a gap to fill):
  - ``basis`` / ``rate_spread`` — relative-value carry: the signal is the
    observed basis / rate differential, traded for convergence; no ML
    prediction (an archetype that ALSO predicts the rate carries a
    ``funding_rate`` signal too).
  - ``staking_yield`` — on-chain staking APR (deterministic, read from chain).
  - ``liquidation_bonus`` — protocol-fixed liquidation incentive (a constant).
  - ``delta_as_expression`` — options-greek expression (deterministic Greek).
  - ``event_surprise`` — discrete event/calendar reaction; no dedicated trained
    target builder (sports in-game events surface via the ``odds`` signal).

Codex SSOT: ``codex/04-architecture/fixed-grid-config.md`` (target taxonomy).
Plan: ``plans/active/issues/capability_wizard_gap_discovery_2026_06_11.md``
(F53 — archetype→model edge derivation).
"""

from __future__ import annotations

from typing import Final

#: Predictive signal_variants → the ml-service ``target_type``(s) they train.
SIGNAL_VARIANT_ML_TARGETS: Final[dict[str, tuple[str, ...]]] = {
    "price": ("direction", "swing_high", "swing_low"),
    "momentum_ranking": ("direction", "swing_high", "swing_low"),
    "zscore_reversion": ("direction", "swing_high", "swing_low"),
    "vol_metric": ("volatility",),
    "iv_dispersion": ("volatility",),
    "spread_capture": ("cross_venue_spread",),
    "funding_rate": ("funding_rate",),
    "odds": ("clv", "xg", "ht_delta", "clv_meta", "xg_meta"),
}

#: Deterministic signal_variants with NO trained ML target (honest absence).
NON_ML_SIGNAL_VARIANTS: Final[frozenset[str]] = frozenset(
    {
        "basis",
        "rate_spread",
        "staking_yield",
        "liquidation_bonus",
        "delta_as_expression",
        "event_surprise",
    }
)


def ml_targets_for_signal(signal_variant: str) -> tuple[str, ...]:
    """Return the ML target_types a signal_variant trains (empty if deterministic)."""
    return SIGNAL_VARIANT_ML_TARGETS.get(signal_variant.strip(), ())


def is_classified_signal(signal_variant: str) -> bool:
    """True if the signal_variant is classified (predictive OR deterministic)."""
    s = signal_variant.strip()
    return s in SIGNAL_VARIANT_ML_TARGETS or s in NON_ML_SIGNAL_VARIANTS
