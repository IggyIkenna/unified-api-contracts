"""UIC-only consistency tests: __all__ exports resolve.

No dependency on unified_api_contracts.internal.

unified_api_contracts.internal has been removed. This file no longer tests alignment
with AC; it only asserts that unified_api_contracts.internal public API is consistent
(e.g. all __all__ exports resolve).
"""

from __future__ import annotations


class TestUICInternalConsistency:
    """UIC exports must all resolve and be well-formed."""

    def test_all_exports_are_importable(self) -> None:
        import unified_api_contracts.internal

        missing: list[str] = []
        all_names: list[str] = getattr(unified_api_contracts.internal, "__all__", [])
        for name in all_names:
            if not hasattr(unified_api_contracts.internal, name):
                missing.append(name)
        assert missing == [], f"Exports declared in __all__ but not importable: {missing}"

    def test_gas_cost_action_enum(self) -> None:
        from unified_api_contracts.internal.defi import GasCostAction

        values = list(GasCostAction)
        assert len(values) >= 5

    def test_messaging_scope_enum(self) -> None:
        from unified_api_contracts.internal.messaging import MessagingScope

        values = list(MessagingScope)
        assert {"in_process", "same_vm", "cross_vm"} == {v.value for v in values}
