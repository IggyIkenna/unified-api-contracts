"""Top-level alias for api_contracts.unified_normalised_contracts.

Import canonical normalised schemas directly:
    from unified_normalised_contracts import CanonicalTrade, CanonicalOrder
    from unified_normalised_contracts.domain import CanonicalOrderBook
    from unified_normalised_contracts.execution import CanonicalFill

All schemas live in api_contracts.unified_normalised_contracts; this package is a
backward-forward shim so consumers can use the shorter top-level path.
"""

import contextlib
import importlib
import sys

_SUBMODULES = ["domain", "execution", "errors", "normalize"]

# Pre-register all submodules in sys.modules so submodule imports work.
for _sub in _SUBMODULES:
    with contextlib.suppress(ImportError):
        sys.modules[f"unified_normalised_contracts.{_sub}"] = importlib.import_module(
            f"api_contracts.unified_normalised_contracts.{_sub}"
        )

# Replace this module with the real one so attribute access and __all__ work naturally.
sys.modules["unified_normalised_contracts"] = importlib.import_module(
    "api_contracts.unified_normalised_contracts"
)
