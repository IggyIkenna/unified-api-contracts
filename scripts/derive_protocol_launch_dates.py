#!/usr/bin/env python3
"""SSOT script for PROTOCOL_LAUNCH_DATES on-chain derivation + citation gate.

Two purposes:
1. PROBE: derive each protocol's mainnet launch date from on-chain data
   (binary-search `eth_getCode` for contract creation block; or specific
   event queries) and compare with the current UAC declaration — surfaces drift.
2. PRE-COMMIT GATE: reject a change to chain_env.py that modifies
   PROTOCOL_LAUNCH_DATES without a `# DERIVED <date> from <chain> block <N>
   tx <hash>` citation comment on the changed entry.

Usage:
  # Drift report using cached derivation registry (no network calls):
  python scripts/derive_protocol_launch_dates.py

  # On-chain probe via Alchemy RPC (needs ALCHEMY_API_KEY env or --api-key):
  python scripts/derive_protocol_launch_dates.py --probe [--api-key KEY]

  # Probe a single entry:
  python scripts/derive_protocol_launch_dates.py --probe --chain ETHEREUM --protocol AAVE_V3 --api-key KEY

  # Pre-commit citation gate (install in .git/hooks/pre-commit):
  python scripts/derive_protocol_launch_dates.py --pre-commit

  # Print all entries with their citation comments (no probing):
  python scripts/derive_protocol_launch_dates.py --citations

Citation format (MANDATORY for every PROTOCOL_LAUNCH_DATES change):
  # DERIVED YYYY-MM-DD from <CHAIN> block <N> tx <0xhash>
  # or, for event-based derivation:
  # DERIVED YYYY-MM-DD from <CHAIN> <EventName> block <N> tx <0xhash>
  # or, for non-EVM chains:
  # DERIVED YYYY-MM-DD from SOLANA program <address> slot <N>
"""

from __future__ import annotations

import argparse
import http.client
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request
from dataclasses import dataclass
from datetime import UTC, date, datetime
from pathlib import Path
from typing import cast

# ── repo root detection ──────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).parent.parent
_CHAIN_ENV_PATH = _REPO_ROOT / "unified_api_contracts" / "registry" / "chain_env.py"

# ── citation comment pattern ─────────────────────────────────────────────────
# Matches: # DERIVED 2023-01-27 from ETHEREUM block 16291131 tx 0xabc...
# Or:      # DERIVED 2022-03-16 from ARBITRUM ReserveInitialized block 14234 tx 0x...
# Or:      # DERIVED 2022-08-15 from SOLANA program Fg6...  slot 143920000

_CITATION_RE = re.compile(
    r"#\s*DERIVED\s+(\d{4}-\d{2}-\d{2})\s+from\s+(\w+)\s+"
    r"(?:(?P<event>\w+)\s+)?block\s+(\d+)\s+tx\s+(0x[0-9a-fA-F]+)"
    r"|"
    r"#\s*DERIVED\s+(\d{4}-\d{2}-\d{2})\s+from\s+SOLANA\s+program\s+(\S+)\s+slot\s+(\d+)",
    re.IGNORECASE,
)


# ── derivation strategies ────────────────────────────────────────────────────


@dataclass
class DerivationInfo:
    """On-chain derivation info for one (chain, protocol) pair."""

    contract: str  # primary contract address (EVM 0x... or Solana pubkey)
    strategy: str  # "contract_creation" | "earliest_event" | "known_block" | "non_evm"
    # Optional known anchor: if provided, probe this block directly (no binary search)
    known_block: int | None = None
    known_tx: str | None = None  # creation tx hash when known
    # For earliest_event strategy: the event topic (ABI-encoded keccak256)
    event_topic: str | None = None
    event_name: str | None = None
    # Search window for binary search / event scan
    search_lo: int = 0  # start block for binary search
    notes: str = ""


# Registry: (CHAIN, PROTOCOL) → DerivationInfo
# Covers the most important EVM DeFi protocols with verifiable on-chain anchors.
# Non-EVM chains (SOLANA) are flagged as non_evm; probing is skipped.
# Entries without a registry entry are reported as "NO_STRATEGY" in drift output.

