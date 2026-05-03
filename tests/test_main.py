from __future__ import annotations

import pytest
from fastapi import HTTPException

import main


class FakeService:
    async def build(self) -> object:
        return object()


class FakeFailingService:
    async def build(self) -> object:
        raise RuntimeError("failed")


class FakeRenderer:
    async def render_bmp(self, data: object) -> bytes:
        return b"BMfake"


@pytest.mark.asyncio
async def test_dashboard_bmp_response() -> None:
    main.app.state.dashboard_service = FakeService()
    main.app.state.dashboard_renderer = FakeRenderer()

    response = await main.dashboard_bmp()

    assert response.media_type == "image/bmp"
    assert response.headers["cache-control"] == "no-store"
    assert response.body == b"BMfake"


@pytest.mark.asyncio
async def test_dashboard_bmp_returns_500_on_generation_error() -> None:
    main.app.state.dashboard_service = FakeFailingService()
    main.app.state.dashboard_renderer = FakeRenderer()

    with pytest.raises(HTTPException) as exc_info:
        await main.dashboard_bmp()

    exception = exc_info.value
    assert exception.status_code == 500
    assert exception.detail == "dashboard generation failed"
