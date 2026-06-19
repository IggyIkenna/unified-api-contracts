"""Databento subscription universe + billing-safety allowlist (SSOT).

We subscribe to EXACTLY three Databento datasets and ingest only the schemas
whose history is included free in that subscription. Anything outside this
allowlist would be billed pay-as-you-go (metered), so every code path that
talks to Databento MUST gate its (dataset, schema, start) tuple through the
``assert_*`` helpers here. The guards FAIL CLOSED (raise) — a disallowed
request never reaches the vendor, so we can never be billed silently.

Subscription (operator decision 2026-06-18):
  * ``GLBX.MDP3``  — CME Globex (S&P / BTC+ETH / gold / WTI+NatGas / FX / sector futures + options-on-futures)
  * ``DBEQ.BASIC`` — Databento US Equities (single stocks + ETFs incl. BTC/ETH/gold ETFs)
  * ``CFE``        — Cboe Futures Exchange (VIX / VX futures)

Included-history windows by schema LEVEL (the rolling, trailing-from-today
allowance — older than this is metered):
  * L0 (aggregate bars / definitions / statistics / status) — 16 years
  * L1 (trades / tbbo / mbp-1 / bbo)                          — 1 year
  * L2 (mbp-10)                                               — 1 month
  * L3 (mbo)                                                  — 1 month

OHLCV policy: we fetch ``ohlcv-1s`` AND ``ohlcv-1m`` (both L0 / free 16y) and
aggregate the coarser bars (15m/1h/1d) downstream — so ``ohlcv-1h`` /
``ohlcv-1d`` are NOT allowed as fetch schemas (they are derived, not fetched).
1m is kept because we already hold a large 1m corpus (completing it exercises
the migration/manifest/data-status path); 1s is the finer-grained add.

Batch policy: ``batch.submit_job`` is BANNED — it is the API most likely to
silently rack up a large metered bill. Use streaming (``timeseries.get_range``)
or the live client only. Re-downloading an already-completed legacy batch job
(``batch.download`` — free within TTL) is not gated here.

Codex SSOT: ``codex/02-data/tradfi-databento-sourcing-ssot.md``.
Plan: ``plans/active/tradfi_databento_subscription_universe_lockdown_2026_06_18.md``.
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta

# ── Datasets we pay for (everything else is metered → banned) ────────────────
ALLOWED_DATABENTO_DATASETS: frozenset[str] = frozenset(
    {
        "GLBX.MDP3",  # CME Globex
        "DBEQ.BASIC",  # Databento US Equities (single stocks + ETFs)
        "XCBF.PITCH",  # Cboe Futures Exchange (VIX / VX futures) — operator calls it "CFE"
    }
)

# ── Schema → Databento billing level ─────────────────────────────────────────
# Keys are the canonical hyphenated Databento schema strings.
DATABENTO_SCHEMA_LEVEL: dict[str, str] = {
    # L0 — aggregate bars + reference, 16-year included history.
    "ohlcv-1s": "L0",
    "ohlcv-1m": "L0",
    "ohlcv-1h": "L0",
    "ohlcv-1d": "L0",
    "definition": "L0",
    "statistics": "L0",
    "status": "L0",
    # L1 — top-of-book + trades, 1-year included history.
    "trades": "L1",
    "tbbo": "L1",
    "mbp-1": "L1",
    "bbo-1s": "L1",
    "bbo-1m": "L1",
    # L2 — market-by-price depth, 1-month included history.
    "mbp-10": "L2",
    # L3 — full market-by-order, 1-month included history.
    "mbo": "L3",
}

# ── Included-history window per level (trailing days from today) ─────────────
# Conservative approximations of Databento's rolling allowance — the real
# boundary may be calendar-based. If you ever see metered charges, REDUCE these.
LEVEL_MAX_LOOKBACK_DAYS: dict[str, int] = {
    "L0": 16 * 365,  # ~16 years
    "L1": 365,  # 1 year
    "L2": 30,  # 1 month
    "L3": 30,  # 1 month
}

# ── Schemas we are allowed to FETCH ──────────────────────────────────────────
# OHLCV fetch = 1s + 1m (both L0/free 16y); coarser bars (15m/1h/1d) are
# aggregated downstream → ohlcv-1h / ohlcv-1d raise loudly.
_BANNED_OHLCV_SCHEMAS: frozenset[str] = frozenset({"ohlcv-1h", "ohlcv-1d"})
ALLOWED_DATABENTO_SCHEMAS: frozenset[str] = frozenset(DATABENTO_SCHEMA_LEVEL) - _BANNED_OHLCV_SCHEMAS

# ── Banned Databento APIs (silent-billing risk) ──────────────────────────────
# Break-glass: a deliberate, audited historical bulk pull may set this True in
# code (never silently) — but the default is to fail closed.
BANNED_DATABENTO_APIS: frozenset[str] = frozenset({"batch.submit_job"})


class DatabentoSubscriptionError(RuntimeError):
    """Base — a Databento request fell outside the paid subscription allowlist."""


class DatabentoDatasetNotAllowedError(DatabentoSubscriptionError):
    """Dataset is not one of the three we subscribe to (would be metered)."""


class DatabentoSchemaNotAllowedError(DatabentoSubscriptionError):
    """Schema is outside the fetch allowlist (e.g. a coarser OHLCV bar we aggregate)."""


class DatabentoLookbackExceededError(DatabentoSubscriptionError):
    """Requested start predates the level's free included-history window (would be metered)."""


