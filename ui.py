from __future__ import annotations

from typing import Optional

from PySide6 import QtCore, QtWidgets, QtGui


class InputTextEdit(QtWidgets.QPlainTextEdit):
    submitRequested = QtCore.Signal(bool)
    cancelRequested = QtCore.Signal()

    def keyPressEvent(self, event: QtGui.QKeyEvent) -> None:  # type: ignore[override]
        modifiers = event.modifiers()
        key = event.key()
        if key in (QtCore.Qt.Key_Return, QtCore.Qt.Key_Enter):
            if modifiers & QtCore.Qt.ShiftModifier:
                super().keyPressEvent(event)
                return
            keep_original = bool(modifiers & QtCore.Qt.ControlModifier)
            self.submitRequested.emit(keep_original)
            return
        if key == QtCore.Qt.Key_Escape:
            self.cancelRequested.emit()
            return
        super().keyPressEvent(event)


class FloatingPanel(QtWidgets.QWidget):
    submitRequested = QtCore.Signal(str, bool)
    cancelRequested = QtCore.Signal()
    textEdited = QtCore.Signal(str)
    panelMoved = QtCore.Signal(QtCore.QPoint)

    def __init__(self) -> None:
        super().__init__(None, QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool)
        self.setWindowTitle("WoW Translator")
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
        self.setWindowFlag(QtCore.Qt.Tool, True)
        self._overlay_mode = False
        self._build_ui()

    def _build_ui(self) -> None:
        frame = QtWidgets.QFrame()
        frame.setStyleSheet("background-color: rgba(27,28,34,0.92); border-radius: 12px;")
        layout = QtWidgets.QVBoxLayout(frame)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        title = QtWidgets.QLabel("即时翻译输入")
        title.setStyleSheet("color: #7f8899; font-size: 14px;")
        layout.addWidget(title)

        self.inputBox = InputTextEdit()
        self.inputBox.setPlaceholderText("在此输入待翻译文本，Shift+Enter 换行")
        self.inputBox.setStyleSheet(
            "color: #f0f3ff; background-color: rgba(255,255,255,0.08);"
            "border: 1px solid rgba(81,160,240,0.3); border-radius: 8px;"
        )
        layout.addWidget(self.inputBox)

        translation_label = QtWidgets.QLabel("翻译结果")
        translation_label.setStyleSheet("color: #7f8899; font-size: 13px;")
        layout.addWidget(translation_label)

        self.translationBox = QtWidgets.QPlainTextEdit()
        self.translationBox.setReadOnly(True)
        self.translationBox.setPlaceholderText("译文...")
        self.translationBox.setStyleSheet(
            "color: #eaefff; background-color: rgba(77,115,205,0.12);"
            "border: 1px solid rgba(81,160,240,0.35); border-radius: 8px;"
        )
        self.translationBox.setFixedHeight(140)
        layout.addWidget(self.translationBox)

        controls = QtWidgets.QHBoxLayout()
        controls.setSpacing(8)

        self.keepOriginalBox = QtWidgets.QCheckBox("保留原文")
        controls.addWidget(self.keepOriginalBox)
        controls.addStretch(1)

        self.translateButton = QtWidgets.QPushButton("翻译")
        controls.addWidget(self.translateButton)

        self.clearButton = QtWidgets.QPushButton("清空")
        controls.addWidget(self.clearButton)

        layout.addLayout(controls)

        self.statusLabel = QtWidgets.QLabel("Alt+Y 呼出 / Esc 取消")
        self.statusLabel.setStyleSheet("color: #51A0F0;")
        layout.addWidget(self.statusLabel)

        wrapper = QtWidgets.QVBoxLayout(self)
        wrapper.setContentsMargins(0, 0, 0, 0)
        wrapper.addWidget(frame)

        self.translateButton.clicked.connect(self._on_translate_clicked)
        self.clearButton.clicked.connect(self._on_clear_clicked)
        self.inputBox.submitRequested.connect(self._on_input_submit)
        self.inputBox.cancelRequested.connect(self.cancelRequested.emit)
        self.inputBox.textChanged.connect(self._emit_text)

    def set_overlay_mode(self, overlay: bool) -> None:
        self._overlay_mode = overlay
        self.setWindowFlag(QtCore.Qt.WindowDoesNotAcceptFocus, overlay)
        self.setAttribute(QtCore.Qt.WA_ShowWithoutActivating, overlay)
        self.keepOriginalBox.setVisible(not overlay)
        self.translateButton.setVisible(not overlay)
        self.clearButton.setVisible(not overlay)
        self.inputBox.setReadOnly(overlay)
        if overlay:
            self.inputBox.setPlaceholderText("实时捕获的原文...")
        else:
            self.inputBox.setPlaceholderText("在此输入待翻译文本，Shift+Enter 换行")
        self.updateGeometry()

    def focus_input(self) -> None:
        if not self.inputBox.isReadOnly():
            self.inputBox.setFocus()
            cursor = self.inputBox.textCursor()
            cursor.movePosition(QtGui.QTextCursor.End)
            self.inputBox.setTextCursor(cursor)

    def _emit_text(self) -> None:
        if not self._overlay_mode:
            self.textEdited.emit(self.inputBox.toPlainText())

    def _on_translate_clicked(self) -> None:
        self.submitRequested.emit(self.inputBox.toPlainText(), self.keepOriginalBox.isChecked())

    def _on_clear_clicked(self) -> None:
        self.inputBox.clear()
        self.translationBox.clear()

    def _on_input_submit(self, keep_original: bool) -> None:
        self.submitRequested.emit(self.inputBox.toPlainText(), keep_original)

    def update_original(self, text: str) -> None:
        self.inputBox.blockSignals(True)
        self.inputBox.setPlainText(text)
        cursor = self.inputBox.textCursor()
        cursor.movePosition(QtGui.QTextCursor.End)
        self.inputBox.setTextCursor(cursor)
        self.inputBox.blockSignals(False)

    def update_translation(self, text: str) -> None:
        self.translationBox.setPlainText(text)

    def update_status(self, text: str) -> None:
        self.statusLabel.setText(text)

    def moveEvent(self, event: QtGui.QMoveEvent) -> None:  # type: ignore[override]
        super().moveEvent(event)
        self.panelMoved.emit(self.pos())


