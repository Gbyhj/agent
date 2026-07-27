"""
LLM Provider Layer — 多模型统一接入

设计融合:
- LiteLLM: 100+ LLM 统一 OpenAI 格式 (completion())
- Cline: @cline/llms Provider 抽象层
- Grok Build: xai-grok-sampler 三层 API

一个接口调所有模型:
    from .llm import LLM
    llm = LLM(provider="deepseek", model="deepseek-v4-flash")
    resp = llm.chat(messages, tools)
"""
from __future__ import annotations

import os
import json
from dataclasses import dataclass
from typing import Any


@dataclass
class LLMResponse:
    content: str | None = None
    tool_calls: list[dict] | None = None
    final_answer: str | None = None
    usage: dict | None = None


class LLM:
    """
    多模型统一调用层

    支持 Provider:
    - openai:     OpenAI API (gpt-4o, gpt-5.5, ...)
    - deepseek:   DeepSeek API (v4-flash, v4-pro, v3.1, ...)
    - anthropic:  Anthropic API (claude-sonnet-4, opus-4.7, ...)
    - openrouter: OpenRouter (200+ models)
    - ollama:     本地模型 (llama3, qwen3, ...)
    - custom:     任意 OpenAI 兼容 API
    """

    PROVIDERS = {
        "deepseek":   {"base_url": "https://api.deepseek.com/v1", "env_key": "DEEPSEEK_API_KEY"},
        "openai":     {"base_url": "https://api.openai.com/v1",   "env_key": "OPENAI_API_KEY"},
        "anthropic":  {"base_url": "https://api.anthropic.com/v1","env_key": "ANTHROPIC_API_KEY"},
        "openrouter": {"base_url": "https://openrouter.ai/api/v1","env_key": "OPENROUTER_API_KEY"},
        "ollama":     {"base_url": "http://localhost:11434/v1",  "env_key": "OLLAMA_API_KEY"},
        "siliconflow": {"base_url": "https://api.siliconflow.cn/v1", "env_key": "SILICONFLOW_API_KEY"},
        "zhipu":      {"base_url": "https://open.bigmodel.cn/api/paas/v4", "env_key": "ZHIPU_API_KEY"},
    }

    def __init__(self, provider: str = "deepseek", model: str = "deepseek-v4-flash",
                 api_key: str = "", base_url: str = "", temperature: float = 0.1):
        self.provider = provider
        self.model = model
        self.temperature = temperature

        # 解析配置
        if provider in self.PROVIDERS:
            cfg = self.PROVIDERS[provider]
            self.base_url = base_url or cfg["base_url"]
            self.api_key = api_key or os.environ.get(cfg["env_key"], "")
            if not self.api_key and cfg["env_key"] == "OLLAMA_API_KEY":
                self.api_key = "ollama"  # Ollama 不需要 key
        else:
            self.base_url = base_url
            self.api_key = api_key

    def chat(self, messages: list[dict], tools: list[dict] | None = None,
             stream: bool = False) -> LLMResponse:
        """
        发送聊天请求

        Args:
            messages: 消息列表 [{"role": "...", "content": "..."}]
            tools:    工具 JSON Schema 列表
            stream:   是否流式
        """
        import httpx

        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": self.temperature,
            "max_tokens": 8192,
        }
        if tools:
            payload["tools"] = tools

        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

        try:
            resp = httpx.post(
                f"{self.base_url}/chat/completions",
                json=payload, headers=headers, timeout=120.0
            )
            resp.raise_for_status()
            data = resp.json()

            choice = data["choices"][0]
            msg = choice["message"]
            usage = data.get("usage", {})

            result = LLMResponse(usage=usage)

            if msg.get("content"):
                result.content = msg["content"]

            if msg.get("tool_calls"):
                result.tool_calls = []
                for tc in msg["tool_calls"]:
                    try:
                        args = json.loads(tc["function"]["arguments"])
                    except (json.JSONDecodeError, KeyError):
                        args = {}
                    result.tool_calls.append({"name": tc["function"]["name"], "args": args})

            # 判断是否是最终回答
            if result.content and not result.tool_calls:
                # 检查是否有最终回答标记
                if any(kw in (result.content or "").lower()[:200]
                       for kw in ["final", "总结", "完成", "最终"]):
                    result.final_answer = result.content

            return result

        except httpx.HTTPStatusError as e:
            return LLMResponse(final_answer=f"API 错误: {e.response.status_code} - {e.response.text[:500]}")
        except Exception as e:
            return LLMResponse(final_answer=f"请求失败: {str(e)}")

    def list_models(self) -> list[str]:
        """列出可用模型"""
        try:
            import httpx
            resp = httpx.get(
                f"{self.base_url}/models",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=15
            )
            data = resp.json()
            return [m["id"] for m in data.get("data", [])]
        except Exception:
            return []

    def __repr__(self):
        return f"LLM({self.provider}/{self.model})"


# ── 快速构建 ──────────────────────────────────────
def from_env() -> LLM:
    """从环境变量自动检测 Provider"""
    for provider, cfg in LLM.PROVIDERS.items():
        key = os.environ.get(cfg["env_key"], "")
        if key and key not in ("ollama",):
            return LLM(provider=provider, api_key=key)
    # 默认 DeepSeek
    return LLM(provider="deepseek")
