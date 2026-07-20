"""Instrument-related enums — cycle-free SSOT.

This module is the single source of truth for instrument enums shared across
both ``canonical`` and ``internal`` packages. It lives at the package root
(not inside ``internal/`` or ``canonical/``) so that importing it never
triggers the heavy ``internal/__init__.py`` or ``canonical/__init__.py``
import chains, avoiding circular dependencies.

Both ``internal.reference.instrument`` and ``canonical.domain.reference``
re-export these enums — downstream code should import from those modules
(or from the top-level ``unified_api_contracts`` facade), not from here.
"""

from enum import StrEnum


class InstrumentType(StrEnum):
    """Unified instrument classification — SSOT for all repos.

    UPPERCASE values are the canonical standard. All downstream consumers
    (instruments-service adapters, MTDS, MDPS, ML, strategy, execution, risk)
    must use these enum members or their string values.

    Mapping from legacy lowercase values (for migration reference):
        spot → SPOT_PAIR, perp → PERPETUAL, futures → FUTURE, option → OPTION,
        pool → POOL, lending_market → LENDING, lst → LST, yield → YIELD_BEARING,
        etf → ETF
    """

    # CeFi
    SPOT_PAIR = "SPOT_PAIR"
    PERPETUAL = "PERPETUAL"
    FUTURE = "FUTURE"
    OPTION = "OPTION"
    # DEPRECATED — collapsed to PERPETUAL/SPOT_PAIR + the tracks_equity /
    # is_equity_perp catalogue tags (operator 2026-07-16). instrument_type is now
    # the BROAD contract-mechanics type ONLY: a crypto-venue single-stock perp is
    # ``PERPETUAL`` and a tokenized stock is ``SPOT_PAIR`` — the equity identity +
    # real-equity linkage ride the ``is_equity_perp`` (bool) + ``tracks_equity``
    # (real-equity ticker) catalogue tags built at roll-up from
    # ``crypto_equity_link.tracks_equity`` + ``CEFI_EQUITY_PERP_BASE_UNIVERSE``.
    # These two members are NO LONGER MINTED (the IS catalogue rollup no longer
    # re-types to them) but are KEPT DEFINED so pre-2026-07-16 persisted catalogue
    # rows + external string consumers (MTDS/deployment-api/UI snapshot) stay
    # parseable, and so every enum member keeps a valid ledger-asset class.
    # See: unified_api_contracts.canonical.crosscutting.crypto_equity_link
    EQUITY_PERP = "EQUITY_PERP"
    TOKENIZED_EQUITY = "TOKENIZED_EQUITY"
    # DeFi
    POOL = "POOL"
    # DeFi — DEX-pool instrument type (Solana basis trading MVP Phase 2,
    # 2026-06-01). Used by ``DEFI_DEX_POOL_DEX_ORDERBOOK`` /
    # ``DEFI_DEX_POOL_DEX_QUOTE`` / ``DEFI_DEX_POOL_DEX_TRADES`` contracts.
    # Distinct from ``POOL`` (legacy EVM AMM pool snapshots — Uniswap,
    # Curve) so the spot-DEX orderbook + quote + per-swap shards can carry
    # venue-specific fields without colliding with the EVM pool contract.
    DEX_POOL = "DEX_POOL"
    LENDING = "LENDING"
    LST = "LST"
    YIELD_BEARING = "YIELD_BEARING"
    A_TOKEN = "A_TOKEN"
    DEBT_TOKEN = "DEBT_TOKEN"
    STAKING = "STAKING"
    # DeFi — LIQUID RESTAKING tokens (operator decision 2026-07-20,
    # distinct_values_noncanonical_audit_2026_07_20.md). Renzo ezETH, KelpDAO
    # rsETH, Puffer pufETH. The DeFi manifest was already emitting
    # ``instrument_type=restaking`` with NO canonical enum member, so these had
    # no canonical home and badged non-canonical on the data-status drift panel.
    # Deliberately NOT folded into ``LST``: a liquid restaking token carries
    # EigenLayer AVS slashing risk STACKED on the base ETH staking slashing an
    # LST carries (ezETH depegged 2024), so collapsing the two would lose real
    # signal for collateral / risk modelling.
    RESTAKING = "RESTAKING"
    SPOT_ASSET = "SPOT_ASSET"
    # DeFi — Solana (distinct shapes vs EVM lending/pool; see UAC@7e9f4ad9 contracts +
    # plan solana_defi_legacy_migration_2026_05_27).
    SOLANA_LENDING = "SOLANA_LENDING"
    SOLANA_VAULT = "SOLANA_VAULT"
    SOLANA_AMM_POOL = "SOLANA_AMM_POOL"
    # TradFi
    ETF = "ETF"
    EQUITY = "EQUITY"
    COMMODITY = "COMMODITY"
    CURRENCY = "CURRENCY"
    INDEX = "INDEX"
    BOND = "BOND"
    CDS = "CDS"
    # Binary YES/NO settlement (CME ECES/ECBTC/etc.); cross-venue arb leg with
    # Polymarket canonical_question_groups. See cme_polymarket_arb_2026_05_08 plan.
    EVENT_CONTRACT = "EVENT_CONTRACT"
    # Multi-leg (combos, spreads, strategies)
    COMBO = "COMBO"
    # Sports / Prediction Markets
    PREDICTION_MARKET = "PREDICTION_MARKET"
    # EXCHANGE_ODDS / FIXED_ODDS are LIVE in the derivation + adapter layer:
    #   - instruments-service ``instruments_service/reference_data/adapters/sports/
    #     adapters/betfair.py:287`` constructs ``InstrumentType.EXCHANGE_ODDS``.
    #   - UTL ``unified_trading_library/canonical/_derive_instrument_id.py:85`` maps
    #     ``("sports", "odds") -> InstrumentType.EXCHANGE_ODDS``.
    # They are NOT the sports manifest's vocabulary. The sports SchemaContract
    # registry deliberately does NOT key on InstrumentType — it keys on the declared
    # contract value ``odds`` (see internal/schemas/_sports_prediction_contracts.py,
    # instrument_type="odds"), which is also the physical GCS hive partition
    # (``instrument_type=odds/``) and is still actively written.
    # Do NOT "fix" the manifest/registry to match these enum members: renaming
    # ``odds`` -> EXCHANGE_ODDS/FIXED_ODDS would create manifest<->disk<->registry
    # divergence to change a value that has zero shard + display consumers
    # (SHARD_AXIS_MATRIX keys sports on ("data_type", "league_id"), not
    # instrument_type). Operator ruling 2026-07-17: closed as not-a-defect.
    EXCHANGE_ODDS = "EXCHANGE_ODDS"
    FIXED_ODDS = "FIXED_ODDS"
    PROP = "PROP"


