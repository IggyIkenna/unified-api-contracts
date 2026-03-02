"""Open-Meteo source schemas — weather data at kick-off."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict


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
