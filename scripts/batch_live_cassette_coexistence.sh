#!/usr/bin/env bash
# STEP 5.7X — Batch-Live WS cassette coexistence check.
#
# Enforces: every true WebSocket connector in MTDS live/connectors/*_ws.py must
# have at least one *_ws.yaml cassette in the matching UAC external/<venue>/mocks/.
#
# REST-polling connectors named *_ws.py are explicitly excluded (see POLLERS below).
#
# Usage:
#   bash scripts/batch_live_cassette_coexistence.sh [--workspace <workspace_root>]
#
# Exit 0 = all WS connectors have cassettes.
# Exit 1 = one or more connectors missing WS cassette.
#
# SSOT: plans/active/canary_coverage_qg_enforcement_2026_05_20.md Phase 4.
set -euo pipefail

# ---------------------------------------------------------------------------
# Defaults — resolve workspace root from repo position
# ---------------------------------------------------------------------------
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Allow override for non-standard workspace layouts
WORKSPACE_ROOT="${WORKSPACE_ROOT:-$(cd "$REPO_ROOT/.." && pwd)}"
# .tabs/2/ is two levels up from unified-api-contracts
if [[ "${WORKSPACE_ROOT}" == *"/.tabs/"* ]]; then
    TABS_DIR="$(dirname "$WORKSPACE_ROOT")"
    WORKSPACE_ROOT="$(dirname "$TABS_DIR")"
fi

MTDS_CONNECTORS="${WORKSPACE_ROOT}/.tabs/2/market-tick-data-service/market_tick_data_service/live/connectors"
UAC_EXTERNAL="${REPO_ROOT}/unified_api_contracts/external"

RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

# ---------------------------------------------------------------------------
# REST pollers named *_ws.py — excluded from coexistence check
# ---------------------------------------------------------------------------
POLLERS=(
    "curve_defi_ws"
    "jito_defi_ws"
    "morpho_defi_ws"
    "odds_api_ws"
    "phoenix_ws"
    "polymarket_ws"
)

# ---------------------------------------------------------------------------
# Connector → UAC venue mapping
# ---------------------------------------------------------------------------
declare -A CONNECTOR_VENUE=(
    ["aster_ws"]="aster"
    ["binance_futures_ws"]="binance"
    ["binance_spot_ws"]="binance"
    ["bybit_ws"]="bybit"
    ["bybit_spot_ws"]="bybit"
    ["coinbase_spot_ws"]="coinbase"
    ["databento_tradfi_ws"]="databento"
    ["deribit_ws"]="deribit"
    ["drift_solana_ws"]="drift"
    ["hyperliquid_ws"]="hyperliquid"
    ["hyperliquid_l2book_ws"]="hyperliquid"
    ["hyperliquid_ticker_ws"]="hyperliquid"
    ["kalshi_ws"]="kalshi"
    ["kraken_futures_ws"]="kraken_futures"
    ["kraken_spot_ws"]="kraken"
    ["okx_ws"]="okx"
    ["okx_spot_ws"]="okx"
)

# ---------------------------------------------------------------------------
# Main check
# ---------------------------------------------------------------------------
if [[ ! -d "$MTDS_CONNECTORS" ]]; then
    echo -e "${RED}❌ STEP 5.7X: MTDS connectors dir not found: ${MTDS_CONNECTORS}${NC}"
    echo "   Check WORKSPACE_ROOT or run from workspace: WORKSPACE_ROOT=<path> bash $0"
    exit 1
fi

FAILURES=0
PASSED=0

is_poller() {
    local stem="$1"
    for p in "${POLLERS[@]}"; do
        [[ "$stem" == "$p" ]] && return 0
    done
    return 1
}

while IFS= read -r connector_file; do
    stem="$(basename "$connector_file" .py)"
    is_poller "$stem" && continue

    venue="${CONNECTOR_VENUE[$stem]:-}"
    if [[ -z "$venue" ]]; then
        echo -e "${RED}❌ STEP 5.7X: connector '$stem' not in CONNECTOR_VENUE map — update $0${NC}"
        FAILURES=$((FAILURES + 1))
        continue
    fi

    mocks_dir="${UAC_EXTERNAL}/${venue}/mocks"
    found=0
    for f in "${mocks_dir}"/*_ws.yaml; do
        [[ -f "$f" ]] && { found=1; break; }
    done

    if [[ $found -eq 1 ]]; then
        PASSED=$((PASSED + 1))
        echo -e "  ✅ ${stem} → ${venue}/mocks/*_ws.yaml"
    else
        echo -e "${RED}  ❌ ${stem} → ${venue}/mocks/ (no *_ws.yaml found)${NC}"
        FAILURES=$((FAILURES + 1))
    fi
done < <(find "$MTDS_CONNECTORS" -maxdepth 1 -name "*_ws.py" | sort)

echo ""
if [[ $FAILURES -eq 0 ]]; then
    echo -e "${GREEN}✅ STEP 5.7X: Batch-Live WS cassette coexistence OK (${PASSED} connectors)${NC}"
    exit 0
else
    echo -e "${RED}❌ STEP 5.7X: ${FAILURES} WS connector(s) missing cassettes. Create *_ws.yaml per Phase 4.${NC}"
    exit 1
fi