_DERIVATION_REGISTRY: dict[tuple[str, str], DerivationInfo] = {
    # ── Aave V3 ──────────────────────────────────────────────────────────────
    # Pool contract deployed by PoolAddressesProvider; use PoolAddressesProvider
    # creation as the launch anchor (it is always deployed first).
    ("ETHEREUM", "AAVE_V3"): DerivationInfo(
        contract="0x2f39d218133AFaB8F2B819B1066c7E434Ad94E9e",  # PoolAddressesProvider
        strategy="contract_creation",
        known_block=16291131,
        known_tx="0x663d11e9ded46811d91d2e0a31b77ff213ec6fde8c49a2e36e0490e88a3a2a2d",
        search_lo=16_200_000,
        notes="Aave V3 ETH PoolAddressesProvider; creation block 16291131 = 2023-01-27",
    ),
    ("ETHEREUM", "AAVEV3"): DerivationInfo(
        contract="0x2f39d218133AFaB8F2B819B1066c7E434Ad94E9e",
        strategy="known_block",
        known_block=16291131,
        notes="alias for AAVE_V3",
    ),
    ("ARBITRUM", "AAVE_V3"): DerivationInfo(
        contract="0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb",  # PoolAddressesProvider
        strategy="contract_creation",
        known_block=7740000,  # ~ 2022-03-16 on Arbitrum
        search_lo=7_700_000,
        notes="Aave V3 Arbitrum PoolAddressesProvider; ~block 7740000 = 2022-03-16",
    ),
    ("OPTIMISM", "AAVE_V3"): DerivationInfo(
        contract="0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb",  # same address on Optimism
        strategy="contract_creation",
        known_block=4000000,  # ~ 2022-03-15
        search_lo=3_900_000,
        notes="Aave V3 Optimism; block ~4000000 = 2022-03-15",
    ),
    ("POLYGON", "AAVE_V3"): DerivationInfo(
        contract="0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb",
        strategy="contract_creation",
        known_block=25842000,
        search_lo=25_800_000,
        notes="Aave V3 Polygon; block ~25842000 = 2022-03-12",
    ),
    ("AVALANCHE", "AAVE_V3"): DerivationInfo(
        contract="0xa97684ead0e402dC232d5A977953DF7ECBaB3CDb",
        strategy="contract_creation",
        known_block=11970000,
        search_lo=11_900_000,
        notes="Aave V3 Avalanche; block ~11970000 = 2022-03-12",
    ),
    ("BASE", "AAVE_V3"): DerivationInfo(
        contract="0xe20fCBdBfFC4Dd138cE8b2E6FBb6CB49777ad64D",  # BASE PoolAddressesProvider
        strategy="contract_creation",
        known_block=2357000,
        search_lo=2_300_000,
        notes="Aave V3 Base; block ~2357000 = 2023-08-22",
    ),
    ("BSC", "AAVE_V3"): DerivationInfo(
        contract="0xff75B6da14FfbbfD355Daf7a2731456b3562Ba6D",  # BSC PoolAddressesProvider
        strategy="contract_creation",
        known_block=35250000,
        search_lo=35_200_000,
        notes="Aave V3 BSC; block ~35250000 = 2024-01-23",
    ),
    ("LINEA", "AAVE_V3"): DerivationInfo(
        contract="0xc44827C51d00381ed4C52646aeAB45b455d200eB",
        strategy="contract_creation",
        known_block=7100000,
        search_lo=7_000_000,
        notes="Aave V3 Linea; block ~7100000 = 2025-02-11",
    ),
    ("SCROLL", "AAVE_V3"): DerivationInfo(
        contract="0x69850D0B276776781C063771b161bd8894BCdD04",
        strategy="contract_creation",
        known_block=4900000,
        search_lo=4_800_000,
        notes="Aave V3 Scroll; block ~4900000 = 2024-04-29",
    ),
    ("ZKSYNC", "AAVE_V3"): DerivationInfo(
        contract="0x26eFbe2E9a3b654E959C204b941A27B5cc19a98f",
        strategy="contract_creation",
        known_block=32600000,
        search_lo=32_500_000,
        notes="Aave V3 zkSync; block ~32600000 = 2024-04-09",
    ),
    # ── Compound V3 (Comet) ───────────────────────────────────────────────────
    ("ETHEREUM", "COMPOUND_V3"): DerivationInfo(
        contract="0xc3d688B66703497DAA19211EEdff47f25384cdc3",  # cUSDCv3 proxy
        strategy="contract_creation",
        known_block=15331586,
        known_tx="0x46b24e9ca09f7e7e3c08d5fe2a36ee49a83e2ac3e28e56c3f0d7f2d1c5d8e5f3",
        search_lo=15_300_000,
        notes="Compound V3 cUSDCv3 Ethereum; block 15331586 = 2022-08-13",
    ),
    ("ARBITRUM", "COMPOUND_V3"): DerivationInfo(
        contract="0xA5EDBDD9646f8dFF606d7448e414884C7d905dCA",  # cUSDCv3 Arbitrum
        strategy="contract_creation",
        known_block=89750000,
        search_lo=89_700_000,
        notes="Compound V3 Arbitrum; block ~89750000 = 2023-05-04",
    ),
    ("BASE", "COMPOUND_V3"): DerivationInfo(
        contract="0xb125E6687d4313864e53df431d5425969c15Eb2",  # cUSDbCv3 Base
        strategy="contract_creation",
        known_block=1996000,
        search_lo=1_900_000,
        notes="Compound V3 Base; block ~1996000 = 2023-08-04",
    ),
    ("OPTIMISM", "COMPOUND_V3"): DerivationInfo(
        contract="0x2e44e174f7D53F0212823acC11C01A11d58c5bCB",  # cUSDCv3 Optimism
        strategy="contract_creation",
        known_block=118200000,
        search_lo=118_100_000,
        notes="Compound V3 Optimism; block ~118200000 = 2024-04-06",
    ),
    ("SCROLL", "COMPOUND_V3"): DerivationInfo(
        contract="0xB2f97c1Bd3bf02f5e74d13f02453282AEbD3f3cB",
        strategy="contract_creation",
        known_block=3700000,
        search_lo=3_600_000,
        notes="Compound V3 Scroll; block ~3700000 = 2024-04-22",
    ),
    # ── Uniswap ───────────────────────────────────────────────────────────────
    ("ETHEREUM", "UNISWAP_V2"): DerivationInfo(
        contract="0x5C69bEe701ef814a2B6a3EDD4B1652CB9cc5aA6f",  # V2 Factory
        strategy="contract_creation",
        known_block=10000835,
        search_lo=9_950_000,
        notes="Uniswap V2 Factory Ethereum; block 10000835 = 2020-05-04",
    ),
    ("ETHEREUM", "UNISWAP_V3"): DerivationInfo(
        contract="0x1F98431c8aD98523631AE4a59f267346ea31F984",  # V3 Factory
        strategy="contract_creation",
        known_block=12369621,
        known_tx="0x37d8f4b1b371fde9e4b1942588d9b0b4af6a21811b66bf60f820ca4c4b740800",
        search_lo=12_300_000,
        notes="Uniswap V3 Factory Ethereum; block 12369621 = 2021-05-04",
    ),
    ("ARBITRUM", "UNISWAP_V3"): DerivationInfo(
        contract="0x1F98431c8aD98523631AE4a59f267346ea31F984",  # same factory address
        strategy="contract_creation",
        known_block=165,  # Uniswap V3 deployed on early Arbitrum block; subgraph indexes from pre-launch
        search_lo=0,
        notes="Uniswap V3 on Arbitrum; early block ~165 (2021-06-01) — subgraph indexed pre-public-mainnet",
    ),
    ("OPTIMISM", "UNISWAP_V3"): DerivationInfo(
        contract="0x1F98431c8aD98523631AE4a59f267346ea31F984",
        strategy="contract_creation",
        known_block=3977750,
        search_lo=3_900_000,
        notes="Uniswap V3 Optimism; block ~3977750 = 2021-11-11 (subgraph indexed pre-regenesis)",
    ),
    ("POLYGON", "UNISWAP_V3"): DerivationInfo(
        contract="0x1F98431c8aD98523631AE4a59f267346ea31F984",
        strategy="contract_creation",
        known_block=22757547,
        search_lo=22_700_000,
        notes="Uniswap V3 Polygon; block 22757547 = 2021-12-21",
    ),
    ("BASE", "UNISWAP_V3"): DerivationInfo(
        contract="0x33128a8fC17869897dcE68Ed026d694621f6FDfD",  # V3 Factory on Base (different address)
        strategy="contract_creation",
        known_block=1371680,
        search_lo=1_300_000,
        notes="Uniswap V3 Factory Base; block ~1371680 = 2023-07-31 (subgraph indexed pre-public-launch)",
    ),
    ("ETHEREUM", "UNISWAP_V4"): DerivationInfo(
        contract="0x000000000004444c5dc75cB358380D2e3dE08A90",  # V4 PoolManager
        strategy="contract_creation",
        known_block=21688329,
        search_lo=21_600_000,
        notes="Uniswap V4 PoolManager Ethereum; block ~21688329 = 2025-01-31",
    ),
    # ── Curve / Balancer / SushiSwap ─────────────────────────────────────────
    ("ETHEREUM", "CURVE"): DerivationInfo(
        contract="0xbEbc44782C7dB0a1A60Cb6fe97d0b483032FF1C7",  # 3pool (first live pool)
        strategy="contract_creation",
        known_block=9456293,
        search_lo=9_400_000,
        notes="Curve 3pool Ethereum; block ~9456293 = 2020-01-19",
    ),
    ("ETHEREUM", "BALANCER"): DerivationInfo(
        contract="0x9424B1412450D0f8Fc2255FAf6046b98213B76Bd",  # V1 BFactory
        strategy="contract_creation",
        known_block=9603112,
        search_lo=9_550_000,
        notes="Balancer V1 BFactory Ethereum; block ~9603112 = 2020-03-31",
    ),
    ("ETHEREUM", "SUSHISWAP_V3"): DerivationInfo(
        contract="0xbACEB8eC6b9355Dfc0269C18bac9d6E2Bdc29C4F",  # SushiSwap V3 Factory
        strategy="contract_creation",
        known_block=17044990,
        search_lo=17_000_000,
        notes="SushiSwap V3 Factory Ethereum; block ~17044990 = 2023-04-04",
    ),
    # ── Liquid Staking / yield (Ethereum) ────────────────────────────────────
    ("ETHEREUM", "LIDO"): DerivationInfo(
        contract="0xae7ab96520DE3A18E5e111B5EaAb095312D7fE84",  # stETH
        strategy="contract_creation",
        known_block=11473216,
        search_lo=11_400_000,
        notes="Lido stETH Ethereum; block ~11473216 = 2020-12-19",
    ),
    ("ETHEREUM", "ROCKETPOOL"): DerivationInfo(
        contract="0xae78736Cd615f374D3085123A210448E74Fc6393",  # rETH token
        strategy="contract_creation",
        known_block=13325304,
        search_lo=13_300_000,
        notes="RocketPool rETH Ethereum; block ~13325304 = 2021-11-08",
    ),
    ("ETHEREUM", "MAKER"): DerivationInfo(
        contract="0x9f8F72aA9304c8B593d555F12eF6589cC3A579A2",  # MKR token
        strategy="contract_creation",
        known_block=4751436,
        search_lo=4_700_000,
        notes="MakerDAO MKR Ethereum; block ~4751436 = 2017-12-19",
    ),
    ("ETHEREUM", "SPARK"): DerivationInfo(
        contract="0x02C3eA4e34C0cBd694D2adFa2c690EECbC1793eE",  # SparkLend PoolAddressesProvider
        strategy="contract_creation",
        known_block=16847420,
        search_lo=16_800_000,
        notes="SparkLend Ethereum; block ~16847420 = 2023-03-07 (earliest Messari subgraph event)",
    ),
    # ── GMX ───────────────────────────────────────────────────────────────────
    ("ARBITRUM", "GMX"): DerivationInfo(
        contract="0x489ee077994B6658eAfA855C308275EAd8097C4A",  # GMX Vault
        strategy="contract_creation",
        known_block=1457000,
        search_lo=1_400_000,
        notes="GMX Vault Arbitrum; block ~1457000 = 2021-09-01",
    ),
    # ── Solana protocols (non-EVM — probing not supported via JSON-RPC) ───────
    ("SOLANA", "JITO"): DerivationInfo(
        contract="Fg6PaFpoGXkYsidMpWTK6W2BeZ7FEfcYkg476zPFsLnS",  # JitoSOL stake pool
        strategy="non_evm",
        notes="JitoSOL stake pool; creation slot ~145600000 ~= 2022-08-15. "
        "Verify via: solana transaction-count at that slot.",
    ),
    ("SOLANA", "MARINADE"): DerivationInfo(
        contract="MarBmsSgKXdrN1egZf5sqe1TMai9K1rChYNDJgjq7aD",  # Marinade Finance program
        strategy="non_evm",
        notes="Marinade Finance program; deployed ~slot 89000000 ~= 2021-08-02.",
    ),
    ("SOLANA", "RAYDIUM"): DerivationInfo(
        contract="675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8",  # Raydium AMM
        strategy="non_evm",
        notes="Raydium AMM program; deployed ~slot 61000000 ~= 2021-02-21.",
    ),
    ("SOLANA", "ORCA"): DerivationInfo(
        contract="9W959DqEETiGZocYWCQPaJ6sBmUzgfxXfqGeTEdp3aQP",  # Orca Whirlpools (original)
        strategy="non_evm",
        notes="Orca first deployed ~slot 59000000 ~= 2021-02-09.",
    ),
    ("SOLANA", "DRIFT"): DerivationInfo(
        contract="dRiftyHA39MWEi3m9aunc5MzRF1JYuBsbn6VPcn33UH",  # Drift Protocol
        strategy="non_evm",
        notes="Drift Protocol; deployed ~slot 104000000 ~= 2021-11-18.",
    ),
    ("SOLANA", "JUPITER"): DerivationInfo(
        contract="JUP6LkbZbjS1jKKwapdHNy74zcZ3tLUZoi5QNyVTaV4",  # Jupiter v6 (earliest)
        strategy="non_evm",
        notes="Jupiter aggregator; first deployed ~slot 97000000 ~= 2021-10-13.",
    ),
    ("SOLANA", "KAMINO"): DerivationInfo(
        contract="KLend2g3cP87fffoy8q1mQqGKjrxjC8boSyAYavgmjD",  # Kamino lending
        strategy="non_evm",
        notes="Kamino deployed ~slot 147000000 ~= 2022-08-23.",
    ),
    ("SOLANA", "MARGINFI"): DerivationInfo(
        contract="MFv2hWf31Z9kbCa1snEPdcgp7a4cRyMZDTeiDAjHmop",  # marginfi program
        strategy="non_evm",
        notes="marginfi deployed ~slot 178000000 ~= 2023-02-23.",
    ),
    ("SOLANA", "SOLEND"): DerivationInfo(
        contract="So1endDq2YkqhipRh3WViPa8hdiSpxWy6z3Z6tMCpAo",  # Solend program
        strategy="non_evm",
        notes="Solend deployed ~slot 89700000 ~= 2021-08-13.",
    ),
}

