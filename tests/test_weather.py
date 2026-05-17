from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

import pytest

from app.weather import TOKYO_TZ, describe_weather, parse_open_meteo_forecast


def test_describe_weather_maps_wmo_codes() -> None:
    assert describe_weather(0) == ("晴れ", "sun")
    assert describe_weather(1) == ("晴れ時々曇り", "partly")
    assert describe_weather(3) == ("曇り", "cloud")
    assert describe_weather(45) == ("霧", "fog")
    assert describe_weather(61) == ("雨", "rain")
    assert describe_weather(71) == ("雪", "snow")
    assert describe_weather(95) == ("雷雨", "storm")
    assert describe_weather(999) == ("曇り", "cloud")


def test_parse_open_meteo_forecast_uses_daily_and_upcoming_three_hourly_values() -> None:
    payload = {
        "daily": {
            "time": ["2026-05-17", "2026-05-18"],
            "temperature_2m_max": [27.3, 26.0],
            "temperature_2m_min": [13.0, 14.4],
            "weather_code": [0, 3],
            "precipitation_probability_max": [10, 40],
        },
        "hourly": {
            "time": [
                "2026-05-17T11:00",
                "2026-05-17T12:00",
                "2026-05-17T13:00",
                "2026-05-17T14:00",
                "2026-05-17T15:00",
                "2026-05-17T16:00",
                "2026-05-17T17:00",
                "2026-05-17T18:00",
                "2026-05-17T19:00",
                "2026-05-17T20:00",
                "2026-05-17T21:00",
                "2026-05-17T22:00",
                "2026-05-17T23:00",
                "2026-05-18T00:00",
            ],
            "temperature_2m": [25.5, 26.5, 27.1, 27.3, 26.9, 26.5, 26.1, 25.8, 25.0, 24.5, 24.0, 23.5, 23.3, 23.2],
            "precipitation_probability": [0, 0, 10, 20, 30, 40, 45, 50, 60, 65, 70, 75, 78, 80],
            "weather_code": [0, 0, 1, 3, 61, 95, 0, 1, 3, 61, 95, 3, 1, 0],
        },
    }
    now = datetime(2026, 5, 17, 12, 30, tzinfo=ZoneInfo("Asia/Tokyo"))

    forecast = parse_open_meteo_forecast(payload, now=now)

    assert forecast.daily.temperature_min == 13.0
    assert forecast.daily.temperature_max == 27.3
    assert forecast.daily.precipitation_probability == 10
    assert forecast.daily.label == "晴れ"
    assert [hour.time for hour in forecast.hourly] == [
        datetime(2026, 5, 17, 15, 0, tzinfo=TOKYO_TZ),
        datetime(2026, 5, 17, 18, 0, tzinfo=TOKYO_TZ),
        datetime(2026, 5, 17, 21, 0, tzinfo=TOKYO_TZ),
        datetime(2026, 5, 18, 0, 0, tzinfo=TOKYO_TZ),
    ]
    assert [hour.temperature for hour in forecast.hourly] == [26.9, 25.8, 24.0, 23.2]
    assert [hour.precipitation_probability for hour in forecast.hourly] == [30, 50, 70, 80]
    assert [hour.icon for hour in forecast.hourly] == ["rain", "partly", "storm", "sun"]


def test_parse_open_meteo_forecast_uses_next_daily_when_today_is_missing() -> None:
    payload = {
        "daily": {
            "time": ["2026-05-18"],
            "temperature_2m_max": [26.0],
            "temperature_2m_min": [14.4],
            "weather_code": [3],
            "precipitation_probability_max": [40],
        },
        "hourly": {
            "time": ["2026-05-17T15:00"],
            "temperature_2m": [27.1],
            "precipitation_probability": [10],
            "weather_code": [1],
        },
    }
    now = datetime(2026, 5, 17, 12, 30, tzinfo=ZoneInfo("Asia/Tokyo"))

    forecast = parse_open_meteo_forecast(payload, now=now)

    assert forecast.daily.temperature_min == 14.4
    assert forecast.daily.temperature_max == 26.0
    assert forecast.daily.label == "曇り"


def test_parse_open_meteo_forecast_rejects_inconsistent_hourly_arrays() -> None:
    payload = {
        "daily": {
            "time": ["2026-05-17"],
            "temperature_2m_max": [27.3],
            "temperature_2m_min": [13.0],
            "weather_code": [0],
            "precipitation_probability_max": [10],
        },
        "hourly": {
            "time": ["2026-05-17T13:00", "2026-05-17T14:00"],
            "temperature_2m": [27.1],
            "precipitation_probability": [10, 20],
            "weather_code": [1, 3],
        },
    }
    now = datetime(2026, 5, 17, 12, 30, tzinfo=ZoneInfo("Asia/Tokyo"))

    with pytest.raises(ValueError, match="inconsistent lengths"):
        parse_open_meteo_forecast(payload, now=now)
