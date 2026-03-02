from __future__ import annotations

from pydantic import BaseModel


class ServiceQuotasGetServiceQuotaRequest(BaseModel):
    """Request for service-quotas.get_service_quota()."""

    ServiceCode: str
    QuotaCode: str


class ServiceQuota(BaseModel):
    """Service quota from get_service_quota/list_service_quotas."""

    ServiceCode: str | None = None
    ServiceName: str | None = None
    QuotaArn: str | None = None
    QuotaCode: str | None = None
    QuotaName: str | None = None
    Value: float | None = None
    Unit: str | None = None
    Adjustable: bool | None = None
    UsageMetric: dict[str, object] | None = None


class ServiceQuotasGetServiceQuotaResponse(BaseModel):
    """Response from service-quotas.get_service_quota()."""

    Quota: ServiceQuota | None = None


class ServiceQuotasListServiceQuotasRequest(BaseModel):
    """Request for service-quotas.list_service_quotas()."""

    ServiceCode: str
    NextToken: str | None = None
    MaxResults: int | None = None


class ServiceQuotasListServiceQuotasResponse(BaseModel):
    """Response from service-quotas.list_service_quotas()."""

    Quotas: list[ServiceQuota] | None = None
    NextToken: str | None = None


class ServiceQuotasErrorDetail(BaseModel):
    """Error detail from Service Quotas API."""

    ErrorCode: str | None = None
    ErrorMessage: str | None = None


class ServiceQuotasErrorResponse(BaseModel):
    """Error response from Service Quotas API."""

    Error: ServiceQuotasErrorDetail | None = None
    ResponseMetadata: dict[str, object] | None = None
