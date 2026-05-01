"""UAC operator-facing CLI tools (workspace audit P4.10 / P4.11, 2026-05-01).

Two scripts:
- ``python -m unified_api_contracts.tools.print_capability_matrix`` --
  prints every (asset_group x archetype) cell from the capability registry
  with status (SUPPORTED / PARTIAL / BLOCKED), venues, and signal variants.
  Single management surface for "what coverage do we ship today?"
- ``python -m unified_api_contracts.tools.generate_architecture_docs`` --
  emits markdown reports under ``docs/generated/`` from the canonical
  registries (event topics, service contract map, archetype capability,
  asset-group ontology, taxonomy). Auto-regen target for QG.
"""
