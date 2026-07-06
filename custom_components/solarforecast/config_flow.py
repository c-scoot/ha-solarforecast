"""Config flow for Solar Forecast."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    EntitySelector,
    EntitySelectorConfig,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
    CONF_ACTUAL_ENERGY_ENTITY,
    CONF_INVERTER_POWER,
    CONF_LOSS_PERCENT,
    CONF_PANEL_POWER,
    CONF_TEMPERATURE_COEFFICIENT,
    CONF_WEATHER_MODEL,
    DEFAULT_LOSS_PERCENT,
    DEFAULT_NAME,
    DEFAULT_PANEL_AZIMUTH,
    DEFAULT_PANEL_POWER,
    DEFAULT_PANEL_TILT,
    DEFAULT_TEMPERATURE_COEFFICIENT,
    DOMAIN,
    WEATHER_MODEL_AUTO,
    WEATHER_MODEL_OPTIONS,
)


class SolarForecastConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Solar Forecast."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: ConfigEntry,
    ) -> SolarForecastOptionsFlow:
        """Return the options flow."""
        return SolarForecastOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        if user_input is not None:
            weather_model = user_input[CONF_WEATHER_MODEL]

            await self.async_set_unique_id(
                (
                    f"{user_input[CONF_NAME]}:"
                    f"{user_input[CONF_LATITUDE]}:"
                    f"{user_input[CONF_LONGITUDE]}"
                ).lower()
            )
            self._abort_if_unique_id_configured()

            inverter_power = user_input.get(CONF_INVERTER_POWER)

            return self.async_create_entry(
                title=user_input[CONF_NAME],
                data={
                    CONF_LATITUDE: user_input[CONF_LATITUDE],
                    CONF_LONGITUDE: user_input[CONF_LONGITUDE],
                },
                options={
                    "azimuth": user_input["azimuth"],
                    "declination": user_input["declination"],
                    CONF_ACTUAL_ENERGY_ENTITY: user_input.get(CONF_ACTUAL_ENERGY_ENTITY)
                    or None,
                    CONF_PANEL_POWER: user_input[CONF_PANEL_POWER],
                    CONF_INVERTER_POWER: inverter_power if inverter_power else None,
                    CONF_LOSS_PERCENT: user_input[CONF_LOSS_PERCENT],
                    CONF_TEMPERATURE_COEFFICIENT: user_input[
                        CONF_TEMPERATURE_COEFFICIENT
                    ],
                    CONF_WEATHER_MODEL: weather_model,
                },
            )

        return self.async_show_form(
            step_id="user",
            data_schema=_user_schema(
                {
                    CONF_NAME: self.hass.config.location_name or DEFAULT_NAME,
                    CONF_LATITUDE: self.hass.config.latitude,
                    CONF_LONGITUDE: self.hass.config.longitude,
                    "declination": DEFAULT_PANEL_TILT,
                    "azimuth": DEFAULT_PANEL_AZIMUTH,
                    CONF_PANEL_POWER: DEFAULT_PANEL_POWER,
                    CONF_ACTUAL_ENERGY_ENTITY: None,
                    CONF_INVERTER_POWER: None,
                    CONF_LOSS_PERCENT: DEFAULT_LOSS_PERCENT,
                    CONF_TEMPERATURE_COEFFICIENT: DEFAULT_TEMPERATURE_COEFFICIENT,
                    CONF_WEATHER_MODEL: WEATHER_MODEL_AUTO,
                }
            ),
        )


class SolarForecastOptionsFlow(OptionsFlowWithReload):
    """Handle Solar Forecast options."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Manage the integration options."""
        if user_input is not None:
            inverter_power = user_input.get(CONF_INVERTER_POWER)
            return self.async_create_entry(
                title="",
                data={
                    "azimuth": user_input["azimuth"],
                    "declination": user_input["declination"],
                    CONF_ACTUAL_ENERGY_ENTITY: user_input.get(CONF_ACTUAL_ENERGY_ENTITY)
                    or None,
                    CONF_PANEL_POWER: user_input[CONF_PANEL_POWER],
                    CONF_INVERTER_POWER: inverter_power if inverter_power else None,
                    CONF_LOSS_PERCENT: user_input[CONF_LOSS_PERCENT],
                    CONF_TEMPERATURE_COEFFICIENT: user_input[
                        CONF_TEMPERATURE_COEFFICIENT
                    ],
                    CONF_WEATHER_MODEL: user_input[CONF_WEATHER_MODEL],
                },
            )

        current_options = {
            "azimuth": self.config_entry.options.get("azimuth", DEFAULT_PANEL_AZIMUTH),
            "declination": self.config_entry.options.get(
                "declination", DEFAULT_PANEL_TILT
            ),
            CONF_ACTUAL_ENERGY_ENTITY: self.config_entry.options.get(
                CONF_ACTUAL_ENERGY_ENTITY
            ),
            CONF_PANEL_POWER: self.config_entry.options.get(
                CONF_PANEL_POWER, DEFAULT_PANEL_POWER
            ),
            CONF_INVERTER_POWER: self.config_entry.options.get(CONF_INVERTER_POWER),
            CONF_LOSS_PERCENT: self.config_entry.options.get(
                CONF_LOSS_PERCENT, DEFAULT_LOSS_PERCENT
            ),
            CONF_TEMPERATURE_COEFFICIENT: self.config_entry.options.get(
                CONF_TEMPERATURE_COEFFICIENT,
                DEFAULT_TEMPERATURE_COEFFICIENT,
            ),
            CONF_WEATHER_MODEL: self.config_entry.options.get(
                CONF_WEATHER_MODEL, WEATHER_MODEL_AUTO
            ),
        }

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                _options_schema(),
                current_options,
            ),
        )


