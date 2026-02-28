#!/usr/bin/env python3
"""Optional live contract verification using config and Secret Manager (same pattern as UMI/UOI).

Uses unified-config-interface for config and config.get_secret() (which uses unified-trading-services).
No duplication of API key resolution. Run only when LIVE_API_VERIFICATION=1.

Install deps first (from workspace):
  uv pip install -e ../unified-trading-services -e ../unified-config-interface
  uv pip install -e ".[live]"
Then: LIVE_API_VERIFICATION=1 uv run python scripts/verify_contracts_vs_reality_live.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_config():
    """Load UnifiedCloudConfig from env (same as UMI/UOI)."""
    from unified_config_interface import UnifiedCloudConfig

    return UnifiedCloudConfig()


def _resolve_secrets_for_venues_with_config(config: object) -> tuple[list[str], list[str]]:
    """Resolve secrets via UCS get_secret_with_fallback (same as UMI/UOI). Uses config + Secret Manager only."""
    from unified_trading_services import get_secret_with_fallback

    from api_contracts.venue_manifest import VENUE_MANIFEST

    project_id = getattr(config, "gcp_project_id", None) or getattr(config, "project_id", None)
    if not project_id:
        return (
            ["GCP_PROJECT_ID or GOOGLE_CLOUD_PROJECT required. Set in env or .env."],
            [],
        )

    errors: list[str] = []
    resolved: list[str] = []
    for venue, contract in VENUE_MANIFEST.items():
        field = contract.get("config_secret_field") or ""
        if not field:
            continue
        if not hasattr(config, field):
            errors.append(f"{venue}: config missing field {field}")
            continue
        secret_name = getattr(config, field)
        if not secret_name or not isinstance(secret_name, str):
            errors.append(f"{venue}: {field} is empty or not a string")
            continue
        try:
            secret = get_secret_with_fallback(
                project_id=project_id,
                secret_name=secret_name,
                fallback_env_var=None,
            )
            if secret:
                resolved.append(venue)
            else:
                errors.append(f"{venue}: secret {secret_name} not found or empty")
        except Exception as e:
            errors.append(f"{venue} ({secret_name}): {e}")
    return (errors, resolved)


def main() -> int:
    if os.environ.get("LIVE_API_VERIFICATION") != "1":
        print("Set LIVE_API_VERIFICATION=1 to run live verification.", file=sys.stderr)
        return 0
    sys.path.insert(0, str(REPO_ROOT))
    config = _load_config()
    errs, resolved = _resolve_secrets_for_venues_with_config(config)
    if errs:
        for e in errs:
            print(e, file=sys.stderr)
        return 1
    print(f"Live verification: config loaded; secrets resolved for: {resolved or '(none with config_secret_field)'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
