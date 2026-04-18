"""Gate G9 — regression tests for failures surfaced during canonicalisation.

Each test class encodes one class of bug that must never recur silently. The
failures they guard are documented in the G9 handoff; the tests themselves
must keep failing the moment a regression is re-introduced.

Covers UAC-owned surfaces:

* Ticker -> exchange resolution must be total (no ``UNKNOWN`` sentinel).
* Human-readable underlying normalisation (``ES`` -> ``SP500``,
  ``6A`` -> ``AUDUSD``) and its interaction with ``build_instrument_id``.
* ``CONTRACT_REGISTRY`` must cover every ``(defi, instrument_type,
  data_type)`` triple that MTDS DeFi handlers emit -- otherwise
  ``lookup_contract`` raises ``SchemaContractNotFoundError`` and the
  migration pipeline drops the shard silently.
"""

from __future__ import annotations

import datetime as _dt

import pytest

from unified_api_contracts import InstrumentType, build_instrument_id
from unified_api_contracts.internal.reference.ticker_registry import (
    EXCHANGE_BY_TICKER,
    UNDERLYING_NORMALIZATION,
    normalize_underlying,
    resolve_exchange,
)
from unified_api_contracts.internal.schemas.contracts import (
    CONTRACT_REGISTRY,
    SchemaContractNotFoundError,
    lookup_contract,
)
from unified_api_contracts.registry.tradfi_ticker_universe import (
    TRADFI_TICKER_UNIVERSE,
)

# ---------------------------------------------------------------------------
# #6 Ticker -> exchange resolution must be total (no UNKNOWN)
# ---------------------------------------------------------------------------


class TestTickerExchangeResolutionTotalG9:
    """Every ticker in TRADFI_TICKER_UNIVERSE must resolve to a known exchange.

    The canonicalisation session surfaced rows routed to ``venue=UNKNOWN`` when
    an equity ticker was missing from the exchange map. The fix is strict: the
    map is exhaustive, and ``resolve_exchange`` raises on unknown input. This
    test keeps the map exhaustive for every equity/ETF ticker we actually
    fetch.
    """

    def _universe_tickers(self) -> list[str]:
        keys = ("sp500_tickers", "etf_tickers", "nasdaq_tickers")
        seen: set[str] = set()
        out: list[str] = []
        for key in keys:
            for ticker in TRADFI_TICKER_UNIVERSE.get(key, []):
                if ticker and ticker not in seen:
                    seen.add(ticker)
                    out.append(ticker)
        return out

    def test_every_universe_ticker_resolves_to_a_known_exchange(self) -> None:
        missing: list[str] = []
        for ticker in self._universe_tickers():
            exchange = EXCHANGE_BY_TICKER.get(ticker)
            if exchange is None or exchange == "UNKNOWN":
                missing.append(ticker)
        assert not missing, (
            "TRADFI_TICKER_UNIVERSE tickers with no exchange mapping "
            f"(would route to UNKNOWN): {missing!r}. Add to "
            "_NASDAQ/_NYSE/_ARCA/_AMEX/_BATS in ticker_registry.py."
        )

    def test_resolve_exchange_raises_on_unknown_ticker(self) -> None:
        # Strict fail-loud — no UNKNOWN sentinel, no silent fallback.
        with pytest.raises(ValueError, match="unknown ticker"):
            resolve_exchange("THIS_TICKER_IS_NOT_REAL_XYZ")

    def test_resolve_exchange_rejects_empty(self) -> None:
        with pytest.raises(ValueError, match="non-empty"):
            resolve_exchange("")


# ---------------------------------------------------------------------------
# #7 Human-readable underlying (ES -> SP500, 6A -> AUDUSD)
# ---------------------------------------------------------------------------


class TestHumanReadableUnderlyingG9:
    """``build_instrument_id`` consumers must produce human-readable IDs.

    Prior to the canonicalisation rewrite, ``build_instrument_id(CME, FUTURE,
    "ES", ...)`` produced ``CME:FUTURE:ES-YYYYMMDD``. The UAC
    ``UNDERLYING_NORMALIZATION`` map now lets callers translate the raw
    exchange code (``ES``) into the human-readable underlying (``SP500``)
    before calling the builder -- so GCS paths / canonical IDs carry
    ``SP500`` rather than the opaque ``ES``.

    This test locks in the mapping AND the builder behaviour that the
    normalised name reaches the final canonical id.
    """

    @pytest.mark.parametrize(
        ("raw", "expected_name"),
        [
            ("ES", "SP500"),
            ("NQ", "NASDAQ100"),
            ("CL", "WTI"),
            ("ZN", "UST-10Y"),
            ("6A", "AUDUSD"),
            ("6B", "GBPUSD"),
            ("6C", "CADUSD"),
            ("6E", "EURUSD"),
        ],
    )
    def test_underlying_normalization_is_human_readable(self, raw: str, expected_name: str) -> None:
        assert normalize_underlying(raw) == expected_name
        assert UNDERLYING_NORMALIZATION[raw] == expected_name

    def test_build_instrument_id_produces_human_readable_id_when_caller_normalises(
        self,
    ) -> None:
        # Callers are expected to normalise the underlying before passing to
        # the builder — this is the canonical pattern documented in
        # ticker_registry.py.
        readable = normalize_underlying("ES")
        inst_id = build_instrument_id(
            "cme",
            InstrumentType.FUTURE,
            readable,
            expiry_date=_dt.date(2026, 6, 19),
        )
        assert inst_id == "CME:FUTURE:SP500-20260619"
        assert ":ES-" not in inst_id, (
            "Canonical ID must carry human-readable underlying (SP500) — the raw exchange code (ES) is a regression."
        )

    def test_build_instrument_id_produces_audusd_for_6a(self) -> None:
        readable = normalize_underlying("6A")
        inst_id = build_instrument_id(
            "cme",
            InstrumentType.FUTURE,
            readable,
            expiry_date=_dt.date(2026, 6, 17),
        )
        assert inst_id == "CME:FUTURE:AUDUSD-20260617"

    def test_normalize_underlying_rejects_unknown(self) -> None:
        with pytest.raises(ValueError, match="unknown underlying"):
            normalize_underlying("XYZZYX")