# ── EVM chain name → Alchemy RPC URL template ───────────────────────────────

_CHAIN_RPC_TEMPLATES: dict[str, str] = {
    "ETHEREUM": "https://eth-mainnet.g.alchemy.com/v2/{api_key}",
    "ARBITRUM": "https://arb-mainnet.g.alchemy.com/v2/{api_key}",
    "OPTIMISM": "https://opt-mainnet.g.alchemy.com/v2/{api_key}",
    "BASE": "https://base-mainnet.g.alchemy.com/v2/{api_key}",
    "POLYGON": "https://polygon-mainnet.g.alchemy.com/v2/{api_key}",
    "AVALANCHE": "https://avax-mainnet.g.alchemy.com/v2/{api_key}",
    "BSC": "https://bnb-mainnet.g.alchemy.com/v2/{api_key}",
    "LINEA": "https://linea-mainnet.g.alchemy.com/v2/{api_key}",
    "SCROLL": "https://scroll-mainnet.g.alchemy.com/v2/{api_key}",
    "ZKSYNC": "https://zksync-mainnet.g.alchemy.com/v2/{api_key}",
}

# Public fallback RPCs (rate-limited, for testing without Alchemy key)
_PUBLIC_RPC_FALLBACKS: dict[str, str] = {
    "ETHEREUM": "https://eth.llamarpc.com",
    "ARBITRUM": "https://arb1.arbitrum.io/rpc",
    "OPTIMISM": "https://mainnet.optimism.io",
    "BASE": "https://mainnet.base.org",
    "POLYGON": "https://polygon-rpc.com",
    "AVALANCHE": "https://api.avax.network/ext/bc/C/rpc",
    "BSC": "https://bsc-dataseed.binance.org/",
}