class OptionType(StrEnum):
    """Option direction."""

    CALL = "call"
    PUT = "put"


class AssetClass(StrEnum):
    """Asset class classification — market domain category.

    Used for position grouping, strategy routing, and domain-specific
    commentary. A BTC future and BTC spot are both ``crypto``. An ES
    future and AAPL stock are both ``equity``. This is the domain the
    instrument belongs to, not the physical form of the underlying.
    """

    CRYPTO = "crypto"
    EQUITY = "equity"
    FX = "fx"
    COMMODITY = "commodity"
    FIXED_INCOME = "fixed_income"


class InstrumentStatus(StrEnum):
    """Instrument trading status."""

    ACTIVE = "active"
    HALTED = "halted"
    EXPIRED = "expired"
    DELISTED = "delisted"


class MarginType(StrEnum):
    """Settlement/margin type for derivative instruments.

    Determines how notional value is calculated and which currency settles PnL.

    LINEAR  — USDT/USDC-margined; notional = qty x price x contract_size (quote currency)
    INVERSE — Coin-margined; contract denominated in USD, settled in base coin.
              USD notional = qty x contract_size (fixed); delta_coin = notional_usd / price.
              Example: Bybit BTCUSD perpetual — 1 contract = $1 USD, settled in BTC.
    QUANTO  — Fixed foreign-currency multiplier; rare (some Deribit instruments).
    """

    LINEAR = "linear"
    INVERSE = "inverse"
    QUANTO = "quanto"
