"""Glassnode on-chain analytics API schemas.

Base URL: https://api.glassnode.com/v1/metrics/{category}/{metric}
Auth: ?api_key=KEY query parameter
Response format: always list[{"t": int, "v": float | dict}]
Free tier: daily (24h) resolution, 1-year history. Paid: 10min resolution, full history.
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from pydantic import BaseModel

from unified_api_contracts.canonical.errors import ErrorAction


class GlassnodeTimeseriesPoint(BaseModel):
    """Single timeseries point: t=timestamp, v=value."""

    t: int | None = None
    v: float | None = None


class GlassnodeMetricResponse(BaseModel):
    """Universal wrapper for all Glassnode endpoints."""

    data: list[GlassnodeTimeseriesPoint] | None = None


class StockToFlowData(BaseModel):
    """Endpoint /indicators/stock_to_flow_ratio."""

    timestamp: int | None = None
    s2f_ratio: float | None = None
    s2f_model_price_usd: float | None = None


class HalvingEvent(BaseModel):
    """Static reference data for Bitcoin halving events."""

    halving_number: int | None = None
    block_height: int | None = None
    date_utc: str | None = None
    pre_halving_supply_per_day: float | None = None
    post_halving_supply_per_day: float | None = None
    btc_price_at_halving: float | None = None


class MvrvRatio(BaseModel):
    """Endpoint /market/mvrv.

    Interpretation: >3.7 historically extreme bull, <1 capitulation.
    """

    timestamp: int | None = None
    mvrv: float | None = None


class MvrvZScore(BaseModel):
    """Endpoint /market/mvrv_z_score."""

    timestamp: int | None = None
    mvrv_z_score: float | None = None


class SoprMetric(BaseModel):
    """Endpoint /indicators/sopr.

    >1 sellers in profit, <1 at loss.
    """

    timestamp: int | None = None
    sopr: float | None = None


class AsoprMetric(BaseModel):
    """Endpoint /indicators/sopr_adjusted. Excludes same-block spent outputs."""

    timestamp: int | None = None
    adjusted_sopr: float | None = None


class NvtRatio(BaseModel):
    """Endpoint /indicators/nvt.

    Bitcoin PE ratio, high NVT = overvalued vs on-chain activity.
    """

    timestamp: int | None = None
    nvt: float | None = None


class NvtSignal(BaseModel):
    """Endpoint /indicators/nvt_signal. 90-day MA of NVT."""

    timestamp: int | None = None
    nvt_signal: float | None = None


class HodlWave(BaseModel):
    """Endpoint /supply/hodl_waves. Response v is dict keyed by cohort."""

    timestamp: int | None = None
    band_1d: float | None = None
    band_1d_1w: float | None = None
    band_1w_1m: float | None = None
    band_1m_3m: float | None = None
    band_3m_6m: float | None = None
    band_6m_12m: float | None = None
    band_1y_2y: float | None = None
    band_2y_3y: float | None = None
    band_3y_5y: float | None = None
    band_5y_7y: float | None = None
    band_7y_10y: float | None = None
    band_10y_plus: float | None = None


class ExchangeReserves(BaseModel):
    """Endpoints: /exchanges/btc_balance_sum + /exchanges/btc_flow_net_sum.

    Positive net_flow = inflow (bearish), negative = outflow (bullish).
    """

    timestamp: int | None = None
    asset: str | None = None
    balance_sum: float | None = None
    net_flow_24h: float | None = None


class RealizedCap(BaseModel):
    """Endpoint /market/marketcap_realized_usd."""

    timestamp: int | None = None
    realized_cap_usd: float | None = None


class ThermoCap(BaseModel):
    """Endpoint /mining/thermocap.

    Total miner revenue, security spend of Bitcoin.
    """

    timestamp: int | None = None
    thermocap_usd: float | None = None


class GlassnodeError(BaseModel):
    """Glassnode API error."""

    status: int | None = None
    message: str | None = None

    @classmethod
    def classify(cls, status: int | None) -> ErrorAction:
        """429->RETRY, 401/403->FAIL."""
        if status == 429:
            return ErrorAction.RETRY
        if status in (401, 403):
            return ErrorAction.FAIL
        return ErrorAction.FAIL