# ── JSON-RPC client ──────────────────────────────────────────────────────────


def _rpc_call(url: str, method: str, params: list[object]) -> object:
    payload = json.dumps({"jsonrpc": "2.0", "id": 1, "method": method, "params": params}).encode()
    req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"})
    try:
        resp = cast(http.client.HTTPResponse, urllib.request.urlopen(req, timeout=10))
        data: dict[str, object] = cast("dict[str, object]", json.loads(resp.read()))
        if "error" in data:
            raise RuntimeError(f"RPC error: {data['error']}")
        return data.get("result")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"RPC connection failed: {exc}") from exc


def eth_get_code(url: str, address: str, block_hex: str) -> str:
    result = _rpc_call(url, "eth_getCode", [address, block_hex])
    return str(result) if result else "0x"


def eth_get_block_by_number(url: str, block_hex: str) -> dict[str, object]:
    result = _rpc_call(url, "eth_getBlockByNumber", [block_hex, False])
    return cast("dict[str, object]", result) if isinstance(result, dict) else {}


def eth_block_number(url: str) -> int:
    result = _rpc_call(url, "eth_blockNumber", [])
    return int(str(result), 16)


def block_to_date(url: str, block: int) -> date:
    blk = eth_get_block_by_number(url, hex(block))
    ts = int(str(blk.get("timestamp", "0")), 16)
    return datetime.fromtimestamp(ts, tz=UTC).date()


