"""Runtime schema validation for InstrumentRecord.

Enforces required-field rules per instrument_type and asset group (cefi/defi/…).
Called by orchestrator before writing to GCS — rejects records
that would produce bad data for downstream consumers.
"""

from __future__ import annotations

import logging
import re
from collections import defaultdict
from datetime import date

from unified_api_contracts.internal.reference.instrument import InstrumentRecord, InstrumentStatus, InstrumentType
from unified_api_contracts.registry.chain_env import MAINNET_CHAIN_IDS
from unified_api_contracts.registry.market_data_categories import VENUES_BY_ASSET_GROUP

logger = logging.getLogger(__name__)

# Asset group (CEFI/DEFI/…) is derived from venue patterns
_DEFI_VENUE_PREFIXES = frozenset(
    {
        "AAVE_V3",
        "UNISWAP_V2",
        "UNISWAP_V3",
        "UNISWAP_V4",
        "BALANCER",
        "MORPHO",
        "CURVE",
        "COMPOUND_V3",
        "FLUID",
        "LIDO",
        "ETHERFI",
        "ETHENA",
        "DRIFT",
        "KAMINO",
        "RAYDIUM",
        "ORCA",
        "MARINADE",
        "JITO",
        # DEX forks (UniV3 adapter with protocol_slug)
        "PANCAKESWAP_V3",
        "SUSHISWAP_V3",
        "AERODROME_V3",
        "CAMELOT_V3",
        "VELODROME_V2",
        "TRADER_JOE_V2",
        "GMX",
        "SUSHISWAP",
        # Lending forks
        "SPARK",
        # Governance / restaking
        "EIGENLAYER",
        # Phase-4 lending protocols (2026-07-09/07-10 rollout) — wired into
        # instruments-service's factory + orchestrator venue lists
        # (defi_venues.py DEFI_VENUE_PHASE) but never added here, so every
        # real record these adapters produced was rejected at schema
        # validation with "unknown venue" (found via a live pipeline_e2e_check
        # force-leg re-verification, 2026-07-12).
        "VENUS",
        "RADIANT",
        "BENQI",
        "EULER_V2",
        # Solana lending adapters (2026-07-09) — same gap as above.
        "MARGINFI",
        "SOLEND",
    }
)

# Sourced from the SSOT (registry/market_data_categories.py:VENUES_BY_ASSET_GROUP)
# so adding a venue there is the only edit needed. CeFi covers Tardis canonical
# venues + on-chain CLOBs; tradfi covers Databento + external providers; sports
# covers bookmakers + odds aggregators; prediction covers binary CLOBs. Extra
# legacy aliases (OKX without suffix, MATCHBOOK / API_FOOTBALL) are still
# accepted for back-compat.
_CEFI_VENUES: frozenset[str] = frozenset(VENUES_BY_ASSET_GROUP["cefi"]) | frozenset(
    {
        "OKX",
        "OKX-SPOT",
        "OKX-FUTURES",
        "OKX-SWAP",
        "COINBASE-SPOT",
    }
)
_TRADFI_VENUES: frozenset[str] = frozenset(VENUES_BY_ASSET_GROUP["tradfi"])
_SPORTS_VENUES: frozenset[str] = (
    frozenset(VENUES_BY_ASSET_GROUP["sports"])
    | frozenset(VENUES_BY_ASSET_GROUP["prediction"])
    | frozenset({"MATCHBOOK", "API_FOOTBALL"})
)

# All known venue names (union of all asset groups)
_ALL_KNOWN_VENUES: frozenset[str] = _TRADFI_VENUES | _CEFI_VENUES | _SPORTS_VENUES

# EVM chains — addresses are 0x + 40 hex chars
_EVM_CHAINS = frozenset(chain for chain, chain_id in MAINNET_CHAIN_IDS.items() if chain_id != 0)

# Solana DeFi protocol prefixes — raw_symbol is base58 address
_SOLANA_DEFI_PREFIXES = frozenset({"DRIFT", "KAMINO", "RAYDIUM", "ORCA", "MARINADE", "JITO"})

# DeFi protocols where raw_symbol is NOT a standard address:
# - DRIFT: uses market symbols ("BTC-PERP", "SOL")
# - COMPOUND_V3: uses market names ("USDC", "ETH") or numeric IDs
_DEFI_NON_ADDRESS_RAW_SYMBOL = frozenset({"DRIFT", "COMPOUND_V3"})

# EVM hex address: 0x followed by exactly 40 hex digits
_EVM_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
# Morpho uniqueKey (bytes32): 0x followed by exactly 64 hex digits
_EVM_BYTES32_RE = re.compile(r"^0x[0-9a-fA-F]{64}$")
# Solana base58 address: 32-44 chars from base58 alphabet
_SOLANA_ADDRESS_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")