# ---------------------------------------------------------------------------
# #9 CONTRACT_REGISTRY coverage for every (protocol, data_type) MTDS handles
# ---------------------------------------------------------------------------


# Pairs of (venue, instrument_type, data_type) emitted by MTDS DeFi handlers.
# These are the shard keys whose schema the migration pipeline must resolve;
# any missing entry turns into a silent drop via SchemaContractNotFoundError
# caught upstream.
_HANDLER_CONTRACT_KEYS: list[tuple[str | None, str, str]] = [
    # Lending indices
    ("AAVE_V3", "a_token", "lending_indices"),
    ("COMPOUND_V3", "a_token", "lending_indices"),
    ("MORPHO", "lending", "lending_indices"),
    ("SPARK", "lending", "lending_indices"),
    ("FLUID", "lending", "lending_indices"),
    ("INSTADAPP", "lending", "lending_indices"),
    # DEX pool state + swaps
    ("UNISWAP_V2", "pool", "dex_pool_state"),
    ("UNISWAP_V3", "pool", "dex_pool_state"),
    ("UNISWAP_V4", "pool", "dex_pool_state"),
    ("CURVE", "pool", "dex_pool_state"),
    ("BALANCER", "pool", "dex_pool_state"),
    ("UNISWAP_V2", "pool", "dex_pool_swaps"),
    ("UNISWAP_V3", "pool", "dex_pool_swaps"),
    ("UNISWAP_V4", "pool", "dex_pool_swaps"),
    # LST rates
    ("LIDO", "lst", "lst_rates"),
    ("ETHERFI", "lst", "lst_rates"),
    ("ETHENA", "lst", "lst_rates"),
    # Liquidations
    (None, "lending", "liquidations"),
    # Gas fees / oracle / perp / staking
    (None, "spot_asset", "gas_fees"),
    (None, "spot_asset", "oracle_prices"),
    (None, "perpetual", "perp_funding"),
    ("EIGENLAYER", "staking", "eigenlayer_rewards"),
    (None, "staking", "yield_snapshots"),
]


class TestDefiContractRegistryCoverageG9:
    """lookup_contract must resolve every (venue, instrument_type, data_type)
    pair that MTDS DeFi handlers actually emit. A missing entry causes the
    migration script to raise ``SchemaContractNotFoundError`` and emit
    DEPLOYMENT_FAILED -- we'd rather catch the gap in CI than in prod.
    """

    @pytest.mark.parametrize(("venue", "instrument_type", "data_type"), _HANDLER_CONTRACT_KEYS)
    def test_registered_handler_key_resolves_to_contract(
        self, venue: str | None, instrument_type: str, data_type: str
    ) -> None:
        contract = lookup_contract(
            category="defi",
            instrument_type=instrument_type,
            data_type=data_type,
            venue=venue,
        )
        assert contract is not None
        assert contract.category == "defi"
        assert contract.instrument_type == instrument_type
        assert contract.data_type == data_type
        # symbol_column is what migrate_defi_canonical reads from each row —
        # it must be explicitly declared, not guessed.
        assert contract.symbol_column, f"Contract for {venue}/{instrument_type}/{data_type} declares no symbol_column"

    def test_unknown_handler_key_raises_not_silent_miss(self) -> None:
        with pytest.raises(SchemaContractNotFoundError) as exc_info:
            lookup_contract(
                category="defi",
                instrument_type="pool",
                data_type="this_data_type_does_not_exist_xyz",
            )
        assert "this_data_type_does_not_exist_xyz" in str(exc_info.value)

    def test_base_registry_entries_cover_all_handler_instrument_types(self) -> None:
        # For every (instrument_type, data_type) in _HANDLER_CONTRACT_KEYS, a
        # base-registry fallback (venue=None key) must exist so that venues
        # without an explicit override still resolve.
        registry_keys = {(itype, dtype) for (_cat, itype, dtype) in CONTRACT_REGISTRY if _cat == "defi"}
        missing_fallbacks: list[tuple[str, str]] = []
        for _venue, itype, dtype in _HANDLER_CONTRACT_KEYS:
            if (itype, dtype) not in registry_keys:
                missing_fallbacks.append((itype, dtype))
        assert not missing_fallbacks, (
            f"DeFi handler (instrument_type, data_type) pairs with no CONTRACT_REGISTRY fallback: {missing_fallbacks!r}"
        )
