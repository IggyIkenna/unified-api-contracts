"""Canonical instrument-type → ledger-asset-class resolution (the SSOT).

This is the single source of truth for deriving a :class:`LedgerRow`'s asset
identity (``asset_symbol`` / ``asset_canonical_id`` / ``asset_class``) FROM the
canonical :class:`InstrumentKey` (``VENUE:INSTRUMENT_TYPE:SYMBOL``) — so the
determinism-spine ledger writers never thread hand-built ``*_of`` metadata maps.

Two layers:

1. :func:`asset_class_for_instrument_type` — the canonical
   ``InstrumentType → LedgerAssetClass`` map. Replaces the ad-hoc per-caller dicts
   that previously guessed an asset class (e.g. the strategy-service
   ``paper_run_emit`` ``_DEFAULT_ASSET_CLASS = PERP`` bolt-on). The instrument's
   ``instrument_type`` is intrinsic to its key, so the ledger asset class is a pure
   function of it — no map to thread.
2. :func:`derive_ledger_asset_fields` — parse an ``instrument_key`` and return the
   three ledger asset fields a :class:`LedgerRow` needs. The symbol IS the
   canonical asset identity at the sim-ledger grain (a downstream
   :class:`InstrumentRecord` join can enrich ``asset_canonical_id`` with an
   on-chain contract address / OCC symbol when one is available — that is an
   enrichment, not a thread-through guess).

Why this lives in UAC ``internal/reference`` (not a service): the
:class:`InstrumentKey`, :class:`InstrumentType`, and the ledger
:class:`LedgerAssetClass` are all UAC types, and BOTH the strategy-service engine
and the UTL ledger writer derive the same fields from the same key — a single UAC
function is the only way they cannot drift (the determinism PROOF). Future
strategies build on this, never on a re-invented local dict.

SSOT: ``codex/09-strategy/operational/paper-batch-live-reconciliation.md`` §4.5
Plan: ``plans/active/citadel_paper_batch_live_reconciliation_2026_06_19.md`` (P1)
"""

from __future__ import annotations

from unified_api_contracts._instrument_enums import InstrumentType
from unified_api_contracts.canonical.crosscutting.ledger._enums import AssetClass as LedgerAssetClass
from unified_api_contracts.internal.architecture_v2.enums import InstructionActionV2
from unified_api_contracts.internal.reference.instrument_key import InstrumentKey

