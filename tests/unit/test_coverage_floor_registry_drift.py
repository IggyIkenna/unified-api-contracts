"""Tests for the cross-registry coverage-floor drift falsifier.

Standing guard against the failure class documented in
``plans/active/issues/coverage_floor_registries_no_cross_propagation_2026_07_17.md``:
``coverage_starts.py`` and ``venue_mapping.py`` each declare a per-venue
coverage floor with no code-level link between them, so an amendment to one
silently never reaches the other. This is the falsifier ``quality-gates.sh``
runs on every gate — it is how a NEW, undeclared divergence gets caught
instead of sitting silently for months (the ``SOURCE_COVERAGE_START`` failure
mode UAC@c280e1ff fixed).
"""

from __future__ import annotations

from datetime import date

from scripts.check_coverage_floor_registry_drift import (
    KNOWN_DIVERGENCES,
    _related_venue_mapping_keys,
    find_cross_registry_mismatches,
)

# ---------------------------------------------------------------------------
# THE STANDING GUARD — this is how the falsifier reaches CI
# ---------------------------------------------------------------------------


def test_no_undeclared_divergence_against_the_real_registries() -> None:
    """Every current cross-registry mismatch must already be a baselined, tracked gap.

    A failure here means either (a) someone introduced a NEW divergence — fix
    the wrong registry, or (b) a [DATA] todo landed and the matching
    ``KNOWN_DIVERGENCES`` entry needs its own removal commit.
    """
    new_findings, _stale_findings = find_cross_registry_mismatches()
    assert new_findings == [], "\n".join(f.message for f in new_findings)


def test_baseline_has_no_stale_entries() -> None:
    """Every ``KNOWN_DIVERGENCES`` entry must still correspond to a real mismatch.

    This is the ratchet: a [DATA] todo that lands but forgets to delete its
    baseline entry fails here, forcing the baseline to shrink instead of
    silently accumulating exemptions nobody re-checks.
    """
    _new_findings, stale_findings = find_cross_registry_mismatches()
    assert stale_findings == [], "\n".join(f.message for f in stale_findings)


def test_known_divergences_all_cite_the_tracking_doc() -> None:
    """Every baseline entry must be auditable back to its tracking todo."""
    for divergence in KNOWN_DIVERGENCES:
        assert "coverage_floor_registries_no_cross_propagation_2026_07_17.md" in divergence.note
        assert "[DATA]" in divergence.note


# ---------------------------------------------------------------------------
# KEY NORMALIZATION — the false-positive that motivated the narrow allowlist
# ---------------------------------------------------------------------------


def test_cefi_bare_key_matches_its_instrument_type_suffixed_siblings() -> None:
    venue_keys = ["BINANCE-SPOT", "BINANCE-FUTURES", "BINANCE-DELIVERY", "UNRELATED-OTHER"]
    related = _related_venue_mapping_keys("cefi", "BINANCE", venue_keys)
    assert set(related) == {"BINANCE-SPOT", "BINANCE-FUTURES", "BINANCE-DELIVERY"}


def test_defi_bare_key_matches_its_chain_suffixed_siblings() -> None:
    venue_keys = ["CURVE-ETHEREUM", "CURVE-AVALANCHE", "UNISWAP_V3-ETHEREUM"]
    related = _related_venue_mapping_keys("defi", "CURVE", venue_keys)
    assert set(related) == {"CURVE-ETHEREUM", "CURVE-AVALANCHE"}


