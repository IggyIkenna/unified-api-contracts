"""Canonical log-level enum for the Unified Trading System.

This is the SSOT for log levels across all services and libraries.
Use ``from unified_api_contracts import LogLevel`` everywhere instead of
ad-hoc string literals or stdlib ``logging`` level integers.
"""

import enum


class LogLevel(enum.StrEnum):
    """Standard log severity levels (compatible with Python ``logging``)."""

    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"
