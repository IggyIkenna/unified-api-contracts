"""
Centralized Venue and Data Type Configuration

Provides canonical venue mappings, data type configurations, and exchange settings
used across all services in the unified trading system.

This is the SSOT for venue identity concepts. Previously duplicated in:
- unified-config-interface/unified_trading_library.config_interface/venue_config.py
- unified-market-interface/unified_market_interface/models/venue_config.py

Moved to unified-api-contracts (T0) because venue identity is a contracts-level
concept, not a config concept.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime


@dataclass
class VenueMapping:
    """CANONICAL venue to exchange API mappings (centralized business logic)"""

    # ALL possible Tardis exchange endpoints (we'll call each to get complete data)
    # Aligned with DATA_SOURCE_TO_VENUES["tardis"] in canonical_mappings.py (19 canonical venues)
    all_tardis_exchanges: list[str] = field(
        default_factory=lambda: [
            # Tier 1: Primary exchanges (highest liquidity)
            "binance",
            "binance-futures",  # BINANCE USDT-margined (perps + dated quarterly)
            "deribit",  # DERIBIT unified (perps + futures + options)
            "bybit",
            "bybit-spot",  # BYBIT unified
            "okex",
            "okex-futures",
            "okex-swap",  # OKX needs all endpoints for complete data
            "coinbase",  # Coinbase - spot only, for coinbase premium
            # Tier 2: Regional / specialist exchanges
            "upbit",  # Upbit (Korean exchange) - spot only, for kimchi premium
            "bitstamp",  # Bitstamp - spot
            # Tier 3: Additional CeFi exchanges
            "huobi",  # Huobi/HTX - spot
            "huobi-dm",  # Huobi/HTX - derivatives (futures/swaps)
        ]
    )

    # Canonical TradFi venues (user-friendly names, not data source names)
    # Note: Not all are Databento-sourced (e.g. CBOE uses Barchart, FX uses Yahoo Finance)
    all_databento_venues: list[str] = field(
        default_factory=lambda: [
            "CME",  # Chicago Mercantile Exchange (futures, options, treasuries)
            "CBOE",  # Cboe Global Markets (VIX index only - special treatment)
            "NASDAQ",  # NASDAQ Stock Market (equities, ETFs)
            "NYSE",  # New York Stock Exchange (equities, ETFs)
            "ICE",  # Intercontinental Exchange (futures, options)
            "FX",  # OTC Foreign Exchange (KRW/USD via Yahoo Finance data provider)
        ]
    )

    # DeFi venues — canonical PROTOCOL-CHAIN format (matches URDI CANONICAL_VENUE_TO_ADAPTER)
    # Note: HYPERLIQUID and ASTER moved to all_cefi_onchain_clob_venues
    all_defi_venues: list[str] = field(
        default_factory=lambda: [
            # Ethereum DEX protocols (swaps)
            "UNISWAPV2-ETHEREUM",
            "UNISWAPV3-ETHEREUM",
            "UNISWAPV4-ETHEREUM",
            "CURVE-ETHEREUM",
            "BALANCER-ETHEREUM",
            # Lending protocols
            "AAVEV3-ETHEREUM",
            "MORPHO-ETHEREUM",
            "FLUID-ETHEREUM",
            # LST/Yield protocols
            "LIDO-ETHEREUM",
            "ETHERFI-ETHEREUM",
            "ETHENA-ETHEREUM",
        ]
    )

    # CEFI on-chain CLOB venues (CLOB-style data, treated as CEFI for buckets)
    # These produce data identical to centralized exchanges:
    # trades, orderbook, funding, liquidations
    all_cefi_onchain_clob_venues: list[str] = field(
        default_factory=lambda: [
            "HYPERLIQUID",  # Hyperliquid perpetual futures (HyperEVM L1)
            "ASTER",  # Aster perpetual futures exchange
        ]
    )

    # All exchanges (computed from above - no duplication)
    @property
    def all_exchanges(self) -> list[str]:
        """All exchanges (Tardis + Databento + CEFI CLOB + DeFi)"""
        return (
            self.all_tardis_exchanges
            + self.all_databento_venues
            + self.all_cefi_onchain_clob_venues
            + self.all_defi_venues
        )

    @property
    def all_cefi_venues(self) -> list[str]:
        """All CEFI venues (Tardis exchanges + on-chain CLOBs like Hyperliquid/Aster)"""
        # Map Tardis exchanges to canonical venue names
        cefi_venues = list(set(self.tardis_to_venue.values()))
        # Add on-chain CLOB venues
        cefi_venues.extend(self.all_cefi_onchain_clob_venues)
        return cefi_venues

    # Map canonical venues to Databento dataset identifiers
    venue_to_databento: dict[str, str] = field(
        default_factory=lambda: {
            "CME": "GLBX.MDP3",  # CME Globex Market Data Platform 3.0
            "CBOE": "BARCHART",  # VIX index only (not via Databento OPRA.PILLAR)
            "NASDAQ": "DBEQ.BASIC",  # NASDAQ equities via Databento DBEQ.BASIC
            "NYSE": "DBEQ.BASIC",  # NYSE equities via Databento DBEQ.BASIC
            "ICE": "IFUS.IMPACT",  # ICE Futures US (Cotton, Coffee, Sugar, Cocoa, OJ, Dollar Index)
            "ICE-EU": "IFEU.IMPACT",  # ICE Europe (Brent, Gas Oil, etc.)
        }
    )

    # Canonical venues to CCXT exchange IDs
    venue_to_ccxt: dict[str, str] = field(
        default_factory=lambda: {
            "BINANCE-SPOT": "binance",
            "BINANCE-FUTURES": "binance",  # Same CCXT class, different market types
            "DERIBIT": "deribit",
            "BYBIT": "bybit",  # Unified
            "OKX": "okx",  # Unified
            "HYPERLIQUID": "hyperliquid",
            "UPBIT": "upbit",
            "COINBASE": "coinbase",
            # Tier 2
            "BITSTAMP-SPOT": "bitstamp",
            # Tier 3
            "HUOBI-SPOT": "htx",  # Huobi rebranded to HTX
            "HUOBI-FUTURES": "htx",
            # Note: ASTER not in CCXT yet
        }
    )

    # Reverse mapping: Tardis exchange endpoint → canonical venue name
    # Each Tardis exchange MUST map to a DISTINCT canonical venue so instruments
    # are distinguishable after date filtering (no venue-collapse).
    tardis_to_venue: dict[str, str] = field(
        default_factory=lambda: {
            # Tier 1
            "binance": "BINANCE-SPOT",
            "binance-futures": "BINANCE-FUTURES",
            "deribit": "DERIBIT",
            "bybit": "BYBIT",
            "bybit-spot": "BYBIT",
            "okex": "OKX-SPOT",
            "okex-swap": "OKX-SWAP",
            "okex-futures": "OKX-FUTURES",
            "coinbase": "COINBASE-SPOT",
            # Tier 2
            "upbit": "UPBIT",
            "hyperliquid": "HYPERLIQUID",
        }
    )

    # Map venues to their data providers (for non-Tardis venues)
    venue_to_data_provider: dict[str, str] = field(
        default_factory=lambda: {
            # TradFi venues with external data providers (not Databento)
            "CBOE": "barchart",  # VIX via Barchart
            "FX": "yahoo_finance",  # KRW/USD via Yahoo Finance
            # DeFi venues with direct API integration
            "HYPERLIQUID": "hyperliquid_api",  # Hyperliquid REST/WebSocket API + S3 archive
            "ASTER": "aster_api",  # Aster REST API
            # DeFi venues — canonical PROTOCOL-CHAIN format
            "UNISWAPV2-ETHEREUM": "the_graph",
            "UNISWAPV3-ETHEREUM": "the_graph",
            "UNISWAPV4-ETHEREUM": "the_graph",
            "CURVE-ETHEREUM": "rpc",
            "BALANCER-ETHEREUM": "balancer_api_v3",
            "AAVEV3-ETHEREUM": "the_graph",
            "MORPHO-ETHEREUM": "the_graph",
            "FLUID-ETHEREUM": "the_graph",
            "LIDO-ETHEREUM": "protocol_sdk",
            "ETHERFI-ETHEREUM": "protocol_sdk",
            "ETHENA-ETHEREUM": "protocol_sdk",
        }
    )

    # Venue launch/start dates (centralized - single source of truth)
    # These are the earliest dates when data is available for each venue
    # Adapters should use these instead of hardcoding dates
    venue_start_dates: dict[str, str] = field(
        default_factory=lambda: {
            # CEFI - Tardis exchanges (Tier 1)
            # Start dates = earliest manifest data, NOT exchange founding dates
            "BINANCE-SPOT": "2020-01-01",
            "BINANCE-FUTURES": "2019-11-17",
            "DERIBIT": "2019-03-30",
            "BYBIT": "2020-01-01",
            "OKX-SPOT": "2020-01-01",
            "OKX-FUTURES": "2020-01-01",
            "OKX-SWAP": "2020-01-01",
            "UPBIT": "2021-03-03",
            "COINBASE-SPOT": "2020-01-01",
            # CEFI - On-chain CLOBs
            "HYPERLIQUID": "2023-11-01",
            "ASTER": "2024-10-01",
            # TradFi - Databento
            # Start dates = earliest manifest data
            "CME": "2020-01-01",
            "CBOE": "2020-06-01",  # Barchart historical data available
            "NASDAQ": "2023-04-15",
            "NYSE": "2023-04-15",
            "ICE": "2020-01-01",
            "FX": "2020-01-01",
            # DeFi - DEX protocols (canonical PROTOCOL-CHAIN format)
            # Start dates = earliest manifest data
            "UNISWAPV2-ETHEREUM": "2020-05-06",  # Uniswap V2 factory deployed May 2020
            "UNISWAPV3-ETHEREUM": "2021-05-05",  # Uniswap V3 mainnet launch
            "UNISWAPV3-ARBITRUM": "2021-06-18",
            "UNISWAPV3-POLYGON": "2021-12-22",  # Uniswap V3 Polygon deployment
            "UNISWAPV3-OPTIMISM": "2021-11-12",
            "UNISWAPV3-BASE": "2023-09-03",  # Earliest subgraph data (Base launched 2023-08-09)
            "UNISWAPV4-ETHEREUM": "2025-01-30",  # Uniswap V4 mainnet deployment
            "CURVE-ETHEREUM": "2020-01-20",  # Curve genesis pool
            "CURVE-AVALANCHE": "2021-11-10",  # Curve Avalanche deployment
            "CURVE-OPTIMISM": "2022-01-13",  # Curve Optimism deployment
            "BALANCER-ETHEREUM": "2021-04-22",  # Earliest subgraph data (V1 launched 2020-02-28)
            "BALANCER-POLYGON": "2021-06-24",
            "BALANCER-ARBITRUM": "2021-08-27",
            "BALANCER-OPTIMISM": "2022-05-20",
            "BALANCER-AVALANCHE": "2023-08-17",
            "BALANCER-BASE": "2023-07-29",
            "PANCAKESWAPV3-BSC": "2023-04-03",  # PancakeSwap V3 BSC launch
            "PANCAKESWAPV3-ETHEREUM": "2023-04-03",  # PancakeSwap V3 ETH launch
            "PANCAKESWAPV3-ARBITRUM": "2023-08-21",
            "PANCAKESWAPV3-BASE": "2023-09-01",
            "PANCAKESWAPV3-ZKSYNC": "2023-08-01",
            "CAMELOTV3-ARBITRUM": "2022-11-01",  # Camelot V3 Arbitrum launch
            "SUSHISWAPV3-ETHEREUM": "2023-04-01",  # SushiSwap V3 ETH launch
            "SUSHISWAPV3-BASE": "2023-09-01",  # SushiSwap V3 Base launch
            "SUSHISWAPV3-AVALANCHE": "2023-04-01",
            "GMX-ARBITRUM": "2021-09-06",  # GMX Arbitrum launch
            "GMX-AVALANCHE": "2022-01-05",  # GMX Avalanche launch
            "AERODROMEV3-BASE": "2023-08-28",  # Aerodrome Base launch
            "VELODROMEV2-OPTIMISM": "2023-06-15",  # Velodrome V2 Optimism launch
            "TRADERJOE-AVALANCHE": "2021-07-04",  # TraderJoe Avalanche launch
            # DeFi - Lending protocols
            "AAVEV3-ETHEREUM": "2023-01-27",
            "AAVEV3-POLYGON": "2022-03-12",
            "AAVEV3-AVALANCHE": "2022-03-12",
            "AAVEV3-ARBITRUM": "2022-03-12",
            "AAVEV3-OPTIMISM": "2022-03-12",
            "AAVEV3-BASE": "2023-08-23",
            "AAVEV3-BSC": "2024-01-24",
            "AAVEV3-SCROLL": "2024-02-10",
            "AAVEV3-LINEA": "2025-02-12",
            "AAVEV3-ZKSYNC": "2024-09-21",
            "COMPOUNDV3-ETHEREUM": "2022-08-14",
            "COMPOUNDV3-ARBITRUM": "2023-05-05",
            "COMPOUNDV3-BASE": "2023-08-20",
            "COMPOUNDV3-OPTIMISM": "2024-04-07",
            "COMPOUNDV3-SCROLL": "2024-02-17",
            "MORPHO-ETHEREUM": "2024-01-08",
            "MORPHO-BASE": "2024-06-01",
            "FLUID-ETHEREUM": "2024-02-27",
            # DeFi - LST/Yield protocols
            "LIDO-ETHEREUM": "2020-12-18",
            "ETHERFI-ETHEREUM": "2023-11-01",
            "ETHENA-ETHEREUM": "2024-02-19",
            # DeFi - Solana protocols
            "DRIFT-SOLANA": "2022-11-04",
            "ORCA-SOLANA": "2023-12-29",
            "RAYDIUM-SOLANA": "2025-06-26",  # Earliest active pool data (REST API set)
            "KAMINO-SOLANA": "2023-01-21",
            "JITO-SOLANA": "2021-11-01",
            "MARINADE-SOLANA": "2021-08-01",
            # Prediction — Polymarket
            # POLYMARKET base venue start = earliest instrument data
            "POLYMARKET": "2025-03-13",
            # Per-underlying shard start dates (consistent daily presence)
            # These are used by deployment-ui for accurate completion %
            "POLYMARKET:BTC": "2025-03-13",
            "POLYMARKET:ETH": "2025-03-14",
            "POLYMARKET:SOL": "2025-05-08",
            "POLYMARKET:XRP": "2025-05-15",
            "POLYMARKET:DOGE": "2026-03-09",
            "POLYMARKET:HYPE": "2026-03-08",
            "POLYMARKET:BNB": "2026-03-08",
            "POLYMARKET:FOOTBALL": "2025-10-18",
            "POLYMARKET:OTHER": "2025-03-13",
        }
    )

    # Source/provider data start dates (distinct from venue launch dates)
    # These are data aggregators or providers, not trading venues.
    # The date is the earliest date with actual data available from the source.
    source_data_start_dates: dict[str, str] = field(
        default_factory=lambda: {
            # Sports — Odds API historical data starts 2020-06-06
            # API returns 401 Unauthorized for dates before this
            "ODDS_API": "2020-06-06",
        }
    )

    # MVP token list for DeFi pool discovery (configurable)
    defi_mvp_base_currencies: list[str] = field(
        default_factory=lambda: [
            "ETH",  # Native Ethereum
            "WETH",  # Wrapped ETH
            "BTC",  # Bitcoin (WBTC on Ethereum)
            "WBTC",  # Wrapped Bitcoin (explicitly include WBTC)
            "USDT",  # Tether
            "USDC",  # USD Coin
            "DAI",  # Dai stablecoin
            "weETH",  # EtherFi LST (Wrapped eETH) - non-rebasing
            "WSTETH",  # Lido LST (non-rebasing, wrapped version)
            # STETH removed - rebasing token, not supported by AAVE
        ]
    )

    # MVP base assets for Hyperliquid and Aster perpetuals
    # These are the 21 trading assets used for CeFi/TradFi MVP
    hyperliquid_aster_mvp_base_assets: list[str] = field(
        default_factory=lambda: [
            "SOL",  # Solana
            "BTC",  # Bitcoin
            "ETH",  # Ethereum
            "AVAX",  # Avalanche
            "ADA",  # Cardano
            "SUSHI",  # SushiSwap
            "CAKE",  # PancakeSwap
            "XRP",  # Ripple
            "DOGE",  # Dogecoin
            "XLM",  # Stellar
            "LTC",  # Litecoin
            "ALGO",  # Algorand
            "FIL",  # Filecoin
            "TRX",  # Tron
            "BNB",  # Binance Coin
            "LINK",  # Chainlink
            "MATIC",  # Polygon
            "APT",  # Aptos
            "VET",  # VeChain
            "ATOM",  # Cosmos
            "NEAR",  # Near Protocol
        ]
    )

    def is_databento_venue(self, venue: str) -> bool:
        """Check if venue uses Databento (canonical venue name)."""
        return venue in self.all_databento_venues

    def is_tardis_exchange(self, exchange: str) -> bool:
        """Check if exchange uses Tardis (API endpoint name)."""
        return exchange in self.all_tardis_exchanges

    def is_defi_venue(self, venue: str) -> bool:
        """Check if venue is a DeFi protocol (swaps, lending, staking)."""
        return venue in self.all_defi_venues

    def is_cefi_onchain_clob_venue(self, venue: str) -> bool:
        """Check if venue is an on-chain CLOB (treated as CEFI for data classification)."""
        return venue in self.all_cefi_onchain_clob_venues

    def is_cefi_venue(self, venue: str) -> bool:
        """Check if venue should be treated as CEFI (includes Tardis + on-chain CLOBs)."""
        # Check if it's a Tardis exchange (via canonical venue mapping)
        canonical_venues = set(self.tardis_to_venue.values())
        if venue in canonical_venues:
            return True
        # Check if it's an on-chain CLOB venue
        return venue in self.all_cefi_onchain_clob_venues

    def get_venue_start_date(self, venue: str) -> str | None:
        """
        Get the start date for a venue or data source.

        Checks venue_start_dates first, then source_data_start_dates as fallback.

        Args:
            venue: Canonical venue name or source name (e.g., "BINANCE-SPOT", "ODDS_API")

        Returns:
            ISO date string (YYYY-MM-DD) or None if not found
        """
        return self.venue_start_dates.get(venue) or self.source_data_start_dates.get(venue)

    def is_venue_available_on_date(self, venue: str, target_date: datetime | date | str) -> bool:
        """
        Check if a venue was available (launched) on a given date.

        Args:
            venue: Canonical venue name
            target_date: datetime or date object to check

        Returns:
            True if venue was available on the target date, False otherwise
        """
        start_date_str = self.venue_start_dates.get(venue) or self.source_data_start_dates.get(venue)
        if not start_date_str:
            # If no start date configured, assume always available
            return True

        # Parse the start date
        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()

        # Normalize target_date to date object
        if isinstance(target_date, datetime):
            target = target_date.date()
        elif isinstance(target_date, date):
            target = target_date
        else:
            # Try to parse string
            date_str = str(target_date)[:10]
            target = datetime.strptime(date_str, "%Y-%m-%d").date()

        return target >= start_date

    def get_venue_to_tardis_exchanges(self) -> dict[str, list[str]]:
        """
        Get reverse mapping: canonical venue -> list of Tardis exchange names.

        Note: One canonical venue can map to multiple Tardis exchanges.
        E.g., OKX -> ["okex", "okex-futures", "okex-swap"]

        Returns:
            Dict mapping canonical venue names to list of Tardis exchange names
        """
        venue_to_exchanges: dict[str, list[str]] = {}
        for tardis_exchange, canonical_venue in self.tardis_to_venue.items():
            if canonical_venue not in venue_to_exchanges:
                venue_to_exchanges[canonical_venue] = []
            venue_to_exchanges[canonical_venue].append(tardis_exchange)
        return venue_to_exchanges

    def _get_direct_tardis_match(self, canonical_venue: str) -> str | None:
        for tardis_exchange, venue in self.tardis_to_venue.items():
            if venue == canonical_venue:
                return tardis_exchange
        return None

    def _get_suffixed_tardis_match(self, canonical_venue: str) -> str | None:
        if "-" not in canonical_venue:
            return None
        base_venue, suffix = canonical_venue.rsplit("-", 1)
        suffix_to_type = {
            "SPOT": "SPOT_PAIR",
            "SWAP": "PERPETUAL",
            "FUTURES": "FUTURE",
            "OPTIONS": "OPTION",
        }
        inst_type = suffix_to_type.get(suffix, suffix)
        for venue_key in (canonical_venue, base_venue):
            tardis_name = self.venue_instrument_type_to_tardis.get((venue_key, inst_type))
            if tardis_name:
                return tardis_name
        if suffix == "FUTURES":
            futures_fallback = self.venue_instrument_type_to_tardis.get((base_venue, "PERPETUAL"))
            if futures_fallback:
                return futures_fallback
        return self._get_direct_tardis_match(base_venue)

    def get_tardis_exchange_for_venue(self, canonical_venue: str) -> str | None:
        """Get Tardis exchange name for a canonical venue.

        Handles suffixed venues (OKX-SPOT → okex, OKX-FUTURES → okex-futures,
        COINBASE-SPOT → coinbase, BINANCE-SPOT → binance).

        Uses the instrument_type_to_tardis mapping for suffixed venues,
        falls back to direct tardis_to_venue lookup for simple names.
        """
        upper = canonical_venue.upper()
        direct_match = self._get_direct_tardis_match(upper)
        if direct_match:
            return direct_match
        return self._get_suffixed_tardis_match(upper)

    def convert_to_tardis_exchange(self, exchange_or_venue: str) -> str:
        """
        Convert exchange name to Tardis API format (lowercase).

        Handles both:
        - Canonical venue names: UPBIT -> upbit, COINBASE -> coinbase
        - Already lowercase Tardis names: upbit -> upbit

        Args:
            exchange_or_venue: Exchange name (could be canonical venue or Tardis name)

        Returns:
            Lowercase Tardis exchange name
        """
        # If it's uppercase, it's likely a canonical venue name
        upper_name = exchange_or_venue.upper()
        lower_name = exchange_or_venue.lower()

        # Check if it's a canonical venue name
        tardis_name = self.get_tardis_exchange_for_venue(upper_name)
        if tardis_name:
            return tardis_name

        # Check if it's already a valid Tardis exchange name
        if lower_name in self.all_tardis_exchanges:
            return lower_name

        # Return lowercase as fallback
        return lower_name

    def get_defi_mvp_tokens(self) -> list[str]:
        """Get MVP token list from the configured defi_mvp_base_currencies field.

        To override the token list, pass a custom list at construction time:
            VenueMapping(defi_mvp_base_currencies=["ETH", "WETH", "USDC"])
        """
        return self.defi_mvp_base_currencies

    def get_databento_exchange_id(self, venue: str) -> str | None:
        """Get Databento exchange identifier for canonical venue."""
        return self.venue_to_databento.get(venue)

    # CRITICAL: Map venue+instrument_type -> Tardis exchange endpoint
    # Note: HYPERLIQUID and ASTER use direct APIs, not Tardis
    venue_instrument_type_to_tardis: dict[tuple[str, str], str] = field(
        default_factory=lambda: {
            # Binance mappings
            ("BINANCE-SPOT", "SPOT_PAIR"): "binance",
            ("BINANCE-FUTURES", "PERPETUAL"): "binance-futures",
            ("BINANCE-FUTURES", "FUTURE"): "binance-futures",
            # OKX mappings (CRITICAL: instrument_type determines endpoint)
            ("OKX", "SPOT_PAIR"): "okex",
            ("OKX", "PERPETUAL"): "okex-swap",
            ("OKX", "FUTURE"): "okex-futures",
            # Bybit mappings
            ("BYBIT", "SPOT_PAIR"): "bybit-spot",
            ("BYBIT", "PERPETUAL"): "bybit",
            ("BYBIT", "FUTURE"): "bybit",
            # Deribit (unified endpoint)
            ("DERIBIT", "SPOT_PAIR"): "deribit",
            ("DERIBIT", "PERPETUAL"): "deribit",
            ("DERIBIT", "FUTURE"): "deribit",
            ("DERIBIT", "OPTION"): "deribit",
            # Upbit (spot only - Korean exchange for kimchi premium)
            ("UPBIT", "SPOT_PAIR"): "upbit",
            # Coinbase (spot only - for coinbase premium)
            ("COINBASE", "SPOT_PAIR"): "coinbase",
            # Tier 2 exchanges (spot only)
            ("BITSTAMP-SPOT", "SPOT_PAIR"): "bitstamp",
            # Tier 3 exchanges
            ("HUOBI-SPOT", "SPOT_PAIR"): "huobi",
            ("HUOBI-FUTURES", "PERPETUAL"): "huobi-dm",
            ("HUOBI-FUTURES", "FUTURE"): "huobi-dm",
        }
    )

    # Which Tardis exchanges map to which instrument types (for filtering)
    tardis_exchange_instrument_types: dict[str, list[str]] = field(
        default_factory=lambda: {
            # Tier 1
            "binance": ["SPOT_PAIR"],
            "binance-futures": ["PERPETUAL", "FUTURE"],
            "okex": ["SPOT_PAIR"],
            "okex-swap": ["PERPETUAL"],
            "okex-futures": ["FUTURE"],
            "bybit": ["PERPETUAL", "FUTURE"],
            "bybit-spot": ["SPOT_PAIR"],
            "deribit": ["SPOT_PAIR", "PERPETUAL", "FUTURE", "OPTION"],
            "coinbase": ["SPOT_PAIR"],
            # Tier 2
            "upbit": ["SPOT_PAIR"],
            "bitstamp": ["SPOT_PAIR"],
            # Tier 3
            "huobi": ["SPOT_PAIR"],
            "huobi-dm": ["PERPETUAL", "FUTURE"],
        }
    )

    # Venues that require MVP base asset filtering (spot only venues for premium calculations)
    # These venues will only include instruments for the 21 MVP base assets
    spot_mvp_filtered_venues: list[str] = field(
        default_factory=lambda: [
            "UPBIT",  # Korean exchange - for kimchi premium
            "COINBASE",  # Coinbase - for coinbase premium
        ]
    )

    def get_data_provider(self, venue: str) -> str | None:
        """Get data provider for a venue.

        Returns one of: tardis, databento, hyperliquid_api, aster_api,
        the_graph, protocol_sdk.
        """
        # Check if it's a Tardis venue
        if venue in self.tardis_to_venue.values() or any(venue == v for v in self.tardis_to_venue.values()):
            return "tardis"
        # Check if it's a Databento venue
        if venue in self.all_databento_venues:
            return "databento"
        # Check venue_to_data_provider mapping
        return self.venue_to_data_provider.get(venue)


@dataclass
class DataTypeConfig:
    """CRITICAL: Data types per instrument type (fixes 66% false positives)"""

    instrument_data_types: dict[str, list[str]] = field(
        default_factory=lambda: {
            # CeFi instrument types
            "SPOT_PAIR": ["trades", "book_snapshot_5"],
            "PERPETUAL": [
                "trades",
                "book_snapshot_5",
                "derivative_ticker",
                "liquidations",
            ],
            "FUTURE": [
                "trades",
                "book_snapshot_5",
                "derivative_ticker",
                "liquidations",
            ],
            "OPTION": ["options_chain", "trades", "book_snapshot_5", "liquidations"],
            # DeFi instrument types
            "POOL": ["swaps", "liquidity"],  # DEX pools (Uniswap, etc.)
            "A_TOKEN": ["rate_indices", "oracle_prices"],  # Lending supply positions (AAVE, Morpho)
            "DEBT_TOKEN": [
                "rate_indices",
                "oracle_prices",
            ],  # Lending borrow positions (AAVE, Morpho)
            "LST": ["oracle_prices"],  # Liquid staking tokens (Lido, EtherFi)
            "YIELD_BEARING": ["oracle_prices"],  # Yield-bearing tokens (Ethena sUSDe)
        }
    )

    default_data_types: list[str] = field(
        default_factory=lambda: [
            "trades",
            "book_snapshot_5",
            "derivative_ticker",
            "liquidations",
            "options_chain",
        ]
    )

    # Instrument type filters (exclude complex types we don't want to process)
    excluded_instrument_types: list[str] = field(
        default_factory=lambda: ["combo"]  # Exclude Deribit combo strategies
    )

    # Complex option strategy filters (Deribit specific - exclude complex strategies)
    excluded_deribit_strategies: list[str] = field(
        default_factory=lambda: [
            "PS-",
            "STRG-",
            "CBUT-",
            "CCOND-",
            "PDIAG-",
            "PBUT-",
            "ICOND-",
            "BOX-",
            "FS-",
            "RR-",
            "CSR12-",
            "PSR12-",
            "CSR13-",
            "PSR13-",
            "CCAL-",
            "CDIAG-",
        ]
    )


@dataclass
class ExchangeInstrumentConfig:
    """Valid instrument types and quote currencies per exchange (CORRECTED canonical venues)"""

    exchange_instrument_types: dict[str, list[str]] = field(
        default_factory=lambda: {
            # CeFi - Tardis exchanges
            "BINANCE-SPOT": ["SPOT_PAIR"],  # Spot only
            "BINANCE-FUTURES": ["PERPETUAL", "FUTURE"],  # Derivatives only
            "DERIBIT": ["PERPETUAL", "FUTURE", "OPTION"],  # Full derivatives exchange
            "BYBIT": ["SPOT_PAIR", "PERPETUAL"],  # Combined
            "OKX": ["SPOT_PAIR", "PERPETUAL", "FUTURE"],  # Combined
            "UPBIT": ["SPOT_PAIR"],  # Spot only (Korean exchange for kimchi premium)
            "COINBASE": ["SPOT_PAIR"],  # Spot only (for coinbase premium)
            # CeFi - On-chain CLOBs
            "HYPERLIQUID": ["PERPETUAL"],  # Perpetuals only (NO liquidations endpoint)
            "ASTER": ["PERPETUAL"],  # Perpetuals only (NO liquidations - endpoint disabled)
            # DeFi - DEX protocols (canonical PROTOCOL-CHAIN format)
            "UNISWAPV2-ETHEREUM": ["POOL"],
            "UNISWAPV3-ETHEREUM": ["POOL"],
            "UNISWAPV4-ETHEREUM": ["POOL"],
            "CURVE-ETHEREUM": ["POOL"],
            "BALANCER-ETHEREUM": ["POOL"],
            # DeFi - Lending protocols
            "AAVEV3-ETHEREUM": ["A_TOKEN", "DEBT_TOKEN"],
            "MORPHO-ETHEREUM": ["A_TOKEN", "DEBT_TOKEN"],
            "FLUID-ETHEREUM": ["A_TOKEN", "DEBT_TOKEN"],
            # DeFi - LST/Yield protocols
            "LIDO-ETHEREUM": ["LST"],
            "ETHERFI-ETHEREUM": ["LST"],
            "ETHENA-ETHEREUM": ["YIELD_BEARING"],
        }
    )

    valid_quote_currencies: dict[str, list[str]] = field(
        default_factory=lambda: {
            "BINANCE-SPOT": ["USDT"],  # STRICT: Only USDT
            "BINANCE-FUTURES": ["USDT"],  # STRICT: Only USDT
            "DERIBIT": ["USD", "USDC"],  # Options exchange
            "BYBIT": ["USDT"],  # STRICT: Only USDT
            "OKX": ["USDT"],  # STRICT: Only USDT
            "UPBIT": ["KRW"],  # Korean Won (for kimchi premium calculations)
            "COINBASE": ["USD"],  # US Dollar (for coinbase premium calculations)
        }
    )

    derivative_exchanges: list[str] = field(
        default_factory=lambda: [
            "DERIBIT",
            "BINANCE-FUTURES",
            "OKX",
            "BYBIT",
        ]
    )

    # Excluded base currencies per exchange (e.g., deprecated tokens, leveraged products)
    excluded_base_currencies: dict[str, list[str]] = field(
        default_factory=lambda: {
            "OKX": ["USTC"],  # USTC (Terra Classic) deprecated
            "BYBIT": [],  # No base currency exclusions
        }
    )

    # Excluded symbol patterns per exchange (e.g., leveraged products)
    excluded_symbol_patterns: dict[str, list[str]] = field(
        default_factory=lambda: {
            "BYBIT": [
                "3L",  # 3x leveraged LONG products
                "2L",  # 2x leveraged LONG products
                "3S",  # 3x leveraged SHORT products
                "2S",  # 2x leveraged SHORT products
            ],
            "OKX": [],  # No symbol pattern exclusions
        }
    )

    # Symbol format per exchange
    # Most exchanges use BASE-QUOTE (e.g., BTC-USD, SOL-USDT)
    # Some exchanges like Upbit use QUOTE-BASE (e.g., KRW-BTC, KRW-SOL)
    symbol_format: dict[str, str] = field(
        default_factory=lambda: {
            "UPBIT": "QUOTE-BASE",  # Upbit uses KRW-SOL format (quote first)
            # All other exchanges use BASE-QUOTE by default
        }
    )

    def get_symbol_format(self, venue: str) -> str:
        """Get symbol format for a venue. Returns 'BASE-QUOTE' if not specified."""
        return self.symbol_format.get(venue, "BASE-QUOTE")