class PromptEditor(QtWidgets.QDialog):
    def __init__(self, prompt: str, presets: dict[str, str], parent: QtWidgets.QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("自定义提示词")
        self.setWindowFlags(self.windowFlags() | QtCore.Qt.WindowStaysOnTopHint)
        self.setMinimumSize(520, 380)
        layout = QtWidgets.QVBoxLayout(self)

        self.edit = QtWidgets.QPlainTextEdit(prompt)
        layout.addWidget(self.edit)

        presetLayout = QtWidgets.QHBoxLayout()
        for name, text in presets.items():
            btn = QtWidgets.QPushButton(name)
            btn.clicked.connect(lambda checked, t=text: self.edit.setPlainText(t))
            presetLayout.addWidget(btn)
        layout.addLayout(presetLayout)

        buttonBox = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel)
        buttonBox.accepted.connect(self.accept)
        buttonBox.rejected.connect(self.reject)
        layout.addWidget(buttonBox)

    def prompt_text(self) -> str:
        return self.edit.toPlainText().strip()



class OcrResizeHandle(QtWidgets.QWidget):
    def __init__(self, window: QtWidgets.QWidget) -> None:
        super().__init__(window)
        self._window = window
        self._dragging = False
        self._press_pos = QtCore.QPoint()
        self._start_size = QtCore.QSize()
        self.setFixedSize(22, 22)
        self.setCursor(QtCore.Qt.SizeFDiagCursor)
        self.setAttribute(QtCore.Qt.WA_Hover)

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # type: ignore[override]
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        rect = self.rect().adjusted(2, 2, -2, -2)
        painter.setBrush(QtGui.QColor(255, 255, 255, 28))
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(rect, 6, 6)
        pen = QtGui.QPen(QtGui.QColor(134, 168, 255, 210))
        pen.setWidth(2)
        painter.setPen(pen)
        right = rect.right()
        bottom = rect.bottom()
        painter.drawLine(right - 12, bottom - 4, right - 4, bottom - 12)
        painter.drawLine(right - 16, bottom - 4, right - 4, bottom - 16)

    def _global_pos(self, event: QtGui.QMouseEvent) -> QtCore.QPoint:
        return event.globalPosition().toPoint() if hasattr(event, "globalPosition") else event.globalPos()

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == QtCore.Qt.LeftButton:
            self._dragging = True
            self._press_pos = self._global_pos(event)
            self._start_size = self._window.size()
            event.accept()
        else:
            super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if not self._dragging:
            super().mouseMoveEvent(event)
            return
        delta = self._global_pos(event) - self._press_pos
        new_width = max(self._window.minimumWidth(), self._start_size.width() + delta.x())
        new_height = max(self._window.minimumHeight(), self._start_size.height() + delta.y())
        self._window.resize(new_width, new_height)
        event.accept()

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == QtCore.Qt.LeftButton and self._dragging:
            self._dragging = False
            event.accept()
        else:
            super().mouseReleaseEvent(event)


