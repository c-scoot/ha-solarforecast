"""Constants for the Solar Forecast integration."""

from __future__ import annotations

from datetime import timedelta
import logging
from typing import Final

DOMAIN = "solarforecast"
LOGGER = logging.getLogger(__package__)

ATTR_CLOUD_COVER = "cloud_cover"
ATTR_DAILY_FORECAST = "daily_forecast"
ATTR_FORECAST_ENERGY = "forecast_energy_today"
ATTR_FORECAST_TIME = "forecast_time"
ATTR_FORECAST_TIMEZONE = "forecast_timezone"
ATTR_GENERATED_AT = "generated_at"
ATTR_HOURLY_FORECAST = "hourly_forecast"
ATTR_IRRADIANCE = "irradiance"
ATTR_ACTUAL_ENERGY = "actual_energy_today"
ATTR_ACTUAL_ENTITY = "actual_energy_entity"
ATTR_PROVIDER = "provider"
ATTR_SITE_AZIMUTH = "site_azimuth"
ATTR_SITE_TILT = "site_tilt"
ATTR_TEMPERATURE = "temperature"
ATTR_VARIANCE_PERCENT = "variance_percent"

CONF_ACTUAL_ENERGY_ENTITY = "actual_energy_entity"
CONF_INVERTER_POWER = "inverter_power"
CONF_LOSS_PERCENT = "loss_percent"
CONF_PANEL_POWER = "panel_power"
CONF_TEMPERATURE_COEFFICIENT = "temperature_coefficient"
CONF_WEATHER_MODEL = "weather_model"

DEFAULT_LOSS_PERCENT = 14.0
DEFAULT_NAME = "Solar Forecast"
DEFAULT_PANEL_AZIMUTH = 180
DEFAULT_PANEL_POWER = 4000
DEFAULT_PANEL_TILT = 35
DEFAULT_SCAN_INTERVAL = timedelta(minutes=30)
DEFAULT_TEMPERATURE_COEFFICIENT = -0.004

OPEN_METEO_PROVIDER = "open_meteo"
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

PLATFORMS = ["sensor"]

WEATHER_MODEL_AUTO = "best_match"

WEATHER_MODEL_OPTIONS: Final[tuple[dict[str, str], ...]] = (
    {
        "value": WEATHER_MODEL_AUTO,
        "label": "Automatic (Best Match)",
    },
    {
        "value": "ukmo_uk_deterministic_2km",
        "label": "UK Met Office UK 2 km",
    },
    {
        "value": "ukmo_global_deterministic_10km",
        "label": "UK Met Office Global 10 km",
    },
    {
        "value": "ecmwf_ifs025",
        "label": "ECMWF IFS 0.25 deg",
    },
    {
        "value": "dwd_icon_eu",
        "label": "DWD ICON EU",
    },
    {
        "value": "ncep_gfs013",
        "label": "NCEP GFS 0.11 deg",
    },
)

WEATHER_MODEL_FORECAST_DAYS: Final[dict[str, int]] = {
    "ukmo_uk_deterministic_2km": 2,
    "ukmo_global_deterministic_10km": 2,
}
