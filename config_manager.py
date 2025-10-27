from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Dict

CONFIG_DIR = Path(__file__).resolve().parent / "config"
SETTINGS_PATH = CONFIG_DIR / "settings.json"
GLOSSARY_PATH = CONFIG_DIR / "wow_glossary.json"

DEFAULT_SETTINGS: Dict[str, Any] = {
    "custom_prompt": "",
    "llm_apis": {
        "qwen": {
            "api_key": "sk-e447bd896e2340208b21ab5c858835c6",
            "model": "qwen-turbo",
            "max_tokens": 300,
            "temperature": 0.3,
        },
        "local_opus": {
            "model_dir": "",
            "device": "cpu",
            "compute_type": "int8",
            "beam_size": 4,
            "source_prefix": ">>cmn<< ",
            "target_prefix": "",
            "max_decoding_length": 256,
        },
    },
    "ocr": {
        "detection_interval": 3500,
        "region": {"x": 320, "y": 220, "width": 420, "height": 210},
    },
    "panel": {
        "position": {"x": 240, "y": 180},
    },
    "ocr_window": {
        "position": {"x": 360, "y": 260},
        "size": {"width": 360, "height": 220},
    },
    "translator": {
        "provider": "qwen"
    },
}


DEFAULT_GLOSSARY: Dict[str, str] = {
    "Alliance": "联盟",
    "Horde": "部落",
    "raid": "团队副本",
    "dungeon": "地下城",
    "tank": "坦克",
    "healer": "治疗",
    "dps": "输出",
    "aggro": "仇恨",
    "cooldown": "冷却",
}


def ensure_config_dir() -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            with path.open("r", encoding="utf-8") as fh:
                return json.load(fh)
    except json.JSONDecodeError:
        pass
    return default


