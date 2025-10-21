from PySide6 import QtWidgets
from config_manager import ConfigManager
from translator import QwenConfig, QwenTranslator
from ocr_manager import OcrController

cfg = ConfigManager()
llm = cfg.get_llm_config()
translator = QwenTranslator(QwenConfig(
    api_key=llm['api_key'],
    model=llm.get('model', 'qwen-turbo'),
    max_tokens=int(llm.get('max_tokens', 300) or 300),
    temperature=float(llm.get('temperature', 0.3) or 0.3),
))
app = QtWidgets.QApplication([])
ocr = OcrController(cfg, translator)
print('OCR init success:', bool(ocr))
ocr.stop()
