from __future__ import annotations

from pydantic import BaseModel


class EcrRepository(BaseModel):
    """ECR repository. ecr.describe_repositories()"""

    repositoryName: str | None = None
    repositoryArn: str | None = None
    registryId: str | None = None
    repositoryUri: str | None = None
    createdAt: str | None = None
    imageTagMutability: str | None = None
    imageScanningConfiguration: dict[str, object] | None = None
    encryptionConfiguration: dict[str, object] | None = None


class EcrImage(BaseModel):
    """ECR image. ecr.describe_images()"""

    registryId: str | None = None
    repositoryName: str | None = None
    imageDigest: str | None = None
    imageTags: list[str] | None = None
    imageSizeInBytes: int | None = None
    imagePushedAt: str | None = None
    imageScanStatus: dict[str, object] | None = None
    imageManifestMediaType: str | None = None


class EcrGetAuthorizationTokenResponse(BaseModel):
    """ECR auth token for docker login. ecr.get_authorization_token()"""

    authorizationData: list[dict[str, object]] | None = None


class EcrLifecyclePolicy(BaseModel):
    """ECR lifecycle policy — auto-delete old images. ecr.put_lifecycle_policy()"""

    registryId: str | None = None
    repositoryName: str | None = None
    lifecyclePolicyText: str | None = None
    lastEvaluatedAt: str | None = None