def test_prediction_bare_key_does_not_false_match_the_unrelated_perp_venue() -> None:
    """THE FALSIFIER-MOTIVATING BUG: a blind startswith() catches this wrongly.

    ``KALSHI-PERP``/``POLYMARKET-PERP`` are cefi crypto-perp venues — a
    DIFFERENT product from the prediction YES/NO markets named ``KALSHI``/
    ``POLYMARKET``, per coverage_starts.py's own comment. A naive
    ``key.startswith(bare_key + "-")`` matches ``KALSHI-PERP`` against bare
    key ``KALSHI`` — wrong. Suffix-scoping by asset_group (prediction gets no
    suffix allowlist) must exclude it.
    """
    venue_keys = ["KALSHI-PERP", "POLYMARKET-PERP", "POLYMARKET", "POLYMARKET:BTC"]
    assert _related_venue_mapping_keys("prediction", "KALSHI", venue_keys) == []
    assert _related_venue_mapping_keys("prediction", "POLYMARKET", venue_keys) == ["POLYMARKET"]


def test_tradfi_bare_key_is_exact_match_only() -> None:
    venue_keys = ["CME", "CME-FUTURES"]
    assert _related_venue_mapping_keys("tradfi", "CME", venue_keys) == ["CME"]


def test_unrelated_key_never_matches() -> None:
    assert _related_venue_mapping_keys("cefi", "BINANCE", ["DERIBIT", "OKX-SPOT"]) == []


# ---------------------------------------------------------------------------
# THE FALSIFIER — a new, undeclared divergence must get CAUGHT
# ---------------------------------------------------------------------------


def _real_registries_copy() -> dict[str, dict[str, date]]:
    """Shallow-copy every real asset-group dict so a test can mutate ONE key
    without collaterally emptying the other asset groups (which would make
    their own unrelated KNOWN_DIVERGENCES entries look falsely stale).
    """
    import scripts.check_coverage_floor_registry_drift as mod

    return {ag: dict(registry) for ag, registry in mod._ASSET_GROUP_REGISTRIES.items()}


def test_falsifier_catches_a_new_undeclared_divergence(monkeypatch: object) -> None:
    """Inject a synthetic new divergence on an UNBASELINED key — must fail."""
    import scripts.check_coverage_floor_registry_drift as mod

    patched = _real_registries_copy()
    patched["tradfi"]["CME"] = date(1999, 1, 1)  # real venue_mapping CME = "2020-01-01"
    monkeypatch.setattr(mod, "_ASSET_GROUP_REGISTRIES", patched)  # pyright: ignore[reportAttributeAccessIssue]

    new_findings, stale_findings = mod.find_cross_registry_mismatches()
    assert stale_findings == []
    assert len(new_findings) == 1
    assert "CME" in new_findings[0].message
    assert "1999-01-01" in new_findings[0].message


def test_falsifier_stays_quiet_on_a_baselined_divergence(monkeypatch: object) -> None:
    """A mismatch WITH a matching KNOWN_DIVERGENCES entry must not be a 'new' finding."""
    import scripts.check_coverage_floor_registry_drift as mod

    patched = _real_registries_copy()
    # BITFINEX is baselined in KNOWN_DIVERGENCES (2026-07-27 [DATA] P1: 6 of
    # the original 8 cefi entries were resolved + removed; BITFINEX/BYBIT
    # remain, narrowed to a real per-suffix product-timing gap).
    patched["cefi"]["BITFINEX"] = date(1999, 1, 1)
    monkeypatch.setattr(mod, "_ASSET_GROUP_REGISTRIES", patched)  # pyright: ignore[reportAttributeAccessIssue]

    new_findings, _stale_findings = mod.find_cross_registry_mismatches()
    assert new_findings == []


def test_falsifier_catches_a_stale_baseline_entry(monkeypatch: object) -> None:
    """A KNOWN_DIVERGENCES entry whose pair now agrees must fail as STALE BASELINE."""
    import scripts.check_coverage_floor_registry_drift as mod

    patched = _real_registries_copy()
    # Remove every cefi baseline key (BITFINEX/BYBIT, post-2026-07-27
    # narrowing) so no mismatch is possible for them — simulating "the
    # [DATA] todo landed and fixed it" without removing the baseline entry.
    # defi/tradfi/prediction stay untouched so they contribute zero stale
    # findings.
    patched["cefi"] = {}
    monkeypatch.setattr(mod, "_ASSET_GROUP_REGISTRIES", patched)  # pyright: ignore[reportAttributeAccessIssue]

    _new_findings, stale_findings = mod.find_cross_registry_mismatches()
    assert len(stale_findings) == 2  # every cefi KNOWN_DIVERGENCES entry (BITFINEX, BYBIT)
    assert all("STALE BASELINE" in f.message for f in stale_findings)
    assert any("BITFINEX" in f.message for f in stale_findings)


