"""Config flow for Solar Forecast."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE, CONF_NAME
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.selector import (
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
)

from .const import (
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
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_NAME, default=self.hass.config.location_name or DEFAULT_NAME
                    ): str,
                    vol.Required(
                        CONF_LATITUDE, default=self.hass.config.latitude
                    ): cv.latitude,
                    vol.Required(
                        CONF_LONGITUDE, default=self.hass.config.longitude
                    ): cv.longitude,
                    vol.Required("declination", default=DEFAULT_PANEL_TILT): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=90)
                    ),
                    vol.Required("azimuth", default=DEFAULT_PANEL_AZIMUTH): vol.All(
                        vol.Coerce(int), vol.Range(min=0, max=360)
                    ),
                    vol.Required(
                        CONF_PANEL_POWER, default=DEFAULT_PANEL_POWER
                    ): vol.All(vol.Coerce(int), vol.Range(min=1, max=500000)),
                    vol.Optional(CONF_INVERTER_POWER): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=500000)
                    ),
                    vol.Required(
                        CONF_LOSS_PERCENT, default=DEFAULT_LOSS_PERCENT
                    ): vol.All(vol.Coerce(float), vol.Range(min=0, max=100)),
                    vol.Required(
                        CONF_TEMPERATURE_COEFFICIENT,
                        default=DEFAULT_TEMPERATURE_COEFFICIENT,
                    ): vol.All(vol.Coerce(float), vol.Range(min=-0.02, max=0)),
                    vol.Required(
                        CONF_WEATHER_MODEL, default=WEATHER_MODEL_AUTO
                    ): SelectSelector(
                        SelectSelectorConfig(
                            options=list(WEATHER_MODEL_OPTIONS),
                            mode=SelectSelectorMode.DROPDOWN,
                        )
                    ),
                }
            ),
        )
