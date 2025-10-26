from __future__ import annotations

import argparse
import concurrent.futures
import logging
import sys
import threading
import time
from pathlib import Path
from typing import Any, List, Optional

from PySide6 import QtCore, QtWidgets, QtGui
import keyboard

from config_manager import ConfigManager, GlossaryManager
from hotkey_listener import HotkeyListener
from ocr_manager import OcrController
from prompt_manager import PromptManager
from translator import LocalOpusConfig, LocalOpusTranslator, QwenConfig, QwenTranslator
from ui import FloatingPanel, PromptEditor, OcrResultWindow

if sys.platform == "win32":  # pragma: no cover - Windows specific helpers
    import ctypes
else:  # pragma: no cover - other platforms fallback
    ctypes = None

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wow_translator_py")


class TranslatorController(QtWidgets.QApplication):
    toggleSessionRequested = QtCore.Signal()
    toggleOcrRequested = QtCore.Signal()
    toggleOcrOverlayRequested = QtCore.Signal()
    showPromptsRequested = QtCore.Signal()
    submissionRequested = QtCore.Signal(str, bool)

    def __init__(self, argv: List[str], *, enable_ocr: bool = True, no_hotkeys: bool = False) -> None:
        super().__init__(argv)
        self.setApplicationName("WoW Translator Python")
        self.setQuitOnLastWindowClosed(False)

        self._hotkeys_disabled = no_hotkeys
        self.cfg = ConfigManager()
        self.prompt_manager = PromptManager(self.cfg)
        self.glossary = GlossaryManager()

        provider = self.cfg.get_translator_provider()
        self._translator_provider = provider
        if provider == "local_opus":
            local_cfg = self.cfg.get_local_opus_config()
            model_dir = str(local_cfg.get("model_dir", "")).strip()
            if model_dir:
                resolved = Path(model_dir).expanduser()
                if not resolved.is_absolute():
                    resolved = (Path.cwd() / resolved).resolve()
                try:
                    self.translator = LocalOpusTranslator(
                        LocalOpusConfig(
                            model_dir=str(resolved),
                            device=str(local_cfg.get("device", "cpu") or "cpu"),
                            compute_type=str(local_cfg.get("compute_type", "int8") or "int8"),
                            beam_size=int(local_cfg.get("beam_size", 4) or 4),
                            source_prefix=str(local_cfg.get("source_prefix", ">>cmn<< ") or ">>cmn<< "),
                            target_prefix=str(local_cfg.get("target_prefix", "") or ""),
                            max_decoding_length=int(local_cfg.get("max_decoding_length", 256) or 256),
                        )
                    )
                except Exception as exc:  # pragma: no cover - fallback on failure
                    logger.warning("Local translator init failed: %s", exc, exc_info=True)
                    provider = "qwen"
                    self._translator_provider = provider
                else:
                    logger.info("Using local translator at %s", resolved)
            else:
                logger.warning("Local translator selected but model_dir is empty, falling back to Qwen API")
                provider = "qwen"
                self._translator_provider = provider
        if provider != "local_opus":
            llm_cfg = self.cfg.get_llm_config()
            self.translator = QwenTranslator(
                QwenConfig(
                    api_key=str(llm_cfg.get("api_key", "")).strip(),
                    model=str(llm_cfg.get("model", "qwen-turbo") or "qwen-turbo"),
                    max_tokens=int(llm_cfg.get("max_tokens", 300) or 300),
                    temperature=float(llm_cfg.get("temperature", 0.3) or 0.3),
                )
            )

        self.toggleSessionRequested.connect(self._on_toggle_session)
        self.toggleOcrRequested.connect(self._on_toggle_ocr)
        self.toggleOcrOverlayRequested.connect(self._on_toggle_ocr_overlay)
        self.showPromptsRequested.connect(self._on_show_prompt_settings)
        self.submissionRequested.connect(self._process_submission)

        self.panel = FloatingPanel()
        panel_cfg = self.cfg.get_panel_config()
        position = panel_cfg.get("position", {}) if isinstance(panel_cfg, dict) else {}
        self.panel.move(int(position.get("x", 240)), int(position.get("y", 180)))
        self.panel.set_overlay_mode(False)
        self.panel.hide()
        self.panel.submitRequested.connect(self._process_submission)
        self.panel.cancelRequested.connect(self._handle_cancel)
        self.panel.textEdited.connect(self._handle_text_edited)
        self.panel.panelMoved.connect(self._handle_panel_moved)

        ocr_window_cfg = self.cfg.get_ocr_window_config()

        def _safe_int(value: Any, default: int) -> int:
            try:
                return int(value)
            except (TypeError, ValueError):
                return default

        pos_cfg = ocr_window_cfg.get("position", {}) if isinstance(ocr_window_cfg, dict) else {}
        size_cfg = ocr_window_cfg.get("size", {}) if isinstance(ocr_window_cfg, dict) else {}
        x = _safe_int(pos_cfg.get("x"), 360)
        y = _safe_int(pos_cfg.get("y"), 260)
        width = max(_safe_int(size_cfg.get("width"), 360), 280)
        height = max(_safe_int(size_cfg.get("height"), 200), 140)
        self.ocr_window = OcrResultWindow(QtCore.QRect(x, y, width, height))
        self.ocr_window.hide()

        self._ocr_window_geometry_timer = QtCore.QTimer()
        self._ocr_window_geometry_timer.setSingleShot(True)
        self._ocr_window_geometry_timer.timeout.connect(self._persist_ocr_window_geometry)
        self._pending_ocr_geometry: Optional[QtCore.QRect] = None
        self.ocr_window.geometryUpdated.connect(self._schedule_ocr_window_geometry_save)

        self._session_active = False
        self._previous_hwnd: Optional[int] = None
        self._pending_live_text: str = ""
        self._last_source_text: str = ""
        self._last_translation: str = ""

        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
        self._live_request_id = 0
        self._live_request_lock = threading.Lock()
        self._debounce_timer = QtCore.QTimer()
        self._debounce_timer.setSingleShot(True)
        self._debounce_timer.timeout.connect(self._execute_live_translation)

        self._panel_move_timer = QtCore.QTimer()
        self._panel_move_timer.setSingleShot(True)
        self._panel_move_timer.timeout.connect(self._persist_panel_position)
        self._pending_panel_pos: Optional[QtCore.QPoint] = None

        self.ocr: OcrController | None = None
        if enable_ocr:
            try:
                self.ocr = OcrController(self.cfg, self.translator)
                self.ocr.textUpdated.connect(self._handle_ocr_update)
                self.ocr.statusUpdated.connect(self._handle_ocr_status)
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("OCR 启动失败: %s", exc, exc_info=True)
                self.ocr_window.update_status(f"OCR 失败：{exc}")
        else:
            self.ocr_window.update_status("OCR 未启用")

        self.hotkeys = HotkeyListener()
        self.hotkeys.on_toggle_session = lambda: self.toggleSessionRequested.emit()
        self.hotkeys.on_toggle_ocr = lambda: self.toggleOcrRequested.emit()
        self.hotkeys.on_toggle_ocr_overlay = lambda: self.toggleOcrOverlayRequested.emit()
        self.hotkeys.on_show_prompts = lambda: self.showPromptsRequested.emit()
        self.hotkeys.on_submit = lambda text, keep: self.submissionRequested.emit(text, keep)

        if not self._hotkeys_disabled:
            self.hotkeys.start()
        else:
            self._set_session_active(True)
            self.panel.update_status("手动模式：输入后点击翻译或按 Enter，Ctrl+Enter 保留原文")

    def shutdown(self) -> None:
        if not self._hotkeys_disabled:
            self.hotkeys.stop()
        if self.ocr:
            self.ocr.stop()
        self._executor.shutdown(wait=False)
        self.panel.close()
        self.ocr_window.close()

    def _remember_foreground_window(self) -> None:
        if ctypes is None:
            self._previous_hwnd = None
            return
        user32 = ctypes.windll.user32
        hwnd = user32.GetForegroundWindow()
        self._previous_hwnd = hwnd or None

    def _restore_foreground_window(self) -> bool:
        if ctypes is None or not self._previous_hwnd:
            return False
        user32 = ctypes.windll.user32
        if not user32.IsWindow(self._previous_hwnd):
            return False
        target_thread = user32.GetWindowThreadProcessId(self._previous_hwnd, None)
        current_thread = ctypes.windll.kernel32.GetCurrentThreadId()
        attached = False
        if target_thread and target_thread != current_thread:
            attached = bool(user32.AttachThreadInput(current_thread, target_thread, True))
        success = bool(user32.SetForegroundWindow(self._previous_hwnd))
        if attached:
            user32.AttachThreadInput(current_thread, target_thread, False)
        if success:
            time.sleep(0.05)
        return success

    def _copy_to_clipboard(self, text: str) -> None:
        QtGui.QGuiApplication.clipboard().setText(text, mode=QtGui.QClipboard.Clipboard)

    def _send_translation_to_foreground(self, text: str) -> None:
        if not text.strip():
            return
        self._copy_to_clipboard(text)
        restored = self._restore_foreground_window()
        if not restored:
            keyboard.write(text)
            return
        time.sleep(0.05)
        keyboard.press_and_release("ctrl+v")

    def _set_session_active(self, active: bool) -> None:
        if self._session_active == active:
            if active:
                self.panel.focus_input()
            return
        self._session_active = active
        if active:
            self.panel.set_overlay_mode(False)
            if not self._hotkeys_disabled:
                self._remember_foreground_window()
            self.panel.update_original("")
            self.panel.update_translation("")
            self.panel.show()
            self.panel.raise_()
            self.panel.activateWindow()
            self.panel.focus_input()
            if self._hotkeys_disabled:
                self.panel.update_status("手动模式：输入后点击翻译或按 Enter，Ctrl+Enter 保留原文")
            else:
                self.panel.update_status("开始录入，Enter 翻译 / Ctrl+Enter 保留原文 / Esc 退出")
        else:
            if not self._hotkeys_disabled:
                self.hotkeys.deactivate()
            self.panel.hide()
            self.panel.update_status("录入已关闭")

    @QtCore.Slot()
    def _on_toggle_session(self) -> None:
        self._set_session_active(not self._session_active)

    @QtCore.Slot()
    def _on_toggle_ocr(self) -> None:
        if not self.ocr:
            self.ocr_window.update_status("OCR unavailable")
            return
        if self.ocr.is_active():
            self.ocr_window.set_pass_through(False)
            self.ocr.stop()
            self.ocr_window.update_status("OCR stopped")
            self.ocr_window.hide()
        else:
            self.ocr_window.update_status("Drag to select capture region")
            self.ocr_window.set_pass_through(False)
            self.ocr_window.show()
            self.ocr_window.raise_()
            self.ocr_window.activateWindow()
            self.ocr.start()

    @QtCore.Slot()
    def _on_toggle_ocr_overlay(self) -> None:
        if not self.ocr or not self.ocr.is_active():
            self.ocr_window.update_status("OCR unavailable")
            return
        state = self.ocr.toggle_pass_through()
        self.ocr_window.set_pass_through(state)
        if state:
            self.ocr_window.update_status("Overlay hidden; windows are click-through")
        else:
            self.ocr_window.update_status("Overlay restored; windows interactive")
            self.ocr_window.raise_()

    @QtCore.Slot()
    def _on_show_prompt_settings(self) -> None:
        dlg = PromptEditor(self.prompt_manager.get_prompt(), self.prompt_manager.get_presets())
        if dlg.exec() == QtWidgets.QDialog.Accepted:
            new_prompt = dlg.prompt_text()
            if new_prompt:
                self.prompt_manager.set_prompt(new_prompt)
                self.panel.update_status("提示词已更新")

    def _handle_text_edited(self, text: str) -> None:
        self._schedule_live_translation(text)

    def _schedule_live_translation(self, text: str) -> None:
        self._pending_live_text = text.strip()
        if not self._pending_live_text:
            self._debounce_timer.stop()
            self._last_source_text = ""
            self._last_translation = ""
            self.panel.update_translation("")
            return
        self._debounce_timer.start(400)

    def _execute_live_translation(self) -> None:
        text = self._pending_live_text
        if not text:
            return
        with self._live_request_lock:
            self._live_request_id += 1
            request_id = self._live_request_id

        def task() -> tuple[int, str, str]:
            result = self._translate_text(text)
            return request_id, text, result

        future = self._executor.submit(task)
        future.add_done_callback(self._handle_live_result)

    def _handle_live_result(self, future: concurrent.futures.Future[tuple[int, str, str]]) -> None:
        try:
            request_id, text, translation = future.result()
        except Exception as exc:  # pragma: no cover - network errors
            logger.warning("实时翻译失败: %s", exc)
            return
        with self._live_request_lock:
            if request_id != self._live_request_id:
                return
        QtCore.QMetaObject.invokeMethod(
            self,
            "_apply_live_result",
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(str, text),
            QtCore.Q_ARG(str, translation),
        )

    @QtCore.Slot(str, str)
    def _apply_live_result(self, text: str, translation: str) -> None:
        self._last_source_text = text
        self._last_translation = translation
        self.panel.update_translation(translation)

    @QtCore.Slot(str, bool)
    def _process_submission(self, text: str, keep_original: bool) -> None:
        submitted = text.strip()
        if not submitted:
            self.panel.update_status("没有检测到可翻译的内容")
            return

        self.panel.update_original(submitted)
        self._debounce_timer.stop()

        if keep_original:
            self.panel.update_translation(submitted)
            self.panel.update_status("已保留原文")
            if not self._hotkeys_disabled:
                self._set_session_active(False)
            return

        if submitted == self._last_source_text and self._last_translation:
            translation = self._last_translation
        else:
            translation = self._translate_text(submitted)
            self._last_source_text = submitted
            self._last_translation = translation

        self.panel.update_translation(translation)
        self.panel.update_status("翻译完成")

        if self._hotkeys_disabled:
            self._copy_to_clipboard(translation)
            return

        self._set_session_active(False)
        self._send_translation_to_foreground(translation)

    @QtCore.Slot()
    def _handle_cancel(self) -> None:
        self._set_session_active(False)

    def _handle_panel_moved(self, pos: QtCore.QPoint) -> None:
        self._pending_panel_pos = pos
        self._panel_move_timer.start(400)

    def _persist_panel_position(self) -> None:
        if self._pending_panel_pos is None:
            return
        panel_cfg = self.cfg.get_panel_config()
        panel_cfg["position"] = {
            "x": int(self._pending_panel_pos.x()),
            "y": int(self._pending_panel_pos.y()),
        }
        self.cfg.save()

    @QtCore.Slot(QtCore.QRect)
    def _schedule_ocr_window_geometry_save(self, rect: QtCore.QRect) -> None:
        if self._ocr_window_geometry_timer.isActive():
            self._ocr_window_geometry_timer.stop()
        self._pending_ocr_geometry = QtCore.QRect(rect)
        self._ocr_window_geometry_timer.start(400)

    def _persist_ocr_window_geometry(self) -> None:
        if self._pending_ocr_geometry is None:
            return
        rect = self._pending_ocr_geometry
        config = self.cfg.get_ocr_window_config()
        config["position"] = {"x": int(rect.x()), "y": int(rect.y())}
        config["size"] = {
            "width": max(int(rect.width()), self.ocr_window.minimumWidth()),
            "height": max(int(rect.height()), self.ocr_window.minimumHeight()),
        }
        self.cfg.save()
        self._pending_ocr_geometry = None

    def _translate_text(self, text: str) -> str:
        context = self.ocr.last_text if self.ocr else ""
        has_chinese = any("\u4e00" <= ch <= "\u9fff" for ch in text)
        if has_chinese:
            prompt = self.prompt_manager.get_zh_to_en_prompt()
            translation = self.translator.translate(text, prompt, context)
        else:
            prompt = self.prompt_manager.get_prompt()
            translation = self.translator.translate(text, prompt, context)
            translation = self.glossary.translate(translation)
        return translation

    @QtCore.Slot(str, str)
    def _handle_ocr_update(self, original: str, translation: str) -> None:
        self.ocr_window.update_translation(translation)

    @QtCore.Slot(str)
    def _handle_ocr_status(self, text: str) -> None:
        self.ocr_window.update_status(text)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WoW Translator Python Edition")
    parser.add_argument("--no-hotkeys", action="store_true", help="仅使用 GUI 而不注册全局热键")
    parser.add_argument("--no-ocr", action="store_true", help="禁用 OCR 功能")
    args, qt_extra = parser.parse_known_args(argv)

    program_name = sys.argv[0] if argv is None else "wow-translator"
    qt_args = [program_name, *qt_extra]

    app = TranslatorController(qt_args, enable_ocr=not args.no_ocr, no_hotkeys=args.no_hotkeys)

    exit_code = app.exec()
    app.shutdown()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