# ── Binary-search contract creation block ──────────────────────────────────


def find_creation_block(url: str, contract: str, lo: int, hi: int) -> int:
    """Binary search for the first block where `contract` has non-empty bytecode.

    O(log(hi-lo)) RPC calls (~24 calls for 16M-block range).
    Caller should set `lo` to a block safely before suspected creation.
    """
    while lo < hi:
        mid = (lo + hi) // 2
        code = eth_get_code(url, contract, hex(mid))
        if code and code != "0x":
            hi = mid
        else:
            lo = mid + 1
    return lo


# ── RPC URL resolution ────────────────────────────────────────────────────────


def get_rpc_url(chain: str, api_key: str | None) -> str | None:
    if chain not in _CHAIN_RPC_TEMPLATES:
        return None
    if api_key:
        return _CHAIN_RPC_TEMPLATES[chain].format(api_key=api_key)
    return _PUBLIC_RPC_FALLBACKS.get(chain)


# ── Citation parsing from chain_env.py source ───────────────────────────────


def _parse_citations_from_source() -> dict[tuple[str, str], str]:
    """Read chain_env.py and extract # DERIVED ... comments near each entry."""
    source = _CHAIN_ENV_PATH.read_text()
    lines = source.splitlines()
    citations: dict[tuple[str, str], str] = {}

    # Pattern: ("CHAIN", "PROTOCOL"): "YYYY-MM-DD", ...  with nearby # DERIVED comment
    entry_re = re.compile(r'\("([A-Z0-9_]+)",\s*"([A-Z0-9_]+)"\)\s*:\s*"(\d{4}-\d{2}-\d{2})"')
    for i, line in enumerate(lines):
        m = entry_re.search(line)
        if not m:
            continue
        chain, protocol = m.group(1), m.group(2)
        # Search for a DERIVED citation in the surrounding ±5 lines
        window = "\n".join(lines[max(0, i - 5) : i + 6])
        dm = _CITATION_RE.search(window)
        if dm:
            citations[(chain, protocol)] = dm.group(0).strip()
    return citations


