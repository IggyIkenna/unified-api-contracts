"""Workspace-root discovery for UAC-internal YAML loading.

Wave E closure (2026-04-20): this module is the ONE permitted reader of
``UNIFIED_TRADING_WORKSPACE_ROOT``. The workspace's config-env-var ban
(use ``UnifiedCloudConfig`` instead) targets arbitrary service-config
reads, NOT filesystem-locating env vars consumed at module import time
for YAML-backed codex fixtures. Siblings ``restriction_profiles.py`` and
``service_family_scope.py`` route through :func:`workspace_root_env` so
the env read is centralised and auditable.

Per-service-config env reads are still forbidden.
"""

from __future__ import annotations

import os  # qg-os-environ: see module docstring (single permitted env reader)
from pathlib import Path

_ENV_VAR = "UNIFIED_TRADING_WORKSPACE_ROOT"


def workspace_root_env() -> Path | None:
    """Return :class:`Path` from ``$UNIFIED_TRADING_WORKSPACE_ROOT`` or None.

    The single centralised reader of that env var. Callers then layer
    an ancestor-walk fallback on top — this helper does NOT walk.
    """

    env_root = os.environ.get(_ENV_VAR)  # qg-os-environ: workspace-root discovery (module docstring)
    if env_root:
        return Path(env_root)
    return None


__all__ = ["workspace_root_env"]
