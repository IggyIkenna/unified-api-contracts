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
#   * GLUED-PAIR (symbolic canonical / human-readable / UI):
#       "UNISWAP_V3-ARBITRUM:POOL:AAVE-USDC-100"
#       = <VENUE_PREFIX>-<CHAIN> : POOL : <TOKEN0>-<TOKEN1>[-<FEE_BPS>]
#     3-SEGMENT (colon-delimited): the fee is glued INTO the symbol segment with
#     a HYPHEN (``AAVE-USDC-100``), NEVER a 4th colon segment (``…:AAVE-USDC:100``
#     is the RETIRED shape — operator ruling 2026-07-18). The venue prefix keeps
#     the underscore-before-version token ("UNISWAP_V3", operator-canonical); the
#     pair is token0-token1 (base-quote, canonical order); the trailing numeric
#     fee segment is OMITTED when unknown. This is byte-aligned with the MTDS
#     producer ``market_tick_data_service.cli.handlers._dex_pool_symbol.build_symbol``
#     + ``live/connectors/dex_swap_uniswap_v3_ws._pool_instrument_id`` ("real
#     basis points ... never a colon-before-fee") so a batch shard and this
#     converter emit an IDENTICAL id for the same pool — the join key both sides
#     rely on.
#
# The converter is the SSOT for translating between them. Under the DeFi two-id
# model (operator ruling 2026-07-18, Option A) instruments-service's catalogue
# carries BOTH and they legitimately DIVERGE for a POOL row: the machine
# ``instrument_id`` COLUMN = the pool ADDRESS (:attr:`DefiPoolIdentity.canonical_instrument_id`,
# the MTDS ``defi_catalog_reader`` join key — do NOT flip it to the symbolic
# form), while the symbolic ``canonical_instrument_id`` COLUMN is materialized
# from :attr:`DefiPoolIdentity.glued_pair_id` (the 3-segment key above). MTDS
# keys market-data joins on the pool ADDRESS. SSOT:
# ``instruments-service/docs/DEFI_INSTRUMENTS.md`` (two-id model) +
# ``codex/02-data/defi-canonical-naming-ssot.md``.


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
        """The machine/operational pool ``instrument_id`` — ``pool_address.lower()``.

        Under the DeFi two-id model (operator ruling 2026-07-18, Option A) this
        is the ADDRESS-anchored **machine** id: the manifest join key + the MTDS
        content-join key. ``market-tick-data-service``'s
        ``engine/defi_catalog_reader`` reads it expecting ``pool_address.lower()``
        for POOL rows across all 13 protocols, so it MUST stay the address —
        flipping it to the symbolic form would silently break that join.

        This is NOT the operator's symbolic ``canonical_instrument_id`` COLUMN:
        for a POOL row the two legitimately DIVERGE. The symbolic
        ``VENUE-CHAIN:POOL:BASE-QUOTE[-FEE_BPS]`` canonical key is
        :attr:`glued_pair_id` (which materializes that column). SSOT:
        ``instruments-service/docs/DEFI_INSTRUMENTS.md`` (two-id model) +
        ``codex/02-data/defi-canonical-naming-ssot.md``.
        """
        return self.pool_address.lower()

    @property
    def glued_pair_id(self) -> str:
        """The symbolic canonical pool id — ``UNISWAP_V3-ARBITRUM:POOL:AAVE-USDC-100``.

        3-segment ``<VENUE_PREFIX>-<CHAIN>:POOL:<BASE>-<QUOTE>[-<FEE_BPS>]`` — the
        fee is glued INTO the symbol segment with a HYPHEN, never a 4th colon
        segment (the ``…:POOL:AAVE-USDC:100`` shape is RETIRED, operator ruling
        2026-07-18). Byte-aligned with the MTDS producer
        (``_dex_pool_symbol.build_symbol`` + ``dex_swap_uniswap_v3_ws``, "never a
        colon-before-fee") so a batch shard and this converter emit an IDENTICAL
        id for the same pool — the data-join key both rely on.

        This IS the operator's symbolic ``canonical_instrument_id`` (it materializes
        the catalogue ``canonical_instrument_id`` COLUMN for a POOL row — the shipped
        two-id Option-A mapping, matching this module's header + MTDS
        ``defi_catalog_reader``); the pool ADDRESS is the separate machine
        :attr:`canonical_instrument_id` / catalogue ``instrument_id`` column (two-id
        model, Option A — POOL rows DIVERGE). Falls
        back to the pool address when the pair is unknown
        (``…:POOL:<pool_address>``) so the id is always non-empty + reversible
        via :func:`parse_glued_pool_id`.
        """
        prefix = glued_venue_prefix(self.venue, self.chain)
        if self.base_asset and self.quote_asset:
            pair = f"{self.base_asset}-{self.quote_asset}"
            symbol = f"{pair}-{self.fee}" if self.fee else pair
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
    """Parse a symbolic glued-pair pool id into a :class:`DefiPoolIdentity`.

    Round-trips the canonical 3-segment form AND the retired 4-segment form:

    * ``"UNISWAP_V3-ARBITRUM:POOL:AAVE-USDC-100"`` (canonical, fee glued into the
      symbol with a hyphen) →
      ``DefiPoolIdentity(venue="UNISWAP_V3", chain="ARBITRUM", base_asset="AAVE",
      quote_asset="USDC", fee="100", pool_address="")``.
    * ``"UNISWAPV3-ARBITRUM:POOL:AAVE-USDC:100"`` (legacy 4-segment fee-as-4th-
      colon, still readable for any un-migrated persisted row) → the same result.

    Fee detection mirrors the MTDS ``build_symbol`` grammar: a legacy 4th-colon
    fee segment wins; otherwise the fee is a TRAILING all-digit hyphen segment of
    the symbol (``<BASE>-<QUOTE>-<FEE_BPS>``), peeled off before the base/quote
    split — so a multi-token Curve symbol (``DAI-USDC-USDT``, no numeric fee) is
    left intact and still round-trips.

    The canonical ``pool_address`` is NOT recoverable from the pair-form glued
    string alone (it encodes the PAIR + fee, not the address), so the returned
    identity carries an empty ``pool_address`` — the caller resolves it from the
    instruments-store mapping (``raw_symbol``/``pool_address`` column). A
    ``…:POOL:<0x…>`` glued form (address-as-symbol) DOES recover the address.

    Returns ``None`` for a string that is not a ``PROTOCOL-CHAIN:POOL:…`` triple.
    """
    parts = glued_pair_id.split(":")
    if len(parts) < 3 or parts[1] != "POOL":
        return None
    bare_venue, chain = split_glued_venue_chain(parts[0])
    symbol = parts[2]
    # ``…:POOL:<0x…>`` — the symbol IS the pool address (no pair/fee encoded).
    if symbol.lower().startswith("0x"):
        return DefiPoolIdentity(venue=bare_venue, chain=chain, pool_address=symbol.lower())
    # A legacy 4th-colon fee segment (``…:POOL:<PAIR>:<FEE>``) takes precedence;
    # otherwise peel a trailing all-digit hyphen segment from the 3-segment
    # symbol as the fee (matches ``build_symbol``: fee is real basis points).
    legacy_fee = parts[3] if len(parts) >= 4 else ""
    segments = symbol.split("-")
    fee = legacy_fee
    if not legacy_fee and len(segments) >= 3 and segments[-1].isdigit():
        fee = segments[-1]
        segments = segments[:-1]
    base = segments[0] if segments else ""
    quote = "-".join(segments[1:]) if len(segments) > 1 else ""
    return DefiPoolIdentity(
        venue=bare_venue,
        chain=chain,
        pool_address="",
        base_asset=base,
        quote_asset=quote,
        fee=fee,
    )