def _weather_model_selector() -> SelectSelector:
    """Return the weather model selector."""
    return SelectSelector(
        SelectSelectorConfig(
            options=list(WEATHER_MODEL_OPTIONS),
            mode=SelectSelectorMode.DROPDOWN,
        )
    )


def _actual_energy_entity_selector() -> EntitySelector:
    """Return the actual energy selector."""
    return EntitySelector(
        EntitySelectorConfig(
            domain="sensor",
        )
    )


def _user_schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build the initial user config schema."""
    return vol.Schema(
        {
            vol.Required(CONF_NAME, default=defaults[CONF_NAME]): str,
            vol.Required(CONF_LATITUDE, default=defaults[CONF_LATITUDE]): cv.latitude,
            vol.Required(CONF_LONGITUDE, default=defaults[CONF_LONGITUDE]): cv.longitude,
            **_options_schema_fields(defaults),
        }
    )


def _options_schema() -> vol.Schema:
    """Build the options schema."""
    return vol.Schema(
        _options_schema_fields(
            {
                "declination": DEFAULT_PANEL_TILT,
                "azimuth": DEFAULT_PANEL_AZIMUTH,
                CONF_ACTUAL_ENERGY_ENTITY: None,
                CONF_PANEL_POWER: DEFAULT_PANEL_POWER,
                CONF_INVERTER_POWER: None,
                CONF_LOSS_PERCENT: DEFAULT_LOSS_PERCENT,
                CONF_TEMPERATURE_COEFFICIENT: DEFAULT_TEMPERATURE_COEFFICIENT,
                CONF_WEATHER_MODEL: WEATHER_MODEL_AUTO,
            }
        )
    )


def _options_schema_fields(defaults: dict[str, Any]) -> dict:
    """Return shared config fields for setup and options."""
    schema: dict = {
        vol.Required("declination", default=defaults["declination"]): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=90)
        ),
        vol.Required("azimuth", default=defaults["azimuth"]): vol.All(
            vol.Coerce(int), vol.Range(min=0, max=360)
        ),
        vol.Required(CONF_PANEL_POWER, default=defaults[CONF_PANEL_POWER]): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=500000)
        ),
        vol.Required(CONF_LOSS_PERCENT, default=defaults[CONF_LOSS_PERCENT]): vol.All(
            vol.Coerce(float), vol.Range(min=0, max=100)
        ),
        vol.Required(
            CONF_TEMPERATURE_COEFFICIENT,
            default=defaults[CONF_TEMPERATURE_COEFFICIENT],
        ): vol.All(vol.Coerce(float), vol.Range(min=-0.02, max=0)),
        vol.Required(
            CONF_WEATHER_MODEL,
            default=defaults[CONF_WEATHER_MODEL],
        ): _weather_model_selector(),
    }

    actual_energy_default = defaults.get(CONF_ACTUAL_ENERGY_ENTITY)
    if actual_energy_default is None:
        schema[vol.Optional(CONF_ACTUAL_ENERGY_ENTITY)] = _actual_energy_entity_selector()
    else:
        schema[
            vol.Optional(CONF_ACTUAL_ENERGY_ENTITY, default=actual_energy_default)
        ] = _actual_energy_entity_selector()

    inverter_default = defaults.get(CONF_INVERTER_POWER)
    if inverter_default is None:
        schema[vol.Optional(CONF_INVERTER_POWER)] = vol.All(
            vol.Coerce(int), vol.Range(min=1, max=500000)
        )
    else:
        schema[vol.Optional(CONF_INVERTER_POWER, default=inverter_default)] = vol.All(
            vol.Coerce(int), vol.Range(min=1, max=500000)
        )

    return schema
