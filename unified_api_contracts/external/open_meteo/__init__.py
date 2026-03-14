"""Open-Meteo weather API contracts."""

from .schemas import (
    OpenMeteoCurrentWeather,
    OpenMeteoDailyResponse,
    OpenMeteoError,
    OpenMeteoForecast,
    OpenMeteoHourlyResponse,
    OpenMeteoRequest,
    OpenMeteoResponse,
    OpenMeteoWeather,
    WeatherAtKickoff,
    WeatherCondition,
)

__all__ = [
    "OpenMeteoCurrentWeather",
    "OpenMeteoDailyResponse",
    "OpenMeteoError",
    "OpenMeteoForecast",
    "OpenMeteoHourlyResponse",
    "OpenMeteoRequest",
    "OpenMeteoResponse",
    "OpenMeteoWeather",
    "WeatherAtKickoff",
    "WeatherCondition",
]
