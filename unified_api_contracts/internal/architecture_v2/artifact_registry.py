"""Artifact registry schemas — Phase 8 of Strategy Architecture v2.

Canonical metadata for every versioned artifact in the system: feature groups,
ML models, execution policies, cost models, allocator algorithms, risk
policies, MEV policies, bridge policies. See
``codex/04-architecture/artifact-versioning.md`` and
``codex/06-coding-standards/artifact-naming.md`` for the 3-axis versioning
model and family-naming conventions.

Every artifact is identified by:

- ``kind``       — coarse category (ArtifactKind)
- ``family``     — stable string family name (e.g. ``crypto-ohlc-5m``,
  ``CRYPTO_BTC_CATBOOST_V4``, ``cefi-crypto-large-size-v3``)
- ``version``    — monotonic integer within family (1, 2, 3, ...; never reused)
- ``content_hash`` — SHA-256 (truncated to 16 hex) of the canonical-JSON
  serialisation of the artifact content. Same content → same hash regardless
  of publish time.

Consumer-pin reference syntax: ``{family}@v{version}``.
"""

from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, Field


class ArtifactKind(StrEnum):
    """Coarse artifact category. Drives storage prefix + registry partitioning.

    Every versioned artifact in the system has exactly one kind. This is NOT
    the strategy family — that lives on ``StrategyInstanceDefinition``. This
    is the artifact-type axis.
    """

    FEATURE_GROUP = "FEATURE_GROUP"
    ML_MODEL = "ML_MODEL"
    EXECUTION_POLICY = "EXECUTION_POLICY"
    COST_MODEL = "COST_MODEL"
    BENCHMARK_MODE = "BENCHMARK_MODE"
    ALLOCATOR_ALGORITHM = "ALLOCATOR_ALGORITHM"
    RISK_POLICY = "RISK_POLICY"
    MEV_POLICY = "MEV_POLICY"
    BRIDGE_POLICY = "BRIDGE_POLICY"
    STRATEGY_CONFIG = "STRATEGY_CONFIG"
    CONFORMANCE_SUITE = "CONFORMANCE_SUITE"


class ArtifactRef(BaseModel):
    """Pin-resolved reference to a specific artifact version.

    Rendered as ``{family}@v{version}`` in configs and event payloads. Never
    ``{family}`` alone — explicit version pinning is mandatory per
    ``codex/04-architecture/artifact-versioning.md`` Rule 3 (no auto-upgrade).
    """

    kind: ArtifactKind
    family: str = Field(
        description="Stable artifact family name; never renamed after first publish.",
    )
    version: int = Field(ge=1, description="Monotonic integer >= 1.")

    @property
    def ref(self) -> str:
        """Return the canonical ``{family}@v{version}`` string."""
        return f"{self.family}@v{self.version}"

    @classmethod
    def parse(cls, kind: ArtifactKind, ref: str) -> ArtifactRef:
        """Parse ``{family}@v{version}`` back into an ``ArtifactRef``.

        Raises ``ValueError`` when the reference is missing the ``@v{N}``
        suffix (implicit-latest is forbidden per the coding standard).
        """
        if "@v" not in ref:
            raise ValueError(
                f"Artifact reference {ref!r} missing '@v{{N}}' version pin "
                "— implicit-latest is forbidden. See "
                "codex/06-coding-standards/artifact-naming.md"
            )
        family, _, ver = ref.partition("@v")
        if not ver.isdigit():
            raise ValueError(f"Artifact reference {ref!r} has non-integer version suffix {ver!r}")
        return cls(kind=kind, family=family, version=int(ver))


class ArtifactMetadata(BaseModel):
    """Full metadata record stored in the artifact registry for one version.

    Produced by owning services at publish time (e.g. features-onchain-service
    publishes a ``FEATURE_GROUP`` after a successful daily pipeline run;
    ml-training-service publishes an ``ML_MODEL`` after Group A walk-forward
    CV; execution-service publishes ``EXECUTION_POLICY`` after a policy
    review).

    Serialised into the ``ARTIFACT_PUBLISHED`` event payload and also mirrored
    to the artifact registry store (GCS JSON or BigQuery — implementation
    choice lives outside this schema).
    """

    kind: ArtifactKind
    family: str
    version: int = Field(ge=1)
    content_hash: str = Field(
        description="SHA-256 truncated to 16 hex chars of the artifact's canonical JSON.",
        min_length=16,
        max_length=16,
    )
    created_at_utc: datetime = Field(default_factory=lambda: datetime.now(UTC))
    created_by: str = Field(
        default="",
        description="Service or user that published this version (e.g. 'features-onchain-service').",
    )
    description: str = Field(default="", description="Human-readable description.")
    # Artifact-to-artifact dependency edges. Every reference MUST carry an
    # explicit @v{N} pin — consumers of this metadata MUST NOT resolve
    # latest. See artifact-versioning.md Rule 3.
    dependencies: list[ArtifactRef] = Field(default_factory=list)
    # Arbitrary tags for registry search ("cefi", "btc", "catboost", etc.).
    tags: tuple[str, ...] = Field(default_factory=tuple)
    # Storage path (GCS / S3) where full content lives. Registry entry is
    # lightweight metadata; content is content-addressed at this path.
    storage_uri: str = Field(
        default="",
        description="Backing store URI (gs://, s3://, file://). Empty until upload completes.",
    )
    # Conformance gate result (pass/fail). Artifacts that fail conformance
    # are not allowed to be referenced by live strategy configs.
    conformance_tests_passed: bool = True

    @property
    def ref(self) -> str:
        """Return the canonical ``{family}@v{version}`` pin string."""
        return f"{self.family}@v{self.version}"

    def as_ref(self) -> ArtifactRef:
        """Project to the lightweight ``ArtifactRef`` form."""
        return ArtifactRef(kind=self.kind, family=self.family, version=self.version)


class ArtifactPublishedPayload(BaseModel):
    """Payload of the ``ARTIFACT_PUBLISHED`` coordination / audit event.

    Emitted by every owning service immediately after a new artifact version
    is accepted by its registry. Consumed by:

    - Strategy-service / allocator-service shadow-runners (maybe promote
      this new version to shadow)
    - UI artifact-registry pages (live update)
    - Dependency-graph consumers doing impact analysis
    """

    metadata: ArtifactMetadata
    replaces_version: int | None = Field(
        default=None,
        description="Prior version this publication succeeds, if any.",
    )


__all__ = [
    "ArtifactKind",
    "ArtifactMetadata",
    "ArtifactPublishedPayload",
    "ArtifactRef",
]
