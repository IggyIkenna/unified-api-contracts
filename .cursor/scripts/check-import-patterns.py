"""Check external import patterns for UAC (unified-api-contracts).

Enforces that external schemas are only imported via
unified_api_contracts.unified_api_contracts_external.* — not via direct
third-party package paths. Placeholder: full implementation pending.
"""

import sys


def main() -> int:
    # --fix mode: nothing to auto-fix yet
    if "--fix" in sys.argv:
        return 0
    # check mode: no violations detected (full checks handled by quality gates)
    return 0


if __name__ == "__main__":
    sys.exit(main())
