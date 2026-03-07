"""
GitHub REST API v3 schemas.

Base URL: https://api.github.com. Used for CI/CD pipeline management, PR creation
via quickmerge, workflow monitoring, and release management.
Auth: Bearer token via GITHUB_TOKEN env var or GitHub App JWT.
"""

__api_version__ = "v3"  # matches provider_api_versions.yaml

from enum import StrEnum

from pydantic import BaseModel, Field


class GitHubErrorAction(StrEnum):
    """Action to take on GitHub API error."""

    RETRY_WITH_BACKOFF = "retry_with_backoff"
    FAIL_HARD = "fail_hard"


class GitHubRepository(BaseModel):
    """GitHub repository resource."""

    id: int | None = None
    name: str | None = None
    full_name: str | None = None
    private: bool | None = None
    html_url: str | None = None
    description: str | None = None
    fork: bool | None = None
    created_at: str | None = None
    updated_at: str | None = None
    pushed_at: str | None = None
    size: int | None = None
    stargazers_count: int | None = None
    default_branch: str | None = None
    visibility: str | None = Field(None, description="public/private/internal")


class GitHubPullRequest(BaseModel):
    """GitHub pull request resource."""

    number: int | None = None
    title: str | None = None
    state: str | None = Field(None, description="open/closed/merged")
    head: dict[str, object] | None = Field(None, description="Branch ref")
    base: dict[str, object] | None = Field(None, description="Target branch")
    user: dict[str, object] | None = None
    merged: bool | None = None
    merged_at: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    html_url: str | None = None
    body: str | None = None
    labels: list[dict[str, object]] | None = None
    draft: bool | None = None


class GitHubWorkflowRun(BaseModel):
    """GitHub Actions workflow run."""

    id: int | None = None
    name: str | None = None
    workflow_id: int | None = None
    status: str | None = Field(None, description="queued/in_progress/completed")
    conclusion: str | None = Field(
        None,
        description="success/failure/cancelled/timed_out",
    )
    branch: str | None = None
    event: str | None = None
    head_sha: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    html_url: str | None = None
    jobs_url: str | None = None


class GitHubWorkflowJob(BaseModel):
    """GitHub Actions workflow job."""

    id: int | None = None
    run_id: int | None = None
    name: str | None = None
    status: str | None = None
    conclusion: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    steps: list[dict[str, object]] | None = None
    html_url: str | None = None
    runner_name: str | None = None


class GitHubCheckRun(BaseModel):
    """GitHub check run (status check)."""

    id: int | None = None
    name: str | None = None
    status: str | None = None
    conclusion: str | None = None
    head_sha: str | None = None
    started_at: str | None = None
    completed_at: str | None = None
    html_url: str | None = None
    output: dict[str, object] | None = Field(None, description="title/summary/text")


class GitHubRelease(BaseModel):
    """GitHub release resource."""

    id: int | None = None
    tag_name: str | None = None
    name: str | None = None
    body: str | None = None
    draft: bool | None = None
    prerelease: bool | None = None
    created_at: str | None = None
    published_at: str | None = None
    html_url: str | None = None
    assets: list[dict[str, object]] | None = None


class GitHubRateLimit(BaseModel):
    """GitHub rate limit for a resource. Endpoint: GET /rate_limit."""

    limit: int | None = None
    remaining: int | None = None
    reset: int | None = Field(None, description="Unix timestamp")
    used: int | None = None
    resource: str | None = Field(None, description="core/search/graphql")


class GitHubRateLimitResponse(BaseModel):
    """Response from GET /rate_limit."""

    rate: GitHubRateLimit | None = None
    resources: dict[str, GitHubRateLimit] | None = None


class GitHubWebhookPayload(BaseModel):
    """Base webhook payload. Specific events add fields."""

    action: str | None = None
    repository: GitHubRepository | None = None
    sender: dict[str, object] | None = None


class GitHubActionsWorkflow(BaseModel):
    """GitHub Actions workflow resource."""

    id: int | None = None
    name: str | None = None
    path: str | None = None
    state: str | None = Field(None, description="active/deleted")
    created_at: str | None = None
    updated_at: str | None = None
    html_url: str | None = None


class GitHubError(BaseModel):
    """GitHub API error response."""

    message: str | None = None
    documentation_url: str | None = None
    errors: list[dict[str, object]] | None = None

    @classmethod
    def classify(cls, status_code: int | None, message: str | None = None) -> GitHubErrorAction:
        """Classify error for retry strategy.

        429 or 'rate limit exceeded' -> RETRY_WITH_BACKOFF
        401/403/404 -> FAIL_HARD
        """
        if status_code == 429:
            return GitHubErrorAction.RETRY_WITH_BACKOFF
        if message and "rate limit exceeded" in message.lower():
            return GitHubErrorAction.RETRY_WITH_BACKOFF
        if status_code in (401, 403, 404):
            return GitHubErrorAction.FAIL_HARD
        return GitHubErrorAction.FAIL_HARD
