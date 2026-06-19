"""Tests for the canonical instrument-type → ledger-asset-class SSOT.

Covers ``asset_class_for_instrument_type`` (the InstrumentType→LedgerAssetClass
map) + ``derive_ledger_asset_fields`` (the instrument_key → ledger asset fields
derivation that retires the ``*_of`` metadata maps on the determinism spine).
"""

from __future__ import annotations

import pytest

from unified_api_contracts import LedgerAssetClass
from unified_api_contracts.internal import (
    InstrumentType,
    UnknownInstrumentTypeError,
    asset_class_for_instrument_type,
    derive_ledger_asset_fields,
)


def test_every_instrument_type_resolves() -> None:
    """Every InstrumentType member has a canonical LedgerAssetClass (completeness)."""
    for itype in InstrumentType:
        resolved = asset_class_for_instrument_type(itype)
        assert isinstance(resolved, LedgerAssetClass)


def test_perp_maps_to_perp() -> None:
    assert asset_class_for_instrument_type(InstrumentType.PERPETUAL) is LedgerAssetClass.PERP


def test_spot_pair_maps_to_spot_token() -> None:
    assert asset_class_for_instrument_type(InstrumentType.SPOT_PAIR) is LedgerAssetClass.SPOT_TOKEN


def test_lst_and_staking_map_to_lst() -> None:
    assert asset_class_for_instrument_type(InstrumentType.LST) is LedgerAssetClass.LST
    assert asset_class_for_instrument_type(InstrumentType.STAKING) is LedgerAssetClass.LST


def test_lending_and_atoken_map_to_atoken() -> None:
    assert asset_class_for_instrument_type(InstrumentType.LENDING) is LedgerAssetClass.ATOKEN
    assert asset_class_for_instrument_type(InstrumentType.A_TOKEN) is LedgerAssetClass.ATOKEN


def test_event_contract_maps_to_prediction() -> None:
    assert asset_class_for_instrument_type(InstrumentType.EVENT_CONTRACT) is LedgerAssetClass.PREDICTION_CONTRACT


def test_string_value_accepted() -> None:
    assert asset_class_for_instrument_type("PERPETUAL") is LedgerAssetClass.PERP


def test_unknown_string_raises() -> None:
    with pytest.raises(UnknownInstrumentTypeError):
        asset_class_for_instrument_type("NOT_A_TYPE")


def test_derive_ledger_asset_fields_perp() -> None:
    symbol, canonical_id, asset_class = derive_ledger_asset_fields("BINANCE-FUTURES:PERPETUAL:BTC-USDT")
    assert symbol == "BTC-USDT"
    assert canonical_id == "BTC-USDT"
    assert asset_class is LedgerAssetClass.PERP


def test_derive_ledger_asset_fields_spot() -> None:
    symbol, canonical_id, asset_class = derive_ledger_asset_fields("BINANCE-SPOT:SPOT_PAIR:ETH-USDT")
    assert symbol == "ETH-USDT"
    assert canonical_id == "ETH-USDT"
    assert asset_class is LedgerAssetClass.SPOT_TOKEN


def test_derive_ledger_asset_fields_lst() -> None:
    _symbol, _canonical_id, asset_class = derive_ledger_asset_fields("LIDO:LST:stETH")
    assert asset_class is LedgerAssetClass.LST


def test_derive_bad_key_raises() -> None:
    with pytest.raises(ValueError):
        derive_ledger_asset_fields("not-a-valid-key")
