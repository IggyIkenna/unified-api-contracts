"""VersiFi institutional digital asset trading API contracts.

VersiFi routes to BINANCE_SPOT, BINANCE_FUTURES, OKX_SPOT, OKX_FUTURES, BINANCE_UNIFIED.
Supports MARKET, LIMIT, STOP, TWAP, VWAP, IS order types.
Auth: X-VERSIFI-API-KEY + X-VERSIFI-API-SIGN (HMAC-SHA256).
"""

from .schemas import (
    VersiFiAlgoOrder as VersiFiAlgoOrder,
)
from .schemas import (
    VersiFiAlgoOrderRequest as VersiFiAlgoOrderRequest,
)
from .schemas import (
    VersiFiAlgoOrderResponse as VersiFiAlgoOrderResponse,
)
from .schemas import (
    VersiFiBasicOrder as VersiFiBasicOrder,
)
from .schemas import (
    VersiFiBasicOrderRequest as VersiFiBasicOrderRequest,
)
from .schemas import (
    VersiFiOrderListItem as VersiFiOrderListItem,
)
from .schemas import (
    VersiFiOrderResponse as VersiFiOrderResponse,
)
from .schemas import (
    VersiFiPairOrder as VersiFiPairOrder,
)
from .schemas import (
    VersiFiPairOrderLeg as VersiFiPairOrderLeg,
)
from .schemas import (
    VersiFiPairOrderRequest as VersiFiPairOrderRequest,
)
from .schemas import (
    VersiFiWebSocketMessage as VersiFiWebSocketMessage,
)
