# OCR Mode Setup & Usage Guide

This guide explains how to run the desktop OCR workflow, translate on-screen text, and use the new overlay passthrough hotkey.

## 1. Requirements

- Windows 10 or newer
- Python 3.10 (the project script will create a virtual environment automatically)
- CPU/GPU capable of running PaddleOCR (first run downloads models and may temporarily use several hundred MB)

## 2. First-Time Setup

1. Clone or download this repository to any directory.
2. Open PowerShell in the project root and run:
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\run_translator.ps1
   ```
   - The script creates `.venv`, upgrades `pip`, and installs dependencies listed in `requirements.txt`.
   - If administrator privileges are missing, the app falls back to GUI-only mode (global hotkeys disabled).
3. When the floating panel appears, the translator is ready.

> Tip: if you prefer not to auto-install OCR dependencies or hotkeys, you can launch with `-NoOcr`, `-NoHotkeys`, or reinstall with `-Reinstall`.

## 3. Launching Later

After the first setup, simply run:
```powershell
powershell -ExecutionPolicy Bypass -File .\run_translator.ps1
```
The script reuses the existing `.venv`. To disable OCR for a session, append `-NoOcr`.

## 4. Optional: Install OCR Runtime Manually

If the log shows `未安装 rapidocr-onnxruntime`, install it inside the virtual environment:
```powershell
.\.venv\Scripts\python.exe -m pip install rapidocr-onnxruntime
```
Re-run the launcher afterwards.

## 5. Hotkeys (Default)

| Hotkey | Usage |
| ------ | ----- |
| `Alt + Y` | Toggle floating panel session (real-time translation input) |
| `Alt + R` | Enter/exit OCR region selection mode |
| `Alt + Shift + R` | When OCR is active, hide the capture overlay and make the translation window click-through; press again to restore |
| `Alt + S` | Open prompt editor |
| `Ctrl + Alt + Y` | Immediately translate clipboard text |
| `Esc` | Cancel the current translation session (inside panel) |

## 6. OCR Workflow

1. Press `Alt + R` to start region selection. Drag a rectangle over the area you want to monitor (e.g., a chat window).
2. Release the mouse to confirm. The OCR status window shows recognized text and translations.
3. Press `Alt + Shift + R` to hide the overlay and allow direct interaction with the game while OCR keeps running. Press again to restore overlay controls.
4. Press `Alt + R` once more to stop OCR. Next time you start OCR, the overlay resets to visible.

## 7. Configuration Files

- `config/settings.json`
  - `custom_prompt`: custom translation prompt
  - `llm_apis`: configure API keys or local model preferences
  - `ocr`: default detection interval and saved region
- `config/wow_glossary.json`: term mappings (English -> translated terms) applied after translation

## 8. Troubleshooting

- **No OCR output**: ensure `Alt + R` was used to define a region and that OCR models finished downloading
- **“未安装 rapidocr-onnxruntime”**: install the dependency as shown in section 4
- **Hotkeys unresponsive**: run PowerShell as administrator or launch with `-NoHotkeys` and operate purely via GUI
- **Windows obstructing gameplay**: toggle passthrough with `Alt + Shift + R`; the translation window becomes click-through

Resetting the configuration is as simple as deleting `.venv` and the `config/` folder; run the launcher again to recreate defaults.
