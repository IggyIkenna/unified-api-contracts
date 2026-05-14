"""Deployment-time error types raised by VM setup + tarball validation."""

from __future__ import annotations


class ManifestShaDriftError(RuntimeError):
    """Raised when a tarball's manifest.json commit_sha doesn't match the expected SHA.

    VM boot fails immediately on drift — deploying stale code to a targeted SHA is never safe.
    The expected SHA is supplied by the VM launcher via TARBALL_EXPECTED_SHA instance metadata.
    """

    def __init__(
        self,
        tarball_name: str,
        expected_sha: str,
        actual_sha: str,
        manifest_path: str,
    ) -> None:
        self.tarball_name = tarball_name
        self.expected_sha = expected_sha
        self.actual_sha = actual_sha
        self.manifest_path = manifest_path
        super().__init__(
            f"Tarball SHA drift: {tarball_name}"
            f" expected={expected_sha[:12]} actual={actual_sha[:12]}"
            f" manifest={manifest_path}"
        )