# DeFi instrument types where quote_asset is not meaningful
# (single-asset lending, staking, yield-bearing tokens).
_SINGLE_ASSET_DEFI_TYPES = frozenset(
    {
        InstrumentType.LENDING.value,  # "LENDING" — Fluid + other not-yet-canonicalized protocols
        InstrumentType.LST.value,  # "LST"
        InstrumentType.YIELD_BEARING.value,  # "YIELD_BEARING" — Ethena sUSDe, Lido stETH, EtherFi eETH
        InstrumentType.STAKING.value,  # "STAKING" — Marinade mSOL
        InstrumentType.A_TOKEN.value,  # "A_TOKEN" — Aave V3, Spark, Compound V3 supply side
        InstrumentType.DEBT_TOKEN.value,  # "DEBT_TOKEN" — Aave V3, Spark, Compound V3 borrow side
    }
)


def _infer_asset_group(venue: str) -> str:
    """Infer CEFI/DEFI/TRADFI/SPORTS/PREDICTION from venue name."""
    venue_upper = venue.upper()
    if venue_upper in _TRADFI_VENUES:
        return "TRADFI"
    if venue_upper in _SPORTS_VENUES:
        return "SPORTS"
    prefix = venue_upper.split("-")[0]
    if prefix in _DEFI_VENUE_PREFIXES:
        return "DEFI"
    return "CEFI"


def validate_instrument_records(
    records: list[InstrumentRecord],
    as_of_date: date | None = None,
) -> tuple[list[InstrumentRecord], list[tuple[InstrumentRecord, str]]]:
    """Validate instrument records against per-type and asset-group rules.

    Returns (valid_records, rejected_records_with_reason).

    Rules:
    - available_from_datetime: RECOMMENDED (not blocking — many venues lack listing dates)
    - quote_asset: REQUIRED for CeFi and TradFi (not DeFi lending types)
    - expiry: REQUIRED for futures and options
    - strike + option_type: REQUIRED for options
    - underlying: REQUIRED for CeFi/TradFi derivatives (futures, options) — not spot/index, not DeFi
    - timezone + holiday_calendar: REQUIRED for all TradFi instruments
    - regular_open_utc + regular_close_utc: REQUIRED for TradFi equities (NASDAQ/NYSE) on trading days
    - available_to: optional (None = still active) — OK
    - CBOE VIX exception: tick_size/lot_size/contract_size not required
    """
    valid: list[InstrumentRecord] = []
    rejected: list[tuple[InstrumentRecord, str]] = []

    for rec in records:
        reason = _check_record(rec, as_of_date)
        if reason:
            rejected.append((rec, reason))
        else:
            valid.append(rec)

    if rejected:
        # Summarise rejections by reason
        by_reason: dict[str, int] = defaultdict(int)
        for _, r in rejected:
            by_reason[r] += 1
        for reason, count in sorted(by_reason.items()):
            logger.warning("Instrument validation: %d rejected — %s", count, reason)

    return valid, rejected


def _validate_venue(venue: str) -> str | None:
    """Validate venue name against known registries. Returns error or None."""
    # Exact match against known non-DeFi venues (case-insensitive)
    venue_upper = venue.upper()
    if venue_upper in _ALL_KNOWN_VENUES:
        return None

    # DeFi venues: must be PROTOCOL-CHAIN format with known prefix and chain
    prefix = venue.split("-")[0]
    if prefix in _DEFI_VENUE_PREFIXES:
        parts = venue.split("-", 1)
        if len(parts) != 2 or not parts[1]:
            return f"DeFi venue must be PROTOCOL-CHAIN format (got {venue!r})"
        chain = parts[1]
        if chain not in MAINNET_CHAIN_IDS:
            return f"unknown chain {chain!r} in DeFi venue {venue!r} (known: {sorted(MAINNET_CHAIN_IDS.keys())})"
        return None

    return f"unknown venue {venue!r} — not in CeFi, TradFi, DeFi, or sports registries"


def _validate_defi_raw_symbol(rec: InstrumentRecord, protocol: str, chain: str) -> str | None:
    """Validate raw_symbol format for DeFi instruments. Returns error or None."""
    raw = rec.raw_symbol
    if not raw:
        return None  # Empty raw_symbol validated elsewhere if needed

    # Protocols that don't use addresses as raw_symbol
    if protocol in _DEFI_NON_ADDRESS_RAW_SYMBOL:
        return None

    # Morpho and UniswapV4 use bytes32 identifiers (0x + 64 hex):
    # - Morpho: uniqueKey (market ID)
    # - UniswapV4: PoolId (keccak256 of pool params)
    if protocol in ("MORPHO", "UNISWAP_V4"):
        if not _EVM_BYTES32_RE.match(raw):
            return f"{protocol} raw_symbol must be bytes32 hex (0x + 64 hex chars), got {raw!r} (venue={rec.venue})"
        return None

    # Solana protocols: base58 address
    if chain == "SOLANA":
        if not _SOLANA_ADDRESS_RE.match(raw):
            return f"Solana raw_symbol must be base58 address (32-44 chars), got {raw!r} (venue={rec.venue})"
        return None

    # EVM protocols: 0x + 40 hex address
    if chain in _EVM_CHAINS:
        if not _EVM_ADDRESS_RE.match(raw):
            return f"EVM raw_symbol must be hex address (0x + 40 hex chars), got {raw!r} (venue={rec.venue})"
        return None

    return None