# ── Canonical InstrumentType → LedgerAssetClass map (the SSOT) ──────────────────
# Every InstrumentType member resolves to exactly one LedgerAssetClass. This is
# the consolidated home for the instrument-type → ledger-asset-class relationship
# that callers previously open-coded (or guessed via a hardcoded default). The
# ledger AssetClass is the FINE-GRAINED discriminant (spot_token / perp / lst /
# atoken / …) that drives attribution bucketing + passive-event synthesis — it is
# a deterministic function of the instrument type, so it must never be threaded
# through a side map.
_INSTRUMENT_TYPE_TO_LEDGER_ASSET_CLASS: dict[InstrumentType, LedgerAssetClass] = {
    # CeFi / TradFi tradeable instruments
    InstrumentType.SPOT_PAIR: LedgerAssetClass.SPOT_TOKEN,
    InstrumentType.SPOT_ASSET: LedgerAssetClass.SPOT_TOKEN,
    InstrumentType.PERPETUAL: LedgerAssetClass.PERP,
    InstrumentType.FUTURE: LedgerAssetClass.FUTURE,
    InstrumentType.OPTION: LedgerAssetClass.OPTION,
    InstrumentType.ETF: LedgerAssetClass.ETF,
    InstrumentType.EQUITY: LedgerAssetClass.SPOT_TOKEN,
    InstrumentType.COMMODITY: LedgerAssetClass.FUTURE,
    InstrumentType.CURRENCY: LedgerAssetClass.CURRENCY,
    InstrumentType.INDEX: LedgerAssetClass.SPOT_TOKEN,
    InstrumentType.BOND: LedgerAssetClass.FUTURE,
    InstrumentType.CDS: LedgerAssetClass.FUTURE,
    # DeFi on-chain instruments
    InstrumentType.POOL: LedgerAssetClass.VAULT_SHARE,
    InstrumentType.DEX_POOL: LedgerAssetClass.SPOT_TOKEN,
    InstrumentType.LENDING: LedgerAssetClass.ATOKEN,
    InstrumentType.LST: LedgerAssetClass.LST,
    InstrumentType.YIELD_BEARING: LedgerAssetClass.VAULT_SHARE,
    InstrumentType.A_TOKEN: LedgerAssetClass.ATOKEN,
    InstrumentType.DEBT_TOKEN: LedgerAssetClass.DEBT_TOKEN,
    InstrumentType.STAKING: LedgerAssetClass.LST,
    InstrumentType.SOLANA_LENDING: LedgerAssetClass.ATOKEN,
    InstrumentType.SOLANA_VAULT: LedgerAssetClass.VAULT_SHARE,
    InstrumentType.SOLANA_AMM_POOL: LedgerAssetClass.SPOT_TOKEN,
    # Event / prediction / sports
    InstrumentType.EVENT_CONTRACT: LedgerAssetClass.PREDICTION_CONTRACT,
    InstrumentType.PREDICTION_MARKET: LedgerAssetClass.PREDICTION_CONTRACT,
    InstrumentType.EXCHANGE_ODDS: LedgerAssetClass.SPORTS_OUTCOME,
    InstrumentType.FIXED_ODDS: LedgerAssetClass.SPORTS_OUTCOME,
    InstrumentType.PROP: LedgerAssetClass.SPORTS_OUTCOME,
    # Multi-leg (the combo's class is resolved per-leg; the combo wrapper is unknown)
    InstrumentType.COMBO: LedgerAssetClass.UNKNOWN,
}


class UnknownInstrumentTypeError(ValueError):
    """Raised when an instrument_type/action has no canonical ledger mapping.

    A loud failure (never a silent ``UNKNOWN`` fallback) — an unmapped instrument
    type or action on the ledger spine is a real gap to fix in this SSOT, not to
    mask: the determinism PROOF requires a deterministic, complete mapping.
    """

    def __init__(self, instrument_type: str) -> None:
        super().__init__(
            f"no canonical LedgerAssetClass/InstrumentType for {instrument_type!r}; "
            f"extend the maps in "
            f"unified_api_contracts.internal.reference.ledger_asset_resolution"
        )
        self.instrument_type = instrument_type


# ── Canonical InstructionActionV2 → InstrumentType map ──────────────────────────
# A v2 instruction's ACTION determines the natural instrument type of the fill it
# settles, so the determinism-spine engine can build a canonical
# ``VENUE:INSTRUMENT_TYPE:SYMBOL`` key from the (action, venue, symbol) it already
# holds at fill time — no instrument_type side map to thread. TRADE is the only
# spot-vs-perp ambiguous action; the basis/funding archetypes that drive paper
# trading are perp-dominant, so TRADE resolves to PERPETUAL (the documented
# archetype default — a strategy that trades CeFi SPOT sets the key explicitly via
# its instruction's instrument identity). This is the canonical, centralized
# derivation that replaces the per-caller ``instrument_type_of`` dict + the
# hardcoded ``_DEFAULT_INSTRUMENT_TYPE = "PERP"`` bolt-on.
_ACTION_TO_INSTRUMENT_TYPE: dict[InstructionActionV2, InstrumentType] = {
    InstructionActionV2.TRADE: InstrumentType.PERPETUAL,
    InstructionActionV2.SWAP: InstrumentType.DEX_POOL,
    InstructionActionV2.LEND: InstrumentType.LENDING,
    InstructionActionV2.BORROW: InstrumentType.DEBT_TOKEN,
    InstructionActionV2.STAKE: InstrumentType.STAKING,
    InstructionActionV2.UNSTAKE: InstrumentType.STAKING,
    InstructionActionV2.QUOTE: InstrumentType.PERPETUAL,
    InstructionActionV2.LP_MINT: InstrumentType.POOL,
    InstructionActionV2.LP_BURN: InstrumentType.POOL,
}


