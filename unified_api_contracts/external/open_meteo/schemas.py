"""Open-Meteo weather API schemas.

Ref: https://open-meteo.com/en/docs
Auth: None (free tier 60+ req/hour); optional apikey for commercial
"""

__api_version__ = "v1"  # matches provider_api_versions.yaml

from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict

from unified_api_contracts.canonical.crosscutting.errors import ErrorAction


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
            return ErrorAction.RETRY
        if code is not None and code >= 500:
            return ErrorAction.RETRY
        if code == 401 or (error and "unauthorized" in (error or "").lower()):
            return ErrorAction.FAIL
        return ErrorAction.FAIL


# =============================================================================
# Source schemas (merged from external/sports/sources/open_meteo/)
# =============================================================================


class WeatherCondition(StrEnum):
    """General weather condition categories."""

    CLEAR = "clear"
    PARTLY_CLOUDY = "partly_cloudy"
    CLOUDY = "cloudy"
    FOG = "fog"
    DRIZZLE = "drizzle"
    RAIN = "rain"
    HEAVY_RAIN = "heavy_rain"
    SNOW = "snow"
    THUNDERSTORM = "thunderstorm"


class OpenMeteoWeather(BaseModel):
    """Open-Meteo current weather observation."""

    model_config = ConfigDict(frozen=True)

    latitude: float
    longitude: float
    temperature_celsius: float
    wind_speed_ms: float | None = None
    wind_direction_degrees: int | None = None
    humidity_pct: int | None = None
    pressure_hpa: int | None = None
    cloud_cover_pct: int | None = None
    precipitation_mm: float | None = None
    condition: WeatherCondition | None = None
    observation_time_utc: datetime

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class OpenMeteoForecast(BaseModel):
    """Open-Meteo hourly forecast entry."""

    model_config = ConfigDict(frozen=True)

    latitude: float
    longitude: float
    forecast_time_utc: datetime
    temperature_celsius: float
    wind_speed_ms: float | None = None
    humidity_pct: int | None = None
    precipitation_probability_pct: int | None = None
    precipitation_mm: float | None = None
    condition: WeatherCondition | None = None

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)


class WeatherAtKickoff(BaseModel):
    """Resolved weather conditions at match kick-off time and venue."""

    model_config = ConfigDict(frozen=True)

    fixture_id: str
    venue_latitude: float
    venue_longitude: float
    kickoff_utc: datetime
    temperature_celsius: float
    wind_speed_ms: float | None = None
    humidity_pct: int | None = None
    precipitation_mm: float | None = None
    condition: WeatherCondition | None = None
    data_source: str

    @classmethod
    def from_raw(cls, data: dict[str, str | int | float | bool | None]) -> Self:
        """Construct from raw API response."""
        return cls.model_validate(data)
