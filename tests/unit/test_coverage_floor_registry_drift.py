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
    patched["cefi"]["BINANCE"] = date(1999, 1, 1)  # BINANCE is baselined in KNOWN_DIVERGENCES
    monkeypatch.setattr(mod, "_ASSET_GROUP_REGISTRIES", patched)  # pyright: ignore[reportAttributeAccessIssue]

    new_findings, _stale_findings = mod.find_cross_registry_mismatches()
    assert new_findings == []


def test_falsifier_catches_a_stale_baseline_entry(monkeypatch: object) -> None:
    """A KNOWN_DIVERGENCES entry whose pair now agrees must fail as STALE BASELINE."""
    import scripts.check_coverage_floor_registry_drift as mod

    patched = _real_registries_copy()
    # Remove every cefi baseline key (BITFINEX/KRAKEN/.../HYPERLIQUID) so no
    # mismatch is possible for them — simulating "the [DATA] todo landed and
    # fixed it" without removing the baseline entry. defi/tradfi/prediction
    # stay untouched so they contribute zero stale findings.
    patched["cefi"] = {}
    monkeypatch.setattr(mod, "_ASSET_GROUP_REGISTRIES", patched)  # pyright: ignore[reportAttributeAccessIssue]

    _new_findings, stale_findings = mod.find_cross_registry_mismatches()
    assert len(stale_findings) == 8  # every cefi KNOWN_DIVERGENCES entry
    assert all("STALE BASELINE" in f.message for f in stale_findings)
    assert any("BINANCE" in f.message for f in stale_findings)
