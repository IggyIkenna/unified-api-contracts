"""Regression guard — RESTAKING is a DeFi single-asset type for quote_asset validation.

``distinct_values_noncanonical_audit_2026_07_20.md`` (RESTAKING InstrumentType, 2026-07-22):
the instruments-service ezETH/rsETH/pufETH/weETH adapters were re-pointed from
``instrument_type=LST`` to ``instrument_type=RESTAKING``. All four emit ``quote_asset=""``
(single-asset LRTs, same shape as the LST rows they used to be). ``_check_record`` rejects
any DeFi record with a blank ``quote_asset`` unless its ``instrument_type`` is in
``_SINGLE_ASSET_DEFI_TYPES`` — RESTAKING was missing from that set until this fix, which
would have silently rejected every one of these adapters' future captures with
"quote_asset is required for DeFi non-lending".
"""

from __future__ import annotations

from unified_api_contracts.internal.reference.instrument import InstrumentRecord, InstrumentType
from unified_api_contracts.internal.reference.instrument_validation import (
    _SINGLE_ASSET_DEFI_TYPES,  # pyright: ignore[reportPrivateUsage]
    validate_instrument_records,
)

_WEETH_ADDRESS = "0xcd5fe23c85820f7b72d0926fc9b05b43e359b7ee"


def _restaking_record(**overrides: object) -> InstrumentRecord:
    """Minimal DeFi RESTAKING record shaped like etherfi.py's real weETH record."""
    kwargs: dict[str, object] = {
        "instrument_key": "ETHERFI-ETHEREUM:LST:WEETH",
        "venue": "ETHERFI-ETHEREUM",
        "instrument_type": InstrumentType.RESTAKING,
        "raw_symbol": _WEETH_ADDRESS,
        "base_asset": "ETH",
        "quote_asset": "",
        "base_asset_decimals": 18,
    }
    kwargs.update(overrides)
    return InstrumentRecord(**kwargs)  # type: ignore[arg-type]


def test_restaking_record_with_blank_quote_asset_passes() -> None:
    valid, rejected = validate_instrument_records([_restaking_record()])
    assert rejected == [], f"Expected no rejections, got {rejected}"
    assert len(valid) == 1


def test_restaking_is_in_single_asset_defi_types() -> None:
    """Direct membership check — this is the exact set the pre-fix bug omitted RESTAKING
    from, which would have made every ezETH/rsETH/pufETH/weETH capture with blank
    quote_asset fail ``_check_record``'s DeFi non-lending quote_asset requirement."""
    assert InstrumentType.RESTAKING.value in _SINGLE_ASSET_DEFI_TYPES
