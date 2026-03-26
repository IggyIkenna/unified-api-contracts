"""Import-smoke tests for manifest library dependencies."""


def test_unified_trading_library_importable():
    from unified_trading_library import get_messaging_protocol

    assert callable(get_messaging_protocol)
