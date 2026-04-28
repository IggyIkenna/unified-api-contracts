"""Integration tests for venue freshness SLAs — domain __init__ re-export surface."""

from __future__ import annotations


class TestDomainReExports:
    """Verify the domain __init__.py re-exports data_quality symbols."""

    def test_import_from_domain(self) -> None:
        from unified_api_contracts.internal.domain import (
            VENUE_FRESHNESS_SLAS,
            VenueCategory,
            VenueFreshnessSLA,
            get_sla_for_venue,
            get_slas_by_category,
        )

        assert len(VENUE_FRESHNESS_SLAS) == 31
        assert VenueCategory.CEFI.value == "cefi"
        assert isinstance(get_sla_for_venue("binance"), VenueFreshnessSLA)
        assert len(get_slas_by_category(VenueCategory.DEFI)) == 13

    def test_import_from_data_quality(self) -> None:
        from unified_api_contracts.internal.domain.data_quality import (
            VENUE_FRESHNESS_SLAS,
            get_sla_for_venue,
        )

        sla = get_sla_for_venue("hyperliquid")
        assert sla.max_staleness_seconds == 2
        assert "hyperliquid" in VENUE_FRESHNESS_SLAS

    def test_sla_consistency_across_import_paths(self) -> None:
        """Same object whether imported from domain or data_quality."""
        from unified_api_contracts.internal.domain import VENUE_FRESHNESS_SLAS as DOMAIN_SLAS
        from unified_api_contracts.internal.domain.data_quality import (
            VENUE_FRESHNESS_SLAS as DQ_SLAS,
        )

        assert DOMAIN_SLAS is DQ_SLAS