# ---------------------------------------------------------------------------
# KEY-MAPPING COMPLETENESS — the [DATA] P3 explicit mapping validator
# ---------------------------------------------------------------------------


def test_mapping_is_complete_against_the_real_registries() -> None:
    """Every declared mapping entry must reference a real venue_mapping key,
    and every venue_mapping key that matches a bare key must be declared."""
    from scripts.check_coverage_floor_registry_drift import _validate_mapping_completeness

    findings = _validate_mapping_completeness()
    assert findings == [], "\n".join(f.message for f in findings)


def test_every_bare_key_in_mapping_exists_in_coverage_starts() -> None:
    """A bare key in the mapping with no corresponding coverage_starts entry is dead."""
    from unified_api_contracts.canonical import coverage_starts as _cs

    for asset_group, mapping in _cs.BARE_KEY_TO_VENUE_MAPPING_KEYS.items():
        registry = {
            "cefi": _cs.CEFI_SOURCE_COVERAGE_START,
            "defi": _cs.DEFI_SOURCE_COVERAGE_START,
        }.get(asset_group)
        assert registry is not None, f"Mapping asset_group {asset_group!r} has no registry"
        for bare_key in mapping:
            assert bare_key in registry, (
                f"BARE_KEY_TO_VENUE_MAPPING_KEYS[{asset_group!r}][{bare_key!r}] "
                f"does not exist in coverage_starts {asset_group} registry"
            )


def test_validate_mapping_catches_stale_reference(monkeypatch: object) -> None:
    """A mapping entry pointing to a key removed from venue_mapping must fail."""
    import scripts.check_coverage_floor_registry_drift as mod

    # Override _venue_mapping_combined_dates to simulate a removed venue_mapping key.
    orig = mod._venue_mapping_combined_dates

    def _patched_dates() -> dict[str, str]:
        d = orig()
        d.pop("BINANCE-DELIVERY", None)  # simulate removal
        return d

    monkeypatch.setattr(mod, "_venue_mapping_combined_dates", _patched_dates)
    findings = mod._validate_mapping_completeness()
    assert len(findings) == 1
    assert "STALE MAPPING" in findings[0].message
    assert "BINANCE-DELIVERY" in findings[0].message
    assert "BINANCE" in findings[0].message


def test_validate_mapping_catches_undeclared_relationship(monkeypatch: object) -> None:
    """A venue_mapping key matching a bare key but omitted from the mapping must fail."""
    import scripts.check_coverage_floor_registry_drift as mod

    orig = mod._venue_mapping_combined_dates

    def _patched_dates() -> dict[str, str]:
        d = orig()
        # Add a synthetic BINANCE-OPTIONS key — it matches bare BINANCE
        # (starts with "BINANCE-") but isn't in the mapping.
        d["BINANCE-OPTIONS"] = "2025-01-01"
        return d

    monkeypatch.setattr(mod, "_venue_mapping_combined_dates", _patched_dates)
    findings = mod._validate_mapping_completeness()
    assert len(findings) == 1
    assert "UNDECLARED MAPPING" in findings[0].message
    assert "BINANCE-OPTIONS" in findings[0].message
    assert "BINANCE" in findings[0].message


def test_validate_mapping_clean_with_no_drift() -> None:
    """The real registries must pass the mapping completeness check (smoke test)."""
    import scripts.check_coverage_floor_registry_drift as mod

    findings = mod._validate_mapping_completeness()
    assert findings == []