class OcrResultWindow(QtWidgets.QWidget):
    def __init__(self) -> None:
        super().__init__(None, QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setMinimumSize(320, 160)

        self._dragging = False
        self._drag_offset = QtCore.QPoint()
        self._last_translation = ''
        self._last_status = ''

        outer = QtWidgets.QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        self._frame = QtWidgets.QFrame()
        self._frame.setObjectName('ocrResultFrame')
        self._frame.setStyleSheet(
            "#ocrResultFrame {"
            "  background-color: rgba(14, 17, 24, 0.6);"
            "  border-radius: 16px;"
            "  border: 1px solid rgba(255, 255, 255, 0.08);"
            "}"
        )
        outer.addWidget(self._frame)

        layout = QtWidgets.QVBoxLayout(self._frame)
        layout.setContentsMargins(18, 12, 18, 12)
        layout.setSpacing(8)

        self._drag_handle = QtWidgets.QWidget()
        self._drag_handle.setFixedHeight(6)
        self._drag_handle.setCursor(QtCore.Qt.SizeAllCursor)
        self._drag_handle.setStyleSheet('background: transparent;')
        layout.addWidget(self._drag_handle)

        self.translationView = QtWidgets.QTextBrowser()
        self.translationView.setOpenExternalLinks(False)
        self.translationView.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.translationView.setVerticalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)
        self.translationView.setFrameStyle(QtWidgets.QFrame.NoFrame)
        self.translationView.setStyleSheet(
            "QTextBrowser {"
            "  background: transparent;"
            "  color: rgba(255,255,255,0.92);"
            "  border: none;"
            "  font-size: 14px;"
            "  line-height: 1.42;"
            "  letter-spacing: 0.3px;"
            "}"
        )
        self.translationView.setSizePolicy(QtWidgets.QSizePolicy.Expanding, QtWidgets.QSizePolicy.Expanding)
        layout.addWidget(self.translationView, 1)

        size_row = QtWidgets.QHBoxLayout()
        size_row.addStretch()
        self._resize_handle = OcrResizeHandle(self)
        size_row.addWidget(self._resize_handle, 0, QtCore.Qt.AlignRight | QtCore.Qt.AlignBottom)
        layout.addLayout(size_row)

        self._drag_handle.installEventFilter(self)
        self._frame.installEventFilter(self)
        self.translationView.viewport().installEventFilter(self)

    def update_translation(self, text: str) -> None:
        self._last_translation = text
        self.translationView.clear()
        self.translationView.setPlainText(text)

    def update_status(self, text: str) -> None:
        self._last_status = text

    def eventFilter(self, obj: QtCore.QObject, event: QtCore.QEvent) -> bool:  # type: ignore[override]
        if isinstance(event, QtGui.QMouseEvent):
            if event.type() == QtCore.QEvent.MouseButtonPress and event.button() == QtCore.Qt.LeftButton:
                if obj in (self._drag_handle, self._frame) or (
                    obj is self.translationView.viewport() and event.modifiers() & QtCore.Qt.AltModifier
                ):
                    self._begin_drag(event)
                    return True
            elif event.type() == QtCore.QEvent.MouseMove and self._dragging:
                self._continue_drag(event)
                return True
            elif (
                event.type() == QtCore.QEvent.MouseButtonRelease
                and event.button() == QtCore.Qt.LeftButton
                and self._dragging
            ):
                self._dragging = False
                return True
        return super().eventFilter(obj, event)

    def _begin_drag(self, event: QtGui.QMouseEvent) -> None:
        self._dragging = True
        global_pos = event.globalPosition().toPoint() if hasattr(event, 'globalPosition') else event.globalPos()
        self._drag_offset = global_pos - self.frameGeometry().topLeft()

    def _continue_drag(self, event: QtGui.QMouseEvent) -> None:
        global_pos = event.globalPosition().toPoint() if hasattr(event, 'globalPosition') else event.globalPos()
        self.move(global_pos - self._drag_offset)

