
from __future__ import annotations

import concurrent.futures
from pathlib import Path
from typing import Optional, Tuple, TYPE_CHECKING
import hashlib

import re

from PySide6 import QtCore, QtGui, QtWidgets
import mss
from mss import tools

try:
    from rapidocr_onnxruntime import RapidOCR
except ImportError:  # pragma: no cover - optional dependency
    RapidOCR = None

from config_manager import ConfigManager
from translator import QwenTranslator
from ui import OcrRegionOverlay

if TYPE_CHECKING:
    from prompt_manager import PromptManager
    from config_manager import GlossaryManager

_WHITESPACE_RE = re.compile(r"\s+")
_OPEN_PUNCT = ("(", "[", "{", "\uFF08", "\u3010", "\u300A")
_CLOSE_PUNCT = (")", "]", "}", "\uFF09", "\u3011", "\u300B")
CHANNEL_TAG_RE = re.compile(
    r'^\[\s*(\d{1,2}\.\s*)?(?:general|trade|localdefense|lookingforgroup|lfg|world|guild|party|raid|officer|instance|bg|arena|综合|交易|公会|队伍|团队|本地防务|系统)\b',
    re.IGNORECASE,
)
PLAYER_TAG_RE = re.compile(r'^\[[^\]]+\]\s*[^:：]{0,32}[:：]', re.IGNORECASE)
SYSTEM_PREFIX_RE = re.compile(
    r"^(you(?:'ve)?\s+(?:receive|received|loot|gain|lose|learn|create|roll)|quest|achievement|auction|system|you are now|你获得|你拾取|你失去|你学会|任务|系统|声望|成就)",
    re.IGNORECASE,
)
NAME_COLON_RE = re.compile(r'^[^\s\[\]<>]{2,24}[:：]')

def _normalize_ocr_segment(raw: str) -> str:
    if not raw:
        return ""
    s = raw.replace("\u3000", " ").strip()
    if not s:
        return ""
    s = _WHITESPACE_RE.sub(" ", s)
    for punct in _CLOSE_PUNCT:
        s = s.replace(f" {punct}", punct)
    for punct in _OPEN_PUNCT:
        s = s.replace(f"{punct} ", punct)
    for mark in (",", ".", ";", ":", "!", "?", "\uFF0C", "\u3002", "\uFF1B", "\uFF1A", "\uFF01", "\uFF1F", "\u3001"):
        s = s.replace(f" {mark}", mark)
    return s.strip()


def _strip_channel_prefix(text: str) -> str:
    stripped = text.lstrip()
    if not stripped.startswith("["):
        return stripped
    closing = stripped.find("]")
    if closing <= 0:
        return stripped
    return stripped[closing + 1 :].lstrip()


def _is_new_message(text: str) -> bool:
    stripped = text.strip()
    if not stripped:
        return False
    if CHANNEL_TAG_RE.match(stripped):
        return True
    if PLAYER_TAG_RE.match(stripped):
        return True
    if SYSTEM_PREFIX_RE.match(stripped):
        return True
    if NAME_COLON_RE.match(stripped):
        return True
    return False



    if stripped.startswith("["):
        closing = stripped.find("]")
        if closing > 0:
            tag = stripped[1:closing].strip()
            if tag:
                lower_tag = tag.lower()
                if lower_tag and lower_tag[0].isdigit():
                    return True
                base = lower_tag.split()[0].strip(".:[]")
                if base in _CHANNEL_KEYWORDS:
                    return True

    lower = stripped.lower()
    for prefix in _PREFIX_KEYWORDS:
        if lower.startswith(prefix):
            return True

    remainder = _strip_channel_prefix(stripped)
    colon_pos = remainder.find(":")
    if 0 <= colon_pos <= 32:
        return True
    cn_colon_pos = remainder.find("：")
    if 0 <= cn_colon_pos <= 32:
        return True

    return False


