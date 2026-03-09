"""Unit tests for phase6 (market_state) normalizers.

Covers:
- market_state: Binance, Bybit, OKX, Deribit, Coinbase, IBKR, Kalshi, Betfair normalizers
"""

from __future__ import annotations

from datetime import UTC, datetime

# ---------------------------------------------------------------------------
# market_state — Generic and per-venue
# ---------------------------------------------------------------------------


class TestMarketStateNormalizers:
    def test_normalize_binance_trading(self):
        from unified_api_contracts.unified_normalised_contracts.domain import (
            CanonicalMarketStateEvent,
            MarketState,
        )
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_binance_market_state,
        )

        result = normalize_binance_market_state(status="TRADING", symbol="BTCUSDT")
        assert isinstance(result, CanonicalMarketStateEvent)
        assert result.state == MarketState.NORMAL
        assert result.venue == "binance"
        assert result.instrument_key == "binance:SPOT:BTCUSDT"

    def test_normalize_binance_halt(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_binance_market_state,
        )

        result = normalize_binance_market_state(status="HALT", symbol="ETHUSDT")
        assert result.state == MarketState.HALTED

    def test_normalize_binance_auction_match(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_binance_market_state,
        )

        result = normalize_binance_market_state(status="AUCTION_MATCH", symbol="BTCUSDT")
        assert result.state == MarketState.AUCTION

    def test_normalize_binance_pre_trading(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_binance_market_state,
        )

        result = normalize_binance_market_state(status="PRE_TRADING", symbol="NEWUSDT")
        assert result.state == MarketState.PRE_MARKET

    def test_normalize_bybit_trading(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_bybit_market_state,
        )

        result = normalize_bybit_market_state(status="TRADING", symbol="BTCUSDT")
        assert result.state == MarketState.NORMAL
        assert result.instrument_key == "bybit:PERPETUAL:BTCUSDT"

    def test_normalize_bybit_closed(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_bybit_market_state,
        )

        result = normalize_bybit_market_state(status="CLOSED", symbol="BTCUSDT")
        assert result.state == MarketState.CLOSED

    def test_normalize_okx_live(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_okx_market_state,
        )

        result = normalize_okx_market_state(state="live", inst_id="BTC-USDT-SWAP")
        assert result.state == MarketState.NORMAL
        assert result.instrument_key == "okx:PERPETUAL:BTC-USDT-SWAP"

    def test_normalize_okx_suspend(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_okx_market_state,
        )

        result = normalize_okx_market_state(state="suspend", inst_id="BTC-USDT-SWAP")
        assert result.state == MarketState.HALTED

    def test_normalize_deribit_open(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_deribit_market_state,
        )

        result = normalize_deribit_market_state(state="open", instrument_name="BTC-PERPETUAL")
        assert result.state == MarketState.NORMAL

    def test_normalize_deribit_closed(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_deribit_market_state,
        )

        result = normalize_deribit_market_state(state="closed", instrument_name="BTC-PERPETUAL")
        assert result.state == MarketState.CLOSED

    def test_normalize_coinbase_online(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_coinbase_market_state,
        )

        result = normalize_coinbase_market_state(trading_mode="ONLINE", product_id="BTC-USD")
        assert result.state == MarketState.NORMAL
        assert result.instrument_key == "coinbase:SPOT:BTC-USD"

    def test_normalize_coinbase_offline(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_coinbase_market_state,
        )

        result = normalize_coinbase_market_state(trading_mode="OFFLINE", product_id="BTC-USD")
        assert result.state == MarketState.HALTED

    def test_normalize_ibkr_open(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_ibkr_market_state,
        )

        result = normalize_ibkr_market_state(trading_phase="OPEN", symbol="AAPL")
        assert result.state == MarketState.NORMAL
        assert result.instrument_key == "ibkr:SPOT:AAPL"

    def test_normalize_ibkr_afterhours(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_ibkr_market_state,
        )

        result = normalize_ibkr_market_state(trading_phase="AFTERHOURS", symbol="AAPL")
        assert result.state == MarketState.POST_MARKET

    def test_normalize_ibkr_futures_type_map(self):
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_ibkr_market_state,
        )

        result = normalize_ibkr_market_state(trading_phase="OPEN", symbol="ES", sec_type="FUT")
        assert result.instrument_key == "ibkr:FUTURE:ES"

    def test_normalize_kalshi_open(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_kalshi_market_state,
        )

        result = normalize_kalshi_market_state(status="open", ticker="BTCZ-25JAN31-T50000")
        assert result.state == MarketState.NORMAL
        assert result.instrument_key == "kalshi:PREDICTION:BTCZ-25JAN31-T50000"

    def test_normalize_kalshi_paused(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_kalshi_market_state,
        )

        result = normalize_kalshi_market_state(status="paused", ticker="BTCZ-25JAN31-T50000")
        assert result.state == MarketState.HALTED

    def test_normalize_betfair_open(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_betfair_market_state,
        )

        result = normalize_betfair_market_state(status="OPEN", market_id="1.234567")
        assert result.state == MarketState.NORMAL
        assert result.instrument_key == "betfair:MARKET:1.234567"

    def test_normalize_betfair_suspended(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_betfair_market_state,
        )

        result = normalize_betfair_market_state(status="SUSPENDED", market_id="1.234567")
        assert result.state == MarketState.HALTED

    def test_normalize_betfair_inactive_pre_market(self):
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_betfair_market_state,
        )

        result = normalize_betfair_market_state(status="INACTIVE", market_id="1.234567")
        assert result.state == MarketState.PRE_MARKET

    def test_normalize_market_state_with_timestamp(self):
        """Custom timestamp propagates correctly."""
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_binance_market_state,
        )

        ts = datetime(2024, 6, 1, 12, 0, 0, tzinfo=UTC)
        result = normalize_binance_market_state(status="TRADING", symbol="BTCUSDT", timestamp=ts)
        assert result.timestamp == ts

    def test_normalize_market_state_with_previous_state(self):
        """previous_state field propagates."""
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_binance_market_state,
        )

        result = normalize_binance_market_state(
            status="HALT",
            symbol="BTCUSDT",
            previous_state=MarketState.NORMAL,
            reason="Circuit breaker triggered",
        )
        assert result.previous_state == MarketState.NORMAL
        assert result.reason == "Circuit breaker triggered"

    def test_normalize_market_state_case_insensitive(self):
        """State lookup is case-insensitive (raw_state.upper())."""
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_binance_market_state,
        )

        result = normalize_binance_market_state(status="trading", symbol="BTCUSDT")
        assert result.state == MarketState.NORMAL

    def test_normalize_market_state_unknown_falls_back_to_normal(self):
        """Unknown states fall back to NORMAL per generic helper default."""
        from unified_api_contracts.unified_normalised_contracts.domain import MarketState
        from unified_api_contracts.unified_normalised_contracts.normalize.market_state import (
            normalize_binance_market_state,
        )

        result = normalize_binance_market_state(status="TOTALLY_UNKNOWN_STATE", symbol="BTCUSDT")
        assert result.state == MarketState.NORMAL
