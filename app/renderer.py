from __future__ import annotations

import io
from pathlib import Path
from types import TracebackType

from jinja2 import Environment, FileSystemLoader, select_autoescape
from PIL import Image
from playwright.async_api import Browser, Playwright, async_playwright

from app.models import DashboardData
from app.quantize import HEIGHT, WIDTH, to_4level_bmp


class DashboardRenderer:
    def __init__(self, template_dir: Path) -> None:
        self._jinja = Environment(
            loader=FileSystemLoader(template_dir),
            autoescape=select_autoescape(("html", "xml")),
        )
        self._playwright: Playwright | None = None
        self._browser: Browser | None = None

    async def __aenter__(self) -> DashboardRenderer:
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        if self._browser is not None:
            await self._browser.close()
            self._browser = None
        if self._playwright is not None:
            await self._playwright.stop()
            self._playwright = None

    def render_html(self, data: DashboardData) -> str:
        template = self._jinja.get_template("dashboard.html")
        return template.render(data=data)

    async def render_bmp(self, data: DashboardData) -> bytes:
        if self._browser is None:
            raise RuntimeError("DashboardRenderer is not started")

        page = await self._browser.new_page(
            viewport={"width": WIDTH, "height": HEIGHT},
            device_scale_factor=1,
        )
        try:
            await page.set_content(self.render_html(data), wait_until="networkidle")
            screenshot = await page.screenshot(type="png", full_page=False)
        finally:
            await page.close()

        with Image.open(io.BytesIO(screenshot)) as image:
            return to_4level_bmp(image)
