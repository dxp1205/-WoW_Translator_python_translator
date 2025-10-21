from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Optional

import requests

logger = logging.getLogger(__name__)


@dataclass
class QwenConfig:
    api_key: str
    model: str = "qwen-turbo"
    max_tokens: int = 300
    temperature: float = 0.3


class QwenTranslator:
    """Simple HTTP client for the Qwen chat completion API."""

    endpoint = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"

    def __init__(self, cfg: QwenConfig) -> None:
        self.cfg = cfg

    def _build_payload(self, prompt: str) -> dict[str, object]:
        return {
            "model": self.cfg.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.cfg.temperature,
            "max_tokens": self.cfg.max_tokens,
        }

    def translate(
        self,
        text: str,
        prompt_template: str,
        ocr_context: str = "",
        glossary_hint: Optional[str] = None,
    ) -> str:
        if not self.cfg.api_key:
            return "[错误] 未配置 Qwen API Key"

        if "{text}" in prompt_template:
            prompt = prompt_template.replace("{text}", text)
        else:
            prompt = f"{prompt_template}{text}"

        if ocr_context:
            prompt = f"【OCR上下文】\n{ocr_context}\n\n{prompt}"
        if glossary_hint:
            prompt += f"\n\n术语提示：{glossary_hint}"

        payload = self._build_payload(prompt)
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.cfg.api_key}",
            "Accept": "application/json",
        }

        logger.debug("Qwen request: %s", json.dumps(payload, ensure_ascii=False))

        try:
            response = requests.post(self.endpoint, headers=headers, json=payload, timeout=40)
        except requests.RequestException as exc:
            logger.exception("Qwen request failed")
            return f"[错误] 网络请求异常：{exc}"

        if response.status_code != 200:
            return f"[错误] API 返回 {response.status_code}：{response.text}"

        try:
            data = response.json()
        except json.JSONDecodeError:
            return "[错误] 无法解析 API 响应"

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return "[错误] API 响应格式不符合预期"

