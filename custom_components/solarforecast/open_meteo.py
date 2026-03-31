"""Open-Meteo client and solar estimation helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

from aiohttp import ClientError, ClientSession

from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE

from .const import (
    CONF_INVERTER_POWER,
    CONF_LOSS_PERCENT,
    CONF_PANEL_POWER,
    CONF_TEMPERATURE_COEFFICIENT,
    CONF_WEATHER_MODEL,
    OPEN_METEO_PROVIDER,
    OPEN_METEO_URL,
    WEATHER_MODEL_AUTO,
)
from .models import SolarForecastData, SolarForecastPoint


class OpenMeteoError(Exception):
    """Raised when Open-Meteo data cannot be fetched or parsed."""


class OpenMeteoClient:
    """Client for fetching irradiance data from Open-Meteo."""

    def __init__(self, session: ClientSession) -> None:
        """Initialize the client."""
        self._session = session

    async def async_fetch_forecast(self, config: dict[str, Any]) -> SolarForecastData:
        """Fetch and transform the site forecast."""
        params = {
            "latitude": config[CONF_LATITUDE],
            "longitude": config[CONF_LONGITUDE],
            "hourly": ",".join(
                [
                    "temperature_2m",
                    "cloud_cover",
                    "global_tilted_irradiance",
                ]
            ),
            "tilt": config["declination"],
            "azimuth": _to_open_meteo_azimuth(config["azimuth"]),
            "forecast_days": 3,
            "timezone": "auto",
        }

        weather_model = config.get(CONF_WEATHER_MODEL)
        if weather_model and weather_model != WEATHER_MODEL_AUTO:
            params["models"] = weather_model

        try:
            response = await self._session.get(OPEN_METEO_URL, params=params)
            response.raise_for_status()
            payload = await response.json()
        except ClientError as err:
            raise OpenMeteoError(f"Error communicating with Open-Meteo: {err}") from err

        try:
            timezone = payload["timezone"]
            hourly = payload["hourly"]
            tzinfo = ZoneInfo(timezone)

            points = tuple(
                _build_forecast_point(
                    start=datetime.fromisoformat(timestamp).replace(tzinfo=tzinfo),
                    irradiance_w_m2=irradiance,
                    cloud_cover_percent=cloud_cover,
                    temperature_c=temperature,
                    config=config,
                )
                for timestamp, temperature, cloud_cover, irradiance in zip(
                    hourly["time"],
                    hourly["temperature_2m"],
                    hourly["cloud_cover"],
                    hourly["global_tilted_irradiance"],
                    strict=True,
                )
            )
        except (KeyError, TypeError, ValueError) as err:
            raise OpenMeteoError("Open-Meteo returned an unexpected response") from err

        return SolarForecastData(
            provider=OPEN_METEO_PROVIDER,
            weather_model=weather_model or WEATHER_MODEL_AUTO,
            timezone=timezone,
            generated_at=datetime.now(tz=tzinfo),
            points=points,
        )


def _build_forecast_point(
    *,
    start: datetime,
    irradiance_w_m2: float,
    cloud_cover_percent: float,
    temperature_c: float,
    config: dict[str, Any],
) -> SolarForecastPoint:
    """Convert weather inputs into a simple PV forecast point."""
    panel_power = float(config[CONF_PANEL_POWER])
    inverter_power = (
        float(config[CONF_INVERTER_POWER])
        if config.get(CONF_INVERTER_POWER) is not None
        else None
    )
    loss_factor = 1 - (float(config[CONF_LOSS_PERCENT]) / 100)
    temperature_coefficient = float(config[CONF_TEMPERATURE_COEFFICIENT])

    cell_temperature = float(temperature_c) + (float(irradiance_w_m2) / 800) * 20
    temperature_factor = 1 + (temperature_coefficient * (cell_temperature - 25))

    dc_power = panel_power * (float(irradiance_w_m2) / 1000) * temperature_factor
    dc_power *= loss_factor
    power_w = max(0.0, dc_power)

    if inverter_power is not None:
        power_w = min(power_w, inverter_power)

    return SolarForecastPoint(
        start=start,
        power_w=round(power_w, 1),
        energy_kwh=round(power_w / 1000, 3),
        irradiance_w_m2=round(float(irradiance_w_m2), 1),
        cloud_cover_percent=round(float(cloud_cover_percent), 1),
        temperature_c=round(float(temperature_c), 1),
    )


def _to_open_meteo_azimuth(home_assistant_azimuth: int | float) -> float:
    """Convert HA azimuth to Open-Meteo azimuth.

    Home Assistant style:
    - 0 = north
    - 90 = east
    - 180 = south
    - 270 = west

    Open-Meteo style:
    - 0 = south
    - -90 = east
    - 90 = west
    - 180 / -180 = north
    """
    return float(home_assistant_azimuth) - 180
