from __future__ import annotations

from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

import httpx

from app.models import DailyForecast, HourlyForecast, WeatherForecast

TOKYO_LATITUDE = 35.6812
TOKYO_LONGITUDE = 139.7671
TOKYO_TZ = ZoneInfo("Asia/Tokyo")
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


def describe_weather(code: int) -> tuple[str, str]:
    if code == 0:
        return "晴れ", "sun"
    if code in {1, 2}:
        return "晴れ時々曇り", "partly"
    if code == 3:
        return "曇り", "cloud"
    if code in {45, 48}:
        return "霧", "fog"
    if 51 <= code <= 67 or 80 <= code <= 82:
        return "雨", "rain"
    if 71 <= code <= 77 or 85 <= code <= 86:
        return "雪", "snow"
    if 95 <= code <= 99:
        return "雷雨", "storm"
    return "不明", "cloud"


class OpenMeteoClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch(self, now: datetime | None = None) -> WeatherForecast:
        params = {
            "latitude": TOKYO_LATITUDE,
            "longitude": TOKYO_LONGITUDE,
            "hourly": "temperature_2m,weather_code,precipitation_probability",
            "daily": "temperature_2m_max,temperature_2m_min,weather_code",
            "timezone": "Asia/Tokyo",
            "forecast_days": 1,
        }
        if self._client is None:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(OPEN_METEO_URL, params=params)
        else:
            response = await self._client.get(OPEN_METEO_URL, params=params)
        response.raise_for_status()
        return parse_open_meteo(response.json(), now=now)


def parse_open_meteo(payload: dict[str, Any], now: datetime | None = None) -> WeatherForecast:
    daily = payload["daily"]
    daily_code = int(daily["weather_code"][0])
    daily_label, daily_icon = describe_weather(daily_code)
    daily_forecast = DailyForecast(
        temperature_max=float(daily["temperature_2m_max"][0]),
        temperature_min=float(daily["temperature_2m_min"][0]),
        weather_code=daily_code,
        label=daily_label,
        icon=daily_icon,
    )

    current = now.astimezone(TOKYO_TZ) if now is not None else datetime.now(TOKYO_TZ)
    hourly = payload["hourly"]
    forecasts: list[HourlyForecast] = []
    for index, time_text in enumerate(hourly["time"]):
        forecast_time = datetime.fromisoformat(time_text).replace(tzinfo=TOKYO_TZ)
        if forecast_time.hour % 3 != 0 or forecast_time < current:
            continue
        code = int(hourly["weather_code"][index])
        label, icon = describe_weather(code)
        precipitation = hourly.get("precipitation_probability", [None] * len(hourly["time"]))[index]
        forecasts.append(
            HourlyForecast(
                time=forecast_time,
                temperature=float(hourly["temperature_2m"][index]),
                weather_code=code,
                precipitation_probability=None if precipitation is None else int(precipitation),
                label=label,
                icon=icon,
            )
        )
    return WeatherForecast(daily=daily_forecast, hourly=forecasts[:8])
