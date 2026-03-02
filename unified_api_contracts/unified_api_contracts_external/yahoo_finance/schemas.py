"""Pydantic schemas for Yahoo Finance adapter responses. Full surface: market data, errors, edge cases."""

from pydantic import BaseModel

from unified_api_contracts.shared import ErrorAction


class YahooOhlcv24h(BaseModel):
    """Daily OHLCV bar from Yahoo Finance (yfinance history / yf.download)."""

    Date: str | None = None
    Open: float | None = None
    High: float | None = None
    Low: float | None = None
    Close: float | None = None
    Adj_Close: float | None = None
    Volume: float | None = None


class YahooSplits(BaseModel):
    """Stock split record from Yahoo Finance (yfinance ticker.splits / actions)."""

    ticker: str | None = None
    effective_date: str | None = None
    ratio: float | None = None
    split_from: int | None = None
    split_to: int | None = None
    is_reverse_split: bool | None = None
    adjustment_factor: float | None = None
    source: str | None = None


class YahooDividends(BaseModel):
    """Dividend record from Yahoo Finance (yfinance ticker.dividends / actions)."""

    ticker: str | None = None
    ex_date: str | None = None
    pay_date: str | None = None
    record_date: str | None = None
    declaration_date: str | None = None
    amount: float | None = None
    dividend_type: str | None = None
    currency: str | None = None
    source: str | None = None


class YahooQuote(BaseModel):
    """Yahoo Finance quote (price data)."""

    symbol: str | None = None
    shortName: str | None = None
    regularMarketPrice: float | None = None
    regularMarketChange: float | None = None
    regularMarketVolume: int | None = None
    bid: float | None = None
    ask: float | None = None
    info: dict | None = None


class YahooChartResult(BaseModel):
    """Chart/quote result wrapper."""

    result: list | None = None
    error: dict | None = None


class YahooError(BaseModel):
    """Yahoo Finance error."""

    code: str | None = None
    description: str | None = None

    @classmethod
    def classify(cls, code: str | None = None, http_status: int | None = None) -> ErrorAction:
        """Map Yahoo Finance error to retry action."""
        if http_status == 429:
            return ErrorAction.RETRY_WITH_BACKOFF
        if code and "RATE_LIMIT" in (code or "").upper():
            return ErrorAction.RETRY_WITH_BACKOFF
        return ErrorAction.FAIL_HARD


class YahooEarningsEvent(BaseModel):
    """Source: ticker.calendar, ticker.earnings_dates."""

    ticker: str | None = None
    earnings_date: str | None = None
    eps_estimate: float | None = None
    eps_actual: float | None = None
    eps_surprise_pct: float | None = None
    revenue_estimate: float | None = None
    revenue_actual: float | None = None
    period: str | None = None
    source: str | None = None


class YahooKeyStatistics(BaseModel):
    """Source: ticker.info."""

    ticker: str | None = None
    beta: float | None = None
    pe_ratio_ttm: float | None = None
    forward_pe: float | None = None
    eps_ttm: float | None = None
    market_cap: float | None = None
    enterprise_value: float | None = None
    price_to_book: float | None = None
    price_to_sales_ttm: float | None = None
    profit_margins: float | None = None
    short_ratio: float | None = None
    short_percent_of_float: float | None = None
    shares_outstanding: float | None = None
    float_shares: float | None = None
    book_value_per_share: float | None = None
    fifty_two_week_high: float | None = None
    fifty_two_week_low: float | None = None
    source: str | None = None


class YahooAnalystRating(BaseModel):
    """Source: ticker.recommendations."""

    ticker: str | None = None
    date: str | None = None
    firm: str | None = None
    to_grade: str | None = None
    from_grade: str | None = None
    action: str | None = None
    source: str | None = None


class YahooPriceTarget(BaseModel):
    """Source: ticker.info."""

    ticker: str | None = None
    mean_price_target: float | None = None
    high_price_target: float | None = None
    low_price_target: float | None = None
    number_of_analyst_opinions: int | None = None
    recommendation_key: str | None = None
    recommendation_mean: float | None = None
    source: str | None = None


class YahooOptionContract(BaseModel):
    """Single option contract from ticker.options chain."""

    ticker: str | None = None
    expiration: str | None = None
    option_type: str | None = None  # call/put
    strike: float | None = None
    last_price: float | None = None
    bid: float | None = None
    ask: float | None = None
    volume: int | None = None
    open_interest: int | None = None
    implied_volatility: float | None = None
    in_the_money: bool | None = None
    contract_symbol: str | None = None
    last_trade_date: str | None = None
    source: str | None = None


class YahooOptionsChain(BaseModel):
    """Source: ticker.option_chain()."""

    ticker: str | None = None
    expiration: str | None = None
    calls: list[YahooOptionContract] | None = None
    puts: list[YahooOptionContract] | None = None
    underlying_price: float | None = None
    source: str | None = None


class YahooInstitutionalHolder(BaseModel):
    """Source: ticker.institutional_holders."""

    ticker: str | None = None
    holder: str | None = None
    shares: int | None = None
    date_reported: str | None = None
    percent_out: float | None = None
    value: float | None = None
    source: str | None = None


class YahooInsiderTransaction(BaseModel):
    """Source: ticker.insider_transactions."""

    ticker: str | None = None
    insider: str | None = None
    relation: str | None = None
    transaction_date: str | None = None
    transaction_type: str | None = None
    shares: int | None = None
    value: float | None = None
    source: str | None = None


class YahooMajorHolder(BaseModel):
    """Source: ticker.info major holders fields."""

    ticker: str | None = None
    pct_shares_held_by_insiders: float | None = None
    pct_shares_held_by_institutions: float | None = None
    pct_float_held_by_institutions: float | None = None
    number_of_institutions_holding: int | None = None
    source: str | None = None
