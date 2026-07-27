"""Sanity tests for ``ORACLE_COVERAGE_START`` -- per-oracle archive
coverage SSOT used by data-status to clip the expected-coverage
denominator and by MTDS oracle handlers to short-circuit pre-archive
fetches.

Mirrors ``test_chain_genesis_dates.py`` shape but at the oracle-source
axis. Per Tab 14 fork1 prep audit 2026-05-08 + Tab 1 sub-agent probes.
"""

from __future__ import annotations

import re
from datetime import date

from unified_api_contracts.registry.capability_declarations._defi_oracle_coverage import (
    ORACLE_COVERAGE_START,
    get_oracle_coverage_start,
)

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def test_oracle_coverage_start_iso_format() -> None:
    """Every value is a parseable ISO YYYY-MM-DD."""
    for source, iso in ORACLE_COVERAGE_START.items():
        assert _ISO_DATE_RE.match(iso), f"{source}: {iso!r} not ISO YYYY-MM-DD"
        date.fromisoformat(iso)


def test_oracle_coverage_start_keys_are_lowercase_snake_case() -> None:
    """Source keys use lowercase + underscore style (matches MTDS handler
    naming + manifest source-priority entries)."""
    for source in ORACLE_COVERAGE_START:
        assert source == source.lower(), f"source {source!r} should be lowercase"
        assert " " not in source and "-" not in source, f"source {source!r} should use snake_case, not space/hyphen"


def test_pyth_hermes_archive_start_2023_10_01() -> None:
    """Pyth Hermes archive coverage start is 2023-10-01 per Tab 14
    fork1 audit + Tab 1 sub-agent probe results 2026-05-08.

    Pre-2023-10-01 timestamps return ``Update data not found`` from
    https://hermes.pyth.network/v2/updates/price/{publish_time}; this
    constant is the SSOT consumed by MTDS oracle_prices_handler to
    short-circuit pre-archive fetches and by data-status to clip the
    denominator."""
    assert ORACLE_COVERAGE_START["pyth_hermes"] == "2023-10-01"


def test_get_oracle_coverage_start_known() -> None:
    assert get_oracle_coverage_start("pyth_hermes") == "2023-10-01"
    assert get_oracle_coverage_start("PYTH_HERMES") == "2023-10-01"
    assert get_oracle_coverage_start("Pyth_Hermes") == "2023-10-01"


def test_get_oracle_coverage_start_unknown_returns_none() -> None:
    assert get_oracle_coverage_start("unknown_oracle") is None
    assert get_oracle_coverage_start("") is None


def test_facade_reexport_from_registry() -> None:
    """Facade wired 2026-07-27 (mirrors LST_TOKEN_GENESIS pattern): the shallow
    ``unified_api_contracts.registry`` path now re-exports this SSOT, not just
    the deep ``_defi_oracle_coverage`` module path used by the tests above."""
    from unified_api_contracts.registry import (
        ORACLE_COVERAGE_START as registry_start,
    )
    from unified_api_contracts.registry import (
        get_oracle_coverage_start as registry_getter,
    )

    assert registry_start is ORACLE_COVERAGE_START
    assert registry_getter is get_oracle_coverage_start
