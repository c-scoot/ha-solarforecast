"""Sensor platform for Solar Forecast."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import (
    ATTR_CLOUD_COVER,
    ATTR_FORECAST_TIME,
    ATTR_GENERATED_AT,
    ATTR_IRRADIANCE,
    ATTR_PROVIDER,
    ATTR_SITE_AZIMUTH,
    ATTR_SITE_TILT,
    ATTR_TEMPERATURE,
    DOMAIN,
)
from .coordinator import SolarForecastUpdateCoordinator
from .entity import SolarForecastEntity
from .models import SolarForecastData, SolarForecastPoint


@dataclass(frozen=True, kw_only=True)
class SolarForecastSensorDescription(SensorEntityDescription):
    """Description for Solar Forecast sensors."""

    value_fn: Callable[[SolarForecastData, SolarForecastUpdateCoordinator], object]
    point_fn: Callable[
        [SolarForecastData, SolarForecastUpdateCoordinator], SolarForecastPoint | None
    ] | None = None


SENSOR_DESCRIPTIONS: tuple[SolarForecastSensorDescription, ...] = (
    SolarForecastSensorDescription(
        key="estimated_power_now",
        translation_key="estimated_power_now",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, coordinator: (
            data.point_for_time(coordinator.local_now).power_w
            if data.point_for_time(coordinator.local_now) is not None
            else None
        ),
        point_fn=lambda data, coordinator: data.point_for_time(coordinator.local_now),
    ),
    SolarForecastSensorDescription(
        key="estimated_energy_next_hour",
        translation_key="estimated_energy_next_hour",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, coordinator: (
            data.next_point_after(coordinator.local_now).energy_kwh
            if data.next_point_after(coordinator.local_now) is not None
            else None
        ),
        point_fn=lambda data, coordinator: data.next_point_after(coordinator.local_now),
    ),
    SolarForecastSensorDescription(
        key="estimated_energy_today",
        translation_key="estimated_energy_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, coordinator: data.energy_for_date(coordinator.local_now.date()),
    ),
    SolarForecastSensorDescription(
        key="estimated_energy_remaining_today",
        translation_key="estimated_energy_remaining_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, coordinator: data.energy_remaining_today(coordinator.local_now),
    ),
    SolarForecastSensorDescription(
        key="estimated_energy_tomorrow",
        translation_key="estimated_energy_tomorrow",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, coordinator: data.energy_for_date(
            coordinator.local_now.date() + timedelta(days=1)
        ),
    ),
    SolarForecastSensorDescription(
        key="weather_model",
        translation_key="weather_model",
        value_fn=lambda data, _coordinator: data.weather_model or "best_match",
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up Solar Forecast sensors from a config entry."""
    coordinator: SolarForecastUpdateCoordinator = hass.data[DOMAIN][entry.entry_id]
    async_add_entities(
        SolarForecastSensor(coordinator, description) for description in SENSOR_DESCRIPTIONS
    )


class SolarForecastSensor(SolarForecastEntity, SensorEntity):
    """Representation of a Solar Forecast sensor."""

    entity_description: SolarForecastSensorDescription

    def __init__(
        self,
        coordinator: SolarForecastUpdateCoordinator,
        description: SolarForecastSensorDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = (
            f"{coordinator.config_entry.entry_id}_{description.key}"
        )

    @property
    def native_value(self) -> object:
        """Return the sensor state."""
        return self.entity_description.value_fn(self.coordinator.data, self.coordinator)

    @property
    def extra_state_attributes(self) -> dict[str, object]:
        """Return extra state attributes."""
        point = None
        if self.entity_description.point_fn is not None:
            point = self.entity_description.point_fn(self.coordinator.data, self.coordinator)

        attributes: dict[str, object] = {
            ATTR_GENERATED_AT: self.coordinator.data.generated_at.isoformat(),
            ATTR_PROVIDER: self.coordinator.data.provider,
            ATTR_SITE_AZIMUTH: self.coordinator.config_entry.options["azimuth"],
            ATTR_SITE_TILT: self.coordinator.config_entry.options["declination"],
        }

        if point is not None:
            attributes |= {
                ATTR_FORECAST_TIME: point.start.isoformat(),
                ATTR_IRRADIANCE: point.irradiance_w_m2,
                ATTR_CLOUD_COVER: point.cloud_cover_percent,
                ATTR_TEMPERATURE: point.temperature_c,
            }

        return attributes
