"""
Google IAM schemas.

google.cloud.iam_v1. Used for service account management and permission checks.
"""

from pydantic import BaseModel, Field

from unified_api_contracts.canonical.errors import ErrorAction


class ServiceAccount(BaseModel):
    """IAM service account resource."""

    name: str | None = Field(
        None,
        description="projects/{p}/serviceAccounts/{sa}",
    )
    email: str | None = None
    displayName: str | None = Field(None, alias="displayName")
    description: str | None = None
    projectId: str | None = Field(None, alias="projectId")
    uniqueId: str | None = Field(None, alias="uniqueId")
    disabled: bool | None = None

    model_config = {"populate_by_name": True}


class ServiceAccountKey(BaseModel):
    """Service account key resource."""

    name: str | None = None
    keyType: str | None = Field(
        None,
        alias="keyType",
        description="USER_MANAGED/SYSTEM_MANAGED",
    )
    privateKeyType: str | None = Field(None, alias="privateKeyType")
    keyAlgorithm: str | None = Field(None, alias="keyAlgorithm")
    privateKeyData: str | None = Field(
        None,
        alias="privateKeyData",
        description="Base64, only on create",
    )
    validAfterTime: str | None = Field(None, alias="validAfterTime")
    validBeforeTime: str | None = Field(None, alias="validBeforeTime")

    model_config = {"populate_by_name": True}


class IamBinding(BaseModel):
    """Single IAM binding (role + members)."""

    role: str = Field(..., description="e.g. roles/storage.admin")
    members: list[str] = Field(
        default_factory=list,
        description="e.g. ['serviceAccount:...', 'user:...']",
    )
    condition: dict[str, object] | None = None


class IamPolicy(BaseModel):
    """IAM policy resource."""

    version: int | None = None
    bindings: list[IamBinding] | None = None
    etag: str | None = None


class SetIamPolicyRequest(BaseModel):
    """Request for set_iam_policy()."""

    resource: str = Field(..., description="Resource name")
    policy: IamPolicy = Field(..., description="Policy to set")
    updateMask: str | None = Field(None, alias="updateMask")

    model_config = {"populate_by_name": True}


class TestIamPermissionsRequest(BaseModel):
    """Request for test_iam_permissions()."""

    resource: str = Field(..., description="Resource name")
    permissions: list[str] = Field(default_factory=list)


class TestIamPermissionsResponse(BaseModel):
    """Response from test_iam_permissions() - subset caller has."""

    permissions: list[str] | None = None


# ---------------------------------------------------------------------------
# Organization and project-level IAM
# ---------------------------------------------------------------------------


class IamRole(BaseModel):
    """IAM role definition (predefined or custom).

    Endpoint: GET https://iam.googleapis.com/v1/projects/{p}/roles/{r}
    Or predefined: GET https://iam.googleapis.com/v1/roles/{r}
    """

    name: str | None = None
    title: str | None = None
    description: str | None = None
    included_permissions: list[str] | None = None
    stage: str | None = None
    etag: str | None = None
    deleted: bool | None = None


class CreateCustomRoleRequest(BaseModel):
    """Create a custom IAM role in a project.

    POST https://iam.googleapis.com/v1/projects/{p}/roles
    """

    role_id: str | None = None
    role: IamRole | None = None


class ListRolesResponse(BaseModel):
    """List of IAM roles."""

    roles: list[IamRole] | None = None
    next_page_token: str | None = None


class IamAuditConfig(BaseModel):
    """Audit logging configuration for a GCP service in an IAM policy."""

    service: str | None = None
    audit_log_configs: list[dict[str, object]] | None = None


class ResourceIamPolicy(BaseModel):
    """IAM policy on a GCP resource (project, bucket, topic, etc.)."""

    version: int | None = None
    bindings: list[IamBinding] | None = None
    audit_configs: list[IamAuditConfig] | None = None
    etag: str | None = None


class OrgPolicy(BaseModel):
    """Organization policy constraint."""

    name: str | None = None
    spec: dict[str, object] | None = None
    effective_policy: dict[str, object] | None = None
    etag: str | None = None
    update_time: str | None = None


class WorkloadIdentityPool(BaseModel):
    """Workload Identity Pool - keyless auth for external workloads."""

    name: str | None = None
    display_name: str | None = None
    description: str | None = None
    state: str | None = None
    disabled: bool | None = None


class WorkloadIdentityPoolProvider(BaseModel):
    """OIDC or AWS provider within a Workload Identity Pool."""

    name: str | None = None
    display_name: str | None = None
    state: str | None = None
    disabled: bool | None = None
    attribute_mapping: dict[str, str] | None = None
    attribute_condition: str | None = None
    oidc: dict[str, object] | None = None
    aws: dict[str, object] | None = None


class ServiceAccountImpersonationRequest(BaseModel):
    """Request to generate an access token by impersonating a service account."""

    name: str | None = None
    delegates: list[str] | None = None
    scope: list[str] | None = None
    lifetime: str | None = None


class ServiceAccountImpersonationResponse(BaseModel):
    """Access token response from SA impersonation."""

    access_token: str | None = None
    expire_time: str | None = None


class IamError(BaseModel):
    """IAM API error."""

    code: int | None = None
    message: str | None = None
    status: str | None = None

    @classmethod
    def classify(cls, code: int | None = None, http_status: int | None = None) -> object:
        if http_status == 429:
            return ErrorAction.RETRY
        if http_status in (403, 404):
            return ErrorAction.FAIL
        return ErrorAction.FAIL
