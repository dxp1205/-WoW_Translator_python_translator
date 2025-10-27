from __future__ import annotations

from typing import Dict

from config_manager import ConfigManager


class PromptManager:
    DEFAULT_PROMPT = (
        "你是一个专业的魔兽世界本地化翻译助手。"
        "这些文本来自游戏内聊天、组队和副本频道，常含职业缩写、装备名称与战术术语。"
        "原始 OCR 可能把同一条消息拆成多个片段，请结合上下文自动合并，并保持每条消息单独成行，优先保留频道与玩家信息。"
        "请结合魔兽世界背景和常见缩写做出自然、准确的中文翻译，保留关键专有名词。"
        "请直接输出译文，不要添加任何解释或额外内容。文本内容：{text}"
    )

    ZH_TO_EN_PROMPT = (
        "You are a localization specialist for World of Warcraft."
        " Translate the following Chinese text into smooth English, keeping lore terms accurate."
        " Text: {text}"
    )

    def __init__(self, cfg: ConfigManager) -> None:
        self.cfg = cfg
        prompt = cfg.get_prompt()
        if not prompt:
            prompt = self.DEFAULT_PROMPT
            self.cfg.set_prompt(prompt)
        self._prompt = prompt

    def get_prompt(self) -> str:
        return self._prompt

    def set_prompt(self, value: str) -> None:
        self._prompt = value
        self.cfg.set_prompt(value)

    def get_zh_to_en_prompt(self) -> str:
        return self.ZH_TO_EN_PROMPT

    def get_presets(self) -> Dict[str, str]:
        return {
            "wow_gaming": self.DEFAULT_PROMPT,
            "formal": "请将以下英文文本翻译为正式、庄重的中文：{text}",
            "casual": "请将以下英文文本翻译成口语化、自然顺畅的中文：{text}",
            "technical": "请将以下英文说明翻译为准确的技术中文，并保持术语专业：{text}",
            "literary": "请将以下英文文本翻译为具有文学色彩的中文表达：{text}",
        }