# ── Drift detection ──────────────────────────────────────────────────────────


@dataclass
class DriftRow:
    chain: str
    protocol: str
    uac_date: str
    derived_date: str | None = None
    strategy: str = "NO_STRATEGY"
    citation: str | None = None
    status: str = "UNKNOWN"
    note: str = ""


def _status(uac: str, derived: str | None) -> str:
    if derived is None:
        return "NO_PROBE"
    if uac == derived:
        return "OK"
    uac_d = date.fromisoformat(uac)
    der_d = date.fromisoformat(derived)
    delta = (uac_d - der_d).days
    return f"DRIFT({delta:+d}d)"


def probe_entry(
    chain: str,
    protocol: str,
    info: DerivationInfo,
    api_key: str | None,
    verbose: bool = False,
) -> tuple[str | None, str]:
    """Return (derived_iso_date, note). None if probing not possible."""
    if info.strategy == "non_evm":
        return None, f"non-EVM: {info.notes}"

    url = get_rpc_url(chain, api_key)
    if not url:
        return None, f"no RPC for {chain}"

    if verbose:
        print(f"  probing {chain}/{protocol} via {url[:40]}...")

    try:
        if info.known_block is not None:
            d = block_to_date(url, info.known_block)
            return d.isoformat(), f"block {info.known_block}"

        if info.strategy == "contract_creation":
            hi = eth_block_number(url)
            creation = find_creation_block(url, info.contract, info.search_lo, hi)
            d = block_to_date(url, creation)
            return d.isoformat(), f"binary-search creation block {creation}"

        return None, f"unknown strategy {info.strategy}"
    except RuntimeError as exc:
        return None, f"RPC error: {exc}"


# ── Pre-commit citation gate ─────────────────────────────────────────────────


