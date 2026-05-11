"""Liquid staking token (LST) canonical mapping.

Single source of truth for the workspace-wide
``token -> (staking_protocol, base_asset)`` table. Every consumer that needs
to translate between LST surface forms speaks through this module:

- features-onchain ``lst_yields`` calculator: emits ``protocol`` / ``asset``
  columns alongside ``token`` so downstream readers don't have to translate.
- strategy-service catalog rows: spec the desired ``(protocol, asset)`` and
  the catalog resolver maps to ``token`` for parquet filtering.
- carry tracer (``trace_all_carry_archetypes.py``): replaces the
  tracer-local ``_TOKEN_TO_PROTOCOL_ASSET`` shim shipped 2026-05-06.
- instruments-service LST discovery: when a new LST is added, the same PR
  must extend ``LST_TOKEN_TO_PROTOCOL_ASSET`` so every downstream resolver
  picks it up.

Schema-drift sentinel (Phase 9 plan
``carry_tracer_phase_9_catalog_paired_dispersion_2026_05_06.plan``):
features-onchain calculator must emit BOTH ``token`` and the canonical
``protocol`` / ``asset`` columns. Once that ships, the tracer-local adapter
shim is deleted (Phase 3.E).
"""

from __future__ import annotations

# Canonical token -> (staking_protocol, base_asset) mapping.
#
# Conventions:
# - Token symbol matches the on-chain ERC20 / SPL-token name (case sensitive).
# - Protocol uppercased, no version suffix (governance / contract version
#   churn lives in ``instrument_id`` not protocol name).
# - Base asset uppercased, the underlying that the LST stakes/wraps.
#
# Adding a new LST: append the row here AND extend the corresponding
# instruments-service LST_REFERENCE_DATA registry in the same PR. The two
# tables must stay in sync — the QG sentinel below catches drift at CI.
LST_TOKEN_TO_PROTOCOL_ASSET: dict[str, tuple[str, str]] = {
    "stETH": ("LIDO", "ETH"),
    "wstETH": ("LIDO_WRAPPED", "ETH"),
    "rETH": ("ROCKET_POOL", "ETH"),
    "cbETH": ("COINBASE", "ETH"),
    "weETH": ("ETHERFI", "ETH"),
    "ankrETH": ("ANKR", "ETH"),
    "mETH": ("MANTLE", "ETH"),
    "swETH": ("SWELL", "ETH"),
    "ETHx": ("STADER", "ETH"),
    "osETH": ("STAKEWISE", "ETH"),
    "pufETH": ("PUFFER", "ETH"),
    "sUSDe": ("ETHENA", "USDE"),
    "sDAI": ("SPARK", "DAI"),
    "jitoSOL": ("JITO", "SOL"),
    "mSOL": ("MARINADE", "SOL"),
    "bSOL": ("BLAZESTAKE", "SOL"),
    # Restaking LRTs (added 2026-05-12 per defi_catalogue_chain_primitives_2026_05_10.md
    # Phase 1G + 1A. Symbiotic/Karak vault tokens NOT in this mapping — those protocols
    # issue per-vault shares rather than a single canonical LRT, so they live in the
    # instruments-service LST_REFERENCE_DATA registry only.)
    "ezETH": ("RENZO", "ETH"),
    "rsETH": ("KELPDAO", "ETH"),
}


def tokens_for_protocol_asset(protocol: str, asset: str) -> set[str]:
    """Return the set of LST tokens matching ``(protocol, asset)``.

    Either side may be the empty string; an empty pair returns every token.
    Matching is case-insensitive on both axes.

    Used by features-onchain readers that filter ``lst_yields`` parquet by
    ``(protocol, asset)`` catalog spec — translating to a ``token`` set
    suitable for ``df["token"].isin(...)``.
    """
    p_norm = protocol.upper() if protocol else ""
    a_norm = asset.upper() if asset else ""
    matches: set[str] = set()
    for token, (proto, ass) in LST_TOKEN_TO_PROTOCOL_ASSET.items():
        if p_norm and proto != p_norm:
            continue
        if a_norm and ass != a_norm:
            continue
        matches.add(token)
    return matches


def protocol_asset_for_token(token: str) -> tuple[str, str] | None:
    """Return ``(protocol, asset)`` for ``token`` or ``None`` if unknown.

    Used by features-onchain calculator-side stamping: when emitting the
    parquet, look up the canonical ``(protocol, asset)`` per row's
    ``token`` and write both columns. Downstream readers then filter on
    either surface form.
    """
    return LST_TOKEN_TO_PROTOCOL_ASSET.get(token)


__all__ = [
    "LST_TOKEN_TO_PROTOCOL_ASSET",
    "protocol_asset_for_token",
    "tokens_for_protocol_asset",
]
