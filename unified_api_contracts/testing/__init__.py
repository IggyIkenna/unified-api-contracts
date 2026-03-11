"""External API testing utilities — fault injection and cassette drift detection.

Import directly from submodules (require optional deps: httpx, pyyaml, pytest):

    from unified_api_contracts.testing.fault_injection import FaultConfig, FaultInjectionTransport
    from unified_api_contracts.testing.fault_injection import make_fault_transport
    from unified_api_contracts.testing.fault_injection import TIMEOUT_SCENARIO, RATE_LIMIT_SCENARIO
    from unified_api_contracts.testing.fault_injection import FLAKY_SCENARIO, HIGH_LATENCY_SCENARIO
    from unified_api_contracts.testing.fault_injection import CASCADE_SCENARIO
    from unified_api_contracts.testing.detect_cassette_drift import run_drift_detection

Pytest network blocker — register in conftest.py:
    pytest_plugins = ["unified_api_contracts.testing.network_block_plugin"]

CLI cassette drift detector:
    python -m unified_api_contracts.testing.detect_cassette_drift \\
        --cassette-dir <dir> --output-json drift.json [--venues binance okx]
"""
# No module-level imports — testing submodules require optional deps.