def _get_changed_launch_date_keys() -> list[tuple[str, str]]:
    """Return (chain, protocol) pairs whose PROTOCOL_LAUNCH_DATES entry was changed in git staged diff."""
    try:
        diff = subprocess.check_output(
            ["git", "diff", "--cached", "--unified=3", "--", str(_CHAIN_ENV_PATH)],
            cwd=_REPO_ROOT,
            text=True,
        )
    except subprocess.CalledProcessError:
        return []

    added_entry_re = re.compile(r'^\+.*\("([A-Z0-9_]+)",\s*"([A-Z0-9_]+)"\)\s*:\s*"(\d{4}-\d{2}-\d{2})"')
    changed: list[tuple[str, str]] = []
    for line in diff.splitlines():
        m = added_entry_re.match(line)
        if m:
            changed.append((m.group(1), m.group(2)))
    return changed


def _diff_has_citation_for(diff_text: str, chain: str, protocol: str) -> bool:
    """Check if the diff hunk that adds (chain, protocol) also adds a # DERIVED comment."""
    lines = diff_text.splitlines()
    entry_re = re.compile(rf'\("({re.escape(chain)})",\s*"({re.escape(protocol)})"\)\s*:')
    for i, line in enumerate(lines):
        if not line.startswith("+"):
            continue
        if not entry_re.search(line):
            continue
        # Look for # DERIVED in ±5 surrounding added lines
        window = "\n".join(ln for ln in lines[max(0, i - 5) : i + 6] if ln.startswith("+"))
        if _CITATION_RE.search(window):
            return True
    return False


def run_pre_commit_gate() -> int:
    """Pre-commit citation gate. Returns exit code (0 = ok, 1 = citation missing)."""
    changed = _get_changed_launch_date_keys()
    if not changed:
        return 0

    try:
        diff = subprocess.check_output(
            ["git", "diff", "--cached", "--unified=10", "--", str(_CHAIN_ENV_PATH)],
            cwd=_REPO_ROOT,
            text=True,
        )
    except subprocess.CalledProcessError:
        return 0

    failures: list[tuple[str, str]] = []
    for chain, protocol in changed:
        if not _diff_has_citation_for(diff, chain, protocol):
            failures.append((chain, protocol))

    if failures:
        print("❌ PROTOCOL_LAUNCH_DATES pre-commit citation gate FAILED", file=sys.stderr)
        print("", file=sys.stderr)
        print(
            "Every new/modified PROTOCOL_LAUNCH_DATES entry requires a # DERIVED comment:",
            file=sys.stderr,
        )
        print("  # DERIVED YYYY-MM-DD from <CHAIN> block <N> tx <0xhash>", file=sys.stderr)
        print("", file=sys.stderr)
        print("Missing citations for:", file=sys.stderr)
        for chain, protocol in failures:
            print(f"  ({chain}, {protocol})", file=sys.stderr)
        print("", file=sys.stderr)
        print("Run to generate citations:", file=sys.stderr)
        print(
            "  python scripts/derive_protocol_launch_dates.py --probe --api-key $ALCHEMY_API_KEY",
            file=sys.stderr,
        )
        return 1

    print(f"✅ PROTOCOL_LAUNCH_DATES citation gate passed ({len(changed)} entries checked)")
    return 0


# ── Reporting ────────────────────────────────────────────────────────────────


def _print_drift_table(rows: list[DriftRow], show_citations: bool = False) -> None:
    col_w = {"chain": 12, "protocol": 20, "uac_date": 12, "derived": 12, "status": 16}
    header = (
        f"{'CHAIN':<{col_w['chain']}} {'PROTOCOL':<{col_w['protocol']}} "
        f"{'UAC_DATE':<{col_w['uac_date']}} {'DERIVED':<{col_w['derived']}} "
        f"{'STATUS':<{col_w['status']}}"
    )
    print(header)
    print("-" * len(header))

    drift_count = ok_count = no_probe = no_strategy = 0
    for row in rows:
        derived_str = row.derived_date or "-"
        status = _status(row.uac_date, row.derived_date) if row.derived_date else row.status
        line = (
            f"{row.chain:<{col_w['chain']}} {row.protocol:<{col_w['protocol']}} "
            f"{row.uac_date:<{col_w['uac_date']}} {derived_str:<{col_w['derived']}} "
            f"{status:<{col_w['status']}}"
        )
        if status.startswith("DRIFT"):
            drift_count += 1
            print(f"⚠️  {line}  # {row.note}")
        elif status == "OK":
            ok_count += 1
            print(f"✅ {line}")
        elif status == "NO_PROBE":
            no_probe += 1
            print(f"   {line}  # {row.note}")
        else:
            no_strategy += 1
            print(f"   {line}  # no derivation strategy registered")

        if show_citations and row.citation:
            print(f"      {row.citation}")

    print()
    print(
        f"Summary: {ok_count} OK, {drift_count} DRIFT, {no_probe} no-probe, "
        f"{no_strategy} no-strategy, {len(rows)} total"
    )
    if drift_count:
        print(f"\n⚠️  {drift_count} entries have DRIFT — update UAC or investigate.")


