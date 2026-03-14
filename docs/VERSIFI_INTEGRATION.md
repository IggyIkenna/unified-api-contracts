# VersiFi Integration Status

## Current State

VersiFi normalizers exist in `unified-api-contracts` but are **not wired** into execution-service.

| Component              | Location                              | Status                                                                |
| ---------------------- | ------------------------------------- | --------------------------------------------------------------------- |
| Order/fill normalizers | `canonical/normalize/versifi.py`      | Ready: `normalize_versifi_order_*`, `normalize_versifi_trade_to_fill` |
| Error normalizer       | `canonical/normalize/errors.py`       | Ready: `normalize_versifi_error`                                      |
| WebSocket message      | `canonical/normalize/connectivity.py` | Ready: `normalize_versifi_ws_message`                                 |
| execution-service      | —                                     | No adapter, no routing, no config                                     |

## Integration Model (When Wired)

When routing to VersiFi, we skip our own order manager for that route and rely on VersiFi's. Parent order → VersiFi API → their child orders. Reconciliation comes from their feedback:

- **WebSocket:** `VersiFiOrderResponse`, `VersiFiChildOrderTrade` via `normalize_versifi_ws_message`
- **REST:** Order list/detail via `normalize_versifi_order_list_item`, `normalize_versifi_order_detail`, `normalize_versifi_trade_to_fill`

Output: `CanonicalOrder`, `CanonicalFill` for our position/order tracking.

## Integration Checklist

1. Add VersiFi to execution-service config (e.g. `enabled_venues` or `prime_broker_routes`)
2. Implement VersiFi adapter that uses `normalize_versifi_*`
3. Subscribe to VersiFi WebSocket for reconciliation
4. Route parent orders to VersiFi when configured
