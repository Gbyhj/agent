"""
Browser Tool — Browser-Use 式浏览器控制

参考 Browser-Use:
  - 截图+DOM 双模态同步获取
  - 动态动作模型(根据页面注册可用操作)
  - 坐标点击(支持 Claude Sonnet/Gemini Pro)

用法:
    tool = BrowserTool()
    state = await tool.get_state()  # 获取当前页面截图+DOM
    await tool.click("button#submit")
    await tool.type("input#q", "search term")
"""
from __future__ import annotations

import asyncio
from typing import Any


class BrowserTool:
    """浏览器交互工具"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self._browser = None
        self._page = None

    async def start(self, url: str = "about:blank"):
        """启动浏览器"""
        try:
            from playwright.async_api import async_playwright
            self._pw = await async_playwright().start()
            self._browser = await self._pw.chromium.launch(headless=self.headless)
            self._page = await self._browser.new_page()
            await self._page.goto(url)
        except ImportError:
            raise ImportError("需要 pip install playwright && playwright install chromium")

    async def get_state(self) -> dict:
        """获取页面状态 — 截图 + 可交互元素"""
        if not self._page:
            return {"error": "浏览器未启动"}
        screenshot = await self._page.screenshot(type="png")
        title = await self._page.title()
        url = self._page.url

        # 提取可交互元素 (Browser-Use 风格)
        elements = await self._page.evaluate("""() => {
            const items = document.querySelectorAll('button, a, input, textarea, select, [onclick]');
            return Array.from(items).slice(0, 50).map((el, i) => ({
                index: i,
                tag: el.tagName.toLowerCase(),
                text: (el.textContent || '').trim().slice(0, 60),
                type: el.type || '',
                id: el.id || '',
                href: el.href || '',
            }));
        }""")

        return {
            "title": title,
            "url": url,
            "screenshot_base64": screenshot.hex()[:100] + "...",
            "interactive_elements": elements,
            "element_count": len(elements),
        }

    async def click(self, selector: str):
        if self._page:
            await self._page.click(selector)

    async def type(self, selector: str, text: str):
        if self._page:
            await self._page.fill(selector, text)

    async def close(self):
        if self._browser:
            await self._browser.close()
