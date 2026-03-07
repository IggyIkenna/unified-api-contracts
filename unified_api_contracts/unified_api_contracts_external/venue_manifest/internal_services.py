"""Internal service contracts: inter-service communication and cloud infrastructure."""

from __future__ import annotations

__api_version__ = "v1"  # matches provider_api_versions.yaml


from typing import TypedDict


class ContractEntry(TypedDict, total=False):
    module: str
    description: str
    is_internal: bool
    sub_modules: dict[str, str]
    response_schema_classes: list[str]
    error_schema_classes: list[str]
    pubsub_topics: dict[str, str]
    sor_schemas: list[str]
    has_rest: bool
    has_websocket: bool
    has_fix: bool
    has_vcr_cassettes: bool
    cassette_schema_version: str
    fix_versions: list[str]
    msg_type_map: dict[str, str]
    supported_providers: list[str]
    regimes: list[str]
    config_secret_field: str
    example_schema_map: dict[str, str]


# Internal service schemas (lifecycle, pubsub, health, risk, etc.) live in unified-internal-contracts.
# AC provides external + normalised only; INTERNAL_CONTRACTS here lists other AC-owned contract groups.
INTERNAL_CONTRACTS: dict[str, ContractEntry] = {
    "fix": {
        "module": "unified_api_contracts.unified_api_contracts_external.fix.schemas",
        "description": (
            "FIX 4.2 / 4.4 / 5.0 message schemas for institutional order routing. "
            "Covers order management (NewOrderSingle, ExecutionReport, Cancel), "
            "market data (Snapshot, IncrementalRefresh), and admin messages. "
            "Venues: IBKR (FIX 4.2), Databento (FIX 4.4), institutional CeFi."
        ),
        "is_internal": False,
        "has_rest": False,
        "has_websocket": False,
        "has_fix": True,
        "has_vcr_cassettes": False,
        "cassette_schema_version": "1.0",
        "fix_versions": ["FIX.4.2", "FIX.4.4", "FIX.5.0"],
        "response_schema_classes": [
            "FixNewOrderSingle",
            "FixExecutionReport",
            "FixOrderCancelRequest",
            "FixOrderCancelReject",
            "FixMarketDataRequest",
            "FixMarketDataSnapshot",
            "FixMarketDataIncrementalRefresh",
            "FixLogon",
            "FixLogout",
            "FixHeartbeat",
            "FixReject",
            "FixSessionConfig",
        ],
        "msg_type_map": {
            "D": "FixNewOrderSingle",
            "8": "FixExecutionReport",
            "F": "FixOrderCancelRequest",
            "9": "FixOrderCancelReject",
            "V": "FixMarketDataRequest",
            "W": "FixMarketDataSnapshot",
            "X": "FixMarketDataIncrementalRefresh",
            "A": "FixLogon",
            "5": "FixLogout",
            "0": "FixHeartbeat",
            "3": "FixReject",
        },
    },
    "prime_broker": {
        "module": "unified_api_contracts.unified_api_contracts_external.prime_broker.schemas",
        "description": (
            "Prime broker integration schemas — HiddenRoad / Talos / FalconX style. "
            "Covers credit accounts, cross-venue position netting, margin calls, "
            "net clearing instructions, and cleared fills."
        ),
        "is_internal": False,
        "has_rest": True,
        "has_websocket": False,
        "has_fix": False,
        "has_vcr_cassettes": False,
        "cassette_schema_version": "1.0",
        "supported_providers": ["hidden_road", "talos", "falconx", "genesis", "cumberland"],
        "response_schema_classes": [
            "PrimeBrokerAccount",
            "PrimeBrokerPosition",
            "PrimeBrokerMarginCall",
            "NetClearingInstruction",
            "CrossMarginNettingResult",
            "PrimeBrokerFill",
            "CollateralAsset",
        ],
        "error_schema_classes": ["PrimeBrokerError"],
    },
    "regulatory": {
        "module": "unified_api_contracts.unified_api_contracts_external.regulatory.schemas",
        "description": (
            "Regulatory reporting schemas: MiFID II (RTS 22/27/28), EMIR, Dodd-Frank, "
            "trade surveillance, and best execution monitoring."
        ),
        "is_internal": True,
        "has_vcr_cassettes": False,
        "cassette_schema_version": "1.0",
        "regimes": ["mifid_ii", "emir", "dodd_frank", "mas", "asic", "cftc", "sec"],
        "response_schema_classes": [
            "MifidIITradeReport",
            "BestExecutionRecord",
            "BestExecutionMonitoringRecord",
            "EmirTradeReport",
            "DoddFrankSwapReport",
            "TradeSurveillanceAlert",
        ],
        "error_schema_classes": ["TradeReportingError"],
    },
    "risk_analytics": {
        "module": "unified_api_contracts.schemas.risk",
        "description": (
            "Advanced quantitative risk schemas: VaR (historical, parametric, Monte Carlo), "
            "CVaR, stress testing, SPAN multi-asset margin, P&L attribution."
        ),
        "is_internal": True,
        "has_vcr_cassettes": False,
        "cassette_schema_version": "1.0",
        "response_schema_classes": [
            "VaRRequest",
            "VaRResult",
            "StressScenario",
            "StressTestResult",
            "MultiAssetMarginCalculation",
            "PnLAttributionRecord",
            "RealTimePnLRecord",
            "RiskLimitBreach",
        ],
    },
    "latency": {
        "module": "unified_api_contracts.schemas.latency",
        "description": (
            "HFT and latency measurement schemas: tick-to-trade, co-location performance, "
            "sub-millisecond operation timing, order latency percentiles."
        ),
        "is_internal": True,
        "has_vcr_cassettes": False,
        "cassette_schema_version": "1.0",
        "response_schema_classes": [
            "TickToTradeMetric",
            "OrderLatencyRecord",
            "CoLocationPerformanceMetric",
            "NetworkJitterMetric",
            "SubMillisecondLatencyRecord",
            "LatencyPercentile",
            "LatencyBenchmarkReport",
        ],
    },
    "analytics": {
        "module": "unified_api_contracts.schemas.analytics",
        "description": (
            "Advanced analytics schemas: factor attribution (momentum, value, carry, etc.), "
            "cross-asset correlation matrices, regime detection, alternative data signals "
            "(sentiment, satellite, options flow, dark pool)."
        ),
        "is_internal": True,
        "has_vcr_cassettes": False,
        "cassette_schema_version": "1.0",
        "response_schema_classes": [
            "FactorAttributionRecord",
            "FactorAttributionModel",
            "CrossAssetCorrelationMatrix",
            "CorrelationRegimeChange",
            "SentimentScore",
            "AlternativeDataSignal",
            "SatelliteObservation",
            "OptionsFlowRecord",
            "DarkPoolPrintRecord",
        ],
    },
    "cloud_sdks": {
        "has_rest": False,
        "has_websocket": False,
        "has_fix": False,
        "config_secret_field": "",
        "response_schema_classes": [
            "AlertPolicy",
            "ArtifactPackage",
            "ArtifactRegistryQuotaUsage",
            "ArtifactRepository",
            "ArtifactTag",
            "ArtifactVersion",
            "BlobDownloadRequest",
            "BlobListRequest",
            "BlobListResponse",
            "BlobUploadRequest",
            "BqQuotaUsage",
            "BucketCreateRequest",
            "CloudBuildBuild",
            "CloudBuildConfig",
            "CloudBuildGitHubConfig",
            "CloudBuildListBuildsResponse",
            "CloudBuildQuotaUsage",
            "CloudBuildRunTriggerRequest",
            "CloudBuildStep",
            "CloudBuildTrigger",
            "CloudBuildTriggerListResponse",
            "CloudLoggingQuotaUsage",
            "CloudSchedulerAttempt",
            "CloudSchedulerCreateJobRequest",
            "CloudSchedulerJob",
            "CloudSchedulerListJobsResponse",
            "CloudSchedulerPauseJobRequest",
            "CloudSchedulerResumeJobRequest",
            "CloudSchedulerRunJobRequest",
            "CloudRunRevision",
            "CloudRunService",
            "ComputeInstance",
            "ComputeOperation",
            "CreateServiceRequest",
            "DeleteInstanceRequest",
            "ExternalTableConfig",
            "ExternalTableCreateRequest",
            "GcpCloudRunQuotaUsage",
            "GcpComputeQuotaUsage",
            "GcsBlobInfo",
            "GcsQuotaUsage",
            "GetInstanceRequest",
            "HivePartitioningOptions",
            "IamBinding",
            "IamPolicy",
            "InsertInstanceRequest",
            "InstanceListResponse",
            "ListInstancesRequest",
            "ListTimeSeriesRequest",
            "ListTimeSeriesResponse",
            "ListLogEntriesRequest",
            "ListLogEntriesResponse",
            "ListPackagesResponse",
            "ListRepositoriesResponse",
            "ListRevisionsRequest",
            "ListSecretsResponse",
            "LogEntry",
            "LogMetric",
            "LogSink",
            "MonitoringCreateTimeSeriesRequest",
            "MonitoringPoint",
            "MonitoringTimeSeries",
            "PubSubAcknowledgeRequest",
            "PubSubMessage",
            "PubSubPublishRequest",
            "PubSubPublishResponse",
            "PubSubPullRequest",
            "PubSubPullResponse",
            "PubSubQuotaUsage",
            "PubSubReceivedMessage",
            "PubSubSeekRequest",
            "PubSubSubscription",
            "PubSubTopic",
            "PythonPackage",
            "QueryJobResult",
            "QueryRequest",
            "RevisionListResponse",
            "SecretAccessRequest",
            "SecretAccessResponse",
            "SecretAddVersionRequest",
            "SecretAddVersionResponse",
            "SecretCreateRequest",
            "SecretManagerQuotaUsage",
            "SecretVersion",
            "ServiceAccount",
            "ServiceAccountKey",
            "SetIamPolicyRequest",
            "StartInstanceRequest",
            "StopInstanceRequest",
            "TableCreateRequest",
            "TableInfo",
            "TestIamPermissionsRequest",
            "TestIamPermissionsResponse",
            "TrafficTarget",
            "UpdateServiceRequest",
            "UpdateTrafficSplitRequest",
            "UptimeCheckConfig",
            "WriteLogEntriesRequest",
        ],
        "error_schema_classes": [],
        "example_schema_map": {"bq_quota_usage_example.json": "BqQuotaUsage"},
    },
}
