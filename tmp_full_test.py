import sys
from PySide6 import QtWidgets
from config_manager import ConfigManager, GlossaryManager
from translator import QwenConfig, QwenTranslator
from prompt_manager import PromptManager
from hotkey_listener import HotkeyListener
from ocr_manager import OcrController
from ui import FloatingPanel

cfg = ConfigManager()
llm_cfg = cfg.get_llm_config()
translator = QwenTranslator(QwenConfig(
    api_key=llm_cfg["api_key"],
    model=llm_cfg.get("model", "qwen-turbo"),
    max_tokens=int(llm_cfg.get("max_tokens", 300) or 300),
    temperature=float(llm_cfg.get("temperature", 0.3) or 0.3),
))

print("LLM 检测: ", translator.translate("For the Alliance!", cfg.get_prompt() or "请翻译以下内容：{text}"))

app = QtWidgets.QApplication([])
panel = FloatingPanel()
prompt_manager = PromptManager(cfg)
glossary = GlossaryManager()
ocr = OcrController(cfg, translator, prompt_manager, glossary)
ocr.statusUpdated.connect(lambda text: print("[OCR]", text))
ocr.textUpdated.connect(lambda orig, trans: print("[OCR 原文]", orig, "\n[OCR 译文]", trans))
ocr.start()

# 手动模拟一次文本提交
input_text = "The Alliance and the Horde are preparing for war."
panel.update_original(input_text)
panel.update_status("翻译中...")
translated = translator.translate(input_text, prompt_manager.get_prompt(), ocr.last_text if hasattr(ocr, "last_text") else "")
translated = glossary.translate(translated)
panel.update_translation(translated)
panel.update_status("翻译完成")

print("手动翻译结果:")
print("原文:", input_text)
print("译文:", translated)

ocr.stop()
panel.close()

# 退出 Qt 循环，确认没有遗留线程
QtWidgets.QApplication.quit()

print("流程完成")
