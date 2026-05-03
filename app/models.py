from __future__ import annotations

from datetime import date, datetime

from pydantic import BaseModel, Field


class CalendarEvent(BaseModel):
    title: str
    start: datetime
    end: datetime | None = None
    location: str | None = None


class TodoItem(BaseModel):
    title: str
    done: bool
    due: date | None = None

    def is_overdue_or_due_today(self, today: date) -> bool:
        return self.due is not None and self.due <= today


class HourlyForecast(BaseModel):
    time: datetime
    temperature: float
    weather_code: int
    precipitation_probability: int | None = None
    label: str
    icon: str


class DailyForecast(BaseModel):
    temperature_max: float
    temperature_min: float
    weather_code: int
    label: str
    icon: str


class WeatherForecast(BaseModel):
    daily: DailyForecast
    hourly: list[HourlyForecast] = Field(default_factory=list)


class DashboardData(BaseModel):
    generated_at: datetime
    weekday: str
    weather: WeatherForecast
    events: list[CalendarEvent]
    todos: list[TodoItem]
