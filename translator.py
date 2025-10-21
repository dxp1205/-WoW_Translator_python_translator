from __future__ import annotations

import json
import logging
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import requests

try:
    import ctranslate2  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    ctranslate2 = None  # type: ignore

try:
    import sentencepiece as spm  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    spm = None  # type: ignore

logger = logging.getLogger(__name__)


@dataclass
class QwenConfig:
    api_key: str
    model: str = "qwen-turbo"
    max_tokens: int = 300
    temperature: float = 0.3


@dataclass
class LocalOpusConfig:
    model_dir: str
    device: str = "cpu"
    compute_type: str = "int8"
    beam_size: int = 4
    source_prefix: str = ">>cmn<< "
    target_prefix: str = ""
    max_decoding_length: int = 256


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
            return "[ERROR] Missing Qwen API Key"

        if "{text}" in prompt_template:
            prompt = prompt_template.replace("{text}", text)
        else:
            prompt = f"{prompt_template}{text}"

        if ocr_context:
            prompt = f"[OCR Context]\n{ocr_context}\n\n{prompt}"
        if glossary_hint:
            prompt += f"\n\nGlossary hint: {glossary_hint}"

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
            return f"[ERROR] Network request failed: {exc}"

        if response.status_code != 200:
            return f"[ERROR] API status {response.status_code}: {response.text}"

        try:
            data = response.json()
        except json.JSONDecodeError:
            return "[ERROR] Cannot parse API response"

        try:
            return data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError):
            return "[ERROR] Unexpected API response structure"


class LocalOpusTranslator:
    """Local INT8 Marian translator powered by CTranslate2."""

    def __init__(self, cfg: LocalOpusConfig) -> None:
        if ctranslate2 is None or spm is None:
            raise ImportError("LocalOpusTranslator requires 'ctranslate2' and 'sentencepiece'")

        self.cfg = cfg
        self.model_dir = Path(cfg.model_dir).expanduser().resolve()
        if not self.model_dir.exists():
            raise FileNotFoundError(f"Local opus model directory not found: {self.model_dir}")

        source_model = self.model_dir / "source.spm"
        target_model = self.model_dir / "target.spm"
        if not source_model.exists() or not target_model.exists():
            raise FileNotFoundError("SentencePiece model files source.spm/target.spm are required")

        self.translator = ctranslate2.Translator(
            str(self.model_dir),
            device=cfg.device,
            compute_type=cfg.compute_type,
        )
        self.sp_source = spm.SentencePieceProcessor()
        self.sp_source.load(str(source_model))
        self.sp_target = spm.SentencePieceProcessor()
        self.sp_target.load(str(target_model))
        self._source_prefix = cfg.source_prefix.strip()
        prefix = cfg.target_prefix.strip()
        self._target_prefix_tokens: Optional[List[List[str]]] = [[prefix]] if prefix else None
        self._lock = threading.Lock()

    def _encode(self, text: str) -> List[str]:
        pieces = list(self.sp_source.encode(text, out_type=str))
        if not pieces or pieces[-1] != "</s>":
            pieces.append("</s>")
        return pieces

    def _decode(self, tokens: List[str]) -> str:
        filtered = [tok for tok in tokens if tok not in {"</s>", "<pad>"}]
        if not filtered:
            return ""
        return self.sp_target.decode(filtered).strip()

    def translate(
        self,
        text: str,
        prompt_template: str,
        ocr_context: str = "",
        glossary_hint: Optional[str] = None,
    ) -> str:
        content = text.strip()
        if not content:
            return ""

        if self._source_prefix and not content.startswith(self._source_prefix):
            content = f"{self._source_prefix}{content}"

        tokens = self._encode(content)
        beam_size = max(1, int(self.cfg.beam_size))
        kwargs = {
            "beam_size": beam_size,
            "target_prefix": self._target_prefix_tokens,
        }
        max_length = int(self.cfg.max_decoding_length)
        if max_length > 0:
            kwargs["max_decoding_length"] = max_length

        with self._lock:
            results = self.translator.translate_batch([tokens], **kwargs)

        if not results:
            return ""

        hypothesis = results[0].hypotheses[0] if results[0].hypotheses else []
        return self._decode(hypothesis)
