from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import cast

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response

from app.dashboard import DashboardService
from app.renderer import DashboardRenderer

ROOT = Path(__file__).parent


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    service = DashboardService.from_project_root(ROOT)
    async with DashboardRenderer(ROOT / "templates") as renderer:
        app.state.dashboard_service = service
        app.state.dashboard_renderer = renderer
        yield


app = FastAPI(title="Inkcross Dashboard", lifespan=lifespan)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/dashboard.bmp")
async def dashboard_bmp() -> Response:
    service = cast(DashboardService, app.state.dashboard_service)
    renderer = cast(DashboardRenderer, app.state.dashboard_renderer)
    try:
        data = await service.build()
        bmp = await renderer.render_bmp(data)
    except Exception as exc:
        raise HTTPException(status_code=500, detail="dashboard generation failed") from exc
    return Response(
        content=bmp,
        media_type="image/bmp",
        headers={"Cache-Control": "no-store"},
    )


def main() -> None:
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()
