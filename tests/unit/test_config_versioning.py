"""Unit tests for per-config versioning — sports-leagues + prediction-markets.

Mirrors the ``MVP_SCOPE`` config-versioning tests
(``test_mvp_scope.py``) for the two parallel config-as-data surfaces, plus the
shared :mod:`unified_api_contracts.canonical.crosscutting.config_versioning`
primitives.

Each config has a monotonic ``config_version`` int + a deterministic
``config_content_hash`` that flips IFF the config content flips (and is stable
across re-computation — ``PYTHONHASHSEED``-independent). PER-CONFIG: a leagues
edit must not change the prediction-markets hash and vice-versa.

Plan ref: ``plans/active/mvp_scope_catalogue_tagging_2026_06_08.md`` §
"Config versioning (config_version)".
"""

from __future__ import annotations

from dataclasses import dataclass, field

from unified_api_contracts import (
    PREDICTION_MARKETS_CONFIG_HASH,
    PREDICTION_MARKETS_CONFIG_VERSION,
    SPORTS_LEAGUES_CONFIG_HASH,
    SPORTS_LEAGUES_CONFIG_VERSION,
    prediction_markets_config_descriptor,
    sports_leagues_config_descriptor,
)
from unified_api_contracts.canonical.crosscutting.config_versioning import (
    ConfigDescriptor,
    canonical_config_repr,
    compute_config_content_hash,
)

# ---------------------------------------------------------------------------
# Shared primitives
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class _Sample:
    name: str
    venues: frozenset[str] = field(default_factory=frozenset)


class TestCanonicalConfigRepr:
    def test_frozenset_order_independent(self) -> None:
        a = _Sample("x", frozenset({"A", "B", "C"}))
        b = _Sample("x", frozenset({"C", "A", "B"}))
        assert canonical_config_repr(a) == canonical_config_repr(b)

    def test_content_change_changes_repr(self) -> None:
        a = _Sample("x", frozenset({"A", "B"}))
        b = _Sample("x", frozenset({"A"}))
        assert canonical_config_repr(a) != canonical_config_repr(b)

    def test_dict_key_order_independent(self) -> None:
        assert canonical_config_repr({"b": 1, "a": 2}) == canonical_config_repr({"a": 2, "b": 1})

    def test_compute_hash_is_16_hex_and_deterministic(self) -> None:
        items = [("k1", _Sample("x", frozenset({"A"}))), ("k2", 7)]
        h1 = compute_config_content_hash(1, items)
        h2 = compute_config_content_hash(1, items)
        assert h1 == h2
        assert len(h1) == 16
        int(h1, 16)  # raises if non-hex

    def test_compute_hash_flips_on_version_bump(self) -> None:
        items = [("k1", _Sample("x", frozenset({"A"})))]
        assert compute_config_content_hash(1, items) != compute_config_content_hash(2, items)


# ---------------------------------------------------------------------------
# Sports-leagues config
# ---------------------------------------------------------------------------


class TestSportsLeaguesConfigVersion:
    def test_public_surface(self) -> None:
        assert isinstance(SPORTS_LEAGUES_CONFIG_VERSION, int)
        assert SPORTS_LEAGUES_CONFIG_VERSION >= 1
        assert isinstance(SPORTS_LEAGUES_CONFIG_HASH, str)
        assert len(SPORTS_LEAGUES_CONFIG_HASH) == 16
        int(SPORTS_LEAGUES_CONFIG_HASH, 16)
        desc = sports_leagues_config_descriptor()
        assert isinstance(desc, ConfigDescriptor)
        assert desc.config_version == SPORTS_LEAGUES_CONFIG_VERSION
        assert desc.config_content_hash == SPORTS_LEAGUES_CONFIG_HASH

    def test_hash_is_deterministic(self) -> None:
        from unified_api_contracts.canonical.domain.sports.league_data import (
            _compute_sports_leagues_content_hash,
        )

        assert _compute_sports_leagues_content_hash() == SPORTS_LEAGUES_CONFIG_HASH
        assert _compute_sports_leagues_content_hash() == _compute_sports_leagues_content_hash()

    def test_hash_changes_iff_content_changes(self) -> None:
        from unified_api_contracts.canonical.domain.sports.league_data import LEAGUE_REGISTRY

        base = [(lid, LEAGUE_REGISTRY[lid]) for lid in sorted(LEAGUE_REGISTRY)]
        unchanged = compute_config_content_hash(SPORTS_LEAGUES_CONFIG_VERSION, base)
        assert unchanged == SPORTS_LEAGUES_CONFIG_HASH
        # Drop one league → different hash (content change).
        dropped = base[1:]
        assert compute_config_content_hash(SPORTS_LEAGUES_CONFIG_VERSION, dropped) != SPORTS_LEAGUES_CONFIG_HASH


# ---------------------------------------------------------------------------
# Prediction-markets config
# ---------------------------------------------------------------------------


class TestPredictionMarketsConfigVersion:
    def test_public_surface(self) -> None:
        assert isinstance(PREDICTION_MARKETS_CONFIG_VERSION, int)
        assert PREDICTION_MARKETS_CONFIG_VERSION >= 1
        assert isinstance(PREDICTION_MARKETS_CONFIG_HASH, str)
        assert len(PREDICTION_MARKETS_CONFIG_HASH) == 16
        int(PREDICTION_MARKETS_CONFIG_HASH, 16)
        desc = prediction_markets_config_descriptor()
        assert isinstance(desc, ConfigDescriptor)
        assert desc.config_version == PREDICTION_MARKETS_CONFIG_VERSION
        assert desc.config_content_hash == PREDICTION_MARKETS_CONFIG_HASH

    def test_hash_is_deterministic(self) -> None:
        from unified_api_contracts.canonical.domain.prediction.prediction_mapping import (
            _compute_prediction_markets_content_hash,
        )

        assert _compute_prediction_markets_content_hash() == PREDICTION_MARKETS_CONFIG_HASH
        assert _compute_prediction_markets_content_hash() == _compute_prediction_markets_content_hash()

    def test_hash_changes_iff_content_changes(self) -> None:
        from unified_api_contracts.canonical.domain.prediction.prediction_mapping import (
            _DEFAULT_RULES,
            PredictionMarketCategory,
        )

        cats = tuple(sorted(c.value for c in PredictionMarketCategory))
        base = [("categories", cats), ("rules", _DEFAULT_RULES)]
        assert compute_config_content_hash(PREDICTION_MARKETS_CONFIG_VERSION, base) == PREDICTION_MARKETS_CONFIG_HASH
        # Removing a category → different hash.
        reduced = [("categories", cats[1:]), ("rules", _DEFAULT_RULES)]
        assert compute_config_content_hash(PREDICTION_MARKETS_CONFIG_VERSION, reduced) != PREDICTION_MARKETS_CONFIG_HASH


# ---------------------------------------------------------------------------
# Per-config independence — the three hashes are distinct surfaces.
# ---------------------------------------------------------------------------


def test_per_config_hashes_are_independent() -> None:
    """The leagues + prediction hashes differ from each other and from
    MVP_SCOPE (each is a separate config surface; a change in one must not
    move the others)."""
    from unified_api_contracts import MVP_SCOPE_CONFIG_HASH

    hashes = {MVP_SCOPE_CONFIG_HASH, SPORTS_LEAGUES_CONFIG_HASH, PREDICTION_MARKETS_CONFIG_HASH}
    assert len(hashes) == 3
