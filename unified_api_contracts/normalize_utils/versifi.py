"""VersiFi order and fill normalizers.

Converts VersiFi REST API responses to CanonicalOrder and CanonicalFill.
"""

from __future__ import annotations

from ..external.versifi.normalize import (
    normalize_versifi_order_detail,
    normalize_versifi_order_list_item,
    normalize_versifi_order_response,
    normalize_versifi_trade_to_fill,
)

__all__ = [
    "normalize_versifi_order_detail",
    "normalize_versifi_order_list_item",
    "normalize_versifi_order_response",
    "normalize_versifi_trade_to_fill",
]
