#!/usr/bin/env python3
"""
Synthetic User Testing — Playwright 自动化模拟真实用户

运行:
    cd agent && source .venv/Scripts/activate
    python synthetic_user_test.py

模拟 10 个真实用户旅程:
    - 免费体验模式: 场景切换 → 输入查询 → 等待思考 → 验证回答
    - API 模式: 输入 Key → 切换模式 → 真实调用
    - 边界情况: 空输入、超长输入、特殊字符
    - 多轮对话: 追问、上下文延续
"""
from __future__ import annotations

import os, sys, json, time
from datetime import datetime
from dataclasses import dataclass, field

from playwright.sync_api import sync_playwright, Page, expect


BASE_URL = "https://agent.保康.top/agent"
# 本地测试用: BASE_URL = "http://localhost:5000"


@dataclass
class UserJourney:
    """用户旅程"""
    name: str
    steps: list[dict]
    expected: list[str]  # 期望页面出现的文本


@dataclass
class JourneyResult:
    name: str
    passed: bool
    duration_ms: float
    screenshots: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)


class SyntheticUser:
    """合成用户"""

    def __init__(self, headless: bool = True):
        self.headless = headless
        self.results: list[JourneyResult] = []
        self.screenshot_dir = "synthetic_test_screenshots"
        os.makedirs(self.screenshot_dir, exist_ok=True)
        self._screenshot_count = 0

    def _screenshot(self, page: Page, name: str) -> str:
        self._screenshot_count += 1
        path = os.path.join(self.screenshot_dir, f"{self._screenshot_count:02d}_{name}.png")
        page.screenshot(path=path, full_page=True)
        return path

    # ═══════════════════════════════════════════
    #  用户旅程定义
    # ═══════════════════════════════════════════
    @property
    def journeys(self) -> list[UserJourney]:
        return [
            # 1. 新用户打开页面
            UserJourney("首次访问", [
                {"action": "goto", "url": BASE_URL},
                {"action": "wait", "selector": "h1", "timeout": 5000},
            ], ["Agent", "免费体验"]),

            # 2. 免费体验 — 代码审查场景
            UserJourney("免费体验-代码审查", [
                {"action": "goto", "url": BASE_URL},
                {"action": "click", "selector": ".scene-btn:nth-child(2)"},  # 审查
                {"action": "fill", "selector": "#msgInput", "value": "审查代码安全性"},
                {"action": "click", "selector": "#sendBtn"},
                {"action": "wait", "selector": ".msg.agent", "timeout": 15000},
            ], ["思考", "工具"]),

            # 3. 免费体验 — 架构分析场景
            UserJourney("免费体验-架构分析", [
                {"action": "goto", "url": BASE_URL},
                {"action": "click", "selector": ".scene-btn:nth-child(3)"},  # 分析
                {"action": "fill", "selector": "#msgInput", "value": "分析项目架构"},
                {"action": "click", "selector": "#sendBtn"},
                {"action": "wait", "selector": ".msg.agent", "timeout": 15000},
            ], ["架构", "模块"]),

            # 4. 免费体验 — 搜索查询
            UserJourney("免费体验-搜索", [
                {"action": "goto", "url": BASE_URL},
                {"action": "fill", "selector": "#msgInput", "value": "搜索最新的 AI Agent 框架"},
                {"action": "click", "selector": "#sendBtn"},
                {"action": "wait", "selector": ".msg.agent", "timeout": 15000},
            ], ["搜索", "框架"]),

            # 5. 免费体验 — 数据库设计
            UserJourney("免费体验-数据库设计", [
                {"action": "goto", "url": BASE_URL},
                {"action": "fill", "selector": "#msgInput", "value": "设计用户表"},
                {"action": "click", "selector": "#sendBtn"},
                {"action": "wait", "selector": ".msg.agent", "timeout": 15000},
            ], ["CREATE", "TABLE"]),

            # 6. 点击快捷标签
            UserJourney("快捷标签", [
                {"action": "goto", "url": BASE_URL},
                {"action": "click", "selector": ".hint"},
                {"action": "click", "selector": "#sendBtn"},
                {"action": "wait", "selector": ".msg.agent", "timeout": 15000},
            ], []),

            # 7. 多轮对话
            UserJourney("多轮对话", [
                {"action": "goto", "url": BASE_URL},
                {"action": "fill", "selector": "#msgInput", "value": "你有哪些功能"},
                {"action": "click", "selector": "#sendBtn"},
                {"action": "wait", "selector": ".msg.agent", "timeout": 15000},
                {"action": "fill", "selector": "#msgInput", "value": "继续说"},
                {"action": "click", "selector": "#sendBtn"},
                {"action": "wait", "selector": ".msg.agent", "timeout": 15000},
            ], ["功能"]),

            # 8. 切换到 API 模式
            UserJourney("API模式切换", [
                {"action": "goto", "url": BASE_URL},
                {"action": "click_text", "text": "API Key"},
                {"action": "wait", "selector": "#apikey", "timeout": 3000},
                {"action": "fill", "selector": "#apikey", "value": "sk-test-demo-key"},
                {"action": "fill", "selector": "#msgInput", "value": "test"},
                {"action": "click", "selector": "#sendBtn"},
                {"action": "wait", "selector": ".msg.error, .msg.agent", "timeout": 10000},
            ], []),

            # 9. 空输入保护
            UserJourney("空输入保护", [
                {"action": "goto", "url": BASE_URL},
                {"action": "click", "selector": "#sendBtn"},
                {"action": "wait", "text": "", "timeout": 2000},
            ], []),

            # 10. 场景切换快捷操作
            UserJourney("场景切换流畅度", [
                {"action": "goto", "url": BASE_URL},
                {"action": "click", "selector": ".scene-btn:nth-child(1)"},
                {"action": "click", "selector": ".scene-btn:nth-child(2)"},
                {"action": "click", "selector": ".scene-btn:nth-child(3)"},
                {"action": "click", "selector": ".scene-btn:nth-child(4)"},
                {"action": "click", "selector": ".scene-btn:nth-child(1)"},
            ], []),
        ]

    # ═══════════════════════════════════════════
    #  执行
    # ═══════════════════════════════════════════
    def run_all(self):
        print("=" * 60)
        print(f"  🎭 Synthetic User Testing")
        print(f"  {BASE_URL}")
        print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M')} · {len(self.journeys)} 个旅程")
        print("=" * 60)
        print()

        with sync_playwright() as p:
            # 使用系统已安装的 Chrome/Edge，不依赖 Playwright 绑定的 Chromium
            try:
                browser = p.chromium.launch(headless=self.headless)
            except Exception:
                # Fallback: 使用系统 Edge
                browser = p.chromium.launch(
                    headless=self.headless,
                    channel="msedge",  # Windows 自带 Edge
                )
            context = browser.new_context(
                viewport={"width": 1280, "height": 800},
                locale="zh-CN",
            )

            for journey in self.journeys:
                result = self._run_journey(journey, context)
                self.results.append(result)

                icon = "✅" if result.passed else "❌"
                print(f"  {icon} {journey.name:20s} → {result.duration_ms:.0f}ms"
                      f"{' · ⚠️ ' + ', '.join(result.issues) if result.issues else ''}")

            context.close()
            browser.close()

        print()
        self._print_report()

    def _run_journey(self, journey: UserJourney, context) -> JourneyResult:
        page = context.new_page()
        t0 = time.time()
        issues = []
        screenshots = []

        try:
            for step in journey.steps:
                action = step["action"]

                if action == "goto":
                    try:
                        page.goto(step["url"], wait_until="domcontentloaded", timeout=20000)
                    except Exception:
                        page.goto(step["url"], timeout=30000)  # retry without wait
                    page.wait_for_timeout(1000)
                    screenshots.append(self._screenshot(page, f"{journey.name}_loaded"))

                elif action == "wait":
                    selector = step.get("selector", "")
                    text = step.get("text", "")
                    timeout = step.get("timeout", 5000)
                    try:
                        if selector:
                            page.wait_for_selector(selector, timeout=timeout)
                        elif text:
                            page.wait_for_selector(f"text={text}", timeout=timeout)
                        screenshots.append(self._screenshot(page, f"{journey.name}_{selector or text}"))
                    except Exception:
                        # 宽松等待
                        page.wait_for_timeout(timeout)

                elif action == "click":
                    selector = step["selector"]
                    try:
                        page.click(selector, timeout=5000)
                    except Exception:
                        issues.append(f"无法点击: {selector}")

                elif action == "click_text":
                    try:
                        page.get_by_text(step["text"], exact=False).first.click(timeout=5000)
                    except Exception:
                        issues.append(f"找不到文本: {step['text']}")

                elif action == "fill":
                    try:
                        page.fill(step["selector"], step["value"], timeout=5000)
                    except Exception:
                        issues.append(f"无法填写: {step['selector']}")

                elif action == "press":
                    try:
                        page.press(step["selector"], step["key"])
                    except Exception:
                        pass

            # 验证期望内容
            for expected in journey.expected:
                try:
                    expect(page.get_by_text(expected, exact=False).first).to_be_visible(timeout=5000)
                except Exception:
                    issues.append(f"未找到期望内容: {expected}")

            screenshots.append(self._screenshot(page, f"{journey.name}_final"))
            page.close()
            elapsed = (time.time() - t0) * 1000
            return JourneyResult(journey.name, len(issues) == 0, elapsed, screenshots, issues)

        except Exception as e:
            elapsed = (time.time() - t0) * 1000
            issues.append(f"异常: {str(e)[:80]}")
            try:
                screenshots.append(self._screenshot(page, "error"))
                page.close()
            except Exception:
                pass
            return JourneyResult(journey.name, False, elapsed, screenshots, issues)

    def _print_report(self):
        total = len(self.results)
        passed = sum(1 for r in self.results if r.passed)
        avg_duration = sum(r.duration_ms for r in self.results) / total if total else 0

        print("=" * 60)
        print("  📊 Synthetic User Report")
        print("=" * 60)
        print(f"  总旅程: {total}  |  通过: {passed}  |  失败: {total - passed}")
        print(f"  通过率: {passed/total*100:.0f}%  |  平均: {avg_duration:.0f}ms")
        print(f"  截图: {self.screenshot_dir}/ ({self._screenshot_count} 张)")
        print()

        failures = [r for r in self.results if not r.passed]
        if failures:
            print("  ❌ 失败详情:")
            for r in failures:
                print(f"  - {r.name}: {', '.join(r.issues)}")
        else:
            print("  🎉 全部用户旅程通过！")

        print(f"\n  可用性评分: {'A' if passed/total >= 0.9 else 'B' if passed/total >= 0.7 else 'C'}")
        print("=" * 60)


if __name__ == "__main__":
    su = SyntheticUser(headless=True)
    su.run_all()
