"""GitHub normalizers — routes to canonical CI types.

Thin routing layer: GitHub* → Canonical*. Single-provider (GitHub) today;
canonicals ready for future GitLab. Covers repo, PR, workflow run usage
across quickmerge, CI monitoring, VCR, deployment-api.
"""

from __future__ import annotations

from ...canonical.domain.infrastructure.ci import (
    CanonicalPullRequest,
    CanonicalRepository,
    CanonicalWorkflowRun,
    SourceControlProvider,
)
from .schemas import (
    GitHubPullRequest,
    GitHubRepository,
    GitHubWorkflowRun,
)


def normalize_github_repository_to_repo(
    raw: GitHubRepository,
    venue: str = "github",
) -> CanonicalRepository | None:
    """Route GitHubRepository to CanonicalRepository."""
    if not raw or not raw.full_name:
        return None
    return CanonicalRepository(
        provider=SourceControlProvider.GITHUB,
        full_name=raw.full_name,
        html_url=raw.html_url,
        default_branch=raw.default_branch,
        visibility=raw.visibility,
    )


def normalize_github_workflow_run_to_run(
    raw: GitHubWorkflowRun,
    venue: str = "github",
) -> CanonicalWorkflowRun | None:
    """Route GitHubWorkflowRun to CanonicalWorkflowRun."""
    if not raw or raw.id is None:
        return None
    return CanonicalWorkflowRun(
        provider=SourceControlProvider.GITHUB,
        run_id=str(raw.id),
        status=raw.status,
        conclusion=raw.conclusion,
        branch=raw.branch,
        event=raw.event,
        html_url=raw.html_url,
    )


def normalize_github_pull_request_to_pr(
    raw: GitHubPullRequest,
    venue: str = "github",
) -> CanonicalPullRequest | None:
    """Route GitHubPullRequest to CanonicalPullRequest."""
    if not raw or raw.number is None:
        return None
    head_ref = None
    base_ref = None
    if raw.head and isinstance(raw.head, dict):
        head_ref = raw.head.get("ref") if isinstance(raw.head.get("ref"), str) else None
    if raw.base and isinstance(raw.base, dict):
        base_ref = raw.base.get("ref") if isinstance(raw.base.get("ref"), str) else None
    return CanonicalPullRequest(
        provider=SourceControlProvider.GITHUB,
        number=raw.number,
        title=raw.title,
        state=raw.state,
        head_ref=head_ref,
        base_ref=base_ref,
        html_url=raw.html_url,
    )
