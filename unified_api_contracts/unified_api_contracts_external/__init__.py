"""Raw external API schemas per venue (request, response, errors).

Venue subpackages: binance, databento, tardis, ccxt, etc.
Consumers: UMI, UTEI, market-tick-data-handler, instruments-service.
"""

# Venue subpackages are imported on demand.
# Alias: unified_api_contracts.binance -> unified_api_contracts.unified_api_contracts_external.binance
# (registered in unified_api_contracts.__init__)
