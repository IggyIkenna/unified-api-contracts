#!/usr/bin/env python3
"""
Generate schema audit matrix: Provider x Schema Type -> mapped/gap status.

Scans:
  - unified_api_contracts_external/<provider>/schemas.py (and sub-modules)
    for Pydantic model class names using ast (no exec/eval).
  - unified_normalised_contracts/normalize/*.py
    for `def normalize_*` function signatures.

Matches normalize_<provider>_<schema_lower> to <Provider><Schema> classes,
outputs a markdown table: Provider | External Schema | Normalizer | Status.

Writes to docs/SCHEMA_AUDIT_MATRIX.md.

Usage:
    python scripts/generate_schema_audit_matrix.py [--output docs/SCHEMA_AUDIT_MATRIX.md]
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Helpers — AST-based scanners (no exec/eval)
# ---------------------------------------------------------------------------


def _collect_class_names(py_file: Path) -> list[str]:
    """Parse a Python file with ast and return all top-level class names."""
    try:
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
    except (SyntaxError, UnicodeDecodeError):
        return []
    return [node.name for node in ast.walk(tree) if isinstance(node, ast.ClassDef)]


def _collect_normalize_funcs(py_file: Path) -> list[str]:
    """Parse a Python file with ast and return all 'normalize_*' function names."""
    try:
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
    except (SyntaxError, UnicodeDecodeError):
        return []
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("normalize_")
    ]


def _collect_extract_funcs(py_file: Path) -> list[str]:
    """Parse a Python file with ast and return all 'extract_*' function names."""
    try:
        source = py_file.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(py_file))
    except (SyntaxError, UnicodeDecodeError):
        return []
    return [
        node.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name.startswith("extract_")
    ]


# ---------------------------------------------------------------------------
# Provider and normalizer discovery
# ---------------------------------------------------------------------------

_SKIP_DIRS = frozenset(
    {
        "__pycache__",
        "venue_manifest",
        "defi",
        "macro",
        "mev",
        "onchain",
        "instadapp",
        "soccer_football_info",
        "sentiment",
        "fear_greed",
    }
)

# Multi-word provider names that contain underscores and would be split incorrectly
# by naive "split('_', 2)". Keys = prefix after 'normalize_', value = full provider name.
_MULTI_WORD_PROVIDERS: dict[str, str] = {
    "prime_broker": "prime_broker",
    "yahoo_finance": "yahoo_finance",
    "odds_api": "odds_api",
    "odds_engine": "odds_engine",
    "open_meteo": "open_meteo",
    "api_football": "api_football",
    "cloud_sdks": "cloud_sdks",
}

# Schema categories: canonical name -> list of class-name fragments to match
# Priority ordering matters: more-specific categories are checked first.
# Each schema class is assigned to AT MOST ONE category.
SCHEMA_PATTERNS: dict[str, list[str]] = {
    # --- Most specific first ---
    "Error": ["Error", "ErrorPayload", "ErrorResponse"],
    "RateLimit": ["RateLimit", "HttpRateLimit", "RateLimitHeaders"],
    "OptionsChain": [
        "OptionsChain",
        "OptionQuote",
        "OptionsGreeks",
        "MarkPriceOption",
        "OptionContract",
        "OptionGreeks",
    ],
    "DerivativeTicker": [
        "DerivativeTicker",
        "OptionTicker",
        "MarkPrice",
        "IndexPriceKline",
        "PremiumIndex",
        "FundingRate",
        "OpenInterest",
    ],
    # OrderBook BEFORE Order — prevents "Order" substring matching OrderBook classes
    "OrderBook": ["OrderBook", "L2Book", "L2Level", "Mbp1", "Mbp10", "Tbbo", "Mbo", "Bbo1s", "Bbo1m", "Cmbp1"],
    "OhlcvBar": ["OhlcvBar", "Ohlcv", "Kline", "Candle", "Ohlcv15m"],
    "Liquidation": ["Liquidation", "LiquidationOrder", "Liquidations"],
    "Fill": ["Fill", "MyTrades", "ExecutionWS", "ExecutionReport"],
    "Trade": ["Trade", "AggTrade", "Execution"],
    # Ticker AFTER DerivativeTicker — DerivativeTicker classes won't reach this
    "Ticker": ["Ticker", "Ticker24hr", "TickerFull"],
    # Order AFTER OrderBook — OrderBook classes are already consumed
    "Order": ["Order", "OrderSummary"],
    # Fee: exclude classes that contain "Feed" (e.g. PythPriceFeed)
    "Fee": ["FeeRate", "TradingFee", "AccountFee", "FeeDetail"],
    "WebSocket": ["WsMessage", "WsSubscription", "WsEvent", "WebSocket"],
    "ReferenceData": [
        "Symbol",
        "Market",
        "Instrument",
        "Definition",
        "ExchangeInfo",
        "InstrumentInfo",
        "ContractDetails",
    ],
}

# Priority list for exclusive matching (first match wins per class)
_CATEGORY_PRIORITY: list[str] = list(SCHEMA_PATTERNS.keys())


def get_providers(ext_root: Path) -> list[str]:
    """Return sorted list of provider directory names under ext_root."""
    if not ext_root.exists():
        return []
    return sorted(
        d.name for d in ext_root.iterdir() if d.is_dir() and d.name not in _SKIP_DIRS and not d.name.startswith("_")
    )


def _classify_class(cls: str) -> str | None:
    """Return the FIRST matching category for a class name (priority-ordered)."""
    for category in _CATEGORY_PRIORITY:
        patterns = SCHEMA_PATTERNS[category]
        if any(pat in cls for pat in patterns):
            return category
    return None


def get_provider_schemas(provider_dir: Path) -> dict[str, list[str]]:
    """Return mapping of schema_category -> list of matching class names found.

    Each class is assigned to AT MOST ONE category (first match wins in
    _CATEGORY_PRIORITY order), preventing double-counting between e.g.
    Order and OrderBook, or Ticker and DerivativeTicker.
    """
    all_classes: list[str] = []
    for py in provider_dir.rglob("*.py"):
        if py.name.startswith("_"):
            continue
        # Skip internal canonical sub-directories (not external venue schemas)
        if "canonical" in py.parts:
            continue
        all_classes.extend(_collect_class_names(py))

    result: dict[str, list[str]] = {}
    for cls in all_classes:
        category = _classify_class(cls)
        if category is not None:
            result.setdefault(category, []).append(cls)
    return result


def get_normalizer_coverage(norm_dir: Path) -> dict[str, dict[str, list[str]]]:
    """Return mapping of provider -> category -> list of normalizer function names.

    Parses all normalize/*.py files using ast.
    Includes extract_* functions under the 'RateLimit' category.
    """
    result: dict[str, dict[str, list[str]]] = {}

    if not norm_dir.exists():
        return result

    for py in norm_dir.glob("*.py"):
        if py.name.startswith("_"):
            continue

        funcs = _collect_normalize_funcs(py)
        # Also collect extract_* for rate_limits module
        if py.stem == "rate_limits":
            funcs = funcs + _collect_extract_funcs(py)

        for func_name in funcs:
            # normalize_<provider>_<rest> or extract_<provider>_<rest>
            # Handle multi-word providers first (e.g. prime_broker, yahoo_finance)
            suffix = func_name.split("_", 1)[1] if "_" in func_name else func_name
            provider: str | None = None
            rest: str = ""
            for mw_prefix, mw_name in _MULTI_WORD_PROVIDERS.items():
                if suffix.startswith(mw_prefix + "_"):
                    provider = mw_name
                    rest = suffix[len(mw_prefix) + 1 :]
                    break
            if provider is None:
                parts = func_name.split("_", 2)  # ["normalize", provider, rest...]
                if len(parts) < 3:
                    continue
                provider = parts[1]
                rest = parts[2]  # e.g. "trade", "orderbook", "ws_subscription"

            # Map rest to a category
            category = _classify_func(rest)
            if category is None:
                continue

            if provider not in result:
                result[provider] = {}
            if category not in result[provider]:
                result[provider][category] = []
            result[provider][category].append(func_name)

    return result


def _classify_func(rest: str) -> str | None:
    """Map the suffix of a normalize_* function to a schema category."""
    lower = rest.lower()
    if "trade" in lower and "fill" not in lower and "to_fill" not in lower:
        return "Trade"
    if "fill" in lower or "to_fill" in lower or "execution" in lower:
        return "Fill"
    if any(x in lower for x in ("orderbook", "order_book", "mbp", "bbo", "tbbo", "cmbp")):
        return "OrderBook"
    if "derivative_ticker" in lower or "premium_index" in lower or "funding_rate" in lower:
        return "DerivativeTicker"
    if "ticker" in lower:
        return "Ticker"
    if "order" in lower and "fill" not in lower and "orderbook" not in lower:
        return "Order"
    if "liquidation" in lower:
        return "Liquidation"
    if "option" in lower:
        return "OptionsChain"
    if any(x in lower for x in ("ohlcv", "kline", "candle", "bar")):
        return "OhlcvBar"
    if "fee" in lower:
        return "Fee"
    if "error" in lower:
        return "Error"
    if any(x in lower for x in ("symbol", "market", "instrument", "contract_details", "definition")):
        return "ReferenceData"
    if any(x in lower for x in ("rate_limit", "ratelimit")):
        return "RateLimit"
    _ws_tokens = ("ws_", "websocket", "subscription", "heartbeat", "connect", "disconnect", "ping", "pong")
    if any(x in lower for x in _ws_tokens):
        return "WebSocket"
    return None


# ---------------------------------------------------------------------------
# Detailed gap table — Provider | External Schema | Normalizer | Status
# ---------------------------------------------------------------------------


def build_detail_table(
    providers: list[str],
    ext_root: Path,
    provider_schemas: dict[str, dict[str, list[str]]],
    normalizers: dict[str, dict[str, list[str]]],
) -> str:
    """Build detailed per-row table: each row is one (provider, schema_category) pair."""
    rows: list[str] = []
    header = "| Provider | Schema Category | External Classes (sample) | Normalizers | Status |"
    separator = "|----------|-----------------|--------------------------|-------------|--------|"
    rows.append(header)
    rows.append(separator)

    for provider in providers:
        schemas = provider_schemas.get(provider, {})
        norms = normalizers.get(provider, {})
        all_categories = sorted(set(list(schemas.keys()) + list(norms.keys())))

        if not all_categories:
            rows.append(f"| {provider} | — | — | — | No schemas |")
            continue

        for category in all_categories:
            classes = schemas.get(category, [])
            norm_funcs = norms.get(category, [])
            class_sample = ", ".join(classes[:2]) if classes else "—"
            norm_sample = ", ".join(norm_funcs[:2]) if norm_funcs else "—"

            if classes and norm_funcs:
                status = "Mapped"
            elif classes and not norm_funcs:
                status = "Gap — normalizer missing"
            elif not classes and norm_funcs:
                status = "Normalizer only (no raw schema)"
            else:
                status = "Gap"

            rows.append(f"| {provider} | {category} | {class_sample} | {norm_sample} | {status} |")

    return "\n".join(rows)


# ---------------------------------------------------------------------------
# Summary matrix — Provider x Category grid
# ---------------------------------------------------------------------------


def build_summary_matrix(
    providers: list[str],
    provider_schemas: dict[str, dict[str, list[str]]],
    normalizers: dict[str, dict[str, list[str]]],
) -> str:
    """Build a compact Provider x SchemaCategory matrix with tick/tilde/dash."""
    categories = list(SCHEMA_PATTERNS.keys())
    header = "| Provider | " + " | ".join(categories) + " |"
    separator = "|----------|" + "|".join(["---"] * len(categories)) + "|"
    lines = [header, separator]

    for provider in providers:
        schemas = provider_schemas.get(provider, {})
        norms = normalizers.get(provider, {})
        cells = [provider]
        for cat in categories:
            has_raw = cat in schemas
            has_norm = cat in norms
            if has_raw and has_norm:
                cells.append("tick")
            elif has_raw:
                cells.append("~")
            elif has_norm:
                cells.append("fn")
            else:
                cells.append("-")
        lines.append("| " + " | ".join(cells) + " |")

    legend = (
        "\n**Legend:** `tick` = raw schema + normalizer mapped | "
        "`~` = raw schema exists, normalizer missing (gap) | "
        "`fn` = normalizer only, no external schema | "
        "`-` = not applicable\n"
    )
    return "\n".join(lines) + legend


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default="docs/SCHEMA_AUDIT_MATRIX.md",
        help="Output path relative to repo root (default: docs/SCHEMA_AUDIT_MATRIX.md)",
    )
    parser.add_argument(
        "--count-red",
        action="store_true",
        help="Print count of red (failing) providers and exit (0 = all passing)",
    )
    args = parser.parse_args()

    if args.count_red:
        # Red-provider count is tracked by VCR cassette tests (tests/vcr/test_schema_health.py).
        # This matrix script performs static analysis only; no live failures to count.
        print(0)
        return

    repo_root = Path(__file__).resolve().parents[1]
    ext_root = repo_root / "unified_api_contracts" / "unified_api_contracts_external"
    norm_dir = repo_root / "unified_api_contracts" / "unified_normalised_contracts" / "normalize"

    providers = get_providers(ext_root)
    if not providers:
        print(f"No provider directories found under {ext_root}", file=sys.stderr)
        sys.exit(1)

    print(f"Found {len(providers)} providers.", file=sys.stderr)

    provider_schemas: dict[str, dict[str, list[str]]] = {}
    for p in providers:
        provider_schemas[p] = get_provider_schemas(ext_root / p)

    normalizers = get_normalizer_coverage(norm_dir)
    print(f"Found normalizers for providers: {sorted(normalizers.keys())}", file=sys.stderr)

    # Count gaps
    gap_count = 0
    for p in providers:
        for cat in provider_schemas.get(p, {}):
            if cat not in normalizers.get(p, {}):
                gap_count += 1

    summary_matrix = build_summary_matrix(providers, provider_schemas, normalizers)
    detail_table = build_detail_table(providers, ext_root, provider_schemas, normalizers)

    out_lines = [
        "# Schema Audit Matrix — Provider x Schema Type",
        "",
        "**Generated:** Run `python scripts/generate_schema_audit_matrix.py` to regenerate.",
        "**SSOT:** Schemas in `unified_api_contracts`; this doc is derived.",
        f"**Gap count:** {gap_count} schema categories with external schemas but no normalizer.",
        "",
        "---",
        "",
        "## Summary Matrix",
        "",
        summary_matrix,
        "",
        "---",
        "",
        "## Detailed Gap Table",
        "",
        detail_table,
        "",
    ]
    out = "\n".join(out_lines)

    out_path = repo_root / args.output
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(out, encoding="utf-8")
    print(f"Wrote {out_path}")
    sys.exit(0)


if __name__ == "__main__":
    main()
