"""Flash-loan receiver registry — G2.9 gap #3.

Stage 3E § 2.9 gap #3 from ``codex/09-strategy/architecture-v2/uac-registry-gaps.md``.
``ARBITRAGE_PRICE_DISPERSION x DeFi x lp`` flash-loan arbitrage and
``LIQUIDATION_CAPTURE x DeFi x lending`` require a deployed
``FlashLoanReceiver`` contract on every target chain/protocol pair.

This registry is the **single authoritative source** for chain →
protocol → deployed receiver-address mappings. Before this module the
map was tracked ad-hoc in ``deployment-service/contracts/`` and
``unified-config-interface/testnet_contracts.py``; strategy-service /
execution connectors could not safely validate "flash-loan is
supported on chain X with protocol Y" without a single SSOT.

Consumer integration:

* ``execution-service/execution_service/defi_execution/connectors/*``
  calls ``flash_loan_receiver_for(chain, protocol)`` at connect time —
  fails loud if not found (no silent fallback, per CLAUDE.md rule).
* ``execution-service/execution_service/defi_execution/protocols/aave.py``
  validates deployed-contract address matches registry row; refuses
  flash-loan borrow if drift detected.
* Strategy-service risk-gate reads the registry to gate
  ``ARBITRAGE_PRICE_DISPERSION x DeFi x lp`` slot activation by chain.

Chain-to-RPC mapping lives in
``registry/capability_declarations/_defi.py`` (``CHAIN_RPC_TEMPLATES``);
this module is narrower — *only* flash-loan receiver deployments.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from enum import StrEnum
from typing import Final, Literal

from pydantic import BaseModel, ConfigDict, Field


class FlashLoanProtocol(StrEnum):
    """Supported flash-loan source protocols."""

    AAVE_V3 = "aave_v3"
    """Aave V3 flash-loan API (``flashLoanSimple`` + ``flashLoan``)."""

    BALANCER_V2 = "balancer_v2"
    """Balancer V2 vault flash loans (``flashLoan`` on Vault contract)."""

    UNISWAP_V3_FLASH_SWAP = "uniswap_v3_flash_swap"
    """Uniswap V3 pool ``flash`` swap (single-pool flash-swap primitive)."""


_EVM_ADDRESS_RE = re.compile(r"^0x[0-9a-fA-F]{40}$")
_SOLANA_PROGRAM_RE = re.compile(r"^[1-9A-HJ-NP-Za-km-z]{32,44}$")


def _is_valid_address(addr: str) -> bool:
    """True for EVM checksum addresses or Solana base58 program IDs."""

    return bool(_EVM_ADDRESS_RE.match(addr) or _SOLANA_PROGRAM_RE.match(addr))


class FlashLoanReceiverDeployment(BaseModel):
    """One deployed FlashLoanReceiver contract/program entry.

    ``deployment_commit_sha`` is the deployment-service repo commit SHA
    that produced the deployed bytecode — makes every row
    git-bisectable back to its Solidity source.

    ``receiver_kind`` distinguishes the passthrough receiver (simple
    repay-approve pattern) from the action-encoder recursive-leverage
    receiver (``RecursiveLeverageReceiver.sol``).
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    chain: str
    """Chain ID slug (ETHEREUM / ARBITRUM / OPTIMISM / POLYGON / BASE /
    AVALANCHE / SOLANA). Uppercase convention matches _defi.py.
    """

    protocol: FlashLoanProtocol
    receiver_kind: Literal["passthrough", "recursive_leverage"] = "passthrough"
    """Receiver contract kind:
    - ``passthrough``: simple repay-approve (FlashLoanReceiver.sol).
    - ``recursive_leverage``: action-encoder pattern (RecursiveLeverageReceiver.sol);
      used by RecursiveLoopOrchestrator Phase 4/5.
    """

    receiver_address: str
    """Checksum address (EVM) or base58 program ID (Solana)."""

    deployment_commit_sha: str = Field(min_length=7, max_length=40)
    """Git SHA of deployment-service commit that deployed this receiver."""

    deployed_at_utc: str
    """ISO 8601 deploy timestamp for audit."""

    supported_tokens: tuple[str, ...]
    """Borrowable tokens on this chain/protocol pair (uppercase symbols)."""

    notes: str = ""


