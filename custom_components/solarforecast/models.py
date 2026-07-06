"""Data models for the Solar Forecast integration."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime


@dataclass(frozen=True, slots=True)
class SolarForecastPoint:
    """A single forecast point for a site."""

    start: datetime
    power_w: float
    energy_kwh: float
    irradiance_w_m2: float
    cloud_cover_percent: float
    temperature_c: float


@dataclass(frozen=True, slots=True)
class SolarForecastData:
    """Forecast output for the configured solar site."""

    provider: str
    weather_model: str | None
    timezone: str
    generated_at: datetime
    points: tuple[SolarForecastPoint, ...]

    def point_for_time(self, at: datetime) -> SolarForecastPoint | None:
        """Return the latest point up to the requested time."""
        latest: SolarForecastPoint | None = None
        for point in self.points:
            if point.start > at:
                break
            latest = point
        return latest

    def next_point_after(self, at: datetime) -> SolarForecastPoint | None:
        """Return the first point after the requested time."""
        for point in self.points:
            if point.start > at:
                return point
        return None

    def energy_for_date(self, target_date: date) -> float:
        """Return the total forecast energy for a local date."""
        return round(
            sum(point.energy_kwh for point in self.points if point.start.date() == target_date),
            3,
        )

    def energy_remaining_today(self, now: datetime) -> float:
        """Return remaining forecast energy for the current day."""
        current_hour = now.replace(minute=0, second=0, microsecond=0)
        return round(
            sum(
                point.energy_kwh
                for point in self.points
                if point.start.date() == now.date() and point.start >= current_hour
            ),
            3,
        )
