"""Canonical environment variable names — SINGLE SOURCE OF TRUTH.

All repos MUST use these constants instead of raw getenv calls with literal strings.
Import EnvVars from unified_api_contracts.internal for validation_alias and env reads.
"""

# Module-level constants (convenience aliases)
RUNTIME_MODE = "RUNTIME_MODE"
DATA_MODE = "DATA_MODE"
CLOUD_PROVIDER = "CLOUD_PROVIDER"
PHASE_MODE = "PHASE_MODE"
TESTNET_MODE = "TESTNET_MODE"
OPERATIONAL_MODE = "OPERATIONAL_MODE"
TESTING_STAGE = "TESTING_STAGE"
CLOUD_MOCK_MODE = "CLOUD_MOCK_MODE"
GCP_PROJECT_ID = "GCP_PROJECT_ID"
AWS_ACCOUNT_ID = "AWS_ACCOUNT_ID"
RUNTIME_TOPOLOGY_PATH = "RUNTIME_TOPOLOGY_PATH"
WORKSPACE_ROOT = "WORKSPACE_ROOT"
LOG_LEVEL = "LOG_LEVEL"


class EnvVars:
    """Canonical env var names. Use for validation_alias and env reads."""

    # Mode (deployment-time)
    RUNTIME_MODE = "RUNTIME_MODE"  # live | batch
    DATA_MODE = "DATA_MODE"  # mock | real
    CLOUD_PROVIDER = "CLOUD_PROVIDER"  # gcp | aws | local
    PHASE_MODE = "PHASE_MODE"  # phase1 | phase2 | phase3

    # Project / bootstrap
    GCP_PROJECT_ID = "GCP_PROJECT_ID"
    AWS_ACCOUNT_ID = "AWS_ACCOUNT_ID"
    RUNTIME_TOPOLOGY_PATH = "RUNTIME_TOPOLOGY_PATH"
    WORKSPACE_ROOT = "WORKSPACE_ROOT"

    # Environment / deployment
    DEPLOYMENT_ENV = "DEPLOYMENT_ENV"
    ENVIRONMENT = "ENVIRONMENT"

    # Protocol (from topology; routing-key suffix applied per domain)
    PROTOCOL_DATA_SINK_BUCKET = "PROTOCOL_DATA_SINK_BUCKET"
    PROTOCOL_DATA_SINK_BACKEND = "PROTOCOL_DATA_SINK_BACKEND"
    PROTOCOL_DATA_SINK_TABLE_PREFIX = "PROTOCOL_DATA_SINK_TABLE_PREFIX"
    PROTOCOL_DATA_SOURCE_BUCKET = "PROTOCOL_DATA_SOURCE_BUCKET"
    PROTOCOL_DATA_SOURCE_BACKEND = "PROTOCOL_DATA_SOURCE_BACKEND"
    PROTOCOL_DATA_SOURCE_DIR = "PROTOCOL_DATA_SOURCE_DIR"
    PROTOCOL_EVENT_BUS_PROJECT = "PROTOCOL_EVENT_BUS_PROJECT"
    PROTOCOL_EVENT_BUS_BACKEND = "PROTOCOL_EVENT_BUS_BACKEND"
    PROTOCOL_ANALYTICS_PROJECT = "PROTOCOL_ANALYTICS_PROJECT"
    PROTOCOL_ANALYTICS_DATASET = "PROTOCOL_ANALYTICS_DATASET"
    PROTOCOL_ANALYTICS_BACKEND = "PROTOCOL_ANALYTICS_BACKEND"

    # Service / factory
    SERVICE_MODE = "SERVICE_MODE"  # LEGACY — use RUNTIME_MODE instead

    # Control surface (service protocol resolution)
    TESTNET_MODE = "TESTNET_MODE"  # mainnet | testnet
    OPERATIONAL_MODE = "OPERATIONAL_MODE"  # live | manual | backtest | paper
    TESTING_STAGE = "TESTING_STAGE"  # strategy progression (see modes.TestingStage)
    CLOUD_MOCK_MODE = "CLOUD_MOCK_MODE"  # true | false (maps to DataMode)

    # Logging (bootstrap, read before config is loaded)
    LOG_LEVEL = "LOG_LEVEL"  # DEBUG | INFO | WARNING | ERROR | CRITICAL

    # AWS
    AWS_REGION = "AWS_REGION"
    AWS_PROFILE = "AWS_PROFILE"
    ATHENA_OUTPUT_BUCKET = "ATHENA_OUTPUT_BUCKET"

    # GCP
    GOOGLE_APPLICATION_CREDENTIALS = "GOOGLE_APPLICATION_CREDENTIALS"
    GCS_REGION = "GCS_REGION"
    GCS_LOCATION = "GCS_LOCATION"
    BIGQUERY_LOCATION = "BIGQUERY_LOCATION"

    # Secrets
    SECRETS_CLOUD_PROVIDER = "SECRETS_CLOUD_PROVIDER"

    # Cache
    REDIS_URL = "REDIS_URL"

    # Emulators (local testing)
    PUBSUB_EMULATOR_HOST = "PUBSUB_EMULATOR_HOST"
    STORAGE_EMULATOR_HOST = "STORAGE_EMULATOR_HOST"
    BIGQUERY_EMULATOR_HOST = "BIGQUERY_EMULATOR_HOST"

    # Live service URLs (Tier 2 gateway routing — unified-trading-api → backend services)
    LIVE_SERVICE_BASE_URL = "LIVE_SERVICE_BASE_URL"
    LIVE_SERVICE_STRATEGY_URL = "LIVE_SERVICE_STRATEGY_URL"
    LIVE_SERVICE_EXECUTION_URL = "LIVE_SERVICE_EXECUTION_URL"
    LIVE_SERVICE_RISK_URL = "LIVE_SERVICE_RISK_URL"
    LIVE_SERVICE_INSTRUMENTS_URL = "LIVE_SERVICE_INSTRUMENTS_URL"
    LIVE_SERVICE_MARKET_DATA_URL = "LIVE_SERVICE_MARKET_DATA_URL"
    LIVE_SERVICE_REPORTING_URL = "LIVE_SERVICE_REPORTING_URL"

    # MDPS (market-data-processing-service) tuning flags
    USE_POLARS = "USE_POLARS"  # true | false — enable Polars aggregation path
    MDPS_TIMEFRAMES = "MDPS_TIMEFRAMES"  # comma-separated timeframes override

    # Adapter cursor-resumption tokens (set per-VM at backfill chunk launch)
    POLYMARKET_START_CURSOR = "POLYMARKET_START_CURSOR"  # base64 offset; first scan position
    POLYMARKET_END_CURSOR = "POLYMARKET_END_CURSOR"  # base64 offset; early-exit bound

    @classmethod
    def _core_canonical(cls) -> set[str]:
        return {
            cls.RUNTIME_MODE,
            cls.DATA_MODE,
            cls.CLOUD_PROVIDER,
            cls.PHASE_MODE,
            cls.GCP_PROJECT_ID,
            cls.AWS_ACCOUNT_ID,
            cls.RUNTIME_TOPOLOGY_PATH,
            cls.WORKSPACE_ROOT,
            cls.DEPLOYMENT_ENV,
            cls.ENVIRONMENT,
            cls.SERVICE_MODE,
            cls.TESTNET_MODE,
            cls.OPERATIONAL_MODE,
            cls.TESTING_STAGE,
            cls.CLOUD_MOCK_MODE,
            cls.LOG_LEVEL,
        }

    @classmethod
    def _protocol_canonical(cls) -> set[str]:
        return {
            cls.PROTOCOL_DATA_SINK_BUCKET,
            cls.PROTOCOL_DATA_SINK_BACKEND,
            cls.PROTOCOL_DATA_SINK_TABLE_PREFIX,
            cls.PROTOCOL_DATA_SOURCE_BUCKET,
            cls.PROTOCOL_DATA_SOURCE_BACKEND,
            cls.PROTOCOL_DATA_SOURCE_DIR,
            cls.PROTOCOL_EVENT_BUS_PROJECT,
            cls.PROTOCOL_EVENT_BUS_BACKEND,
            cls.PROTOCOL_ANALYTICS_PROJECT,
            cls.PROTOCOL_ANALYTICS_DATASET,
            cls.PROTOCOL_ANALYTICS_BACKEND,
        }

    @classmethod
    def _cloud_canonical(cls) -> set[str]:
        return {
            cls.AWS_REGION,
            cls.AWS_PROFILE,
            cls.ATHENA_OUTPUT_BUCKET,
            cls.GOOGLE_APPLICATION_CREDENTIALS,
            cls.GCS_REGION,
            cls.GCS_LOCATION,
            cls.BIGQUERY_LOCATION,
            cls.SECRETS_CLOUD_PROVIDER,
            cls.REDIS_URL,
            cls.PUBSUB_EMULATOR_HOST,
            cls.STORAGE_EMULATOR_HOST,
            cls.BIGQUERY_EMULATOR_HOST,
        }

    @classmethod
    def _service_canonical(cls) -> set[str]:
        return {
            cls.LIVE_SERVICE_BASE_URL,
            cls.LIVE_SERVICE_STRATEGY_URL,
            cls.LIVE_SERVICE_EXECUTION_URL,
            cls.LIVE_SERVICE_RISK_URL,
            cls.LIVE_SERVICE_INSTRUMENTS_URL,
            cls.LIVE_SERVICE_MARKET_DATA_URL,
            cls.LIVE_SERVICE_REPORTING_URL,
            cls.USE_POLARS,
            cls.MDPS_TIMEFRAMES,
            cls.POLYMARKET_START_CURSOR,
            cls.POLYMARKET_END_CURSOR,
        }

    @classmethod
    def all_canonical(cls) -> set[str]:
        """Return set of all canonical env var string values."""
        return cls._core_canonical() | cls._protocol_canonical() | cls._cloud_canonical() | cls._service_canonical()
