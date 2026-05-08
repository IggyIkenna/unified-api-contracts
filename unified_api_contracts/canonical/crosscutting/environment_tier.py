"""Environment-tier taxonomy — closed-set of {DEV, STAGING, PROD} for hosting.

SSOT for the environment-tier axis the deployment-UI / deployment-api use to
discriminate dev / staging / prod hosting. Defined by
``deployment_ui_lifecycle_tabs_2026_05_08`` plan Phase A.5 — the doc-touchpoint
plan section names this module as the single source of truth for the
3-tier closed set, and pins the resolution rule (hostname → tier OR
``CLOUD_DEPLOYMENT_ENV`` env-var → tier) so client + server always agree on
which tier they run in.

The three tiers
---------------

* :attr:`EnvironmentTier.DEV` — local-dev / workstation hosting; resolves from
  hostnames ``localhost`` / ``127.0.0.1`` / ``*.local``.
* :attr:`EnvironmentTier.STAGING` — staging hosting; resolves from any hostname
  starting with ``staging.`` (e.g. ``staging.<research-domain>``).
* :attr:`EnvironmentTier.PROD` — production hosting; default tier for any
  hostname not matching the DEV / STAGING patterns.

The tier is **always derived**, never an in-UI toggle — the deployment-UI's
header env badge reads the resolved tier and renders it read-only. The
deployment-api boot-time config server-side mirror reads ``CLOUD_DEPLOYMENT_ENV``
env var (already used elsewhere in workspace per
``codex/05-infrastructure/runtime-tiers-and-deployment.md``) and asserts it
matches the hostname-derived tier when both are present.

Layer split
-----------

* **[UAC]** — this module. The 3-tier StrEnum + the two ``resolve_*`` helpers.
* **[deployment-ui]** — Header env badge calls
  :func:`resolve_environment_from_hostname` against ``window.location.hostname``
  (Phase H.3 + B.7 wire this in via a generated TypeScript mirror of the
  enum). Never offers an in-UI toggle.
* **[deployment-api]** — boot-time config calls
  :func:`resolve_environment_from_env` against ``CLOUD_DEPLOYMENT_ENV``. The
  resolved tier is exposed via a ``/health`` field so the UI can cross-check.
"""

from __future__ import annotations

from enum import StrEnum

_LOCALHOST_HOSTNAMES: frozenset[str] = frozenset({"localhost", "127.0.0.1"})
"""Bare hostnames that always resolve to :attr:`EnvironmentTier.DEV`.

Case-insensitive: callers normalise via ``hostname.casefold()`` before
membership check.
"""

_LOCAL_TLD_SUFFIX: str = ".local"
"""TLD suffix that marks a hostname as :attr:`EnvironmentTier.DEV`.

Matches mDNS / Bonjour names like ``my-mac.local`` and Docker-compose service
names. Match is case-insensitive on the casefolded hostname.
"""

_STAGING_HOSTNAME_PREFIX: str = "staging."
"""Hostname prefix that marks a host as :attr:`EnvironmentTier.STAGING`.

Matches the workspace convention of ``staging.<research-domain>``. Match is
case-insensitive on the casefolded hostname.
"""


class EnvironmentTier(StrEnum):
    """Closed-set 3-tier hosting taxonomy.

    Each member's value equals its name (canonical UAC StrEnum convention,
    see :class:`unified_api_contracts.canonical.crosscutting.lifecycle_class.LifecycleClass`
    + :class:`unified_api_contracts.canonical.crosscutting.share_class.ShareClass`
    for the precedent).
    """

    DEV = "DEV"
    """Local-dev / workstation hosting — ``localhost`` / ``127.0.0.1`` / ``*.local``."""

    STAGING = "STAGING"
    """Staging hosting — ``staging.<research-domain>``."""

    PROD = "PROD"
    """Production hosting — any hostname not matching DEV / STAGING."""


def resolve_environment_from_hostname(hostname: str) -> EnvironmentTier:
    """Resolve the :class:`EnvironmentTier` for a hostname.

    Encodes the workspace convention (Phase A.5 of the
    ``deployment_ui_lifecycle_tabs_2026_05_08`` plan):

    * ``localhost`` / ``127.0.0.1`` / any ``*.local`` host →
      :attr:`EnvironmentTier.DEV`.
    * Any host whose lowercased name starts with ``staging.`` →
      :attr:`EnvironmentTier.STAGING`.
    * Anything else → :attr:`EnvironmentTier.PROD`.

    The match is case-insensitive (``HOSTNAME`` / ``Hostname`` / ``hostname``
    all resolve identically).

    Args:
        hostname: The hostname to classify (e.g. ``window.location.hostname``
            on the client, ``request.url.hostname`` on the server).

    Returns:
        The resolved :class:`EnvironmentTier`.

    Raises:
        ValueError: If ``hostname`` is empty (after stripping whitespace).
            Callers must pass a real hostname; the helper does not silently
            default to PROD when the caller forgot to populate the field.
    """
    stripped = hostname.strip()
    if not stripped:
        raise ValueError(
            "Cannot resolve EnvironmentTier from empty hostname; caller must pass a non-empty hostname string."
        )
    folded = stripped.casefold()
    if folded in _LOCALHOST_HOSTNAMES or folded.endswith(_LOCAL_TLD_SUFFIX):
        return EnvironmentTier.DEV
    if folded.startswith(_STAGING_HOSTNAME_PREFIX):
        return EnvironmentTier.STAGING
    return EnvironmentTier.PROD


def resolve_environment_from_env(env_var_value: str | None) -> EnvironmentTier:
    """Resolve the :class:`EnvironmentTier` from a server-side env-var value.

    Used by the deployment-api boot-time config to read its own tier from the
    ``CLOUD_DEPLOYMENT_ENV`` env var (loaded via ``UnifiedCloudConfig``, never
    via the standard library env-var read API; this helper takes the
    already-loaded value as a parameter and keeps the env-var-read concern out
    of UAC).

    The accepted values are case-insensitive matches for the three member
    names: ``"DEV"`` / ``"STAGING"`` / ``"PROD"``.

    Args:
        env_var_value: The env-var content. ``None`` is rejected loudly
            because boot-time config MUST set the var explicitly — silently
            defaulting to PROD on a missing env var is a footgun (a misconfig'd
            staging pod would render as PROD in the UI).

    Returns:
        The resolved :class:`EnvironmentTier`.

    Raises:
        ValueError: If ``env_var_value`` is ``None``, empty, or not one of
            the three accepted member names. The error message lists the
            accepted set so misconfigurations surface immediately.
    """
    if env_var_value is None:
        raise ValueError(
            "Cannot resolve EnvironmentTier from None; "
            "CLOUD_DEPLOYMENT_ENV must be set to one of "
            "'DEV' / 'STAGING' / 'PROD'."
        )
    stripped = env_var_value.strip()
    if not stripped:
        raise ValueError(
            "Cannot resolve EnvironmentTier from empty env-var value; "
            "CLOUD_DEPLOYMENT_ENV must be set to one of "
            "'DEV' / 'STAGING' / 'PROD'."
        )
    upper = stripped.upper()
    try:
        return EnvironmentTier(upper)
    except ValueError as exc:
        accepted = ", ".join(repr(member.value) for member in EnvironmentTier)
        raise ValueError(
            f"Unrecognised CLOUD_DEPLOYMENT_ENV value {env_var_value!r}; expected one of {accepted}."
        ) from exc
