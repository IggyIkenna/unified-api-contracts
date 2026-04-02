"""AWS normalizers — infra types to canonical.

Maps CodeBuild schemas to CanonicalComputeJob (kept).
Removed: S3->CanonicalCloudStorage, EC2->CanonicalVirtualMachine,
ECR->CanonicalContainerRegistry (speculative infra types deleted).
"""

from __future__ import annotations