def _check_record(rec: InstrumentRecord, as_of_date: date | None = None) -> str | None:
    """Return rejection reason or None if valid."""
    # --- Venue validation ---
    venue_err = _validate_venue(rec.venue)
    if venue_err:
        return venue_err

    asset_group = _infer_asset_group(rec.venue)
    inst_type = str(rec.instrument_type)

    # --- DeFi address validation ---
    if asset_group == "DEFI":
        parts = rec.venue.split("-", 1)
        if len(parts) == 2:
            protocol, chain = parts[0], parts[1]
            addr_err = _validate_defi_raw_symbol(rec, protocol, chain)
            if addr_err:
                return addr_err

    # available_from_datetime: RECOMMENDED but not blocking.
    # Many venues (Bybit, Coinbase, OKX, Hyperliquid, DeFi) don't expose listing dates.
    # Rejecting on this would block the entire pipeline.

    # quote_asset: REQUIRED for CeFi and TradFi (not DeFi single-asset types, not sports/prediction)
    is_single_asset = inst_type in _SINGLE_ASSET_DEFI_TYPES
    if asset_group not in ("DEFI", "SPORTS") and not rec.quote_asset:
        return f"quote_asset is required for {asset_group} (venue={rec.venue}, symbol={rec.raw_symbol})"
    if asset_group == "DEFI" and not is_single_asset and not rec.quote_asset:
        # DeFi non-lending (pools, swaps) should have quote_asset
        return f"quote_asset is required for DeFi non-lending (venue={rec.venue}, type={inst_type})"

    # expiry: REQUIRED for futures and options
    if inst_type in (InstrumentType.FUTURE, InstrumentType.OPTION) and rec.expiry is None:
        return f"expiry is required for {inst_type} (venue={rec.venue}, symbol={rec.raw_symbol})"

    # expiry guard: reject instruments already expired as of the processing date
    if rec.status == InstrumentStatus.EXPIRED:
        return f"instrument is EXPIRED (venue={rec.venue}, symbol={rec.raw_symbol})"
    if as_of_date is not None and rec.expiry is not None and rec.expiry.date() < as_of_date:
        return (
            f"instrument expired before as_of_date: expiry={rec.expiry.date()} "
            f"as_of={as_of_date} (venue={rec.venue}, symbol={rec.raw_symbol})"
        )

    # strike + option_type: REQUIRED for options
    if inst_type == InstrumentType.OPTION:
        if rec.strike is None:
            return f"strike is required for options (venue={rec.venue}, symbol={rec.raw_symbol})"
        if not rec.option_type:
            return f"option_type is required for options (venue={rec.venue}, symbol={rec.raw_symbol})"

    # underlying: REQUIRED for CeFi/TradFi derivatives (not spot/index/combo, not DeFi)
    if asset_group != "DEFI" and inst_type in (InstrumentType.FUTURE, InstrumentType.OPTION) and not rec.underlying:
        return f"underlying is required for {asset_group} derivatives (venue={rec.venue}, symbol={rec.raw_symbol})"

    # TradFi session metadata: timezone and holiday_calendar REQUIRED for all TradFi
    if asset_group == "TRADFI":
        if not rec.timezone:
            return f"timezone required for TradFi (venue={rec.venue}, symbol={rec.raw_symbol})"
        if not rec.holiday_calendar:
            return f"holiday_calendar required for TradFi (venue={rec.venue}, symbol={rec.raw_symbol})"

    # TradFi equity session hours: REQUIRED for NASDAQ/NYSE on trading days
    is_equity_trading_day = rec.venue in ("NASDAQ", "NYSE") and rec.is_trading_day is True
    if is_equity_trading_day and (not rec.regular_open_utc or not rec.regular_close_utc):
        return f"regular_open/close_utc required for {rec.venue} on trading days (symbol={rec.raw_symbol})"

    # COMBO: legs must be non-empty
    if inst_type == InstrumentType.COMBO and not rec.legs:
        return f"legs required for COMBO instruments (venue={rec.venue}, symbol={rec.raw_symbol})"

    # tick_size: must be present and positive for CeFi/TradFi tradeable instruments.
    # Every CeFi/TradFi adapter sets a value — None means a bug in the adapter.
    # Exceptions: INDEX (non-tradeable pricing), COMBO (tick derived from legs),
    # and all DeFi instruments (AMM pools, lending, staking — no order book tick).
    is_tick_exempt = asset_group == "DEFI" or inst_type in (
        InstrumentType.INDEX.value,
        InstrumentType.COMBO.value,
    )
    if not is_tick_exempt and (rec.tick_size is None or rec.tick_size <= 0):
        return f"tick_size must be positive (venue={rec.venue}, symbol={rec.raw_symbol}, tick_size={rec.tick_size})"

    return None
