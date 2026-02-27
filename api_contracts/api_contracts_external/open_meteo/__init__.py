"""Open-Meteo weather API contracts."""

from .schemas import (
    OpenMeteoCurrentWeather,
    OpenMeteoDailyResponse,
    OpenMeteoError,
    OpenMeteoHourlyResponse,
    OpenMeteoRequest,
    OpenMeteoResponse,
)

__all__ = [
    "OpenMeteoCurrentWeather",
    "OpenMeteoDailyResponse",
    "OpenMeteoError",
    "OpenMeteoHourlyResponse",
    "OpenMeteoRequest",
    "OpenMeteoResponse",
]
