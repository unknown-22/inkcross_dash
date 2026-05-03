from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.weather import TOKYO_TZ, describe_weather, parse_open_meteo


def test_describe_weather_maps_wmo_codes() -> None:
    assert describe_weather(0) == ("晴れ", "sun")
    assert describe_weather(3) == ("曇り", "cloud")
    assert describe_weather(61) == ("雨", "rain")
    assert describe_weather(71) == ("雪", "snow")
    assert describe_weather(95) == ("雷雨", "storm")


def test_parse_open_meteo_keeps_three_hour_forecasts_after_now() -> None:
    payload = {
        "daily": {
            "temperature_2m_max": [20.2],
            "temperature_2m_min": [10.4],
            "weather_code": [1],
        },
        "hourly": {
            "time": [
                "2026-05-03T00:00",
                "2026-05-03T03:00",
                "2026-05-03T04:00",
                "2026-05-03T06:00",
                "2026-05-03T09:00",
            ],
            "temperature_2m": [10, 11, 12, 13, 14],
            "weather_code": [0, 1, 2, 61, 71],
            "precipitation_probability": [0, 10, 20, 30, 40],
        },
    }
    now = datetime(2026, 5, 3, 3, 30, tzinfo=ZoneInfo("Asia/Tokyo"))

    forecast = parse_open_meteo(payload, now=now)

    assert forecast.daily.label == "晴れ時々曇り"
    assert [hour.time for hour in forecast.hourly] == [
        datetime(2026, 5, 3, 6, 0, tzinfo=TOKYO_TZ),
        datetime(2026, 5, 3, 9, 0, tzinfo=TOKYO_TZ),
    ]
    assert [hour.label for hour in forecast.hourly] == ["雨", "雪"]
