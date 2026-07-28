"""MVP scope config + ``is_mvp()`` predicate — Phase 1.

This module is the UAC SSOT that defines which catalogue cells belong to
the **MVP scope** (a strict, rules-derived SUBSET of the could-exist
universe). No manifest column is ever written: membership is evaluated
on-the-fly by consumers (instruments-service catalogue view,
deployment-api data-status endpoint) via the :func:`is_mvp` predicate.

Hierarchy (from largest to smallest):
    ALL instrument types  ⊇  could-exist universe  ⊇  MVP scope

Grain of the rule (everything-or-nothing):
    ``(asset_group, venue, instrument_type, data_type[, base_ccy])``

    For sports: ``+ league``
    For prediction: ``+ market_group``

A cell is MVP iff its ``(venue, instrument_type)`` pair is declared in
the rule for its ``asset_group`` AND every other declared axis matches.
A ``(venue, instrument_type)`` absent from the rule → could-exist but
NOT MVP → ``is_mvp()`` returns ``False``.

Per-instrument-type grain note:
    If ``(venue, instrument_type)`` is declared as MVP, ALL of that
    venue's catalogued expiries/strikes/markets for that instrument_type
    are in-scope. The grain is NOT per-expiry, per-strike, or per-turn.
    (See the grain test in ``tests/unit/test_mvp_scope.py``.)

Phase-1 scope:
    Config + predicate + exports + tests.
    IS catalogue view (Phase 2) and deployment-api endpoint (Phase 3)
    are NOT part of this phase.

TODO(mvp-scope): operator sign-off on final membership before Phase 2
    integration. Items marked ``# TODO(mvp-scope)`` below need explicit
    operator confirmation. Conservative defaults are used until sign-off.

SSOT: ``plans/active/mvp_scope_catalogue_tagging_2026_06_08.md``.

Module layout (900-line file-size QG split, 2026-07-09; pure
file-organization move, no behavior change — every name below is
re-exported here unchanged so the public import path
``unified_api_contracts.canonical.crosscutting.mvp_scope`` is
byte-identical for every caller):
    * ``_mvp_scope_rules.py``     — the typed rule dataclasses + ``MVP_SCOPE``.
    * ``_mvp_scope_predicate.py`` — ``is_mvp`` + venue/data_type matching.
    * ``_mvp_scope_capture.py``   — ``is_in_mvp_capture_universe`` (perp-gate).
    * ``_mvp_scope_mdps.py``      — ``mdps_mvp_universe`` (MDPS == MDS universe).
"""

from __future__ import annotations

from typing import Final

from unified_api_contracts.canonical.crosscutting._mvp_scope_capture import (
    is_in_mvp_capture_universe,
)
from unified_api_contracts.canonical.crosscutting._mvp_scope_mdps import (
    mdps_mvp_universe,
)
from unified_api_contracts.canonical.crosscutting._mvp_scope_predicate import (
    get_mvp_data_types_for_cefi_venue,
    get_mvp_data_types_for_cefi_venue_itype,
    is_model_mvp,
    is_mvp,
)
from unified_api_contracts.canonical.crosscutting._mvp_scope_rules import (
    MVP_SCOPE,
    TRADFI_MVP_OPTION_UNDERLYING_ROOTS,
    CeFiMvpRule,
    DeFiMvpRule,
    FeaturesModelsMvpStub,
    ModelsMvpRule,
    PredictionMvpRule,
    SportsMvpRule,
    TradFiMvpRule,
)
from unified_api_contracts.canonical.crosscutting.config_versioning import (
    ConfigDescriptor,
    canonical_config_repr,
    compute_config_content_hash,
)