class OcrRegionOverlay(QtWidgets.QWidget):
    regionChanged = QtCore.Signal(QtCore.QRect)

    _HANDLE_SIZE = 10

    def __init__(self, rect: QtCore.QRect) -> None:
        super().__init__(None, QtCore.Qt.Window | QtCore.Qt.FramelessWindowHint | QtCore.Qt.Tool)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
        self.setWindowFlag(QtCore.Qt.WindowStaysOnTopHint, True)
        self.setGeometry(rect)
        self._moving = False
        self._resizing = False
        self._resize_anchor = QtCore.QPoint()
        self._move_offset = QtCore.QPoint()
        self._resize_handle: Optional[int] = None

    def paintEvent(self, event: QtGui.QPaintEvent) -> None:  # type: ignore[override]
        painter = QtGui.QPainter(self)
        painter.setRenderHint(QtGui.QPainter.Antialiasing)
        painter.fillRect(self.rect(), QtGui.QColor(0, 0, 0, 40))
        pen = QtGui.QPen(QtGui.QColor(81, 160, 240))
        pen.setWidth(2)
        painter.setPen(pen)
        painter.drawRect(self.rect().adjusted(1, 1, -2, -2))
        painter.setBrush(QtGui.QColor(81, 160, 240))
        for handle in self._handle_rects():
            painter.drawRect(handle)

    def mousePressEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if event.button() != QtCore.Qt.LeftButton:
            return
        handle_index = self._handle_index(event.pos())
        if handle_index is not None:
            self._resizing = True
            self._resize_anchor = event.globalPos()
            self._resize_handle = handle_index
            self.setCursor(QtCore.Qt.SizeFDiagCursor)
        elif self.rect().contains(event.pos()):
            self._moving = True
            self._move_offset = event.globalPos() - self.pos()
            self.setCursor(QtCore.Qt.SizeAllCursor)

    def mouseMoveEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if self._moving:
            new_pos = event.globalPos() - self._move_offset
            self.move(new_pos)
            self.regionChanged.emit(self.geometry())
            return
        if self._resizing and self._resize_handle is not None:
            self._perform_resize(event.globalPos())
            return
        handle_index = self._handle_index(event.pos())
        if handle_index is not None:
            self.setCursor(QtCore.Qt.SizeFDiagCursor)
        elif self.rect().contains(event.pos()):
            self.setCursor(QtCore.Qt.SizeAllCursor)
        else:
            self.setCursor(QtCore.Qt.ArrowCursor)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent) -> None:  # type: ignore[override]
        if event.button() == QtCore.Qt.LeftButton:
            self._moving = False
            self._resizing = False
            self._resize_handle = None
            self.setCursor(QtCore.Qt.ArrowCursor)
            self.regionChanged.emit(self.geometry())

    def _handle_rects(self) -> list[QtCore.QRect]:
        s = self._HANDLE_SIZE
        w = self.width()
        h = self.height()
        return [
            QtCore.QRect(0, 0, s, s),
            QtCore.QRect(w - s, 0, s, s),
            QtCore.QRect(0, h - s, s, s),
            QtCore.QRect(w - s, h - s, s, s),
        ]

    def _handle_index(self, point: QtCore.QPoint) -> Optional[int]:
        for idx, rect in enumerate(self._handle_rects()):
            if rect.contains(point):
                return idx
        return None

    def _perform_resize(self, global_pos: QtCore.QPoint) -> None:
        if self._resize_handle is None:
            return
        delta = global_pos - self._resize_anchor
        geom = self.geometry()
        left, top, right, bottom = geom.left(), geom.top(), geom.right(), geom.bottom()
        if self._resize_handle == 0:
            left += delta.x()
            top += delta.y()
        elif self._resize_handle == 1:
            right += delta.x()
            top += delta.y()
        elif self._resize_handle == 2:
            left += delta.x()
            bottom += delta.y()
        elif self._resize_handle == 3:
            right += delta.x()
            bottom += delta.y()
        new_rect = QtCore.QRect(QtCore.QPoint(left, top), QtCore.QPoint(right, bottom)).normalized()
        if new_rect.width() >= 60 and new_rect.height() >= 60:
            self._resize_anchor = global_pos
            self.setGeometry(new_rect)
            self.regionChanged.emit(new_rect)