class OcrSelectionOverlay(QtWidgets.QWidget):
    """Fullscreen translucent overlay for selecting an OCR capture region."""

    selectionMade = QtCore.Signal(QtCore.QRect)
    cancelled = QtCore.Signal()

    def __init__(self) -> None:
        flags = QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool
        super().__init__(None, flags)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
        self.setCursor(QtCore.Qt.CrossCursor)
        self._dragging = False
        self._origin = QtCore.QPoint()
        self._current = QtCore.QRect()
        self._apply_virtual_geometry()

    def _apply_virtual_geometry(self) -> None:
        rect = QtCore.QRect()
        for screen in QtGui.QGuiApplication.screens():
            rect = rect.united(screen.geometry())
        if rect.isNull():
            rect = QtGui.QGuiApplication.primaryScreen().geometry()
        self.setGeometry(rect)

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:
        if event.key() == QtCore.Qt.Key_Escape:
            self.cancelled.emit()
            self.close()
        else:
            super().keyPressEvent(event)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton:
            self._dragging = True
            self._origin = event.pos()
            self._current = QtCore.QRect(self._origin, QtCore.QSize())
            self.update()
        elif event.button() == QtCore.Qt.RightButton:
            self.cancelled.emit()
            self.close()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:
        if self._dragging:
            self._current = QtCore.QRect(self._origin, event.pos()).normalized()
            self.update()
        else:
            super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:
        if event.button() == QtCore.Qt.LeftButton and self._dragging:
            self._dragging = False
            rect = QtCore.QRect(self._origin, event.pos()).normalized()
            if rect.width() >= 20 and rect.height() >= 20:
                rect.translate(self.geometry().topLeft())
                self.selectionMade.emit(rect)
            else:
                self.cancelled.emit()
            self.close()
        else:
            super().mouseReleaseEvent(event)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 90))
        if not self._current.isNull():
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_Clear)
            painter.fillRect(self._current, QtCore.Qt.transparent)
            painter.setCompositionMode(QtGui.QPainter.CompositionMode_SourceOver)
            pen = QtGui.QPen(QtGui.QColor(81, 160, 240))
            pen.setWidth(2)
            painter.setPen(pen)
            painter.drawRect(self._current)