def instrument_type_for_action(action: InstructionActionV2) -> InstrumentType:
    """Return the canonical :class:`InstrumentType` an action's fill settles.

    The single SSOT for v2-action → instrument-type, used by the benchmark-fill
    engine to build a canonical ``instrument_key`` from the (action, venue, symbol)
    a fill already carries — so the ledger writers derive the asset class from the
    key (intrinsic) rather than from a threaded ``instrument_type_of`` map.

    Raises:
        UnknownInstrumentTypeError: the action has no settling instrument type
            (control-plane actions like CANCEL / TRANSFER / BRIDGE produce no fill,
            so they never need a key — a real gap if reached on the fill path).
    """
    resolved = _ACTION_TO_INSTRUMENT_TYPE.get(action)
    if resolved is None:
        raise UnknownInstrumentTypeError(f"action:{action.value}")
    return resolved


def asset_class_for_instrument_type(instrument_type: InstrumentType | str) -> LedgerAssetClass:
    """Return the canonical :class:`LedgerAssetClass` for an instrument type.

    The single SSOT for instrument-type → ledger-asset-class. Accepts the
    :class:`InstrumentType` enum or its string value (canonical UPPERCASE).

    Raises:
        UnknownInstrumentTypeError: the instrument type is not in the canonical map
            (a real gap — extend the map, never mask with UNKNOWN).
    """
    if isinstance(instrument_type, str):
        try:
            instrument_type = InstrumentType(instrument_type)
        except ValueError as exc:
            raise UnknownInstrumentTypeError(instrument_type) from exc
    resolved = _INSTRUMENT_TYPE_TO_LEDGER_ASSET_CLASS.get(instrument_type)
    if resolved is None:
        raise UnknownInstrumentTypeError(instrument_type.value)
    return resolved


def derive_ledger_asset_fields(instrument_key: str) -> tuple[str, str, LedgerAssetClass]:
    """Derive the three ledger asset fields from a canonical ``instrument_key``.

    Parses ``VENUE:INSTRUMENT_TYPE:SYMBOL`` via :class:`InstrumentKey` and returns
    ``(asset_symbol, asset_canonical_id, asset_class)`` for a :class:`LedgerRow`:

      - ``asset_symbol`` = the key's ``symbol`` (the human-readable instrument
        symbol, e.g. ``BTC-USDT``).
      - ``asset_canonical_id`` = the symbol as the canonical asset id at the
        sim-ledger grain. (An InstrumentRecord join can enrich this with an
        on-chain contract address / OCC symbol downstream — that is an enrichment,
        not a thread-through.)
      - ``asset_class`` = :func:`asset_class_for_instrument_type` of the key's
        ``instrument_type``.

    This is the canonical replacement for the ``asset_symbol_of`` /
    ``asset_canonical_id_of`` / ``asset_class_of`` maps the ledger writers used to
    thread — the instrument identity is intrinsic to the key.

    Raises:
        ValueError: ``instrument_key`` is not a parseable ``VENUE:TYPE:SYMBOL``.
        UnknownInstrumentTypeError: the key's instrument_type has no ledger class.
    """
    key = InstrumentKey.from_string(instrument_key)
    asset_class = asset_class_for_instrument_type(key.instrument_type)
    return key.symbol, key.symbol, asset_class


__all__ = [
    "UnknownInstrumentTypeError",
    "asset_class_for_instrument_type",
    "derive_ledger_asset_fields",
    "instrument_type_for_action",
]
