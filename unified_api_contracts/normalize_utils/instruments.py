"""Instrument and reference-data normalizers.

Converts raw venue symbol/definition payloads to CanonicalInstrument canonical types.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ..canonical.domain import CanonicalInstrument
from ..canonical.domain.sports.arbitrage import ArbitrageMarket
from ..external.aster.normalize import (
    normalize_aster_exchange_info,
    normalize_aster_market,
)
from ..external.binance.normalize import normalize_binance_symbol
from ..external.bybit.normalize import normalize_bybit_market
from ..external.ccxt.normalize import normalize_ccxt_market
from ..external.coingecko.normalize import (
    normalize_coingecko_global_market,
    normalize_coingecko_global_market_response,
)
from ..external.databento.normalize import (
    normalize_databento_definition,
    normalize_databento_symbol,
)
from ..external.deribit.normalize import normalize_deribit_instrument
from ..external.dydx.normalize import normalize_dydx_perpetual_market
from ..external.fix.normalize import (
    normalize_fix_market_data_request,
    normalize_fix_market_data_snapshot,
)
from ..external.ibkr.normalize import normalize_ibkr_contract_details
from ..external.matchbook.normalize import normalize_matchbook_market
from ..external.metabet.normalize import normalize_metabet_market
from ..external.nautilus.normalize import normalize_nautilus_instrument
from ..external.odds_api.normalize import normalize_odds_api_market
from ..external.odds_engine.normalize import normalize_odds_engine_market
from ..external.okx.normalize import normalize_okx_market
from ..external.predictit.normalize import normalize_predictit_market
from ..external.tardis.normalize import normalize_tardis_instrument
from ..external.upbit.normalize import normalize_upbit_market

# ---------------------------------------------------------------------------
# Sports — arbitrage market (no external venue equivalent)
# ---------------------------------------------------------------------------


def normalize_arbitrage_market(
    raw: ArbitrageMarket,
    venue: str = "sports",
) -> CanonicalInstrument:
    """Normalize ArbitrageMarket (sports canonical) to CanonicalInstrument.

    ArbitrageMarket represents one leg of an arbitrage opportunity at a bookmaker.
    """
    sym = raw.selection or ""
    ik = f"{venue.upper()}:MARKET:{raw.bookmaker_key}:{sym}"
    return CanonicalInstrument(
        instrument_key=ik,
        venue=venue,
        symbol=sym,
        timestamp=datetime.now(UTC),
        tick_size=None,
        min_size=None,
        contract_size=None,
        base_asset=None,
        quote_asset=None,
        settle_asset=None,
    )


__all__ = [
    "normalize_arbitrage_market",
    "normalize_aster_exchange_info",
    "normalize_aster_market",
    "normalize_binance_symbol",
    "normalize_bybit_market",
    "normalize_ccxt_market",
    "normalize_coingecko_global_market",
    "normalize_coingecko_global_market_response",
    "normalize_databento_definition",
    "normalize_databento_symbol",
    "normalize_deribit_instrument",
    "normalize_dydx_perpetual_market",
    "normalize_fix_market_data_request",
    "normalize_fix_market_data_snapshot",
    "normalize_ibkr_contract_details",
    "normalize_matchbook_market",
    "normalize_metabet_market",
    "normalize_nautilus_instrument",
    "normalize_odds_api_market",
    "normalize_odds_engine_market",
    "normalize_okx_market",
    "normalize_predictit_market",
    "normalize_tardis_instrument",
    "normalize_upbit_market",
]
