"""Rule 12 service-family scope enforcement (G1.11 of stage-3e-refactor-plan).

Loads ``codex/14-playbooks/_ssot-rules/12-service-family-scope-rules.yaml``
from the sibling PM checkout and exposes
:func:`check_service_family_scope` as a pre-check for G1.6's
``access_control()``. Scope denial short-circuits the full gate before
visibility / phase checks run.

**Citadel host (Option X carry-through from G1.6 + G1.7):** pure
functions + types live in UAC alongside the rest of the derivation layer.
Consumers import via the public ``unified_api_contracts.strategy``
facade.

**Closed ServiceFamily enum** — see rule 12 md for rationale. Six
members: ``IM``, ``RegUmbrella``, ``DART``, ``DART_reporting_only``,
``admin``, ``IM_desk``. Adding a family requires a rule-12 YAML edit +
operator-approved plan + new unit-test cases.

**Route matching** — glob-style, fnmatch-like. ``**`` matches any path
segments (translated to ``.*``); ``*`` inside a segment matches any chars
except ``/``. Negation via ``!`` prefix — a ``!/admin/**`` pattern in
``route_allowlist`` rejects the route even if another pattern allows it.

SSOT:
- ``unified-trading-pm/codex/14-playbooks/_ssot-rules/12-service-family-scope-rules.yaml``
- ``unified-trading-pm/codex/14-playbooks/_ssot-rules/12-service-family-scope-rules.md``
- Validator: ``unified-trading-pm/codex/14-playbooks/_ssot-rules/_tools/validate_scope_yaml.py``
"""

from __future__ import annotations

import fnmatch
import os
import re
from pathlib import Path
from typing import Literal, cast

import yaml  # pyright: ignore[reportMissingTypeStubs]
from pydantic import BaseModel, ConfigDict

from unified_api_contracts.internal.architecture_v2.derivation import (
    ClientAudience,
    UserContext,
)

ServiceFamily = Literal[
    "IM",
    "RegUmbrella",
    "DART",
    "DART_reporting_only",
    "admin",
    "IM_desk",
]
"""Closed enum of service families. Matches the rule-12 YAML keys
verbatim. Snake_case variants (``DART_reporting_only``, ``IM_desk``) avoid
hyphen issues in Python identifiers."""


class ScopeDeny(BaseModel):
    """Scope-denial envelope returned when a family's ``route_allowlist``
    rejects the requested route, or when the ``ServiceFamily`` cannot be
    inferred from the caller's ``UserContext``."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["deny"] = "deny"
    reason: str
    upgrade_hint: str = ""


class ScopeAllow(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["allow"] = "allow"
    reason: str = ""


ScopeDecision = ScopeAllow | ScopeDeny
"""Discriminated-union output of :func:`check_service_family_scope`."""


class ServiceFamilyScopeRule(BaseModel):
    """Parsed rule-12 YAML row — one service family's scope."""

    model_config = ConfigDict(frozen=True, extra="allow")

    description: str = ""
    surfaces: tuple[str, ...]
    excludes: tuple[str, ...] = ()
    route_allowlist: tuple[str, ...]


def _find_rule_yaml() -> Path | None:
    """Resolve rule-12 YAML via env-var then ancestor walk (G1.8 pattern)."""

    env_root = os.environ.get("UNIFIED_TRADING_WORKSPACE_ROOT")
    if env_root:
        candidate = (
            Path(env_root)
            / "unified-trading-pm"
            / "codex"
            / "14-playbooks"
            / "_ssot-rules"
            / "12-service-family-scope-rules.yaml"
        )
        if candidate.is_file():
            return candidate

    current = Path(__file__).resolve()
    for ancestor in current.parents:
        candidate = (
            ancestor
            / "unified-trading-pm"
            / "codex"
            / "14-playbooks"
            / "_ssot-rules"
            / "12-service-family-scope-rules.yaml"
        )
        if candidate.is_file():
            return candidate
    return None


def _load_rules() -> dict[str, ServiceFamilyScopeRule]:
    yaml_path = _find_rule_yaml()
    if yaml_path is None:
        return {}
    with yaml_path.open("r", encoding="utf-8") as handle:
        raw = cast(object, yaml.safe_load(handle))  # pyright: ignore[reportUnknownMemberType]
    if not isinstance(raw, dict):
        return {}
    raw_typed = cast(dict[str, object], raw)
    families: dict[str, ServiceFamilyScopeRule] = {}
    families_raw = raw_typed.get("service_families", {})
    if not isinstance(families_raw, dict):
        return {}
    families_raw_typed = cast(dict[str, object], families_raw)
    for name, body in families_raw_typed.items():
        # ``cast`` annotates ``name`` as ``str`` — no runtime check needed
        # per YAML mapping semantics; pydantic flags bad shapes downstream.
        families[name] = ServiceFamilyScopeRule.model_validate(body)
    return families


SERVICE_FAMILY_SCOPE_RULES: dict[str, ServiceFamilyScopeRule] = _load_rules()
"""Module-level frozen mapping of rule-12 YAML. Empty in siloed CI."""


