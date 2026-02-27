"""Raw external API schemas per venue (request, response, errors).

Venue subpackages: binance, databento, tardis, ccxt, etc.
Consumers: UMI, UTEI, market-tick-data-handler, instruments-service.
"""

# Venue subpackages are imported on demand.
# Backward compat: api_contracts.binance -> api_contracts.api_contracts_external.binance
# (registered in api_contracts.__init__)