class DatabentoBatchApiBannedError(DatabentoSubscriptionError):
    """A banned Databento API (batch.submit_job) was called — use streaming/live instead."""


def _normalize_schema(schema: object) -> str:
    """Canonicalise a schema token to the hyphenated Databento wire form.

    Accepts the ``databento.Schema`` enum (str-valued OR ``Schema.OHLCV_1S``
    repr), an underscore data_type (``ohlcv_1m``), or the hyphenated form
    (``ohlcv-1m``).
    """
    text = str(schema).strip().lower()
    text = text.rsplit(".", 1)[-1]  # tolerate a 'schema.ohlcv_1s' enum repr
    return text.replace("_", "-")


def databento_schema_level(schema: object) -> str:
    """Return the billing LEVEL (``L0``…``L3``) for a schema; raise if unknown."""
    norm = _normalize_schema(schema)
    level = DATABENTO_SCHEMA_LEVEL.get(norm)
    if level is None:
        raise DatabentoSchemaNotAllowedError(
            f"Unknown Databento schema {norm!r}: not in the subscription allowlist. "
            f"Allowed fetch schemas: {sorted(ALLOWED_DATABENTO_SCHEMAS)}."
        )
    return level


def assert_dataset_allowed(dataset: str) -> None:
    """Raise unless ``dataset`` is one of the three subscribed datasets."""
    if dataset not in ALLOWED_DATABENTO_DATASETS:
        raise DatabentoDatasetNotAllowedError(
            f"Databento dataset {dataset!r} is NOT in the paid subscription "
            f"{sorted(ALLOWED_DATABENTO_DATASETS)} — querying it would be billed "
            f"pay-as-you-go. Refusing. (codex/02-data/tradfi-databento-sourcing-ssot.md)"
        )


def assert_schema_allowed(schema: object) -> None:
    """Raise unless ``schema`` is on the fetch allowlist.

    Coarser OHLCV bars (1m/1h/1d) raise with a pointer to the aggregate-from-1s
    policy; any other unknown schema raises as a metered-billing risk.
    """
    norm = _normalize_schema(schema)
    if norm in _BANNED_OHLCV_SCHEMAS:
        raise DatabentoSchemaNotAllowedError(
            f"Databento OHLCV schema {norm!r} is NOT fetched — we ingest 'ohlcv-1s' + 'ohlcv-1m' "
            f"and aggregate {norm!r} downstream. (codex/02-data/tradfi-databento-sourcing-ssot.md)"
        )
    if norm not in ALLOWED_DATABENTO_SCHEMAS:
        raise DatabentoSchemaNotAllowedError(
            f"Databento schema {norm!r} is outside the subscription allowlist "
            f"{sorted(ALLOWED_DATABENTO_SCHEMAS)} — would be metered. Refusing."
        )


def _coerce_start(start: str | date | datetime) -> datetime:
    """Parse a Databento ``start`` (ISO date/datetime string, date, or datetime) to aware UTC."""
    if isinstance(start, datetime):
        dt = start
    elif isinstance(start, date):
        dt = datetime(start.year, start.month, start.day, tzinfo=UTC)
    else:
        text = str(start).strip().replace("Z", "+00:00")
        dt = datetime.fromisoformat(text)
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


def earliest_allowed_start(schema: object, *, now: datetime | None = None) -> datetime:
    """Return the oldest ``start`` permitted for ``schema`` under its free window."""
    now_utc = now if now is not None else datetime.now(UTC)
    level = databento_schema_level(schema)
    return now_utc - timedelta(days=LEVEL_MAX_LOOKBACK_DAYS[level])


def assert_lookback_allowed(schema: object, start: str | date | datetime, *, now: datetime | None = None) -> None:
    """Raise if ``start`` predates ``schema``'s free included-history window."""
    floor = earliest_allowed_start(schema, now=now)
    start_dt = _coerce_start(start)
    if start_dt < floor:
        level = databento_schema_level(schema)
        raise DatabentoLookbackExceededError(
            f"Databento {schema!r} (level {level}) start {start_dt.date()} is older than the "
            f"{LEVEL_MAX_LOOKBACK_DAYS[level]}-day free window (floor {floor.date()}) — older history is "
            f"billed pay-as-you-go. Refusing. (codex/02-data/tradfi-databento-sourcing-ssot.md)"
        )


def assert_batch_api_allowed(api_name: str, *, break_glass: bool = False) -> None:
    """Raise if ``api_name`` is a banned Databento API (e.g. ``batch.submit_job``).

    ``break_glass=True`` is a deliberate, audited override for a one-off historical
    bulk pull — pass it explicitly in code, never wire it to a silent default.
    """
    if api_name in BANNED_DATABENTO_APIS and not break_glass:
        raise DatabentoBatchApiBannedError(
            f"Databento API {api_name!r} is BANNED (silent-billing risk) — use streaming "
            f"(timeseries.get_range) or the live client. Pass break_glass=True only for an "
            f"audited one-off. (codex/02-data/tradfi-databento-sourcing-ssot.md)"
        )


def assert_databento_request_allowed(
    dataset: str,
    schema: object,
    start: str | date | datetime,
    *,
    now: datetime | None = None,
) -> None:
    """Composite guard: dataset ∈ allowlist, schema ∈ allowlist, start within free window.

    Call this at every Databento fetch entry point. Fails closed (raises) on the
    first violation so a metered request never reaches the vendor.
    """
    assert_dataset_allowed(dataset)
    assert_schema_allowed(schema)
    assert_lookback_allowed(schema, start, now=now)
