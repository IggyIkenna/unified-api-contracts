from __future__ import annotations

from pydantic import BaseModel


class AwsIamUser(BaseModel):
    """IAM user. iam.get_user() / iam.list_users()"""

    UserName: str | None = None
    UserId: str | None = None
    Arn: str | None = None
    Path: str | None = None
    CreateDate: str | None = None
    PasswordLastUsed: str | None = None
    PermissionsBoundary: dict[str, object] | None = None
    Tags: list[dict[str, object]] | None = None


class AwsIamRole(BaseModel):
    """IAM role. iam.get_role() / iam.list_roles()"""

    RoleName: str | None = None
    RoleId: str | None = None
    Arn: str | None = None
    Path: str | None = None
    AssumeRolePolicyDocument: dict[str, object] | None = None
    CreateDate: str | None = None
    Description: str | None = None
    MaxSessionDuration: int | None = None
    PermissionsBoundary: dict[str, object] | None = None
    Tags: list[dict[str, object]] | None = None


class AwsIamPolicy(BaseModel):
    """IAM managed policy. iam.get_policy()"""

    PolicyName: str | None = None
    PolicyId: str | None = None
    Arn: str | None = None
    Path: str | None = None
    DefaultVersionId: str | None = None
    AttachmentCount: int | None = None
    CreateDate: str | None = None
    UpdateDate: str | None = None
    Description: str | None = None
    IsAttachable: bool | None = None


class AwsIamPolicyDocument(BaseModel):
    """IAM policy document (JSON policy). iam.get_policy_version()"""

    Version: str | None = None
    Statement: list[dict[str, object]] | None = None


class AwsAssumeRoleRequest(BaseModel):
    """Assume an IAM role. sts.assume_role()"""

    RoleArn: str | None = None
    RoleSessionName: str | None = None
    DurationSeconds: int | None = None
    ExternalId: str | None = None
    Policy: str | None = None
    Tags: list[dict[str, object]] | None = None
    TransitiveTagKeys: list[str] | None = None


class AwsAssumeRoleResponse(BaseModel):
    """Credentials from sts.assume_role(). Equivalent of GCP ServiceAccountImpersonationResponse."""

    Credentials: dict[str, object] | None = None
    AssumedRoleUser: dict[str, object] | None = None


class AwsIamAccessKey(BaseModel):
    """IAM access key. iam.list_access_keys() / iam.create_access_key()"""

    UserName: str | None = None
    AccessKeyId: str | None = None
    Status: str | None = None
    SecretAccessKey: str | None = None
    CreateDate: str | None = None
