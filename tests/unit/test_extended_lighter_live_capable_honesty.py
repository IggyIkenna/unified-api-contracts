"""EXTENDED-STARKNET / LIGHTER-ZKSYNC live_capable honesty guard (2026-07-18).

Their live WS connectors are BLOCKED-CREDENTIALS stubs (0 ticks), so declaring
``live_capable=True`` was dishonest — flipped to False (batch scaffold preserved). Also locks
that PACIFICA stays fully removed (decommissioned 2026-07-16) — no accidental resurrection.
"""

from __future__ import annotations

from unified_api_contracts.registry.data_type_capability import DATA_TYPE_CAPABILITY_REGISTRY

_BLOCKED_LIVE_VENUES = {"EXTENDED-STARKNET", "LIGHTER-ZKSYNC"}


def test_extended_lighter_live_capable_is_honest_false() -> None:
    """Every EXTENDED-STARKNET / LIGHTER-ZKSYNC row: live_capable=False, batch_capable=True."""
    rows = [c for c in DATA_TYPE_CAPABILITY_REGISTRY if c.venue in _BLOCKED_LIVE_VENUES]
    assert rows, "expected EXTENDED-STARKNET / LIGHTER-ZKSYNC capability rows to exist"
    for c in rows:
        tag = f"{c.venue}/{c.data_type}"
        assert c.live_capable is False, f"{tag}: live_capable must be False (BLOCKED-CREDENTIALS stub)"
        assert c.batch_capable is True, f"{tag}: batch_capable must stay True (MVP batch scaffold)"


def test_pacifica_stays_fully_removed() -> None:
    """PACIFICA was decommissioned 2026-07-16 — it must appear in NO capability row
    (guards against an accidental resurrection while the 07-16 decommission vs 07-18
    'keep MVP' ruling conflict is pending operator resolution)."""
    pacifica = [c for c in DATA_TYPE_CAPABILITY_REGISTRY if "PACIFICA" in str(c.venue).upper()]
    assert pacifica == [], f"PACIFICA must not be in the capability registry (decommissioned 2026-07-16): {pacifica}"
