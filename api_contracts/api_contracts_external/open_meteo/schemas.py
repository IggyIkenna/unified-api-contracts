"""Open-Meteo weather API schemas.

Ref: https://open-meteo.com/en/docs
Auth: None (free tier 60+ req/hour); optional apikey for commercial
"""

from pydantic import BaseModel

from api_contracts.shared import ErrorAction


class OpenMeteoRequest(BaseModel):
    """Open-Meteo forecast request parameters."""

    latitude: float | None = None
    longitude: float | None = None
    hourly: list[str] | None = None
    daily: list[str] | None = None
    timezone: str | None = None
    forecast_days: int | None = None
    past_days: int | None = None


class OpenMeteoHourlyResponse(BaseModel):
    """Hourly weather data from Open-Meteo."""

    time: list[str] | None = None
    temperature_2m: list[float] | None = None
    precipitation: list[float] | None = None
    wind_speed_10m: list[float] | None = None
    wind_gusts_10m: list[float] | None = None
    weather_code: list[int] | None = None
    cloud_cover: list[int] | None = None
    relative_humidity_2m: list[int] | None = None
    surface_pressure: list[float] | None = None


class OpenMeteoDailyResponse(BaseModel):
    """Daily weather data from Open-Meteo."""

    time: list[str] | None = None
    temperature_2m_max: list[float] | None = None
    temperature_2m_min: list[float] | None = None
    precipitation_sum: list[float] | None = None
    wind_speed_10m_max: list[float] | None = None
    sunrise: list[str] | None = None
    sunset: list[str] | None = None


class OpenMeteoCurrentWeather(BaseModel):
    """Current weather from Open-Meteo."""

    temperature: float | None = None
    windspeed: float | None = None
    winddirection: float | None = None
    weathercode: int | None = None
    time: str | None = None


class OpenMeteoResponse(BaseModel):
    """Open-Meteo forecast/historical response."""

    latitude: float | None = None
    longitude: float | None = None
    timezone: str | None = None
    hourly: OpenMeteoHourlyResponse | None = None
    daily: OpenMeteoDailyResponse | None = None
    current_weather: OpenMeteoCurrentWeather | None = None


class OpenMeteoError(BaseModel):
    """Open-Meteo error response."""

    error: bool | None = None
    reason: str | None = None

    @classmethod
    def classify(cls, code: int | None = None, error: str | None = None) -> ErrorAction:
        """Map Open-Meteo error to retry action."""
        if code == 429 or (error and "rate" in (error or "").lower()):
            return ErrorAction.RETRY_WITH_BACKOFF
        if code is not None and code >= 500:
            return ErrorAction.RETRY_WITH_BACKOFF
        if code == 401 or (error and "unauthorized" in (error or "").lower()):
            return ErrorAction.FAIL_HARD
        return ErrorAction.FAIL_HARD