def save_json(path: Path, data: Any) -> None:
    ensure_config_dir()
    tmp_path = path.with_suffix(path.suffix + ".tmp")
    with tmp_path.open("w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    tmp_path.replace(path)


class ConfigManager:
    """Load and persist translator settings in JSON format."""

    def __init__(self) -> None:
        ensure_config_dir()
        self._settings: Dict[str, Any] = load_json(SETTINGS_PATH, {})
        self._apply_defaults()

    @property
    def data(self) -> Dict[str, Any]:
        return self._settings

    def save(self) -> None:
        save_json(SETTINGS_PATH, self._settings)

    def get_llm_config(self) -> Dict[str, Any]:
        llm = self._settings.setdefault("llm_apis", {})
        if not isinstance(llm, dict):
            llm = {}
            self._settings["llm_apis"] = llm
        qwen = llm.setdefault("qwen", {})
        if not isinstance(qwen, dict):
            qwen = {}
            llm["qwen"] = qwen
        return qwen

    def get_local_opus_config(self) -> Dict[str, Any]:
        llm = self._settings.setdefault("llm_apis", {})
        if not isinstance(llm, dict):
            llm = {}
            self._settings["llm_apis"] = llm
        local = llm.setdefault("local_opus", {})
        if not isinstance(local, dict):
            local = {}
            llm["local_opus"] = local
        return local

    def get_translator_provider(self) -> str:
        translator = self._settings.setdefault("translator", {})
        if not isinstance(translator, dict):
            translator = {"provider": DEFAULT_SETTINGS["translator"]["provider"]}
            self._settings["translator"] = translator
        provider = str(translator.get("provider", DEFAULT_SETTINGS["translator"]["provider"]))
        if provider not in {"qwen", "local_opus"}:
            provider = DEFAULT_SETTINGS["translator"]["provider"]
            translator["provider"] = provider
        return provider

    def set_translator_provider(self, provider: str) -> None:
        translator = self._settings.setdefault("translator", {})
        if not isinstance(translator, dict):
            translator = {}
            self._settings["translator"] = translator
        translator["provider"] = provider
        self.save()

    def get_prompt(self) -> str:
        return str(self._settings.get("custom_prompt", ""))

    def set_prompt(self, value: str) -> None:
        self._settings["custom_prompt"] = value
        self.save()

    def get_ocr_config(self) -> Dict[str, Any]:
        ocr = self._settings.setdefault("ocr", {})
        if not isinstance(ocr, dict):
            ocr = {}
            self._settings["ocr"] = ocr
        return ocr

    def get_panel_config(self) -> Dict[str, Any]:
        panel = self._settings.setdefault("panel", {})
        if not isinstance(panel, dict):
            panel = {}
            self._settings["panel"] = panel
        return panel

    def get_ocr_window_config(self) -> Dict[str, Any]:
        window = self._settings.setdefault("ocr_window", {})
        if not isinstance(window, dict):
            window = {}
            self._settings["ocr_window"] = window
        return window

    def _apply_defaults(self) -> None:
        changed = False
        if "custom_prompt" not in self._settings:
            self._settings["custom_prompt"] = DEFAULT_SETTINGS["custom_prompt"]
            changed = True

        llm_cfg = self.get_llm_config()
        defaults = DEFAULT_SETTINGS["llm_apis"]["qwen"]
        for key, value in defaults.items():
            if key not in llm_cfg:
                llm_cfg[key] = value
                changed = True

        local_cfg = self.get_local_opus_config()
        local_defaults = DEFAULT_SETTINGS["llm_apis"]["local_opus"]
        for key, value in local_defaults.items():
            if key not in local_cfg:
                local_cfg[key] = value
                changed = True

        ocr_cfg = self.get_ocr_config()
        if "detection_interval" not in ocr_cfg:
            ocr_cfg["detection_interval"] = DEFAULT_SETTINGS["ocr"]["detection_interval"]
            changed = True
        region = ocr_cfg.setdefault("region", {})
        if not isinstance(region, dict):
            region = {}
            ocr_cfg["region"] = region
            changed = True
        for key, value in DEFAULT_SETTINGS["ocr"]["region"].items():
            if key not in region:
                region[key] = value
                changed = True

        panel_cfg = self.get_panel_config()
        default_panel = DEFAULT_SETTINGS["panel"]["position"]
        position = panel_cfg.setdefault("position", {})
        if not isinstance(position, dict):
            position = {}
            panel_cfg["position"] = position
            changed = True
        for key, value in default_panel.items():
            if key not in position:
                position[key] = value
                changed = True

        ocr_window_cfg = self.get_ocr_window_config()
        default_window = DEFAULT_SETTINGS["ocr_window"]
        win_position = ocr_window_cfg.setdefault("position", {})
        if not isinstance(win_position, dict):
            win_position = {}
            ocr_window_cfg["position"] = win_position
            changed = True
        for key, value in default_window["position"].items():
            if key not in win_position:
                win_position[key] = value
                changed = True
        win_size = ocr_window_cfg.setdefault("size", {})
        if not isinstance(win_size, dict):
            win_size = {}
            ocr_window_cfg["size"] = win_size
            changed = True
        for key, value in default_window["size"].items():
            if key not in win_size:
                win_size[key] = value
                changed = True
        translator_cfg = self._settings.setdefault("translator", {})
        if not isinstance(translator_cfg, dict):
            translator_cfg = dict(DEFAULT_SETTINGS["translator"])
            self._settings["translator"] = translator_cfg
            changed = True
        if "provider" not in translator_cfg:
            translator_cfg["provider"] = DEFAULT_SETTINGS["translator"]["provider"]
            changed = True

        if changed:
            self.save()


class GlossaryManager:
    def __init__(self) -> None:
        ensure_config_dir()
        raw = load_json(GLOSSARY_PATH, {"glossary": DEFAULT_GLOSSARY})
        glossary = raw.get("glossary") if isinstance(raw, dict) else None
        if isinstance(glossary, dict):
            merged = dict(DEFAULT_GLOSSARY)
            merged.update({str(k): str(v) for k, v in glossary.items()})
        else:
            merged = dict(DEFAULT_GLOSSARY)
        self._terms: Dict[str, str] = merged
        self._sorted_terms = sorted(self._terms.items(), key=lambda kv: len(kv[0]), reverse=True)
        self._word_patterns = {
            key: re.compile(rf"\b{re.escape(key)}\b")
            for key, _ in self._sorted_terms
            if self._is_word_token(key)
        }
        if not GLOSSARY_PATH.exists() or not isinstance(glossary, dict):
            save_json(GLOSSARY_PATH, {"glossary": self._terms})

    @staticmethod
    def _is_word_token(token: str) -> bool:
        return token.isalnum()

    def translate(self, text: str, focus: str | None = None) -> str:
        result = text
        focus_lower = focus.lower() if focus else None
        for english, chinese in self._sorted_terms:
            key = english.strip()
            if not key:
                continue
            if focus_lower and focus_lower not in key.lower():
                continue
            if self._is_word_token(key):
                pattern = self._word_patterns.get(key)
                if pattern:
                    result = pattern.sub(chinese, result)
            else:
                result = result.replace(key, chinese)
        return result

    def get_terms(self) -> Dict[str, str]:
        return dict(self._terms)
