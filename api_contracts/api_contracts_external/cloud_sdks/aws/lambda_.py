from __future__ import annotations

from typing import Literal

from pydantic import BaseModel


class LambdaInvokeRequest(BaseModel):
    """Request schema for lambda.invoke()."""

    FunctionName: str
    InvocationType: Literal["Event", "RequestResponse", "DryRun"] | None = "RequestResponse"
    Payload: bytes | str | None = None
    Qualifier: str | None = None


class LambdaInvokeResponse(BaseModel):
    """Response from lambda.invoke()."""

    StatusCode: int | None = None
    ExecutedVersion: str | None = None
    Payload: bytes | None = None
    FunctionError: str | None = None
    LogResult: str | None = None