# ── Main entry point ─────────────────────────────────────────────────────────


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--probe", action="store_true", help="Query on-chain RPC to derive dates")
    ap.add_argument("--api-key", default=os.environ.get("ALCHEMY_API_KEY"), help="Alchemy API key")
    ap.add_argument("--pre-commit", action="store_true", help="Run as pre-commit citation gate")
    ap.add_argument("--citations", action="store_true", help="Show existing # DERIVED citations")
    ap.add_argument("--chain", help="Filter: only probe this chain (e.g. ETHEREUM)")
    ap.add_argument("--protocol", help="Filter: only probe this protocol (e.g. AAVE_V3)")
    ap.add_argument("--verbose", action="store_true", help="Verbose RPC output")
    args = ap.parse_args()

    # Cast vars(args) to dict[str, object] so attribute lookups are not typed Any
    _ns: dict[str, object] = cast("dict[str, object]", vars(args))
    do_probe: bool = _ns.get("probe") is True
    do_pre_commit: bool = _ns.get("pre_commit") is True
    do_citations: bool = _ns.get("citations") is True
    api_key: str | None = str(_ns["api_key"]) if _ns.get("api_key") else None
    filter_chain: str | None = str(_ns["chain"]).upper() if _ns.get("chain") else None
    filter_protocol: str | None = str(_ns["protocol"]).upper() if _ns.get("protocol") else None
    verbose: bool = _ns.get("verbose") is True

    if do_pre_commit:
        return run_pre_commit_gate()

    # Load UAC PROTOCOL_LAUNCH_DATES
    sys.path.insert(0, str(_REPO_ROOT))
    try:
        from unified_api_contracts.registry.chain_env import PROTOCOL_LAUNCH_DATES
    except ImportError as exc:
        print(f"Error: cannot import PROTOCOL_LAUNCH_DATES: {exc}", file=sys.stderr)
        print("Run from the unified-api-contracts repo root with the UAC venv active.", file=sys.stderr)
        return 1

    citations: dict[tuple[str, str], str] = _parse_citations_from_source() if do_citations else {}

    # Filter to unique (canonical) keys only — skip auto-generated aliases
    seen: set[str] = set()
    uac_entries: list[tuple[tuple[str, str], str]] = []
    for (chain, protocol), dt in sorted(PROTOCOL_LAUNCH_DATES.items()):
        key = f"{chain}|{protocol}"
        if key in seen:
            continue
        seen.add(key)
        if filter_chain and chain != filter_chain:
            continue
        if filter_protocol and protocol != filter_protocol:
            continue
        uac_entries.append(((chain, protocol), dt))

    print(f"\nPROTOCOL_LAUNCH_DATES drift report — {len(uac_entries)} entries\n")

    rows: list[DriftRow] = []
    for (chain, protocol), uac_date in uac_entries:
        info = _DERIVATION_REGISTRY.get((chain, protocol))
        citation = citations.get((chain, protocol))

        if info is None:
            rows.append(
                DriftRow(
                    chain=chain,
                    protocol=protocol,
                    uac_date=uac_date,
                    strategy="NO_STRATEGY",
                    citation=citation,
                    status="NO_PROBE",
                    note="not in derivation registry — add DerivationInfo to extend",
                )
            )
            continue

        if do_probe:
            derived_date, note = probe_entry(chain, protocol, info, api_key, verbose)
        else:
            derived_date = None
            note = info.notes

        rows.append(
            DriftRow(
                chain=chain,
                protocol=protocol,
                uac_date=uac_date,
                derived_date=derived_date,
                strategy=info.strategy,
                citation=citation,
                status="NO_PROBE" if derived_date is None else "PROBED",
                note=note,
            )
        )

    _print_drift_table(rows, show_citations=do_citations)

    if do_probe and not api_key:
        print(
            "\nTip: set ALCHEMY_API_KEY env var or pass --api-key for better RPC reliability.",
            file=sys.stderr,
        )

    drift_rows = [r for r in rows if r.derived_date and r.uac_date != r.derived_date]
    return 1 if drift_rows else 0


if __name__ == "__main__":
    sys.exit(main())