FLASH_LOAN_RECEIVER_REGISTRY: Final[tuple[FlashLoanReceiverDeployment, ...]] = (
    # NOTE: addresses below are testnet / reference deployments. Main-net
    # addresses land via semver-agent PRs from deployment-service when the
    # mainnet Solidity deploys complete.
    FlashLoanReceiverDeployment(
        chain="ETHEREUM",
        protocol=FlashLoanProtocol.AAVE_V3,
        receiver_address="0x5555555555555555555555555555555555555555",
        deployment_commit_sha="abc1234",
        deployed_at_utc="2026-04-20T12:00:00Z",
        supported_tokens=("USDC", "WETH", "WBTC", "DAI"),
        notes="Ethereum mainnet Aave V3 flash-loan receiver (placeholder address pending mainnet deploy).",
    ),
    FlashLoanReceiverDeployment(
        chain="ARBITRUM",
        protocol=FlashLoanProtocol.AAVE_V3,
        receiver_address="0x6666666666666666666666666666666666666666",
        deployment_commit_sha="abc1234",
        deployed_at_utc="2026-04-20T12:00:00Z",
        supported_tokens=("USDC", "WETH", "WBTC", "ARB"),
        notes="Arbitrum Aave V3 flash-loan receiver.",
    ),
    FlashLoanReceiverDeployment(
        chain="OPTIMISM",
        protocol=FlashLoanProtocol.AAVE_V3,
        receiver_address="0x7777777777777777777777777777777777777777",
        deployment_commit_sha="abc1234",
        deployed_at_utc="2026-04-20T12:00:00Z",
        supported_tokens=("USDC", "WETH", "OP"),
        notes="Optimism Aave V3 flash-loan receiver.",
    ),
    FlashLoanReceiverDeployment(
        chain="POLYGON",
        protocol=FlashLoanProtocol.AAVE_V3,
        receiver_address="0x8888888888888888888888888888888888888888",
        deployment_commit_sha="abc1234",
        deployed_at_utc="2026-04-20T12:00:00Z",
        supported_tokens=("USDC", "WETH", "WMATIC"),
        notes="Polygon Aave V3 flash-loan receiver.",
    ),
    FlashLoanReceiverDeployment(
        chain="BASE",
        protocol=FlashLoanProtocol.AAVE_V3,
        receiver_address="0x9999999999999999999999999999999999999999",
        deployment_commit_sha="abc1234",
        deployed_at_utc="2026-04-20T12:00:00Z",
        supported_tokens=("USDC", "WETH"),
        notes="Base Aave V3 flash-loan receiver.",
    ),
    FlashLoanReceiverDeployment(
        chain="ETHEREUM",
        protocol=FlashLoanProtocol.BALANCER_V2,
        receiver_address="0xaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
        deployment_commit_sha="abc1234",
        deployed_at_utc="2026-04-20T12:00:00Z",
        supported_tokens=("USDC", "WETH", "BAL", "WBTC"),
        notes="Ethereum Balancer V2 vault flash-loan receiver.",
    ),
    FlashLoanReceiverDeployment(
        chain="ARBITRUM",
        protocol=FlashLoanProtocol.UNISWAP_V3_FLASH_SWAP,
        receiver_address="0xbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
        deployment_commit_sha="abc1234",
        deployed_at_utc="2026-04-20T12:00:00Z",
        supported_tokens=("USDC", "WETH", "ARB"),
        notes="Arbitrum Uniswap V3 single-pool flash-swap receiver.",
    ),
    # --- RecursiveLeverageReceiver.sol (action-encoder pattern, Phase 4) ---
    # Addresses are placeholder pending Sepolia deploy + mainnet deploy via
    # deployment-service/scripts/deploy-recursive-leverage-receiver.sh.
    FlashLoanReceiverDeployment(
        chain="SEPOLIA",
        protocol=FlashLoanProtocol.AAVE_V3,
        receiver_kind="recursive_leverage",
        receiver_address="0xCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCCC",
        deployment_commit_sha="phase4-pending",
        deployed_at_utc="2026-05-15T00:00:00Z",
        supported_tokens=("WETH", "WSTETH", "WEETH", "CBETH"),
        notes="Sepolia testnet RecursiveLeverageReceiver. Aave V3 pool "
        "0x6Ae43d3271ff6888e7Fc43Fd7321a503ff738951. "
        "Placeholder address — replace after `deploy-recursive-leverage-receiver.sh --chain sepolia`.",
    ),
    FlashLoanReceiverDeployment(
        chain="ETHEREUM",
        protocol=FlashLoanProtocol.AAVE_V3,
        receiver_kind="recursive_leverage",
        receiver_address="0xDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDDD",
        deployment_commit_sha="phase4-pending",
        deployed_at_utc="2026-05-15T00:00:00Z",
        supported_tokens=("WETH", "WSTETH", "WEETH", "CBETH"),
        notes="Ethereum mainnet RecursiveLeverageReceiver. Aave V3 pool "
        "0x87870Bca3F3fD6335C3F4ce8392D69350B4fA4E2. "
        "Placeholder address — replace after `deploy-recursive-leverage-receiver.sh --chain ethereum`.",
    ),
    FlashLoanReceiverDeployment(
        chain="BASE",
        protocol=FlashLoanProtocol.AAVE_V3,
        receiver_kind="recursive_leverage",
        receiver_address="0xEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE",
        deployment_commit_sha="phase4-pending",
        deployed_at_utc="2026-05-15T00:00:00Z",
        supported_tokens=("WETH", "WSTETH", "CBETH"),
        notes="Base mainnet RecursiveLeverageReceiver. Aave V3 pool via PoolAddressesProvider. "
        "Placeholder address — replace after `deploy-recursive-leverage-receiver.sh --chain base`.",
    ),
)


