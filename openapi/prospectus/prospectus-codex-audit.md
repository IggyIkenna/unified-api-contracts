# Prospectus vs Codex Two-Sided Audit

_Machine-generated audit — deterministic output. Do not hand-edit; re-run `audit_prospectus_vs_codex.py`._

## Summary

| Metric                                  | Count |
| --------------------------------------- | ----- |
| StrategyArchetype enum values           | 57    |
| Codex archetype docs in `archetypes/`   | 59    |
| Archetypes with codex doc               | 57    |
| Archetypes WITHOUT codex doc (a)        | 0     |
| Codex docs WITHOUT enum entry (b)       | 2     |
| Venue-category contradictions (c)       | 1     |
| Legs-in-prose drift (d)                 | 6     |
| ARCHETYPE_CAPABILITY_REGISTRY available | yes   |
| ARCHETYPE_LEG_STRUCTURES available      | yes   |

## (a) StrategyArchetype Enum Values WITHOUT Codex Doc

_All enum values have codex docs._

## (b) Codex Docs WITHOUT StrategyArchetype Enum Entry (Orphan Docs)

These files exist in the archetypes codex directory but have no corresponding StrategyArchetype enum value. They are either:

- Stale docs for deleted/renamed archetypes, or
- New archetypes authored in codex but not yet added to the enum.

- `carry-recursive-borrow-perp-hedged.md` (would map to `CARRY_RECURSIVE_BORROW_PERP_HEDGED`)
- `carry-recursive-staked-config-variants.md` (would map to `CARRY_RECURSIVE_STAKED_CONFIG_VARIANTS`)

## (c) Venue-Category / Instrument Contradictions

These are CLEAR STRUCTURED contradictions between the codex `venue_universe` frontmatter field and ARCHETYPE_CAPABILITY_REGISTRY. Prose-only ambiguity is excluded.

| Archetype              | Category | Codex Claims                                                                    | Registry Says                                              | Severity |
| ---------------------- | -------- | ------------------------------------------------------------------------------- | ---------------------------------------------------------- | -------- |
| `CARRY_BASIS_PERP_INV` | CEFI     | venue_universe field references CEFI venues: [AAVE, MORPHO, HYPERLIQUID, BYBIT] | ARCHETYPE_CAPABILITY_REGISTRY has no CEFI capability cells | WARNING  |

## (d) Legs-in-Prose Drift (F22 — multi-leg structure only as text)

These archetypes have ARCHETYPE_CAPABILITY_REGISTRY cell `notes` that imply a multi-leg structure (match `ATOMIC|hedge|+`) but have NO entry in ARCHETYPE_LEG_STRUCTURES — so the per-leg restriction lives ONLY as prose, not as the queryable leg SSOT the wizard/prospectus can render. Each should get a leg structure (the F22 fix pattern).

| Archetype                         | Cell notes (prose implying legs)                                                           |
| --------------------------------- | ------------------------------------------------------------------------------------------ |
| `EVENT_DRIVEN`                    | News-feed + lineup timing model not declared.                                              |
| `LIQUIDATION_CAPTURE`             | Flash-loan receiver contract required per-chain. Aave V3 + Kamino primary.                 |
| `MARKET_MAKING_CONTINUOUS`        | Active LP (Uniswap V3/V4, Orca, Raydium) + Passive LP (Curve, Balancer, Uniswap V2).       |
| `RULES_DIRECTIONAL_EVENT_SETTLED` | Docs + example instances gap. \| Engine code complete; docs + example instances minor gap. |
| `STAT_ARB_CROSS_SECTIONAL`        | Multi-token atomic basket trade on DeFi is gas-prohibitive; needs specialised router.      |
| `VOL_TRADING_OPTIONS`             | Full Deribit surface support; multi-leg ATOMIC supported.                                  |

## Archetypes With Codex Doc (full inventory)

- `ARBITRAGE_CROSS_DOMAIN_EVENT`
- `ARBITRAGE_MEV_BACKRUN`
- `ARBITRAGE_MEV_JIT_LIQUIDITY`
- `ARBITRAGE_MEV_LIQUIDATION_BUNDLE`
- `ARBITRAGE_MEV_SANDWICH`
- `ARBITRAGE_PRICE_DISPERSION`
- `CARRY_BASIS_DATED`
- `CARRY_BASIS_DATED_INV`
- `CARRY_BASIS_PERP`
- `CARRY_BASIS_PERP_INV`
- `CARRY_RECURSIVE_BORROW_LENDING_ONLY`
- `CARRY_RECURSIVE_STAKED`
- `CARRY_STAKED_BASIS`
- `CARRY_STAKED_BASIS_DATED`
- `DEFI_LP_CONCENTRATED`
- `DEFI_LP_POOL`
- `DEFI_LP_VAULT`
- `EVENT_DRIVEN`
- `LIQUIDATION_CAPTURE`
- `MARKET_MAKING_CONTINUOUS`
- `MARKET_MAKING_EVENT_SETTLED`
- `MARKET_MAKING_INVENTORY_SKEW`
- `MARKET_MAKING_ML_LEAN`
- `MARKET_MAKING_PASSIVE_SPREAD`
- `MARKET_MAKING_PREDICTION`
- `MARKET_MAKING_QUEUE_MICROSTRUCTURE`
- `ML_DIRECTIONAL_CONTINUOUS`
- `ML_DIRECTIONAL_EVENT_SETTLED`
- `PORTFOLIO_FACTOR_ALLOCATION`
- `PORTFOLIO_MULTI_STRATEGY`
- `PORTFOLIO_RISK_PARITY`
- `PORTFOLIO_TACTICAL_OVERLAY`
- `RULES_DIRECTIONAL_CONTINUOUS`
- `RULES_DIRECTIONAL_EVENT_SETTLED`
- `STAT_ARB_CROSS_SECTIONAL`
- `STAT_ARB_PAIRS_FIXED`
- `VOL_0DTE_GAMMA_SCALPING`
- `VOL_0DTE_PIN_RISK`
- `VOL_ARB_RV_IV`
- `VOL_CARRY`
- `VOL_CROSS_ASSET_SPREAD`
- `VOL_DISPERSION`
- `VOL_LEAPS_CONVEXITY`
- `VOL_MARKET_MAKING`
- `VOL_ML_LEAN`
- `VOL_OVERLAY_COVERED_CALLS`
- `VOL_OVERLAY_PROTECTIVE_PUT`
- `VOL_RATIO_SPREAD`
- `VOL_SPREAD_STRUCTURES`
- `VOL_STRADDLE`
- `VOL_SYNTHETIC_DELTA`
- `VOL_TERM_STRUCTURE_ARB`
- `VOL_TERM_STRUCTURE_SLOPE`
- `VOL_TRADING_OPTIONS`
- `VOL_VARIANCE_SWAP`
- `YIELD_ROTATION_LENDING`
- `YIELD_STAKING_SIMPLE`

## Audit Provenance

- Generated by: `scripts/openapi/audit_prospectus_vs_codex.py` (unified-trading-pm)
- Codex dir: `codex/09-strategy/architecture-v2/archetypes/`
- Registry: `unified_api_contracts.internal.architecture_v2.archetype_capability.ARCHETYPE_CAPABILITY_REGISTRY`
