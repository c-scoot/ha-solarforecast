# ha-solarforecast

Home Assistant custom integration for forecasting rooftop solar production.

This project is intended to be original work. We can learn from the public behavior, documentation, and API shape of existing tools such as Forecast.Solar, but we should not copy their code or repackage their service as our own. The goal is to keep the simple Home Assistant user experience people already like, while improving forecast accuracy, especially on cloudy and changeable days.

## Goals

- Keep the setup simple for Home Assistant users.
- Support the core inputs people already understand: location, tilt, azimuth, array size, inverter cap, and optional shading/horizon information.
- Improve forecast accuracy when cloud cover changes quickly.
- Build a provider-agnostic architecture so we can test and switch weather sources.
- Optionally learn from recent actual production data in Home Assistant to reduce site-specific bias.

## What Forecast.Solar currently does

Based on the current Home Assistant integration and the `forecast_solar` Python client:

- Home Assistant sends latitude, longitude, panel declination, azimuth, total module power, and optional API key.
- The integration also supports morning/evening damping and inverter size tuning.
- The upstream Python client supports extra parameters such as horizon, multiple planes, and an `actual` production value for the current day when an API key is available.
- Home Assistant polls the service hourly on the public tier, or every 30 minutes when an API key is configured.
- The built-in integration exposes sensors for today's production, tomorrow's production, remaining today, this hour, next hour, current power, and peak times.
- Forecast.Solar is described by Home Assistant as a service based on historic averages combined with weather forecasting.

### Current strengths

- Very easy to configure.
- Good enough for basic "rough planning" automations.
- Includes practical tuning knobs such as damping and inverter clipping.
- Works well when the weather is stable and the array geometry is known.

### Current limitations relevant to this project

- The Home Assistant integration is a cloud-polling wrapper around a third-party forecast service rather than an independently modeled PV forecast.
- Accuracy appears to depend heavily on the upstream weather model and on manually tuned damping values.
- Cloud-driven underperformance and overperformance are hard to correct with only morning/evening damping.
- The free/public tier is limited to lower time resolution and shorter forecast horizon.
- The built-in integration handles multi-plane systems by asking users to create multiple integration instances instead of modeling a complete site in one place.

### Important inference

The public docs explain the Forecast.Solar inputs, outputs, and account tiers, but they do not clearly document the exact weather-model stack on the pages reviewed for this pass. So the points above about cloud-related weaknesses are partly an inference from the exposed controls and from how the Home Assistant integration calls the API.

## Why cloudy forecasts are the main problem

Cloudy-day accuracy usually breaks down for one or more of these reasons:

- Total cloud cover is too coarse. Two forecasts with the same cloud percentage can produce very different irradiance depending on cloud thickness and cloud layer.
- Fast-moving local cloud edges matter. A one-hour forecast can miss short bright or dark periods that strongly affect PV output.
- Plane-of-array irradiance is more important than generic weather summaries. For PV forecasting we care about GHI, DNI, DHI, GTI or POA-style inputs, not just "cloudy" versus "sunny".
- Site effects matter. Nearby obstructions, haze, coastal microclimates, snow, dirt, and clipping can create repeatable bias that a generic forecast misses.
- A static damping factor is a blunt tool. It helps with predictable morning or evening shade but not with midday cloud variability.

## Weather and solar data sources worth evaluating

The strongest improvement path is to separate "weather source" from "PV model" so we can benchmark multiple providers against actual output history.

### 1. Open-Meteo

Why it is interesting:

- Exposes solar radiation variables including GHI, DNI, DHI, and GTI.
- Exposes total, low, mid, and high cloud cover.
- Offers 15-minute data in Central Europe and North America, with hourly elsewhere.
- Can route to multiple underlying forecast models including ECMWF, DWD ICON, NOAA, and UK Met Office models.

Why it may help with cloudy conditions:

- Gives us better raw irradiance inputs than a simple cloud percentage.
- Lets us compare multiple weather models without redesigning the integration.
- UK users may benefit from trying UK Met Office-backed data where available.

Trade-offs:

- We would still need to build our own PV conversion model and bias correction.
- Best results will likely require choosing models per region.

### 2. Solcast

Why it is interesting:

- Built specifically for solar forecasting rather than general weather.
- Provides irradiance and PV forecast data at 5 to 60 minute granularity.
- Markets high-resolution cloud tracking and rooftop PV models.
- Offers a free home-PV path with usage limits for personal use.

Why it may help with cloudy conditions:

- Their product is explicitly designed around cloud and irradiance behavior.
- Near-term forecasts should be stronger than generic weather APIs when clouds move quickly.

Trade-offs:

- This is closer to consuming another solar forecast service than owning the full model stack.
- Licensing and rate limits need checking for Home Assistant usage patterns.

### 3. SolarAnywhere

Why it is interesting:

- Uses satellite cloud motion for short horizons and NWP blending for longer horizons.
- Exposes irradiance fields such as GHI, DNI, and DHI, plus modeled power outputs in higher tiers.
- Offers solar-specific forecasting rather than generic weather.

Why it may help with cloudy conditions:

- Satellite cloud motion can be especially useful for the next minutes to few hours, when broken cloud is hardest to predict from coarse hourly forecasts.

Trade-offs:

