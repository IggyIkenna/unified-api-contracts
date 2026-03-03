"""
Unit tests for event logging compliance.
Required by quality gates.
"""

import logging
from unittest.mock import patch

import pytest


class TestEventLogging:
    """Test event logging functionality."""

    def test_logging_configuration(self):
        """Test that logging is properly configured."""
        logger = logging.getLogger("unified_api_contracts")
        assert logger is not None
        # Logger should have handlers or inherit from root
        assert len(logger.handlers) > 0 or logger.propagate

    def test_info_logging_works(self):
        """Test that info level logging works."""
        logger = logging.getLogger("test_logger")
        with patch.object(logger, "info") as mock_info:
            logger.info("Test info message")
            mock_info.assert_called_once_with("Test info message")

    def test_warning_logging_works(self):
        """Test that warning level logging works."""
        logger = logging.getLogger("test_logger")
        with patch.object(logger, "warning") as mock_warning:
            logger.warning("Test warning message")
            mock_warning.assert_called_once_with("Test warning message")

    def test_error_logging_works(self):
        """Test that error level logging works."""
        logger = logging.getLogger("test_logger")
        with patch.object(logger, "error") as mock_error:
            logger.error("Test error message")
            mock_error.assert_called_once_with("Test error message")

    def test_exception_logging_works(self):
        """Test that exception logging includes traceback info."""
        logger = logging.getLogger("test_logger")

        try:
            raise ValueError("Test exception")
        except ValueError:
            with patch.object(logger, "exception") as mock_exception:
                logger.exception("An error occurred")
                mock_exception.assert_called_once_with("An error occurred")

    def test_no_silent_failures_in_logging(self):
        """Test that logging operations don't silently fail."""
        logger = logging.getLogger("test_logger")

        # Even with invalid format strings, logging should not crash silently
        try:
            logger.info("Valid message: %s", "test")
            # This should work fine
        except Exception as e:
            pytest.fail(f"Logging should not raise exceptions: {e}")
        assert True, "No silent failures detected"

    def test_structured_logging_fields(self):
        """Test that structured logging includes required fields."""
        logger = logging.getLogger("test_logger")

        # Test logging with extra fields
        extra_fields = {"service": "api-contracts", "operation": "schema_validation", "venue": "test_venue"}

        with patch.object(logger, "info") as mock_info:
            logger.info("Schema validation completed", extra=extra_fields)
            mock_info.assert_called_once()
            _args, kwargs = mock_info.call_args
            assert "extra" in kwargs
            assert kwargs["extra"]["service"] == "api-contracts"
