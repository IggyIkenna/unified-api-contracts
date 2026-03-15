"""Open-Meteo weather normalizers.

Weather data -> CanonicalFeatureRecord.
"""

from __future__ import annotations

from datetime import UTC, datetime

from ...canonical.domain.features import CanonicalFeatureRecord, FeatureMetadata
from .schemas import OpenMeteoForecast, OpenMeteoWeather


def _to_iso_utc(dt: datetime | None) -> str:
    """Convert datetime to ISO 8601 UTC string."""
    if dt is None:
        return datetime.now(UTC).isoformat()
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt.isoformat()


def normalize_open_meteo_weather(
    raw: OpenMeteoWeather,
    source: str = "open_meteo",
) -> CanonicalFeatureRecord:
    """Normalize OpenMeteoWeather to CanonicalFeatureRecord.

    Primary feature: temperature_celsius. Single record per observation.
    """
    return CanonicalFeatureRecord(
        feature_name="temperature_celsius",
        value=float(raw.temperature_celsius),
        timestamp=_to_iso_utc(raw.observation_time_utc),
        metadata=FeatureMetadata(
            name="open_meteo_weather",
            version="v1",
            source=source,
            domain="weather",
        ),
    )


def normalize_open_meteo_weather_multi(
    raw: OpenMeteoWeather,
    source: str = "open_meteo",
) -> list[CanonicalFeatureRecord]:
    """Normalize OpenMeteoWeather to multiple CanonicalFeatureRecords.

    One record per metric: temperature, humidity, wind_speed, precipitation, etc.
    """
    ts = _to_iso_utc(raw.observation_time_utc)
    meta = FeatureMetadata(
        name="open_meteo_weather",
        version="v1",
        source=source,
        domain="weather",
    )
    records: list[CanonicalFeatureRecord] = [
        CanonicalFeatureRecord(
            feature_name="temperature_celsius",
            value=float(raw.temperature_celsius),
            timestamp=ts,
            metadata=meta,
        ),
    ]
    if raw.humidity_pct is not None:
        records.append(
            CanonicalFeatureRecord(
                feature_name="humidity_pct",
                value=float(raw.humidity_pct),
                timestamp=ts,
                metadata=meta,
            )
        )
    if raw.wind_speed_ms is not None:
        records.append(
            CanonicalFeatureRecord(
                feature_name="wind_speed_ms",
                value=float(raw.wind_speed_ms),
                timestamp=ts,
                metadata=meta,
            )
        )
    if raw.precipitation_mm is not None:
        records.append(
            CanonicalFeatureRecord(
                feature_name="precipitation_mm",
                value=float(raw.precipitation_mm),
                timestamp=ts,
                metadata=meta,
            )
        )
    if raw.cloud_cover_pct is not None:
        records.append(
            CanonicalFeatureRecord(
                feature_name="cloud_cover_pct",
                value=float(raw.cloud_cover_pct),
                timestamp=ts,
                metadata=meta,
            )
        )
    return records


def normalize_open_meteo_forecast(
    raw: OpenMeteoForecast,
    source: str = "open_meteo",
) -> CanonicalFeatureRecord:
    """Normalize OpenMeteoForecast to CanonicalFeatureRecord.

    Primary feature: temperature_celsius at forecast time.
    """
    return CanonicalFeatureRecord(
        feature_name="temperature_celsius",
        value=float(raw.temperature_celsius),
        timestamp=_to_iso_utc(raw.forecast_time_utc),
        metadata=FeatureMetadata(
            name="open_meteo_forecast",
            version="v1",
            source=source,
            domain="weather",
        ),
    )


__all__ = [
    "normalize_open_meteo_forecast",
    "normalize_open_meteo_weather",
    "normalize_open_meteo_weather_multi",
]
