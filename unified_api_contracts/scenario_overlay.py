"""Facade — makes ``unified_api_contracts.scenario_overlay.ScenarioOverlay`` importable.

Phase 6.C of ``simulation_scenarios_topology_price_shocks_2026_05_09.md``.

Re-exports :class:`ScenarioOverlay` so operators and the backtest CLI can
reference it via the canonical Phase 6.C import path::

    from unified_api_contracts.scenario_overlay import ScenarioOverlay
    overlay = ScenarioOverlay.model_validate_yaml(yaml_text)

The underlying implementation lives in
:mod:`unified_api_contracts.canonical.crosscutting.scenario_overlay`.
"""

from .canonical.crosscutting.scenario_overlay import ScenarioOverlay

__all__ = ["ScenarioOverlay"]
