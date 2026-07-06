"""Base entity for Solar Forecast."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import SolarForecastUpdateCoordinator


class SolarForecastEntity(CoordinatorEntity[SolarForecastUpdateCoordinator]):
    """Base entity for the Solar Forecast integration."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: SolarForecastUpdateCoordinator) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        entry = coordinator.config_entry
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            manufacturer="Open-Meteo",
            model="PV Forecast",
            name=entry.title,
        )