class OcrController(QtCore.QObject):
    """Coordinate OCR capture, text extraction, and translation."""

    textUpdated = QtCore.Signal(str, str)
    statusUpdated = QtCore.Signal(str)

    def __init__(self, cfg: ConfigManager, translator: QwenTranslator, prompt_manager: 'PromptManager', glossary: 'GlossaryManager') -> None:
        super().__init__()
        if RapidOCR is None:
            raise RuntimeError("未安装 rapidocr-onnxruntime，请使用 --no-ocr 或先安装依赖")

        self.cfg = cfg
        self.translator = translator
        self.prompt_manager = prompt_manager
        self.glossary = glossary
        self.ocr = RapidOCR()

        self._active = False
        self._capture_rect: Optional[QtCore.QRect] = None
        self._capture_token = 0
        self._pending_future: Optional[
            concurrent.futures.Future[Tuple[int, str, str, Optional[str]]]
        ] = None
        self._executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)

        self._timer = QtCore.QTimer(self)
        self._timer.setInterval(int(self.cfg.get_ocr_config().get("detection_interval", 2500)))
        self._timer.timeout.connect(self._tick)

        self.selection_overlay: Optional[OcrSelectionOverlay] = None
        self.overlay: Optional[OcrRegionOverlay] = None

        self._pass_through = False
        self.last_text: str = ""
        self._last_translation: str = ""

    def start(self) -> None:
        if self._active:
            return
        region = self._load_region()
        if region and not region.isNull():
            self._activate_with_region(region)
        else:
            self.statusUpdated.emit("请拖拽选择识别区域（右键或 Esc 取消）")
            self._show_selection_overlay()

    def stop(self) -> None:
        if self.selection_overlay:
            self.selection_overlay.close()
            self.selection_overlay = None
        if self.overlay:
            self.overlay.close()
            self.overlay = None
        if self._pending_future:
            self._pending_future.cancel()
            self._pending_future = None
        self._timer.stop()
        self._active = False
        self._pass_through = False
        self._capture_rect = None
        self._capture_token += 1
        self.statusUpdated.emit("OCR 已停止")

    def is_active(self) -> bool:
        return self._active

    def _show_selection_overlay(self) -> None:
        overlay = OcrSelectionOverlay()
        overlay.selectionMade.connect(self._handle_selection)
        overlay.cancelled.connect(self._handle_cancel_selection)
        overlay.show()
        overlay.raise_()
        overlay.activateWindow()
        self.selection_overlay = overlay

    def _handle_cancel_selection(self) -> None:
        self.selection_overlay = None
        self.statusUpdated.emit("Selection cancelled")

    def toggle_pass_through(self) -> bool:
        if not self._active or not self._capture_rect:
            self.statusUpdated.emit("OCR inactive; cannot hide region")
            return self._pass_through
        self._pass_through = not self._pass_through
        if self.overlay:
            self.overlay.set_pass_through(self._pass_through)
            if not self._pass_through:
                self.overlay.raise_()
        if self._active and not self._timer.isActive():
            self._timer.start()
        if not self._pass_through:
            self._tick()
            self.statusUpdated.emit("Overlay restored; windows interactive")
        else:
            self.statusUpdated.emit("Overlay hidden; OCR running in background")
        return self._pass_through

    def _handle_selection(self, rect: QtCore.QRect) -> None:
        self.selection_overlay = None
        self._save_region(rect)
        self._activate_with_region(rect)

    def _activate_with_region(self, rect: QtCore.QRect) -> None:
        self._capture_rect = QtCore.QRect(rect)
        self._capture_token += 1
        if self._pending_future:
            self._pending_future.cancel()
            self._pending_future = None
        if self.overlay:
            self.overlay.close()

        overlay = OcrRegionOverlay(rect)
        overlay.regionChanged.connect(self._handle_region_change)
        overlay.show()
        overlay.raise_()
        overlay.activateWindow()
        self.overlay = overlay

        self._pass_through = False
        self.overlay.set_pass_through(False)

        self._pass_through = False
        self.overlay.set_pass_through(False)

        self._active = True
        self.statusUpdated.emit("OCR active")
        self.last_text = ""
        self._last_translation = ""
        self._timer.start()
        self._tick()

    def _handle_region_change(self, rect: QtCore.QRect) -> None:
        self._capture_rect = QtCore.QRect(rect)
        self._save_region(rect)
        self._capture_token += 1
        if self._pending_future:
            self._pending_future.cancel()
            self._pending_future = None
        self.last_text = ""
        self._last_translation = ""
        self.statusUpdated.emit("识别区域已更新，重新识别中…")
        self._timer.start()
        self._tick()

    def _tick(self) -> None:
        if not self._capture_rect or self._pending_future is not None:
            return
        path = self._capture(self._capture_rect)
        if not path:
            return
        token = self._capture_token

        def job() -> Tuple[int, str, str, Optional[str]]:
            original, translation, error = self._perform_ocr(path)
            return token, original, translation, error

        future = self._executor.submit(job)
        self._pending_future = future
        future.add_done_callback(self._handle_future_result)

    def _handle_future_result(
        self,
        future: concurrent.futures.Future[Tuple[int, str, str, Optional[str]]],
    ) -> None:
        try:
            token, original, translation, error = future.result()
        except Exception as exc:
            if self._pending_future is future:
                self._pending_future = None
            QtCore.QMetaObject.invokeMethod(
                self,
                "_emit_status",
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(str, f"OCR 失败：{exc}"),
            )
            return

        if self._pending_future is future:
            self._pending_future = None

        if token != self._capture_token:
            return

        if error:
            QtCore.QMetaObject.invokeMethod(
                self,
                "_emit_status",
                QtCore.Qt.QueuedConnection,
                QtCore.Q_ARG(str, f"OCR 结果：{error}"),
            )
            return

        self.last_text = original
        self._last_translation = translation

        QtCore.QMetaObject.invokeMethod(
            self,
            "_emit_result",
            QtCore.Qt.QueuedConnection,
            QtCore.Q_ARG(str, translation),
        )

    @QtCore.Slot(str)
    def _emit_result(self, translation: str) -> None:
        if translation:
            self.statusUpdated.emit("OCR 已刷新")
        else:
            self.statusUpdated.emit("未检测到文本")
        self.textUpdated.emit(self.last_text, translation)

    @QtCore.Slot(str)
    def _emit_status(self, text: str) -> None:
        self.statusUpdated.emit(text)

    def _perform_ocr(self, path: str) -> Tuple[str, str, Optional[str]]:
        try:
            result, _ = self.ocr(path)
        except Exception:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass
            return "", "", "未识别到文本"

        try:
            raw_segments: list[str] = []
            if result:
                for _, segment, _ in result:
                    if segment:
                        raw_segments.append(segment)

            messages: list[str] = []
            pending_fragment: str | None = None
            for segment in raw_segments:
                cleaned = _normalize_ocr_segment(segment)
                if not cleaned:
                    continue
                if pending_fragment is not None:
                    cleaned = f"{pending_fragment}{cleaned}"
                    pending_fragment = None
                if cleaned.startswith('[') and ']' not in cleaned and len(cleaned) < 24:
                    pending_fragment = cleaned
                    continue
                if cleaned.startswith(']') and messages:
                    messages[-1] = f"{messages[-1]}{cleaned}".strip()
                    continue
                if cleaned.startswith(':') and messages:
                    messages[-1] = f"{messages[-1]}{cleaned}".strip()
                    continue
                if _is_new_message(cleaned) or not messages:
                    messages.append(cleaned)
                else:
                    messages[-1] = f"{messages[-1]} {cleaned}".strip()

            if pending_fragment and messages:
                messages[-1] = f"{messages[-1]} {pending_fragment}".strip()
            elif pending_fragment:
                messages.append(pending_fragment)

            text = "\n".join(messages).strip()
            if not text:
                return "", "", "未识别到文本"

            has_chinese = any('\u4e00' <= ch <= '\u9fff' for ch in text)
            prompt = self.prompt_manager.get_zh_to_en_prompt() if has_chinese else self.prompt_manager.get_prompt()
            context = self.last_text
            try:
                translation = self.translator.translate(text, prompt, context)
            except Exception as exc:
                return text, "", f"翻译失败:{exc}"

            if not has_chinese and self.glossary:
                translation = self.glossary.translate(translation)

            return text, translation, None
        finally:
            try:
                Path(path).unlink(missing_ok=True)
            except Exception:
                pass

    def _capture(self, rect: QtCore.QRect) -> Optional[str]:
        monitor = self._rect_to_monitor(rect)
        if monitor is None:
            return None
        location = QtCore.QStandardPaths.writableLocation(QtCore.QStandardPaths.TempLocation)
        if not location:
            return None
        output_dir = Path(location)
        try:
            output_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            return None
        file_path = output_dir / f"wow_translator_{QtCore.QDateTime.currentMSecsSinceEpoch()}.png"
        try:
            with mss.mss() as grabber:
                shot = grabber.grab(monitor)
                tools.to_png(shot.rgb, shot.size, output=str(file_path))
        except mss.exception.ScreenShotError:
            return None
        return str(file_path)

    def _rect_to_monitor(self, rect: QtCore.QRect) -> Optional[dict[str, int]]:
        if rect.width() <= 0 or rect.height() <= 0:
            return None
        screen = QtGui.QGuiApplication.screenAt(rect.center())
        if screen is None:
            screen = QtGui.QGuiApplication.primaryScreen()
        if screen is None:
            return None

        logical = screen.geometry()
        native = screen.nativeGeometry() if hasattr(screen, "nativeGeometry") else None

        if native and logical.width() and logical.height():
            scale_x = native.width() / logical.width()
            scale_y = native.height() / logical.height()
            left = int(round(native.x() + (rect.x() - logical.x()) * scale_x))
            top = int(round(native.y() + (rect.y() - logical.y()) * scale_y))
            width = max(int(round(rect.width() * scale_x)), 1)
            height = max(int(round(rect.height() * scale_y)), 1)
        else:
            dpr = screen.devicePixelRatio()
            left = int(round(rect.x() * dpr))
            top = int(round(rect.y() * dpr))
            width = max(int(round(rect.width() * dpr)), 1)
            height = max(int(round(rect.height() * dpr)), 1)

        return {
            "left": left,
            "top": top,
            "width": width,
            "height": height,
        }

    def _save_region(self, rect: QtCore.QRect) -> None:
        ocr_cfg = self.cfg.get_ocr_config()
        ocr_cfg["region"] = {
            "x": rect.x(),
            "y": rect.y(),
            "width": rect.width(),
            "height": rect.height(),
        }
        self.cfg.save()

    def _load_region(self) -> Optional[QtCore.QRect]:
        data = self.cfg.get_ocr_config().get("region")
        if not isinstance(data, dict):
            return None
        try:
            return QtCore.QRect(
                int(data.get("x", 0)),
                int(data.get("y", 0)),
                int(data.get("width", 0)),
                int(data.get("height", 0)),
            )
        except (TypeError, ValueError):
            return None