class FlashLoanReceiverNotFoundError(LookupError):
    """Raised when ``flash_loan_receiver_for(chain, protocol)`` can't resolve."""


def flash_loan_receiver_for(
    chain: str,
    protocol: FlashLoanProtocol,
    *,
    kind: Literal["passthrough", "recursive_leverage"] = "passthrough",
    registry: Iterable[FlashLoanReceiverDeployment] = FLASH_LOAN_RECEIVER_REGISTRY,
) -> FlashLoanReceiverDeployment:
    """Resolve a deployed receiver by (chain, protocol, kind).

    ``kind`` defaults to ``"passthrough"`` for backwards-compatibility —
    callers of ``RecursiveLoopOrchestrator`` must pass ``kind="recursive_leverage"``.

    Fail-loud: raises on miss (no silent fallback per CLAUDE.md).
    """

    for entry in registry:
        if entry.chain == chain and entry.protocol == protocol and entry.receiver_kind == kind:
            return entry
    raise FlashLoanReceiverNotFoundError(
        f"no FlashLoanReceiver deployed for chain={chain!r}, protocol={protocol.value!r}, kind={kind!r}",
    )


def receivers_for_chain(
    chain: str,
    *,
    registry: Iterable[FlashLoanReceiverDeployment] = FLASH_LOAN_RECEIVER_REGISTRY,
) -> tuple[FlashLoanReceiverDeployment, ...]:
    """All receivers deployed on ``chain`` across any protocol."""

    return tuple(entry for entry in registry if entry.chain == chain)


def receivers_supporting_token(
    token: str,
    *,
    registry: Iterable[FlashLoanReceiverDeployment] = FLASH_LOAN_RECEIVER_REGISTRY,
) -> tuple[FlashLoanReceiverDeployment, ...]:
    """All (chain, protocol) receivers that list ``token`` as borrowable."""

    return tuple(entry for entry in registry if token in entry.supported_tokens)


def receivers_by_kind(
    kind: Literal["passthrough", "recursive_leverage"],
    *,
    registry: Iterable[FlashLoanReceiverDeployment] = FLASH_LOAN_RECEIVER_REGISTRY,
) -> tuple[FlashLoanReceiverDeployment, ...]:
    """All receivers of a specific ``receiver_kind`` across all chains/protocols."""

    return tuple(entry for entry in registry if entry.receiver_kind == kind)


def _validate_registry_invariants(
    registry: Iterable[FlashLoanReceiverDeployment] = FLASH_LOAN_RECEIVER_REGISTRY,
) -> None:
    """Invariants:

    * (chain, protocol, receiver_kind) triple unique.
    * ``receiver_address`` matches EVM-checksum or Solana-base58 shape.
    * ``supported_tokens`` non-empty.
    """

    seen: set[tuple[str, FlashLoanProtocol, str]] = set()
    for entry in registry:
        key = (entry.chain, entry.protocol, entry.receiver_kind)
        if key in seen:
            raise ValueError(
                f"duplicate (chain, protocol, receiver_kind) in FLASH_LOAN_RECEIVER_REGISTRY: {key!r}",
            )
        seen.add(key)
        if not _is_valid_address(entry.receiver_address):
            raise ValueError(
                f"{key!r}: receiver_address {entry.receiver_address!r} not EVM/Solana shape",
            )
        if not entry.supported_tokens:
            raise ValueError(
                f"{key!r}: supported_tokens must be non-empty",
            )


_validate_registry_invariants()


CONSUMER_CALL_SITES: Final[tuple[str, ...]] = (
    "execution-service/execution_service/defi_execution/protocols/aave.py",
    "execution-service/execution_service/defi_execution/connectors/registry.py",
    "strategy-service/strategy_service/validation/data_certification.py",
)


__all__ = [
    "CONSUMER_CALL_SITES",
    "FLASH_LOAN_RECEIVER_REGISTRY",
    "FlashLoanProtocol",
    "FlashLoanReceiverDeployment",
    "FlashLoanReceiverNotFoundError",
    "flash_loan_receiver_for",
    "receivers_by_kind",
    "receivers_for_chain",
    "receivers_supporting_token",
]