def service_family_from_audience(audience: ClientAudience) -> ServiceFamily | None:
    """Map a :class:`ClientAudience` JWT claim to a :class:`ServiceFamily`.

    The mapping mirrors rule 04 commercial-axes resolution. Returns
    ``None`` for audiences that cannot be scope-gated (the caller emits a
    scope-deny with an actionable reason).
    """

    if audience == "admin":
        return "admin"
    if audience == "im_desk":
        return "IM_desk"
    if audience == "im_client":
        return "IM"
    if audience == "reg_umbrella_client":
        return "RegUmbrella"
    if audience == "trading_platform_subscriber":
        # trading_platform_subscriber covers DART + signals-only +
        # DART-reporting-only. Default to full DART; callers that want
        # DART_reporting_only must pass ServiceFamily explicitly via
        # ``UserContext.entitlements`` (future extension — Wave D treats
        # the default as DART).
        return "DART"
    return None


def _glob_to_regex(pattern: str) -> re.Pattern[str]:
    """Translate a rule-12 glob to a compiled regex.

    Supports ``**`` for path-segment wildcarding (translated to ``.*``
    across ``/`` boundaries) and single ``*`` (matches within a segment).
    """

    # Temporarily stash `**` behind a sentinel so fnmatch.translate doesn't
    # collapse it, then restore it post-translate.
    sentinel = "__DOUBLE_GLOB_SENTINEL__"
    guarded = pattern.replace("**", sentinel)
    translated = fnmatch.translate(guarded)
    translated = translated.replace(re.escape(sentinel), ".*")
    return re.compile(translated)


def _pattern_matches(pattern: str, route: str) -> bool:
    """Match a glob pattern against a route path.

    Treats ``/foo/**`` as matching both ``/foo`` (the bare prefix) and
    ``/foo/anything`` — closing the gap left by fnmatch.translate, which
    requires the explicit trailing slash.
    """

    regex = _glob_to_regex(pattern)
    if regex.fullmatch(route) is not None:
        return True
    # Allow ``/foo/**`` to match bare ``/foo`` (drop trailing ``/**``).
    if pattern.endswith("/**"):
        parent_regex = _glob_to_regex(pattern[:-3])
        if parent_regex.fullmatch(route) is not None:
            return True
    return False


def check_service_family_scope(
    user: UserContext,
    route: str,
    *,
    rules: dict[str, ServiceFamilyScopeRule] | None = None,
) -> ScopeDecision:
    """Pre-check for ``access_control``: does the user's service family
    include the requested route?

    Allows when:

    1. Rules registry is empty (siloed CI, no PM checkout) — fail OPEN so
       tests don't need the full PM tree. Production CI always has PM
       checked out.
    2. ``user.audience`` maps to a known ``ServiceFamily`` AND the family's
       ``route_allowlist`` contains at least one non-negated pattern
       matching ``route`` AND no negation pattern rejects it.

    Denies when:

    * The user's audience doesn't map to a known ``ServiceFamily`` and the
      rules registry is non-empty (deterministic siloed-CI pass-through is
      handled by rule #1 above).
    * No pattern matches (out-of-scope URL).
    * A negation pattern explicitly rejects (e.g. ``!/admin/**``).
    """

    active_rules = rules if rules is not None else SERVICE_FAMILY_SCOPE_RULES
    if not active_rules:
        # Siloed CI — fail open with an advisory reason. Real CI always
        # has PM available.
        return ScopeAllow(reason="scope rules registry empty (siloed CI)")

    family = service_family_from_audience(user.audience)
    if family is None:
        return ScopeDeny(
            reason=(
                f"audience={user.audience!r} does not map to a service family "
                f"(closed enum: IM, RegUmbrella, DART, DART_reporting_only, admin, IM_desk)"
            ),
            upgrade_hint="see rule 12 service-family-scope-rules.md",
        )

    rule = active_rules.get(family)
    if rule is None:
        return ScopeDeny(
            reason=f"rule 12 YAML missing family {family!r}",
            upgrade_hint="re-run validate_scope_yaml.py",
        )

    # Check negation patterns first — they always win.
    for pattern in rule.route_allowlist:
        if pattern.startswith("!") and _pattern_matches(pattern[1:], route):
            return ScopeDeny(
                reason=(f"service_family={family} excludes route {route!r} via negation pattern {pattern!r}"),
                upgrade_hint=f"see rule 12 {family} surfaces/excludes table",
            )

    # Then check positive allow patterns.
    for pattern in rule.route_allowlist:
        if pattern.startswith("!"):
            continue
        if _pattern_matches(pattern, route):
            return ScopeAllow(reason=f"service_family={family} matches pattern {pattern!r}")

    return ScopeDeny(
        reason=(
            f"service_family={family} has no route_allowlist pattern matching {route!r} "
            f"(allowed: {list(rule.route_allowlist)}, excludes: {list(rule.excludes)})"
        ),
        upgrade_hint=f"see rule 12 {family} surfaces/excludes table",
    )


__all__ = [
    "SERVICE_FAMILY_SCOPE_RULES",
    "ScopeAllow",
    "ScopeDecision",
    "ScopeDeny",
    "ServiceFamily",
    "ServiceFamilyScopeRule",
    "check_service_family_scope",
    "service_family_from_audience",
]
