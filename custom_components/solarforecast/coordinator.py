"""Coordinator for Solar Forecast."""

from __future__ import annotations

from datetime import datetime

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_SCAN_INTERVAL, DOMAIN, LOGGER
from .models import SolarForecastData
from .open_meteo import OpenMeteoClient, OpenMeteoError


class SolarForecastUpdateCoordinator(DataUpdateCoordinator[SolarForecastData]):
    """Fetch solar forecast data for a config entry."""

    config_entry: ConfigEntry

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            logger=LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=DEFAULT_SCAN_INTERVAL,
            always_update=False,
        )
        self._client = OpenMeteoClient(async_get_clientsession(hass))

    async def _async_update_data(self) -> SolarForecastData:
        """Fetch the latest forecast."""
        config: dict[str, object] = {
            CONF_LATITUDE: self.config_entry.data[CONF_LATITUDE],
            CONF_LONGITUDE: self.config_entry.data[CONF_LONGITUDE],
            **self.config_entry.options,
        }

        try:
            return await self._client.async_fetch_forecast(config)
        except OpenMeteoError as err:
            raise UpdateFailed(str(err)) from err

    @property
    def local_now(self) -> datetime:
        """Return the current time in the forecast timezone."""
        return datetime.now(self.data.generated_at.tzinfo)