__all__ = [
    "MVP_SCOPE",
    "MVP_SCOPE_CONFIG_HASH",
    "MVP_SCOPE_CONFIG_VERSION",
    "TRADFI_MVP_OPTION_UNDERLYING_ROOTS",
    "CeFiMvpRule",
    "ConfigDescriptor",
    "DeFiMvpRule",
    "FeaturesModelsMvpStub",
    "ModelsMvpRule",
    "PredictionMvpRule",
    "SportsMvpRule",
    "TradFiMvpRule",
    "get_mvp_data_types_for_cefi_venue",
    "get_mvp_data_types_for_cefi_venue_itype",
    "is_in_mvp_capture_universe",
    "is_model_mvp",
    "is_mvp",
    "mdps_mvp_universe",
    "mvp_scope_config_descriptor",
]

# Re-exported (the generic descriptor type now lives in ``config_versioning``;
# kept importable here + at the package root for backwards compatibility).
_canonical_repr = canonical_config_repr


# ---------------------------------------------------------------------------
# Config versioning — monotonic version + deterministic content hash.
#
# Per the audit (mvp_scope_catalogue_tagging § "Config versioning"): so a
# coverage delta in data-status attributes to a SCOPE change vs a DATA change,
# carry a (config_version, config_content_hash) descriptor. Bump
# MVP_SCOPE_CONFIG_VERSION whenever MVP_SCOPE content changes; the hash is
# computed at module load and flips IFF the content flips. NOT a GCS key.
# ---------------------------------------------------------------------------


