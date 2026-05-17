from __future__ import annotations

from datetime import date, datetime
from typing import Any, cast
from zoneinfo import ZoneInfo

import httpx

from app.models import DailyForecast, HourlyForecast, WeatherForecast

TOKYO_TZ = ZoneInfo("Asia/Tokyo")
JMA_FORECAST_URL = "https://www.jma.go.jp/bosai/forecast/data/forecast/130000.json"
JMA_WEATHER_AREA_CODE = "130010"
JMA_TEMPERATURE_AREA_CODE = "44132"


def describe_weather(code: int) -> tuple[str, str]:
    """気象庁の天気コードを短い表示名とアイコン名へ変換する。"""
    code_text = f"{code:03d}"
    hundreds = code_text[0]

    if hundreds == "1":
        if _code_mentions_rain(code_text):
            return "晴れ時々雨", "rain"
        if _code_mentions_snow(code_text):
            return "晴れ時々雪", "snow"
        if code_text == "100":
            return "晴れ", "sun"
        return "晴れ時々曇り", "partly"
    if hundreds == "2":
        if _code_mentions_rain(code_text):
            return "曇り時々雨", "rain"
        if _code_mentions_snow(code_text):
            return "曇り時々雪", "snow"
        return "曇り", "cloud"
    if hundreds == "3":
        if _code_mentions_snow(code_text):
            return "雨か雪", "snow"
        return "雨", "rain"
    if hundreds == "4":
        return "雪", "snow"
    return "不明", "cloud"


def _code_mentions_rain(code_text: str) -> bool:
    return code_text in {
        "102",
        "103",
        "106",
        "107",
        "108",
        "112",
        "113",
        "114",
        "118",
        "119",
        "120",
        "121",
        "122",
        "124",
        "125",
        "126",
        "127",
        "128",
        "130",
        "131",
        "132",
        "202",
        "203",
        "206",
        "207",
        "208",
        "212",
        "213",
        "214",
        "218",
        "219",
        "220",
        "221",
        "222",
        "224",
        "225",
        "226",
        "228",
        "229",
        "230",
        "231",
        "240",
    }


def _code_mentions_snow(code_text: str) -> bool:
    return code_text in {
        "104",
        "105",
        "106",
        "107",
        "115",
        "116",
        "117",
        "181",
        "204",
        "205",
        "206",
        "207",
        "215",
        "216",
        "217",
        "228",
        "229",
        "230",
        "231",
        "250",
        "260",
        "270",
        "281",
        "303",
        "304",
        "309",
        "322",
        "329",
        "340",
        "350",
        "361",
        "371",
    }


class JmaWeatherClient:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    async def fetch(self, now: datetime | None = None) -> WeatherForecast:
        if self._client is None:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.get(JMA_FORECAST_URL)
        else:
            response = await self._client.get(JMA_FORECAST_URL)
        response.raise_for_status()
        return parse_jma_forecast(cast(list[dict[str, Any]], response.json()), now=now)


def parse_jma_forecast(payload: list[dict[str, Any]], now: datetime | None = None) -> WeatherForecast:
    current = now.astimezone(TOKYO_TZ) if now is not None else datetime.now(TOKYO_TZ)
    short_term = payload[0]
    weekly = payload[1] if len(payload) > 1 else None

    weather_series = short_term["timeSeries"][0]
    precipitation_series = short_term["timeSeries"][1]
    temperature_series = short_term["timeSeries"][2]

    weather_area = _find_area(weather_series, JMA_WEATHER_AREA_CODE)
    precipitation_area = _find_area(precipitation_series, JMA_WEATHER_AREA_CODE)
    temperature_area = _find_area(temperature_series, JMA_TEMPERATURE_AREA_CODE)

    daily_index = _first_forecast_index(weather_series["timeDefines"], current.date())
    daily_code = int(weather_area["weatherCodes"][daily_index])
    daily_label, daily_icon = describe_weather(daily_code)

    temperature_min, temperature_max = _daily_temperatures(
        temperature_series=temperature_series,
        temperature_area=temperature_area,
        weekly=weekly,
        target_date=_parse_datetime(weather_series["timeDefines"][daily_index]).date(),
        current_date=current.date(),
    )
    daily_precipitation = _max_precipitation_for_date(
        precipitation_series["timeDefines"],
        precipitation_area["pops"],
        target_date=current.date(),
    )

    daily_forecast = DailyForecast(
        temperature_max=temperature_max,
        temperature_min=temperature_min,
        weather_code=daily_code,
        precipitation_probability=daily_precipitation,
        label=daily_label,
        icon=daily_icon,
    )

    hourly = _hourly_forecasts(
        weather_series=weather_series,
        weather_area=weather_area,
        precipitation_series=precipitation_series,
        precipitation_area=precipitation_area,
        temperature_series=temperature_series,
        temperature_area=temperature_area,
        daily_min=temperature_min,
        daily_max=temperature_max,
        current=current,
    )
    return WeatherForecast(daily=daily_forecast, hourly=hourly)


def _find_area(series: dict[str, Any], area_code: str) -> dict[str, Any]:
    for area in series["areas"]:
        if area["area"]["code"] == area_code:
            return cast(dict[str, Any], area)
    raise ValueError(f"JMA area code not found: {area_code}")


