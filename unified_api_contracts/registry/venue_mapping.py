"""
Centralized Venue and Data Type Configuration

Provides canonical venue mappings, data type configurations, and exchange settings
used across all services in the unified trading system.

This is the SSOT for venue identity concepts. Previously duplicated in:
- unified-config-interface/unified_config_interface/venue_config.py
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
            "binance-futures",  # BINANCE split
            "deribit",  # DERIBIT unified
            "bybit",
            "bybit-spot",  # BYBIT unified
            "okex",
            "okex-futures",
            "okex-swap",  # OKX needs all endpoints for complete data
            "coinbase",  # Coinbase - spot only, for coinbase premium
            # Tier 2: Regional / specialist exchanges
            "upbit",  # Upbit (Korean exchange) - spot only, for kimchi premium
            "gemini",  # Gemini - spot
            "bitstamp",  # Bitstamp - spot
            # Tier 3: Additional CeFi exchanges
            "huobi",  # Huobi/HTX - spot
            "huobi-dm",  # Huobi/HTX - derivatives (futures/swaps)
            "phemex",  # Phemex - spot + derivatives
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

    # DeFi venues (multi-chain support: Ethereum, Plasma)
    # Note: HYPERLIQUID and ASTER moved to all_cefi_onchain_clob_venues
    all_defi_venues: list[str] = field(
        default_factory=lambda: [
            # Ethereum DEX protocols (swaps)
            "UNISWAPV2-ETH",  # Uniswap V2 Ethereum
            "UNISWAPV3-ETH",  # Uniswap V3 Ethereum
            "UNISWAPV4-ETH",  # Uniswap V4 Ethereum (launched January 31, 2025)
            "CURVE-ETH",  # Curve Ethereum (MetaRegistry RPC)
            "BALANCER-ETH",  # Balancer V2/V3 Ethereum (API v3 GraphQL)
            # Lending protocols
            "AAVE_V3_ETH",  # AAVE V3 Ethereum
            "MORPHO-ETHEREUM",  # Morpho lending protocol (Ethereum)
            # Plasma lending protocols
            "EULER-PLASMA",  # Euler lending (Plasma)
            "FLUID-PLASMA",  # Fluid lending (Plasma)
            "AAVE-PLASMA",  # AAVE Plasma market (Plasma)
            # LST/Yield protocols
            "ETHERFI",  # EtherFi LST (Ethereum)
            "LIDO",  # Lido LST (Ethereum)
            "ETHENA",  # Ethena synthetic dollars (Ethereum)
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
            "GEMINI-SPOT": "gemini",
            "BITSTAMP-SPOT": "bitstamp",
            # Tier 3
            "HUOBI-SPOT": "htx",  # Huobi rebranded to HTX
            "HUOBI-FUTURES": "htx",
            "PHEMEX-SPOT": "phemex",
            # Note: ASTER not in CCXT yet
        }
    )

    # Reverse mapping: Tardis exchange endpoint → canonical venue name
    # Aligned with DATA_SOURCE_TO_VENUES["tardis"] in canonical_mappings.py
    tardis_to_venue: dict[str, str] = field(
        default_factory=lambda: {
            # Tier 1
            "binance": "BINANCE-SPOT",
            "binance-futures": "BINANCE-FUTURES",
            "deribit": "DERIBIT",
            "bybit": "BYBIT",
            "bybit-spot": "BYBIT",
            "okex": "OKX",
            "okex-futures": "OKX",
            "okex-swap": "OKX",
            "coinbase": "COINBASE",
            # Tier 2
            "upbit": "UPBIT",
            "gemini": "GEMINI-SPOT",
            "bitstamp": "BITSTAMP-SPOT",
            # Tier 3
            "huobi": "HUOBI-SPOT",
            "huobi-dm": "HUOBI-FUTURES",
            "phemex": "PHEMEX-SPOT",
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
            # DeFi venues using The Graph
            "UNISWAPV2-ETH": "the_graph",
            "UNISWAPV3-ETH": "the_graph",
            "UNISWAPV4-ETH": "the_graph",
            "CURVE-ETH": "rpc",  # Curve MetaRegistry RPC (The Graph deprecated)
            "BALANCER-ETH": "balancer_api_v3",  # Balancer API v3 GraphQL (public, no key)
            # DeFi venues using protocol SDKs
            "AAVE_V3_ETH": "protocol_sdk",
            "MORPHO-ETHEREUM": "protocol_sdk",
            "EULER-PLASMA": "protocol_sdk",
            "FLUID-PLASMA": "protocol_sdk",
            "AAVE-PLASMA": "protocol_sdk",
            "ETHERFI": "protocol_sdk",
            "LIDO": "protocol_sdk",
            "ETHENA": "protocol_sdk",
        }
    )

    # Venue launch/start dates (centralized - single source of truth)
    # These are the earliest dates when data is available for each venue
    # Adapters should use these instead of hardcoding dates
    venue_start_dates: dict[str, str] = field(
        default_factory=lambda: {
            # CEFI - Tardis exchanges (Tier 1)
            "BINANCE-SPOT": "2017-07-14",
            "BINANCE-FUTURES": "2019-09-13",
            "DERIBIT": "2016-06-01",
            "BYBIT": "2018-03-01",
            "OKX": "2017-05-31",
            "UPBIT": "2017-10-24",
            "COINBASE": "2015-01-26",
            # CEFI - Tardis exchanges (Tier 2)
            "GEMINI-SPOT": "2015-10-08",
            "BITSTAMP-SPOT": "2011-08-18",
            # CEFI - Tardis exchanges (Tier 3)
            "HUOBI-SPOT": "2013-09-01",
            "HUOBI-FUTURES": "2018-12-10",
            "PHEMEX-SPOT": "2019-11-25",
            # CEFI - On-chain CLOBs
            "HYPERLIQUID": "2023-04-15",
            "ASTER": "2024-10-01",
            # TradFi - Databento
            "CME": "2020-01-01",
            "CBOE": "2020-01-01",
            "NASDAQ": "2020-01-01",
            "NYSE": "2020-01-01",
            "ICE": "2018-12-23",
            "FX": "2020-01-01",  # OTC Foreign Exchange (KRW/USD via Yahoo Finance)
            # DeFi - DEX protocols
            "UNISWAPV2-ETH": "2020-05-18",
            "UNISWAPV3-ETH": "2021-05-05",
            "UNISWAPV4-ETH": "2024-11-01",
            "CURVE-ETH": "2020-01-20",  # Curve Ethereum (MetaRegistry RPC)
            "BALANCER-ETH": "2020-03-31",  # Balancer Ethereum (API v3 GraphQL)
            # DeFi - Lending protocols
            "AAVE_V3_ETH": "2023-01-27",
            "MORPHO-ETHEREUM": "2024-01-08",
            "EULER-PLASMA": "2024-03-01",
            "FLUID-PLASMA": "2024-06-01",
            "AAVE-PLASMA": "2024-03-01",
            # DeFi - LST/Yield protocols
            "LIDO": "2020-12-18",
            "ETHERFI": "2024-01-01",
            "ETHENA": "2024-02-16",
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
        Get the launch/start date for a venue.

        Args:
            venue: Canonical venue name (e.g., "ETHERFI", "UNISWAPV3-ETH")

        Returns:
            ISO date string (YYYY-MM-DD) or None if venue not found
        """
        return self.venue_start_dates.get(venue)

    def is_venue_available_on_date(self, venue: str, target_date: datetime | date | str) -> bool:
        """
        Check if a venue was available (launched) on a given date.

        Args:
            venue: Canonical venue name
            target_date: datetime or date object to check

        Returns:
            True if venue was available on the target date, False otherwise
        """
        start_date_str = self.venue_start_dates.get(venue)
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

    def get_tardis_exchange_for_venue(self, canonical_venue: str) -> str | None:
        """
        Get primary Tardis exchange name for a canonical venue.

        For venues with multiple Tardis endpoints (e.g., OKX), returns the first/primary one.
        For simple venues like UPBIT, COINBASE, returns the single Tardis exchange name.

        Args:
            canonical_venue: Canonical venue name (e.g., "UPBIT", "COINBASE", "OKX")

        Returns:
            Tardis exchange name (lowercase) or None if not found
        """
        # Direct lookup in reverse mapping
        for tardis_exchange, venue in self.tardis_to_venue.items():
            if venue == canonical_venue:
                return tardis_exchange
        return None

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
            ("GEMINI-SPOT", "SPOT_PAIR"): "gemini",
            ("BITSTAMP-SPOT", "SPOT_PAIR"): "bitstamp",
            # Tier 3 exchanges
            ("HUOBI-SPOT", "SPOT_PAIR"): "huobi",
            ("HUOBI-FUTURES", "PERPETUAL"): "huobi-dm",
            ("HUOBI-FUTURES", "FUTURE"): "huobi-dm",
            ("PHEMEX-SPOT", "SPOT_PAIR"): "phemex",
            ("PHEMEX-SPOT", "PERPETUAL"): "phemex",
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
            "gemini": ["SPOT_PAIR"],
            "bitstamp": ["SPOT_PAIR"],
            # Tier 3
            "huobi": ["SPOT_PAIR"],
            "huobi-dm": ["PERPETUAL", "FUTURE"],
            "phemex": ["SPOT_PAIR", "PERPETUAL"],
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
            # DeFi - DEX protocols
            "UNISWAPV2-ETH": ["POOL"],
            "UNISWAPV3-ETH": ["POOL"],
            "UNISWAPV4-ETH": ["POOL"],
            # DeFi - Lending protocols
            "AAVE_V3_ETH": ["A_TOKEN", "DEBT_TOKEN"],
            "MORPHO-ETHEREUM": ["A_TOKEN", "DEBT_TOKEN"],
            # DeFi - LST protocols
            "LIDO": ["LST"],
            "ETHERFI": ["LST"],
            "ETHENA": ["YIELD_BEARING"],
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