MVP_SCOPE_CONFIG_VERSION: Final[int] = 21
"""Monotonic version of :data:`MVP_SCOPE`. Bump on any content change.

v21 (2026-07-28): ``MVP_SCOPE["models"]`` graduated from the ``FeaturesModelsMvpStub``
placeholder to a typed :class:`ModelsMvpRule` (P2b —
mvp_scope_catalogue_tagging_2026_06_08.md, corrected 2026-07-27: the "no stable
model_id MVP taxonomy" blocker was stale — ``generate_model_id``/``parse_model_id``
in ``ml-service/ml_service/training/ml/config_schema.py`` already provide a
stable, versioned identity scheme). New :func:`is_model_mvp` predicate matches on
the decomposed ``{ASSET_GROUP}_{ASSET}_{TARGET_TYPE}_{MODEL_TYPE}_{TIMEFRAME}_V{N}``
identity axes — a SEPARATE grain from every other rule above (no venue/
instrument_type/data_type; UAC never imports ml-service, so callers parse a raw
model_id string locally and pass the components in). Ships with a CONSERVATIVE
EMPTY default (every axis frozenset empty, so ``is_model_mvp`` returns ``False``
for every model_id today) — there is no existing ml-service model-OUTPUT
tracking/manifest surface to derive an objective default from (unlike DeFi's
v13 "everything we currently produce" derivation), and concrete membership is a
genuine Phase-3 operator-policy call, not part of this identity-axis wiring.
``features``/``strategy`` are UNCHANGED (still ``FeaturesModelsMvpStub`` — P2a,
a separate dispatch). The data-status coverage CONSUMER for ml-service model
output (extending the ``scope=mvp|could_exist|all`` pattern from
``deployment-api@3390c98`` to models) is NOT part of this version bump — no
model-output manifest/tracking surface exists yet to build a coverage endpoint
against; tracked as a follow-up in the P2b plan todo, not guessed at here.

v20 (2026-07-21): DERIBIT-COMBO fully deregistered from ``CeFiMvpRule`` (operator
decision, verbatim: "delete everything to do with deribit combo since it is [a]
once venue in practice — manifest/GCS path wise etc. all migrated to split
venue+instrument_type"). Re-verified data-safe before removal: 0 captured rows
(196 total manifest rows, none ``captured``) and 0 GCS objects. Reverts v12's
``venues`` membership + ``venue_data_types`` override ({trades, book_snapshot_5})
and v16's ``COMBO`` instrument_type addition (DERIBIT-COMBO was the ONLY CeFi
consumer of "COMBO"; TradFi's separate ``TradFiMvpRule`` instance keeps its own
independent "COMBO" declaration for Databento spread/bag instruments,
unaffected). See market_data_categories.py's VENUES_BY_ASSET_GROUP["cefi"]
comment for the full deregistration rationale across all UAC registries.

v19 (2026-07-21): TradFi MVP-set expansion (operator directive) — four new
instrument groups flipped into tradfi MVP. (1) CME crypto FUTURES: BTC/ETH
full-size + MBT/MET micro roots added to ``TradFiMvpRule.underliers`` (FUTURE
cells only; ``option_underliers``={"ES"} keeps CME BTC/ETH OPTIONS out, per the
operator's "no CME option for BTC and ETH"). (2) CBOE VIX (VX) futures,
(3) the daily US Treasury-yield INDEX tenors (US2Y/US5Y/US10Y/US30Y/US3M,
Yahoo ohlcv_24h), and (4) the FX KRW-USD spot pair, all added as declarative
``TradFiMvpRule.extra_mvp_cells`` (venue_root, instrument_type, base) triples so
the predicate tags exactly those cells WITHOUT widening the flat
venue/type/underlier sets (which would over-tag — e.g. the ~33k CBOE SPX/VIX
OPTION rows). The prior tradfi MVP set (CME futures complex ES/NQ/VX + the 7
commodity roots + CME ES options + the NASDAQ/NYSE/KRX equity-basis carve-out +
IBIT/ETHA ETFs) is UNCHANGED. NOTE: ``mdps_mvp_universe("tradfi")`` and
``expected_coverage`` enumerate ``venues x instrument_types`` (+ the equity-basis
carve-out) and do NOT read ``underliers``/``extra_mvp_cells``, so the four new
groups are catalogue-MVP-tagged + download-covered but not yet in those two
enumerations — a tracked follow-up, not part of this scope.

v18 (2026-07-18): ``book_snapshot_5`` added to ``PredictionMvpRule.data_types``
(prediction_consolidated_closeout_2026_07_18.md P1 reconcile). It was already in
the OTHER two prediction registries — ``DATA_TYPES_BY_ASSET_GROUP["prediction"]``
+ ``VENUE_DATA_TYPE_CAPABILITIES["POLYMARKET"/"KALSHI"]`` +
``expected_coverage._PREDICTION`` (all re-added 2026-06-23 when both CLOB venues
began genuinely emitting the top-5 depth ladder) — and the depth data is captured
(live A0 measured 399,713 book_snapshot_5 prediction rows), but was ABSENT from
this MVP rule, so a plain MTDS matrix gave 4 shards
({POLYMARKET,KALSHI} x {trades,book_snapshot_5}) while ``--mvp-only`` silently
tested only ``trades`` (2 shards). This aligns the outlier rule with the other
registries + the captured data. No OTHER asset_group's data_types set changes
(cefi/tradfi/defi/sports MVP sets are unchanged — see
``TestPredictionReconcileCrossAgUnchanged``).

v17 (2026-07-18): 26 LST / restaking / vault DeFi venues onboarded to the
IS-producible set P (``instruments-service`` wired their factory adapters — which
already had populated curated registries — into ``_build_defi_venues()``), so they
flip ``DEFI_VENUE_PHASE`` "pipeline"→"live" and, since ``_mvp_defi_venues()`` == P,
become MVP automatically (the "newly-live ⇒ MVP" derivation). New: ROCKETPOOL /
RENZO(ETH,ARB) / KELPDAO / PUFFER / KARAK(ETH,ARB) / SYMBIOTIC / YEARN_V3(ETH,ARB) /
BEEFY(ETH,ARB,BASE,AVAX,BSC) / PENDLE(ETH,ARB) / CONVEX / IDLE-ETHEREUM /
SANCTUM / SOLBLAZE / JITORESTAKING / SOLANA-NATIVE (Solana) + 2 new single-token
LST adapters COINBASE-ETHEREUM (cbETH) / BINANCE-ETHEREUM,BINANCE-BSC (wBETH).
Empty-per-chain-registry venues (YEARN_V3-OPTIMISM / BEEFY-POLYGON / IDLE-ARBITRUM /
IDLE-POLYGON) stay "pipeline" (0 rows → not producible → not MVP), preserving the
MVP⊆P invariant. Same pattern as v13 (MarginFi/Solend onboarding).

v16 (2026-07-16): ``COMBO`` added to ``CeFiMvpRule.instrument_types`` (operator
decision on cefi_deribit_combo_and_okx_bare_venue_gaps_2026_07_12.md's
BLOCKED-OPERATOR-DECISION item, option (a)). The instruments-service catalogue
tags DERIBIT-COMBO rows with instrument_type ``"COMBO"`` (distinct from
``"OPTION"``), so ``is_mvp()`` unconditionally returned ``False`` for every
DERIBIT-COMBO catalogue row (68,847 rows, fully backfilled 2026-07-14) despite
DERIBIT-COMBO already being a declared MVP venue with its own
``venue_data_types`` override (``{trades, book_snapshot_5}``, operator decision
#6, 2026-07-10) — the venue-level work was silently inert without this
instrument_type entry. No other axis changes: the existing DERIBIT-COMBO
``venue_data_types`` override still wins over any per-instrument_type default
(so no phantom ``options_chain`` cell is minted), and "COMBO" only appears on
CeFi's DERIBIT-COMBO venue (TradFi's Databento spread/bag "COMBO" rows route
through the separate ``TradFiMvpRule`` instance, unaffected).

v15 (2026-07-15): ``liquidations`` restored as a PERPETUAL-leg CeFi MVP data_type
(cefi_completion_program_2026_07_15.md workstream E). New
``CeFiMvpRule.instrument_type_data_types["PERPETUAL"]`` override = the flat tick
set + ``liquidations`` (a FULL replacement for PERPETUAL cells; the flat
``data_types`` set is UNCHANGED, so SPOT_PAIR/EQUITY_PERP/FUTURE do NOT gain
``liquidations``). liquidations is densely captured (732,751 captured PERPETUAL
manifest rows, 99.95% of all captured cefi liquidations) but had been excluded
from CeFiMvpRule since 2026-06-29, contradicting the un-superseded
``mvp-universe.yaml`` ("liquidations P1-critical for CEFI"); CeFiMvpRule is now
the live SSOT. The VENUE axis is gated by ``VENUE_DATA_TYPE_CAPABILITIES`` to the
6 real-feed perp venues (BINANCE-FUTURES/OKX-SWAP/BYBIT/KRAKEN-FUTURES/
BITFINEX-FUTURES/BITGET-FUTURES); the same pass REMOVED ``liquidations`` from the
gate for ASTER (live-only, 0 batch captures — live-only must not seed the batch
denominator), DERIBIT (3 noise rows), and bare OKX (lives on OKX-SWAP). The
instruments-service expected-universe enumerator consumes the new itype-aware
``get_mvp_data_types_for_cefi_venue_itype`` helper so the per-instrument_type
override narrows the denominator WITHOUT bypassing the per-venue
``venue_data_types`` overrides (COINBASE-FUTURES stays trades-only — no regress).

v14 (2026-07-14): TradFi MVP OPTION underlier narrowing (operator ruling,
tradfi_eu_not_draining_source_axis_drift_2026_06_24.md, verbatim: "We DO want
tradfi options for S&P 500 — options and futures — but NO other options in
tradfi MVP; just the single stocks, ETFs and futures already in MVP."). New
``TradFiMvpRule.option_underliers`` field (mirrors the existing CeFi
``options_base_ccys`` narrower-options-carve-out pattern) narrows OPTION-cell
MVP membership to ``TRADFI_MVP_OPTION_UNDERLYING_ROOTS = frozenset({"ES"})`` —
the S&P 500 / ES complex ONLY. Before this change every OPTION cell inherited
the full ``underliers`` set (ES/NQ/VX/GC/SI/PL/PA/NG/CL/HG) with no
OPTION-specific narrowing, which is why the 2026-07-14 tradfi catalogue regen
tagged ALL 739,278 real CME OPTION rows ``mvp=True`` (every one of those
options resolves to one of those 10 roots). FUTURE cells, the equity-basis
carve-out, and single stocks/ETFs are UNCHANGED — this narrowing applies to
``instrument_type == "OPTION"`` only.

v13 (2026-07-09): DeFi MVP framing defined — "everything we capture" (operator
ruling on ``defi_perp_funding_mvp_scope_contradiction_2026_06_29.md`` §E5).
Previously DeFi had no dedicated MVP set distinct from the factory registry;
the prior ``DeFiMvpRule`` (v10-v12) was a curated 11-venue Ethereum/3-Solana-DEX
subset, unlike cefi/tradfi/sports/prediction which each have a real,
deliberately-narrowed MVP rule. New ruling: DeFi MVP == the full current
capture universe — every IS-producible venue (``_mvp_defi_venues()`` ==
``VENUES_BY_ASSET_GROUP["defi"]``, 57 venues, up from 11), every real
instrument_type a live venue adapter emits (9 values, up from 4 — adds
A_TOKEN/DEBT_TOKEN/YIELD_BEARING/PERPETUAL/STAKING; drops the never-real
``DEX_POOL`` placeholder), and every DeFi data_type
(``_mvp_defi_data_types()`` == the full ``DATA_TYPES_BY_ASSET_GROUP["defi"]``
list, up from a curated 6-entry subset). The Decision-D invariant "every
DeFi-MVP venue is IS-producible" is preserved (venues derive from P, not the
broader ``ALL_DEFI_VENUES`` declarative registry) — ROCKETPOOL-ETHEREUM stays
excluded. Same pass wired 2 new real Solana lending adapters (MarginFi,
Solend) into instruments-service + flipped their ``DEFI_VENUE_PHASE`` to
"live", growing P from 55 to 57.

v12 (2026-06-29): DeFi MVP-exclusion (Decision D —
instrument_universe_registry_consolidation_2026_06_29.md): remove
``ROCKETPOOL-ETHEREUM`` from ``DeFiMvpRule.venues``. ROCKETPOOL-ETHEREUM is
NOT in the IS-producible set P (as confirmed by running ``_build_defi_venues()``
in the IS venv). All other ``DeFiMvpRule.venues`` ARE in P.

v11 (2026-06-28): operator per-venue data_type cut (decision A — cost
reduction, no depth features derived from Coinbase):
  A. COINBASE-SPOT + COINBASE-FUTURES → **trades ONLY** (no book_snapshot_5).
     Coinbase depth backfill VMs are extremely heavy (~30 GB pandas peak for
     BTC-USD book5 days). No depth features are derived from Coinbase
     specifically. Implemented via new ``CeFiMvpRule.venue_data_types`` field
     (the first per-venue override; analogous to the existing per-instrument_type
     override for OPTIONs). All other cefi venues unchanged — they keep
     trades + book_snapshot_5. Deribit is UNCHANGED from v10: OPTION remains
     options_chain-only (``instrument_type_data_types``); PERP/FUTURE/SPOT remain
     trades + book_snapshot_5 (wanted for Deribit perp/future tick capture).

v10 (2026-06-27): operator's CANONICAL MVP definition (7 decisions reconciling
the prior audit's drifts):
  1. SPORTS 94-league FIX — sports MVP leagues = the 94 ``sport == "FOOTBALL"``
     leagues (``_mvp_football_league_ids()``), not the 2-league EPL+LA_LIGA
     literal. The 7 non-football leagues (NFL/NBA/MLB/NHL/ATP/WTA/EUROLEAGUE)
     are no longer MVP.
  2. CEFI Deribit OPTION → ``options_chain`` ONLY (cost cut) — new
     ``CeFiMvpRule.instrument_type_data_types`` override (OPTION ->
     {options_chain}); per-strike trades + book_snapshot_5 EXCLUDED for options.
     Perps/spot/dated-futures unchanged (trades + book_snapshot_5 + funding).
  3. DROP ``BINANCE-DELIVERY`` from the cefi MVP venues (COIN-M delivery not
     MVP). Other venues' dated/quarterly futures STAY MVP (FUTURE type).
  4. LIGHTER-ZKSYNC / EXTENDED-STARKNET / PACIFICA (Solana) added to the cefi
     MVP venues (CLOB perp DEXs, classified cefi everywhere — reconciled vs
     the instruments-side which already had them cefi). PACIFICA (Solana)
     removed entirely 2026-07-16 — operator ruling: all Solana perp DEXes
     dropped except Jupiter, not integrated.
  5. PREDICTION KALSHI flipped in-MVP — prediction MVP = the Kalshi↔Polymarket
     arb-overlap (needs BOTH venues). TODO resolved.
  7. TRADFI data_types narrowed to ``ohlcv_1m`` ONLY (no ohlcv_1s/trades); CME
     OPTION stays an MVP instrument_type so CME options tag MVP at ohlcv_1m once
     ingested.
(Decision #6 — sports structural honest-absence — is encoded in the sibling
``sports_structural_gaps.py`` registry, not in MVP_SCOPE membership.)

v9 (2026-06-24): added ``BINANCE-DELIVERY`` (Binance COIN-M inverse/delivery
perps + dated futures) to the CeFi MVP scope venues. Inverse perps (e.g.
BTCUSD_PERP) captured on base-membership via PERPETUAL + FUTURE paths, same
CEFI_BASE_ASSET_UNIVERSE as linear venues. cefi_universe_capture_rule 2026-06-24.

v8 (2026-06-23): added 8 CeFi venues to the cefi rule ``venues`` set
(BYBIT-SPOT, COINBASE-SPOT, COINBASE-FUTURES, BITFINEX-SPOT, BITFINEX-FUTURES,
BITGET-SPOT, BITGET-FUTURES, UPBIT) — previously ABSENT so their cells were mvp=0
regardless of the perp-gate (cefi_universe_capture_rule 2026-06-23). Added the
**UPBIT venue carve-out** to :func:`is_in_mvp_capture_universe`
(``_CEFI_SPOT_PERP_GATE_EXEMPT_VENUES``): UPBIT spot is mvp=true REGARDLESS of
perp existence (the ONE spot-only venue exception — kimchi premium). KRW quote
acceptance for UPBIT is handled at the IS ``_passes_asset_filter`` gate via the UAC
``accepted_quotes_for_venue`` SSOT (registry/cefi_instrument_universe.py).

v7 (2026-06-23): expanded ``STAKING_SPOT_EXCEPTION`` from 13 → 28 members to
cover ALL wrapped + unwrapped LST/LRT equivalents (operator 2026-06-23,
cefi_universe_capture_rule — forward-looking allow-list, harmless extras). Added
ETH LSTs/LRTs FRXETH/SFRXETH (Frax), ANKRETH (Ankr), OSETH (StakeWise),
SWETH/RSWETH (Swell), ETHX (Stader), METH (Mantle), RSETH (Kelp), EZETH (Renzo),
PUFETH (Puffer), RSTETH; + SOL LSTs JSOL, SCNSOL, INF (Sanctum). Each is ALSO
added to ``CEFI_BASE_ASSET_UNIVERSE`` (subset invariant holds) so the cefi
``base_ccys`` content-hash flips with the constant.

v6 (2026-06-23): added the **staking-spot exception** to
:func:`is_in_mvp_capture_universe` — a base in ``STAKING_SPOT_EXCEPTION``
(EIGEN/KING/ETHFI restaking + STETH/WSTETH/RETH/WEETH/EETH/CBETH ETH-LSTs +
MSOL/JITOSOL/JTO/BSOL SOL-LSTs) has its SPOT captured on ANY venue that lists it
REGARDLESS of perp existence (the ONLY spot-without-perp carve-out; operator
2026-06-23, cefi_universe_capture_rule). Also expanded ``CEFI_BASE_ASSET_UNIVERSE``
by the 7 previously-absent LSTs (WSTETH/RETH/WEETH/EETH/MSOL/JITOSOL/BSOL) so the
base-membership leg passes for them — the cefi ``base_ccys`` content-hash flips
with the constant.

v5 (2026-06-23): added :func:`is_in_mvp_capture_universe` — the perp-gated CeFi
capture predicate (operator 2026-06-23). It composes the base-membership /
instrument-type / Deribit-options / TradFi-perp rules of :func:`is_mvp` with the
HARD perp-gate (a spot/dated-future cell is in-universe ONLY IF the venue also
lists a perp for the same base). ``MVP_SCOPE`` rule *content* is unchanged, but
the predicate surface (what "MVP capture universe" means) changed, so the
version bumps. ``cefi_universe_capture_rule_2026_06_23``.

v4 (2026-06-23): ``CEFI_BASE_ASSET_UNIVERSE`` expanded from the 44-coin MVP cap
to the curated, survivorship-bias-free capture set (legacy-44 +
top-100-mcap-aggregated-since-2019 + HL/ASTER perp bases, ~490 assets). CeFi
``base_ccys`` therefore now spans that wider universe; the content hash flips
automatically with the constant. ``options_base_ccys`` unchanged (BTC+ETH).

v3 (2026-06-17): CeFi venue set reconciled from the bare ``OKX`` token to the
canonical sub-venues ``OKX-SPOT`` / ``OKX-SWAP`` / ``OKX-FUTURES`` (the form the
instruments-store catalogue + the rest of the pipeline use), so OKX instruments
tag MVP. A bare ``OKX`` caller still resolves via the predicate's base-venue-token
normalisation (``_cefi_venue_in_rule``). Also introduced the unbound-data_type
convention in ``is_mvp`` (``data_type`` blank → "any MVP data_type") — predicate
behaviour, not config content, but versioned together. (mvp_instrument_universe_gap_audit
P2 #1 + #2.)

v2 (2026-06-17): CeFi ``base_ccys`` reconciled from the 4-base BTC/ETH/SOL/USDT
set to the (then) 44-base ``CEFI_BASE_ASSET_UNIVERSE`` (operator-confirmed SSOT),
added ``OPTION`` to CeFi ``instrument_types``, and added the Deribit-options
carve-out (``options_base_ccys = CEFI_OPTIONS_UNDERLYINGS`` = BTC+ETH only). The
content hash flips automatically with the version + content change.
"""


def _compute_mvp_scope_content_hash() -> str:
    """SHA-256 (16-hex prefix) of the canonical MVP_SCOPE content + version."""
    return compute_config_content_hash(
        MVP_SCOPE_CONFIG_VERSION,
        [(asset_group, MVP_SCOPE[asset_group]) for asset_group in sorted(MVP_SCOPE)],
    )


MVP_SCOPE_CONFIG_HASH: Final[str] = _compute_mvp_scope_content_hash()
"""Content hash of :data:`MVP_SCOPE` — flips IFF the scope content changes."""


def mvp_scope_config_descriptor() -> ConfigDescriptor:
    """Return the :data:`MVP_SCOPE` ``(version, content-hash)`` descriptor."""
    return ConfigDescriptor(MVP_SCOPE_CONFIG_VERSION, MVP_SCOPE_CONFIG_HASH)
