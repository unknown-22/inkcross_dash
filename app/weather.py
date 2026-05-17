from __future__ import annotations

from datetime import datetime
from typing import Any, cast
from zoneinfo import ZoneInfo

import httpx

from app.models import DailyForecast, HourlyForecast, WeatherForecast

TOKYO_TZ = ZoneInfo("Asia/Tokyo")
OPEN_METEO_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
TOKYO_LATITUDE = 35.6895
TOKYO_LONGITUDE = 139.6917

OPEN_METEO_PARAMS: dict[str, str | float | int] = {
    "latitude": TOKYO_LATITUDE,
    "longitude": TOKYO_LONGITUDE,
    "timezone": "Asia/Tokyo",
    "forecast_days": 2,
    "hourly": "temperature_2m,precipitation_probability,weather_code",
    "daily": "temperature_2m_max,temperature_2m_min,weather_code,precipitation_probability_max",
}


def describe_weather(code: int) -> tuple[str, str]:
    """Open-Meteo の WMO 天気コードを短い表示名とアイコン名へ変換する。"""
    if code == 0:
        return "晴れ", "sun"
    if code in {1, 2}:
        return "晴れ時々曇り", "partly"
    if code == 3:
        return "曇り", "cloud"
    if code in {45, 48}:
        return "霧", "fog"
    if code in {51, 53, 55, 56, 57, 61, 63, 65, 66, 67, 80, 81, 82}:
        return "雨", "rain"
    if code in {71, 73, 75, 77, 85, 86}:
        return "雪", "snow"
    if code in {95, 96, 99}:
        return "雷雨", "storm"
    return "曇り", "cloud"


class OpenMeteoWeatherClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch(self, now: datetime | None = None) -> WeatherForecast:
        if self._client is None:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(OPEN_METEO_FORECAST_URL, params=OPEN_METEO_PARAMS)
        else:
            response = await self._client.get(OPEN_METEO_FORECAST_URL, params=OPEN_METEO_PARAMS)
        response.raise_for_status()
        return parse_open_meteo_forecast(cast(dict[str, Any], response.json()), now=now)


def parse_open_meteo_forecast(payload: dict[str, Any], now: datetime | None = None) -> WeatherForecast:
    current = now.astimezone(TOKYO_TZ) if now is not None else datetime.now(TOKYO_TZ)
    daily = _required_mapping(payload, "daily")
    hourly = _required_mapping(payload, "hourly")

    daily_index = _daily_index(_required_list(daily, "time"), current)
    daily_code = int(_required_list(daily, "weather_code")[daily_index])
    daily_label, daily_icon = describe_weather(daily_code)

    daily_forecast = DailyForecast(
        temperature_max=float(_required_list(daily, "temperature_2m_max")[daily_index]),
        temperature_min=float(_required_list(daily, "temperature_2m_min")[daily_index]),
        weather_code=daily_code,
        precipitation_probability=_optional_int(
            _required_list(daily, "precipitation_probability_max")[daily_index]
        ),
        label=daily_label,
        icon=daily_icon,
    )

    return WeatherForecast(
        daily=daily_forecast,
        hourly=_hourly_forecasts(hourly=hourly, current=current),
    )


def _required_mapping(payload: dict[str, Any], key: str) -> dict[str, Any]:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"Open-Meteo response is missing object: {key}")
    return cast(dict[str, Any], value)


def _required_list(payload: dict[str, Any], key: str) -> list[Any]:
    value = payload.get(key)
    if not isinstance(value, list):
        raise ValueError(f"Open-Meteo response is missing list: {key}")
    if not value:
        raise ValueError(f"Open-Meteo response list is empty: {key}")
    return cast(list[Any], value)


def _daily_index(times: list[Any], current: datetime) -> int:
    current_date = current.date()
    fallback_index = len(times) - 1
    for index, time_text in enumerate(times):
        forecast_date = _parse_datetime(str(time_text)).date()
        if forecast_date == current_date:
            return index
        if forecast_date > current_date:
            return index
    return fallback_index


def _hourly_forecasts(*, hourly: dict[str, Any], current: datetime) -> list[HourlyForecast]:
    times = _required_list(hourly, "time")
    temperatures = _required_list(hourly, "temperature_2m")
    precipitation_probabilities = _required_list(hourly, "precipitation_probability")
    weather_codes = _required_list(hourly, "weather_code")
    first_slot = _current_three_hour_slot(current)

    if not (len(times) == len(temperatures) == len(precipitation_probabilities) == len(weather_codes)):
        raise ValueError("Open-Meteo hourly arrays have inconsistent lengths")

    forecasts: list[HourlyForecast] = []
    for time_text, temperature, precipitation_probability, weather_code in zip(
        times,
        temperatures,
        precipitation_probabilities,
        weather_codes,
        strict=True,
    ):
        forecast_time = _parse_datetime(str(time_text))
        if forecast_time < first_slot:
            continue
        if forecast_time.hour % 3 != 0:
            continue
        code = int(weather_code)
        label, icon = describe_weather(code)
        forecasts.append(
            HourlyForecast(
                time=forecast_time,
                temperature=float(temperature),
                weather_code=code,
                precipitation_probability=_optional_int(precipitation_probability),
                label=label,
                icon=icon,
            )
        )
        if len(forecasts) == 4:
            return forecasts

    if forecasts:
        return forecasts
    raise ValueError("Open-Meteo hourly forecast has no upcoming slots")


def _current_three_hour_slot(current: datetime) -> datetime:
    return current.replace(hour=current.hour // 3 * 3, minute=0, second=0, microsecond=0)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _parse_datetime(time_text: str) -> datetime:
    parsed = datetime.fromisoformat(time_text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=TOKYO_TZ)
    return parsed.astimezone(TOKYO_TZ)