- Commercial product aimed more at professional and utility-grade use cases.
- Likely too expensive for many hobbyist Home Assistant installs unless we support it as an optional premium provider.

### 4. Tomorrow.io

Why it is interesting:

- Provides solar radiation fields including `solarGHI`, `solarDNI`, and `solarDHI`.
- Also provides broader weather context we could use for temperature and cloud-aware adjustments.

Why it may help with cloudy conditions:

- Gives us solar-specific weather inputs instead of only generic cloud forecasts.

Trade-offs:

- The solar layers are premium features.
- We would still need to build the PV estimation layer ourselves.

## Recommended product direction

Instead of cloning Forecast.Solar behavior, build our own forecast pipeline:

1. Fetch weather and irradiance data from one or more providers.
2. Convert those inputs into plane-of-array irradiance for the user's array geometry.
3. Model DC and AC power with inverter clipping and configurable loss factors.
4. Compare forecast versus recent actual production from Home Assistant.
5. Apply optional site-specific bias correction and short-term adjustment.
6. Expose both forecast sensors and confidence/error metrics.

## Proposed architecture

### Provider layer

- `WeatherProvider` interface
- `OpenMeteoProvider` first, because it is accessible and flexible
- Optional premium providers later: `SolcastProvider`, `SolarAnywhereProvider`, `TomorrowProvider`

### Modeling layer

- Solar position
- Irradiance normalization and transposition to panel plane
- Temperature-aware PV output calculation
- Inverter clipping
- Optional horizon and obstruction losses
- Optional multi-plane aggregation

### Calibration layer

- Compare recent forecast to actual production sensor history
- Learn stable bias per site, per season, and per time-of-day bucket
- Add a short-term "cloud correction" path when recent actual output diverges sharply from forecast under partly cloudy conditions

### Home Assistant layer

- Config flow for system geometry and provider credentials
- Entities for hourly forecast, daily totals, next-hour estimate, peak time, and forecast confidence
- Diagnostics to show why the forecast changed: weather source, cloud impact, clipping, calibration offset

## Proposed build plan

### Phase 1: discovery and benchmark

- Create a baseline dataset using actual production from Home Assistant plus one or more external weather sources.
- Benchmark Forecast.Solar output against actuals if we have sample data available.
- Define error metrics: MAE, MAPE, bias, cloudy-only error, and next-2-hours error.
- Confirm which regions we want to optimize first, because source selection may vary by geography.

### Phase 2: MVP integration

- Implement a Home Assistant custom integration scaffold.
- Add Open-Meteo as the first provider.
- Build the first deterministic PV model from irradiance, geometry, and inverter limits.
- Expose forecast sensors that match the most useful Forecast.Solar outputs.

### Phase 3: accuracy improvements

- Add multi-plane support in a single config entry.
- Add optional recent-actual calibration using Home Assistant history.
- Add horizon and obstruction support.
- Add forecast confidence and "cloud volatility" indicators.

### Phase 4: premium provider support

- Add Solcast and/or SolarAnywhere as optional providers.
- Add provider comparison mode so users can see which source performs best for their site.

### Phase 5: polish

- Documentation, tests, diagnostics, and example dashboards/automations.
- Migration guide for users currently relying on Forecast.Solar style sensors.

## Initial recommendation for the first build

Start with:

- Open-Meteo as the first provider
- A deterministic PV model we own
- Support for actual-production-based calibration from Home Assistant history
- A strong diagnostics story so we can learn why forecasts miss

This gives us an original implementation, avoids locking the project to a closed solar forecast API, and gives us the best chance of improving cloudy-day accuracy over time.

## Open questions before implementation

- Do we want the first release to be fully free/open-data only, or should premium providers be in scope from the start?
- Do we want to optimize first for UK installs, or aim for global defaults immediately?
- Should actual production history be optional but strongly recommended for best accuracy?
- Do we want to expose a single combined site forecast, or also keep per-plane entities visible?

## Sources reviewed

- Forecast.Solar Home Assistant docs: <https://www.home-assistant.io/integrations/forecast_solar/>
- Forecast.Solar library README: <https://github.com/home-assistant-libs/forecast_solar>
- Forecast.Solar account overview: <https://forecast.solar/>
- Home Assistant Forecast.Solar integration source:
  - <https://github.com/home-assistant/core/blob/dev/homeassistant/components/forecast_solar/coordinator.py>
  - <https://github.com/home-assistant/core/blob/dev/homeassistant/components/forecast_solar/config_flow.py>
  - <https://github.com/home-assistant/core/blob/dev/homeassistant/components/forecast_solar/strings.json>
- Open-Meteo docs: <https://open-meteo.com/en/docs>
- Solcast data/model pages:
  - <https://www.solcast.com/forecast-solar-irradiance-data>
  - <https://www.solcast.com/rooftop-pv-power-model>
  - <https://solcast.com/free-rooftop-solar-forecasting>
- SolarAnywhere forecast docs:
  - <https://www.solaranywhere.com/support/forecast-data/model/>
  - <https://www.solaranywhere.com/products/solaranywhere-forecast/forecast-services/>
- Tomorrow.io solar docs:
  - <https://support.tomorrow.io/hc/en-us/articles/38449657894804-Solar-Radiation-Premium-Layer>
