from __future__ import annotations

import threading
from typing import Callable, List

import keyboard


class HotkeyListener:
    """Manage global hotkeys, emitting callbacks for control actions only."""

    def __init__(self) -> None:
        self._shutdown = threading.Event()
        self._thread: threading.Thread | None = None
        self._handles: List[int] = []

        self.on_toggle_session: Callable[[], None] | None = None
        self.on_toggle_ocr: Callable[[], None] | None = None
        self.on_toggle_ocr_overlay: Callable[[], None] | None = None
        self.on_show_prompts: Callable[[], None] | None = None
        self.on_submit: Callable[[str, bool], None] | None = None

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._shutdown.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._shutdown.set()
        if self._thread:
            self._thread.join(timeout=1)
            self._thread = None
        self._clear_hotkeys()

    def deactivate(self) -> None:
        """Maintained for backwards compatibility."""

    def _run(self) -> None:
        try:
            self._register_hotkeys()
            self._shutdown.wait()
        finally:
            self._clear_hotkeys()

    def _register_hotkeys(self) -> None:
        self._handles = [
            keyboard.add_hotkey("alt+y", self._handle_toggle_session, suppress=True),
            keyboard.add_hotkey("alt+r", self._handle_toggle_ocr, suppress=True),
            keyboard.add_hotkey("alt+shift+r", self._handle_toggle_ocr_overlay, suppress=True),
            keyboard.add_hotkey("alt+s", self._handle_show_prompts, suppress=True),
            keyboard.add_hotkey("ctrl+alt+y", self._handle_clipboard_submit, suppress=True)
        ]

    def _clear_hotkeys(self) -> None:
        for handle in self._handles:
            try:
                keyboard.remove_hotkey(handle)
            except Exception:  # pragma: no cover - defensive
                pass
        self._handles.clear()

    def _handle_toggle_session(self) -> None:
        if self.on_toggle_session:
            self.on_toggle_session()

    def _handle_toggle_ocr(self) -> None:
        if self._shift_active():
            return
        if self.on_toggle_ocr:
            self.on_toggle_ocr()

    @staticmethod
    def _shift_active() -> bool:
        try:
            return any(keyboard.is_pressed(key) for key in ("shift", "left shift", "right shift"))
        except RuntimeError:
            return False

    def _handle_toggle_ocr_overlay(self) -> None:
        if self.on_toggle_ocr_overlay:
            self.on_toggle_ocr_overlay()

    def _handle_show_prompts(self) -> None:
        if self.on_show_prompts:
            self.on_show_prompts()

    def _handle_clipboard_submit(self) -> None:
        if not self.on_submit:
            return
        try:
            text = keyboard.get_clipboard()
        except RuntimeError:
            text = ""
        if text:
            self.on_submit(text, False)

