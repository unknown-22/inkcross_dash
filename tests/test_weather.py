from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from app.weather import TOKYO_TZ, describe_weather, parse_jma_forecast


def test_describe_weather_maps_jma_codes() -> None:
    assert describe_weather(100) == ("晴れ", "sun")
    assert describe_weather(111) == ("晴れ時々曇り", "partly")
    assert describe_weather(211) == ("曇り", "cloud")
    assert describe_weather(300) == ("雨", "rain")
    assert describe_weather(400) == ("雪", "snow")


def test_parse_jma_forecast_keeps_upcoming_precipitation_slots() -> None:
    payload = [
        {
            "timeSeries": [
                {
                    "timeDefines": [
                        "2026-05-04T17:00:00+09:00",
                        "2026-05-05T00:00:00+09:00",
                        "2026-05-06T00:00:00+09:00",
                    ],
                    "areas": [
                        {
                            "area": {"name": "東京地方", "code": "130010"},
                            "weatherCodes": ["211", "100", "111"],
                            "weathers": ["くもり　夜遅く　晴れ", "晴れ", "晴れ　後　くもり"],
                        }
                    ],
                },
                {
                    "timeDefines": [
                        "2026-05-04T18:00:00+09:00",
                        "2026-05-05T00:00:00+09:00",
                        "2026-05-05T06:00:00+09:00",
                        "2026-05-05T12:00:00+09:00",
                        "2026-05-05T18:00:00+09:00",
                    ],
                    "areas": [
                        {
                            "area": {"name": "東京地方", "code": "130010"},
                            "pops": ["10", "0", "0", "20", "30"],
                        }
                    ],
                },
                {
                    "timeDefines": [
                        "2026-05-05T00:00:00+09:00",
                        "2026-05-05T09:00:00+09:00",
                    ],
                    "areas": [
                        {
                            "area": {"name": "東京", "code": "44132"},
                            "temps": ["12", "23"],
                        }
                    ],
                },
            ]
        },
        {
            "timeSeries": [
                {
                    "timeDefines": ["2026-05-05T00:00:00+09:00"],
                    "areas": [{"area": {"name": "東京地方", "code": "130010"}, "weatherCodes": ["100"]}],
                },
                {
                    "timeDefines": [
                        "2026-05-05T00:00:00+09:00",
                        "2026-05-06T00:00:00+09:00",
                    ],
                    "areas": [
                        {
                            "area": {"name": "東京", "code": "44132"},
                            "tempsMin": ["", "14"],
                            "tempsMax": ["", "23"],
                        }
                    ],
                },
            ]
        },
    ]
    now = datetime(2026, 5, 4, 17, 30, tzinfo=ZoneInfo("Asia/Tokyo"))

    forecast = parse_jma_forecast(payload, now=now)

    assert forecast.daily.label == "曇り"
    assert forecast.daily.temperature_min == 12
    assert forecast.daily.temperature_max == 23
    assert forecast.daily.precipitation_probability == 10
    assert [hour.time for hour in forecast.hourly] == [
        datetime(2026, 5, 4, 18, 0, tzinfo=TOKYO_TZ),
        datetime(2026, 5, 5, 0, 0, tzinfo=TOKYO_TZ),
        datetime(2026, 5, 5, 6, 0, tzinfo=TOKYO_TZ),
        datetime(2026, 5, 5, 12, 0, tzinfo=TOKYO_TZ),
    ]
    assert [hour.label for hour in forecast.hourly] == ["曇り", "晴れ", "晴れ", "晴れ"]
    assert [hour.precipitation_probability for hour in forecast.hourly] == [10, 0, 0, 20]


def test_parse_jma_forecast_starts_hourly_at_latest_precipitation_slot() -> None:
    payload = [
        {
            "timeSeries": [
                {
                    "timeDefines": [
                        "2026-05-17T05:00:00+09:00",
                        "2026-05-17T17:00:00+09:00",
                        "2026-05-18T00:00:00+09:00",
                    ],
                    "areas": [
                        {
                            "area": {"name": "東京地方", "code": "130010"},
                            "weatherCodes": ["211", "100", "111"],
                        }
                    ],
                },
                {
                    "timeDefines": [
                        "2026-05-17T12:00:00+09:00",
                        "2026-05-17T18:00:00+09:00",
                        "2026-05-18T00:00:00+09:00",
                        "2026-05-18T06:00:00+09:00",
                        "2026-05-18T12:00:00+09:00",
                    ],
                    "areas": [
                        {
                            "area": {"name": "東京地方", "code": "130010"},
                            "pops": ["10", "20", "30", "40", "50"],
                        }
                    ],
                },
                {
                    "timeDefines": [
                        "2026-05-17T09:00:00+09:00",
                        "2026-05-17T15:00:00+09:00",
                    ],
                    "areas": [
                        {
                            "area": {"name": "東京", "code": "44132"},
                            "temps": ["20", "24"],
                        }
                    ],
                },
            ]
        }
    ]
    now = datetime(2026, 5, 17, 13, 0, tzinfo=ZoneInfo("Asia/Tokyo"))

    forecast = parse_jma_forecast(payload, now=now)

    assert [hour.time for hour in forecast.hourly] == [
        datetime(2026, 5, 17, 12, 0, tzinfo=TOKYO_TZ),
        datetime(2026, 5, 17, 18, 0, tzinfo=TOKYO_TZ),
        datetime(2026, 5, 18, 0, 0, tzinfo=TOKYO_TZ),
        datetime(2026, 5, 18, 6, 0, tzinfo=TOKYO_TZ),
    ]
    assert [hour.precipitation_probability for hour in forecast.hourly] == [10, 20, 30, 40]


def test_parse_jma_forecast_uses_weekly_temperature_when_short_term_is_empty() -> None:
    payload = [
        {
            "timeSeries": [
                {
                    "timeDefines": ["2026-05-04T17:00:00+09:00"],
                    "areas": [
                        {
                            "area": {"name": "東京地方", "code": "130010"},
                            "weatherCodes": ["100"],
                        }
                    ],
                },
                {
                    "timeDefines": ["2026-05-04T18:00:00+09:00"],
                    "areas": [{"area": {"name": "東京地方", "code": "130010"}, "pops": [""]}],
                },
                {
                    "timeDefines": ["2026-05-05T00:00:00+09:00"],
                    "areas": [{"area": {"name": "東京", "code": "44132"}, "temps": [""]}],
                },
            ]
        },
        {
            "timeSeries": [
                {
                    "timeDefines": ["2026-05-05T00:00:00+09:00"],
                    "areas": [{"area": {"name": "東京地方", "code": "130010"}, "weatherCodes": ["100"]}],
                },
                {
                    "timeDefines": [
                        "2026-05-05T00:00:00+09:00",
                        "2026-05-06T00:00:00+09:00",
                    ],
                    "areas": [
                        {
                            "area": {"name": "東京", "code": "44132"},
                            "tempsMin": ["", "14"],
                            "tempsMax": ["", "26"],
                        }
                    ],
                },
            ]
        },
    ]
    now = datetime(2026, 5, 4, 17, 30, tzinfo=ZoneInfo("Asia/Tokyo"))

    forecast = parse_jma_forecast(payload, now=now)

    assert forecast.daily.temperature_min == 14
    assert forecast.daily.temperature_max == 26
    assert forecast.hourly[0].temperature == 14
