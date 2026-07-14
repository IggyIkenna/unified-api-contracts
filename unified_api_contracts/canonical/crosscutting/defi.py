"""DeFi crosscutting protocol and chain enums — shared across MTDS, strategy, execution, risk.

These enums identify DeFi lending protocols and chain identifiers used across
the DeFi pipeline (MTDS adapters, strategy-service archetype configs, execution-service
connectors, strategy-service/risk HF calculations).

They live here (not in a service-specific module) because the same enum values
flow through UAC archetype config, strategy-service factory, execution-service
orchestrator, strategy-service/risk HF calculation, and MTDS lending-rate
adapter keys — four services, one source of truth.

Plans:
- ``plans/active/defi_recursive_borrow_archetypes_2026_05_10.md`` Phase 2
  (UAC config schema extension — LendingProtocol)
- ``plans/active/defi_master.md`` § "Chain coverage + CLOB-on-chain"
  Phase 1 (ChainKind + CHAIN_BRIDGE_GRAPH)
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum


class ChainKind(StrEnum):
    """Canonical chain identifier for strategy archetype configs.

    Used by:

    * Strategy-service archetype configs — ``allowed_chains: list[ChainKind]``
      field gates which chains the archetype is permitted to execute on.
    * Execution-service — connector routing per chain.
    * MTDS adapters — per-chain adapter dispatch keys.

    Covers both EVM chains (where ``CHAIN_CONFIGS`` provides per-chain
    operational settings keyed by EVM chain ID) and non-EVM chains (Solana,
    Hyperliquid L1, Starknet) which have separate RPC template dicts.

    String values are lowercase; canonical string names match the UPPERCASE
    keys in ``CHAIN_GENESIS_DATES`` (lowercased).  E.g.
    ``ChainKind.ARBITRUM == "arbitrum"`` and
    ``CHAIN_GENESIS_DATES["ARBITRUM"] == "2021-08-31"``.
    """

    # ── Tier 1: Core ETH + major L2s ─────────────────────────────────────
    ETHEREUM = "ethereum"
    """Ethereum mainnet (chain ID 1). Primary DeFi chain."""
    ARBITRUM = "arbitrum"
    """Arbitrum One (chain ID 42161). Primary low-gas L2 for DeFi."""
    BASE = "base"
    """Base mainnet (chain ID 8453). Coinbase-backed OP-stack L2."""
    OPTIMISM = "optimism"
    """Optimism mainnet (chain ID 10)."""
    POLYGON = "polygon"
    """Polygon PoS mainnet (chain ID 137)."""
    AVALANCHE = "avalanche"
    """Avalanche C-Chain (chain ID 43114)."""

    # ── Tier 2: Major non-ETH EVM chains ─────────────────────────────────
    BSC = "bsc"
    """Binance Smart Chain / BNB Chain (chain ID 56)."""
    GNOSIS = "gnosis"
    """Gnosis Chain / xDai (chain ID 100)."""

    # ── Tier 3: ETH-native L2s + zkEVMs ──────────────────────────────────
    LINEA = "linea"
    """Linea mainnet (chain ID 59144)."""
    SCROLL = "scroll"
    """Scroll mainnet (chain ID 534352)."""
    ZKSYNC = "zksync"
    """zkSync Era mainnet (chain ID 324)."""
    BLAST = "blast"
    """Blast mainnet (chain ID 81457)."""
    MODE = "mode"
    """Mode mainnet (chain ID 34443)."""

    # ── Tier 4: Alt-L1s ───────────────────────────────────────────────────
    CELO = "celo"
    """Celo mainnet."""
    AURORA = "aurora"
    """Aurora (NEAR-based EVM) mainnet."""
    FANTOM = "fantom"
    """Fantom Opera mainnet."""
    MANTLE = "mantle"
    """Mantle mainnet."""
    METIS = "metis"
    """Metis Andromeda mainnet."""
    MOONBEAM = "moonbeam"
    """Moonbeam (Polkadot-based EVM) mainnet."""

    # ── Non-EVM chains ────────────────────────────────────────────────────
    SOLANA = "solana"
    """Solana mainnet. Primary Solana DeFi chain (Jito/Marinade/Orca/Raydium)."""
    BITCOIN = "bitcoin"
    """Bitcoin mainnet. Wrapped BTC on EVM chains (WBTC, cbBTC, tBTC)."""
    STARKNET = "starknet"
    """Starknet mainnet. ZK-rollup L2 on Ethereum; Extended DEX-perp venue.
    RPC: ``STARKNET_RPC_TEMPLATES``. Bridge: STARKNET ↔ ETHEREUM via STARK proof."""
    HYPERLIQUID_L1 = "hyperliquid_l1"
    """Hyperliquid L1 native chain. CLOB-on-chain perp venue (Lighter/Pacifica sibling).
    RPC: ``HYPERLIQUID_RPC_TEMPLATES``. Bridge: HYPERLIQUID_L1 ↔ ARBITRUM via native bridge.

    **Wire/storage chain= segment is ``HYPERLIQUID``, NOT ``HYPERLIQUID_L1``**
    (operator-locked 2026-06-01 DeFi canonical naming SSOT). The enum member
    name / ``.value`` are kept (``HYPERLIQUID_L1`` / ``hyperliquid_l1``) so the
    existing ``CHAIN_GENESIS_DATES`` / ``MAINNET_CHAIN_IDS`` / ``VENUE_CHAIN_MAP``
    / ``CHAIN_BRIDGE_GRAPH`` keys keep working; the canonical ``chain=`` path
    segment + ``chain`` column value resolve via
    :func:`to_canonical_chain_wire` → ``HYPERLIQUID``. SSOT:
    ``codex/02-data/defi-canonical-naming-ssot.md``."""


# ---------------------------------------------------------------------------
# Canonical chain= wire/storage segment values (operator-locked 2026-06-01).
#
# The on-disk ``chain=`` partition segment + the ``chain`` column value are
# UPPERCASE (``ETHEREUM`` / ``ARBITRUM`` / ``SOLANA`` / ...), matching the enum
# *member name* — EXCEPT Hyperliquid, whose canonical wire value is
# ``HYPERLIQUID`` (not the member name ``HYPERLIQUID_L1``), matching the live
# perp handler ``chain=HYPERLIQUID``. This map holds only the overrides where
# the wire value differs from ``ChainKind.<MEMBER>.name``; everything else
# resolves to the member name. SSOT: ``codex/02-data/defi-canonical-naming-ssot.md``.
# ---------------------------------------------------------------------------
CHAIN_WIRE_VALUE_OVERRIDES: dict[ChainKind, str] = {
    ChainKind.HYPERLIQUID_L1: "HYPERLIQUID",
}


def to_canonical_chain_wire(chain: ChainKind | str) -> str:
    """Resolve a chain to its canonical UPPERCASE ``chain=`` wire/storage value.

    The canonical wire value is the enum member name uppercased
    (``ChainKind.ETHEREUM`` → ``"ETHEREUM"``), with the Hyperliquid override
    ``ChainKind.HYPERLIQUID_L1`` → ``"HYPERLIQUID"`` (operator-locked
    2026-06-01). Accepts either a :class:`ChainKind` member or a raw string
    (the enum ``.value`` like ``"hyperliquid_l1"``, the member name like
    ``"HYPERLIQUID_L1"``, or an already-canonical wire value like
    ``"HYPERLIQUID"`` / ``"ETHEREUM"``).

    Examples:
        >>> to_canonical_chain_wire(ChainKind.HYPERLIQUID_L1)
        'HYPERLIQUID'
        >>> to_canonical_chain_wire("hyperliquid_l1")
        'HYPERLIQUID'
        >>> to_canonical_chain_wire("HYPERLIQUID")
        'HYPERLIQUID'
        >>> to_canonical_chain_wire(ChainKind.ARBITRUM)
        'ARBITRUM'
    """
    if isinstance(chain, ChainKind):
        member = chain
    else:
        # Try value first (``"hyperliquid_l1"``), then member name
        # (``"HYPERLIQUID_L1"`` / ``"HYPERLIQUID"`` / ``"ETHEREUM"``).
        try:
            member = ChainKind(chain.lower())
        except ValueError:
            try:
                member = ChainKind[chain.upper()]
            except KeyError:
                # Already a canonical wire value not equal to a member name
                # (e.g. ``"HYPERLIQUID"``) — pass through uppercased.
                return chain.upper()
    return CHAIN_WIRE_VALUE_OVERRIDES.get(member, member.name)


# ---------------------------------------------------------------------------
# Chain bridge graph — which chains can transfer assets to which
#
# This is the *direct* (1-hop) bridge graph: ``CHAIN_BRIDGE_GRAPH[A]`` lists
# chains directly bridgeable from A.  Multi-hop paths (A → B → C) are not
# enumerated here.
#
# Sources:
# - Hyperliquid L1 ↔ Arbitrum: Hyperliquid native bridge (USDC-based)
# - Starknet ↔ Ethereum: StarkGate (STARK proof bridge, ~8h withdrawal delay)
#
# Extended with all EVM L2 ↔ Ethereum bridges (used by transfer-rebalance
# service to enumerate valid rebalance paths).
#
# Plan: defi_master.md § "Chain coverage + CLOB-on-chain" Phase 1.
# ---------------------------------------------------------------------------
CHAIN_BRIDGE_GRAPH: dict[str, list[str]] = {
    # New non-EVM chain bridges (2026-05-18)
    ChainKind.HYPERLIQUID_L1: [ChainKind.ARBITRUM],
    ChainKind.STARKNET: [ChainKind.ETHEREUM],
    # EVM L2 ↔ Ethereum bridges (symmetric — added for completeness)
    ChainKind.ARBITRUM: [ChainKind.ETHEREUM, ChainKind.HYPERLIQUID_L1],
    ChainKind.BASE: [ChainKind.ETHEREUM],
    ChainKind.OPTIMISM: [ChainKind.ETHEREUM],
    ChainKind.LINEA: [ChainKind.ETHEREUM],
    ChainKind.SCROLL: [ChainKind.ETHEREUM],
    ChainKind.ZKSYNC: [ChainKind.ETHEREUM],
    ChainKind.BLAST: [ChainKind.ETHEREUM],
    ChainKind.MODE: [ChainKind.ETHEREUM],
    ChainKind.ETHEREUM: [
        ChainKind.ARBITRUM,
        ChainKind.BASE,
        ChainKind.OPTIMISM,
        ChainKind.LINEA,
        ChainKind.SCROLL,
        ChainKind.ZKSYNC,
        ChainKind.BLAST,
        ChainKind.MODE,
        ChainKind.STARKNET,
    ],
}


class LendingProtocol(StrEnum):
    """Canonical DeFi lending protocol identifier.

    Used by:

    * :mod:`unified_api_contracts.internal.architecture_v2.archetype_config` —
      ``lending_protocol`` field on :class:`~archetype_config.ArchetypeConfig`
      to declare which protocol the recursive-borrow strategy targets.
    * MTDS lending-rate adapters — ``aave_v3_lending_rates.py`` /
      ``compound_v3_lending_rates.py`` / etc. as their canonical protocol key.
    * Strategy-service factory — to route lending-leg execution to the
      correct on-chain integration.
    * Risk-and-exposure-service — to look up
      ``defi_reserve_params.get_reserve_params(asset, protocol=...)`` for HF
      calculation.

    Members ``SPARK``, ``MORPHO_BLUE``, and ``MAKER_DSR`` are included for
    completeness; they are P1/P2 for May-23 (AAVE_V3 + COMPOUND_V3 are P0).
    """

    AAVE_V3 = "aave_v3"
    """Aave V3 (multi-chain: Ethereum, Arbitrum, Base, Optimism, Polygon, …)."""

    COMPOUND_V3 = "compound_v3"
    """Compound V3 / Comet (multi-chain: Ethereum, Arbitrum, Base, Polygon)."""

    SPARK = "spark"
    """Spark Protocol (Aave V3 fork on Ethereum, operated by MakerDAO/Sky)."""

    MORPHO_BLUE = "morpho_blue"
    """Morpho Blue — isolated per-market lending with configurable LLTV."""

    MAKER_DSR = "maker_dsr"
    """MakerDAO DAI Savings Rate — single yield stream, no borrow leg."""


# ───────────────────────────────────────────────────────────────────────────
# DUAL-FORM DeFi POOL IDENTITY — canonical (manifest) ↔ glued-pair (UI)
# (defi_instrument_catalogue_and_capture_pipeline_2026_06_23, operator Refinement 1)
# ───────────────────────────────────────────────────────────────────────────
#
# Every DEX pool carries TWO ids + a bidirectional converter, so the manifest
# keys on the machine-canonical form while the UI renders the human-readable
# form — both live in instruments-service (which holds the address↔tokens↔fee
# mapping), and both ride alongside on every catalogue row.
#
#   * CANONICAL (manifest / capture shard atom):
#       venue = "UNISWAP_V3" (bare protocol), chain = "ARBITRUM" (separate),
#       instrument_id = pool_address.lower()  (e.g. "0x88e6a0c2...").
#     This matches MTDS ``_canonical_defi_id`` + the writer's per-pool
#     ``record_captured(instrument_id=pool_address.lower(), instrument_type="pool")``.
#
#   * GLUED-PAIR (human-readable / UI):
#       "UNISWAPV3-ARBITRUM:POOL:AAVE-USDC:100"
#       = <VENUE_PREFIX>-<CHAIN> : POOL : <TOKEN0>-<TOKEN1> : <FEE>
#     The venue prefix glues the bare venue with the underscore-before-version
#     token STRIPPED ("UNISWAP_V3" -> "UNISWAPV3"); the pair is token0-token1
#     (base-quote, canonical order); the fee is the pool's fee amount.
#
# The converter is the SSOT for translating between them. instruments-service's
# catalogue carries BOTH (``instrument_id`` = canonical; ``glued_pair_id`` =
# human-readable) so consumers can resolve either; MTDS keys on the canonical.


@dataclass(frozen=True)
class DefiPoolIdentity:
    """Dual-form identity for a single DeFi DEX pool.

    Holds every field both id forms are built from, so the canonical (manifest)
    and glued-pair (human-readable / UI) ids are derivable + reversible. Built
    by :func:`build_pool_identity` from an ``InstrumentRecord``'s fields, or by
    :func:`parse_glued_pool_id` from a legacy glued-pair string.
    """

    venue: str
    """Bare canonical protocol venue, e.g. ``UNISWAP_V3`` (no ``-CHAIN`` suffix)."""
    chain: str
    """Canonical chain key, e.g. ``ARBITRUM`` (uppercase)."""
    pool_address: str
    """On-chain pool contract address, lowercased — the canonical instrument_id."""
    base_asset: str = ""
    """token0 (canonical base) — the first half of the glued-pair PAIR token."""
    quote_asset: str = ""
    """token1 (canonical quote) — the second half of the glued-pair PAIR token."""
    fee: str = ""
    """Pool fee amount as a string (e.g. ``"100"`` / ``"3000"``); blank when unknown."""

    @property
    def canonical_instrument_id(self) -> str:
        """The machine/manifest pool id — ``pool_address.lower()``."""
        return self.pool_address.lower()

    @property
    def glued_pair_id(self) -> str:
        """The human-readable UI pool id — ``UNISWAP_V3-ARBITRUM:POOL:AAVE-USDC:100``.

        Falls back to the pool address when the pair/fee are unknown
        (``…:POOL:<pool_address>``) so the id is always non-empty + reversible
        to the canonical form.
        """
        prefix = glued_venue_prefix(self.venue, self.chain)
        pair = f"{self.base_asset}-{self.quote_asset}" if (self.base_asset and self.quote_asset) else ""
        if pair and self.fee:
            symbol = f"{pair}:{self.fee}"
        elif pair:
            symbol = pair
        else:
            symbol = self.pool_address.lower()
        return f"{prefix}:POOL:{symbol}"


def _insert_version_underscore(protocol: str) -> str:
    """``UNISWAPV3`` → ``UNISWAP_V3`` (the canonical bare-venue AND glued-prefix form).

    Mirror of ``VenueMapping._canonicalise_defi_protocol_spelling`` for a
    chain-less protocol token — inserts the underscore before a version token.
    Idempotent on an already-canonical protocol. Operator-decided canonical form
    (``plans/active/issues/instrument_id_format_canonicalization_2026_07_08.md``
    finding 2): the WITH-underscore spelling is correct everywhere, including the
    glued venue-chain prefix — this function self-heals any legacy no-underscore
    ``glued_pair_id`` data read back through ``split_glued_venue_chain``.
    """
    return re.sub(r"([A-Za-z])V(\d)", r"\1_V\2", protocol)


def glued_venue_prefix(venue: str, chain: str) -> str:
    """Build the glued venue-chain prefix for the human-readable pool id.

    ``("UNISWAP_V3", "ARBITRUM")`` → ``"UNISWAP_V3-ARBITRUM"``. The version
    underscore is PRESERVED in the protocol (operator-decided canonical form,
    see ``_insert_version_underscore``'s docstring — this also self-heals a
    protocol token read back without its underscore), and the chain is
    appended uppercase. A ``venue`` already carrying a ``-CHAIN`` suffix is
    split first (defensive — callers should pass the bare venue).
    """
    bare = venue
    if "-" in venue and not chain:
        bare, _split_chain = venue.rsplit("-", 1)
        chain = _split_chain
    return f"{_insert_version_underscore(bare)}-{chain.upper()}"


def split_glued_venue_chain(glued_venue: str) -> tuple[str, str]:
    """Split a glued ``PROTOCOL-CHAIN`` venue into ``(bare_venue, chain)``.

    ``"UNISWAPV3-ARBITRUM"`` → ``("UNISWAP_V3", "ARBITRUM")``. Canonicalises the
    protocol spelling (inserts the version underscore) so the bare venue matches
    the MTDS-captured ``venue=`` form. A venue with no ``-`` (already bare) →
    ``(canonicalised_venue, "")``.
    """
    if "-" in glued_venue:
        protocol, chain = glued_venue.rsplit("-", 1)
        return _insert_version_underscore(protocol), chain.upper()
    return _insert_version_underscore(glued_venue), ""


def build_pool_identity(
    *,
    venue: str,
    chain: str,
    pool_address: str,
    base_asset: str = "",
    quote_asset: str = "",
    fee: str | int | None = None,
) -> DefiPoolIdentity:
    """Construct a :class:`DefiPoolIdentity` from an instrument's fields.

    ``venue`` may be the bare canonical form (``UNISWAP_V3``) or the glued
    ``PROTOCOL-CHAIN`` form (``UNISWAPV3-ARBITRUM``) — the latter is split, and
    the explicit ``chain`` wins when both are present. ``fee`` accepts an int or
    string (Uniswap feeTier / Balancer fee / …); ``None`` → blank.
    """
    bare_venue, derived_chain = split_glued_venue_chain(venue) if "-" in venue else (venue, "")
    resolved_chain = (chain or derived_chain or "").upper()
    fee_str = "" if fee is None else str(fee)
    return DefiPoolIdentity(
        venue=bare_venue,
        chain=resolved_chain,
        pool_address=pool_address.lower(),
        base_asset=base_asset,
        quote_asset=quote_asset,
        fee=fee_str,
    )


def parse_glued_pool_id(glued_pair_id: str) -> DefiPoolIdentity | None:
    """Parse a legacy glued-pair pool id into a :class:`DefiPoolIdentity`.

    ``"UNISWAPV3-ARBITRUM:POOL:AAVE-USDC:100"`` →
    ``DefiPoolIdentity(venue="UNISWAP_V3", chain="ARBITRUM", base_asset="AAVE",
    quote_asset="USDC", fee="100", pool_address="")``.

    The canonical ``pool_address`` is NOT recoverable from the glued-pair string
    alone (the glued form encodes the PAIR + fee, not the address), so the
    returned identity carries an empty ``pool_address`` — the caller resolves it
    from the instruments-store mapping (``raw_symbol``/``pool_address`` column).
    A ``…:POOL:<0x…>`` glued form (address-as-symbol) DOES recover the address.

    Returns ``None`` for a string that is not a ``PROTOCOL-CHAIN:POOL:…`` triple.
    """
    parts = glued_pair_id.split(":")
    if len(parts) < 3 or parts[1] != "POOL":
        return None
    bare_venue, chain = split_glued_venue_chain(parts[0])
    symbol = parts[2]
    fee = parts[3] if len(parts) >= 4 else ""
    # ``…:POOL:<0x…>`` — the symbol IS the pool address (no pair/fee encoded).
    if symbol.lower().startswith("0x"):
        return DefiPoolIdentity(venue=bare_venue, chain=chain, pool_address=symbol.lower())
    base, _sep, quote = symbol.partition("-")
    return DefiPoolIdentity(
        venue=bare_venue,
        chain=chain,
        pool_address="",
        base_asset=base,
        quote_asset=quote,
        fee=fee,
    )