def _first_forecast_index(time_defines: list[str], current_date: date) -> int:
    for index, time_text in enumerate(time_defines):
        if _parse_datetime(time_text).date() >= current_date:
            return index
    return len(time_defines) - 1


def _daily_temperatures(
    *,
    temperature_series: dict[str, Any],
    temperature_area: dict[str, Any],
    weekly: dict[str, Any] | None,
    target_date: date,
    current_date: date,
) -> tuple[float, float]:
    short_term_temps = _temps_by_date(temperature_series["timeDefines"], temperature_area["temps"])
    if target_date in short_term_temps:
        return _min_max(short_term_temps[target_date])
    if current_date in short_term_temps:
        return _min_max(short_term_temps[current_date])
    for forecast_date in sorted(short_term_temps):
        if forecast_date >= current_date:
            return _min_max(short_term_temps[forecast_date])

    if weekly is not None:
        weekly_temperature_series = weekly["timeSeries"][1]
        weekly_temperature_area = _find_area(weekly_temperature_series, JMA_TEMPERATURE_AREA_CODE)
        for time_text, temp_min, temp_max in zip(
            weekly_temperature_series["timeDefines"],
            weekly_temperature_area["tempsMin"],
            weekly_temperature_area["tempsMax"],
            strict=False,
        ):
            forecast_date = _parse_datetime(time_text).date()
            if forecast_date >= current_date and temp_min != "" and temp_max != "":
                return float(temp_min), float(temp_max)

    available = [temp for temps in short_term_temps.values() for temp in temps]
    if available:
        return _min_max(available)
    raise ValueError("JMA temperature data is empty")


def _temps_by_date(time_defines: list[str], temps: list[str]) -> dict[date, list[float]]:
    grouped: dict[date, list[float]] = {}
    for time_text, temp in zip(time_defines, temps, strict=False):
        if temp == "":
            continue
        grouped.setdefault(_parse_datetime(time_text).date(), []).append(float(temp))
    return grouped


def _min_max(values: list[float]) -> tuple[float, float]:
    return min(values), max(values)


def _max_precipitation_for_date(
    time_defines: list[str],
    pops: list[str],
    *,
    target_date: date,
) -> int | None:
    values = [
        int(pop)
        for time_text, pop in zip(time_defines, pops, strict=False)
        if pop != "" and _parse_datetime(time_text).date() == target_date
    ]
    return max(values) if values else None


def _hourly_forecasts(
    *,
    weather_series: dict[str, Any],
    weather_area: dict[str, Any],
    precipitation_series: dict[str, Any],
    precipitation_area: dict[str, Any],
    temperature_series: dict[str, Any],
    temperature_area: dict[str, Any],
    daily_min: float,
    daily_max: float,
    current: datetime,
) -> list[HourlyForecast]:
    weather_slots = [
        (
            _parse_datetime(time_text),
            int(code),
        )
        for time_text, code in zip(
            weather_series["timeDefines"],
            weather_area["weatherCodes"],
            strict=False,
        )
    ]
    temperature_slots = [
        (_parse_datetime(time_text), float(temp))
        for time_text, temp in zip(
            temperature_series["timeDefines"],
            temperature_area["temps"],
            strict=False,
        )
        if temp != ""
    ]

    precipitation_slots = [
        (_parse_datetime(time_text), pop)
        for time_text, pop in zip(
            precipitation_series["timeDefines"],
            precipitation_area["pops"],
            strict=False,
        )
    ]
    start_index = 0
    for index, (forecast_time, _) in enumerate(precipitation_slots):
        if forecast_time <= current:
            start_index = index
        else:
            break

    forecasts: list[HourlyForecast] = []
    for forecast_time, pop in precipitation_slots[start_index:]:
        code = _nearest_weather_code(weather_slots, forecast_time)
        label, icon = describe_weather(code)
        forecasts.append(
            HourlyForecast(
                time=forecast_time,
                temperature=_nearest_temperature(
                    temperature_slots,
                    forecast_time,
                    daily_min=daily_min,
                    daily_max=daily_max,
                ),
                weather_code=code,
                precipitation_probability=None if pop == "" else int(pop),
                label=label,
                icon=icon,
            )
        )
    return forecasts[:4]


def _nearest_weather_code(weather_slots: list[tuple[datetime, int]], target: datetime) -> int:
    if not weather_slots:
        raise ValueError("JMA weather code data is empty")

    selected_code = weather_slots[0][1]
    for slot_time, code in weather_slots:
        if slot_time > target:
            break
        selected_code = code
    return selected_code


def _nearest_temperature(
    temperature_slots: list[tuple[datetime, float]],
    target: datetime,
    *,
    daily_min: float,
    daily_max: float,
) -> float:
    if temperature_slots:
        return min(temperature_slots, key=lambda item: abs(item[0] - target))[1]
    if 9 <= target.hour < 18:
        return daily_max
    return daily_min


def _parse_datetime(time_text: str) -> datetime:
    parsed = datetime.fromisoformat(time_text)
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=TOKYO_TZ)
    return parsed.astimezone(TOKYO_TZ)
