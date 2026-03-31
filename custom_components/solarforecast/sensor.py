"""Sensor platform for Solar Forecast."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any, Callable

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event

from .const import (
    ATTR_ACTUAL_ENERGY,
    ATTR_ACTUAL_ENTITY,
    ATTR_CLOUD_COVER,
    ATTR_DAILY_FORECAST,
    ATTR_FORECAST_ENERGY,
    ATTR_FORECAST_TIME,
    ATTR_FORECAST_TIMEZONE,
    ATTR_GENERATED_AT,
    ATTR_HOURLY_FORECAST,
    ATTR_IRRADIANCE,
    ATTR_PROVIDER,
    ATTR_SITE_AZIMUTH,
    ATTR_SITE_TILT,
    ATTR_TEMPERATURE,
    ATTR_VARIANCE_PERCENT,
    CONF_ACTUAL_ENERGY_ENTITY,
    DOMAIN,
)
from .coordinator import SolarForecastUpdateCoordinator
from .entity import SolarForecastEntity
from .models import SolarForecastData, SolarForecastPoint

ACTUAL_DEPENDENT_SENSOR_KEYS = {
    "actual_energy_today",
    "production_variance_today",
    "production_variance_percentage_today",
}


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
        key="actual_energy_today",
        translation_key="actual_energy_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda _data, coordinator: _get_actual_energy_today_kwh(coordinator),
    ),
    SolarForecastSensorDescription(
        key="production_variance_today",
        translation_key="production_variance_today",
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, coordinator: _production_variance_today(data, coordinator),
    ),
    SolarForecastSensorDescription(
        key="production_variance_percentage_today",
        translation_key="production_variance_percentage_today",
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data, coordinator: _production_variance_percentage_today(
            data, coordinator
        ),
    ),
    SolarForecastSensorDescription(
        key="forecast_outlook",
        translation_key="forecast_outlook",
        device_class=SensorDeviceClass.TIMESTAMP,
        value_fn=lambda data, _coordinator: data.generated_at,
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
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{description.key}"

    async def async_added_to_hass(self) -> None:
        """Register callbacks when the entity is added."""
        await super().async_added_to_hass()

        actual_entity_id = _actual_energy_entity_id(self.coordinator)
        if (
            actual_entity_id is not None
            and self.entity_description.key in ACTUAL_DEPENDENT_SENSOR_KEYS
        ):
            self.async_on_remove(
                async_track_state_change_event(
                    self.hass,
                    [actual_entity_id],
                    self._handle_actual_sensor_change,
                )
            )

    @callback
    def _handle_actual_sensor_change(self, _event: Any) -> None:
        """Refresh sensor state when the selected actual sensor changes."""
        self.async_write_ha_state()

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
            ATTR_FORECAST_TIMEZONE: self.coordinator.data.timezone,
            ATTR_SITE_AZIMUTH: self.coordinator.config_entry.options["azimuth"],
            ATTR_SITE_TILT: self.coordinator.config_entry.options["declination"],
        }

        actual_entity_id = _actual_energy_entity_id(self.coordinator)
        if actual_entity_id is not None:
            attributes[ATTR_ACTUAL_ENTITY] = actual_entity_id

        if point is not None:
            attributes |= {
                ATTR_FORECAST_TIME: point.start.isoformat(),
                ATTR_IRRADIANCE: point.irradiance_w_m2,
                ATTR_CLOUD_COVER: point.cloud_cover_percent,
                ATTR_TEMPERATURE: point.temperature_c,
            }

        if self.entity_description.key in ACTUAL_DEPENDENT_SENSOR_KEYS:
            actual_energy = _get_actual_energy_today_kwh(self.coordinator)
            forecast_energy = self.coordinator.data.energy_for_date(
                self.coordinator.local_now.date()
            )
            if actual_energy is not None:
                attributes[ATTR_ACTUAL_ENERGY] = actual_energy
                attributes[ATTR_FORECAST_ENERGY] = forecast_energy
                variance_percent = _production_variance_percentage_today(
                    self.coordinator.data,
                    self.coordinator,
                )
                if variance_percent is not None:
                    attributes[ATTR_VARIANCE_PERCENT] = variance_percent

        if self.entity_description.key == "forecast_outlook":
            attributes[ATTR_HOURLY_FORECAST] = _hourly_forecast_points(
                self.coordinator.data,
                self.coordinator,
            )
            attributes[ATTR_DAILY_FORECAST] = _daily_forecast_summary(
                self.coordinator.data,
                self.coordinator,
            )

        return attributes


def _actual_energy_entity_id(
    coordinator: SolarForecastUpdateCoordinator,
) -> str | None:
    """Return the selected actual-energy entity."""
    return coordinator.config_entry.options.get(CONF_ACTUAL_ENERGY_ENTITY)


def _get_actual_energy_today_kwh(
    coordinator: SolarForecastUpdateCoordinator,
) -> float | None:
    """Return the selected actual production value in kWh."""
    entity_id = _actual_energy_entity_id(coordinator)
    if entity_id is None:
        return None

    state = coordinator.hass.states.get(entity_id)
    if state is None or state.state in {"unknown", "unavailable"}:
        return None

    try:
        value = float(state.state)
    except ValueError:
        return None

    unit = state.attributes.get("unit_of_measurement")
    if unit == "kWh":
        return round(value, 3)
    if unit == "Wh":
        return round(value / 1000, 3)
    if unit == "MWh":
        return round(value * 1000, 3)

    return None


def _production_variance_today(
    data: SolarForecastData,
    coordinator: SolarForecastUpdateCoordinator,
) -> float | None:
    """Return today's production variance in kWh."""
    actual_energy = _get_actual_energy_today_kwh(coordinator)
    if actual_energy is None:
        return None

    forecast_energy = data.energy_for_date(coordinator.local_now.date())
    return round(actual_energy - forecast_energy, 3)


def _production_variance_percentage_today(
    data: SolarForecastData,
    coordinator: SolarForecastUpdateCoordinator,
) -> float | None:
    """Return today's production variance as a percentage of forecast."""
    actual_energy = _get_actual_energy_today_kwh(coordinator)
    if actual_energy is None:
        return None

    forecast_energy = data.energy_for_date(coordinator.local_now.date())
    if forecast_energy <= 0:
        return None

    return round(((actual_energy - forecast_energy) / forecast_energy) * 100, 1)


def _hourly_forecast_points(
    data: SolarForecastData,
    coordinator: SolarForecastUpdateCoordinator,
) -> list[dict[str, object]]:
    """Return the next 72 hourly forecast points."""
    current_hour = coordinator.local_now.replace(minute=0, second=0, microsecond=0)
    points = [
        point
        for point in data.points
        if point.start >= current_hour
    ][:72]
    return [
        {
            "start": point.start.isoformat(),
            "energy_kwh": point.energy_kwh,
            "power_w": point.power_w,
            "irradiance_w_m2": point.irradiance_w_m2,
            "cloud_cover_percent": point.cloud_cover_percent,
            "temperature_c": point.temperature_c,
        }
        for point in points
    ]


def _daily_forecast_summary(
    data: SolarForecastData,
    coordinator: SolarForecastUpdateCoordinator,
) -> list[dict[str, object]]:
    """Return a simple daily forecast summary for the next 3 days."""
    today = coordinator.local_now.date()
    return [
        {
            "date": (today + timedelta(days=offset)).isoformat(),
            "energy_kwh": data.energy_for_date(today + timedelta(days=offset)),
        }
        for offset in range(3)
    ]
