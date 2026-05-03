from __future__ import annotations

from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from app.models import DashboardData, DailyForecast, HourlyForecast, WeatherForecast
from app.renderer import DashboardRenderer


@pytest.mark.asyncio
async def test_renderer_outputs_four_bit_bmp() -> None:
    zone = ZoneInfo("Asia/Tokyo")
    data = DashboardData(
        generated_at=datetime(2026, 5, 3, 12, 0, tzinfo=zone),
        weekday="日",
        weather=WeatherForecast(
            daily=DailyForecast(
                temperature_max=22,
                temperature_min=14,
                weather_code=0,
                label="晴れ",
                icon="sun",
            ),
            hourly=[
                HourlyForecast(
                    time=datetime(2026, 5, 3, hour, 0, tzinfo=zone),
                    temperature=20 + hour / 10,
                    weather_code=0,
                    precipitation_probability=0,
                    label="晴れ",
                    icon="sun",
                )
                for hour in (12, 15, 18, 21)
            ],
        ),
        events=[],
        todos=[],
    )

    async with DashboardRenderer(Path("templates")) as renderer:
        bmp = await renderer.render_bmp(data)

    assert bmp[:2] == b"BM"
    assert len(bmp) == 192118
    assert int.from_bytes(bmp[18:22], "little", signed=True) == 480
    assert abs(int.from_bytes(bmp[22:26], "little", signed=True)) == 800
    assert int.from_bytes(bmp[28:30], "little") == 4
