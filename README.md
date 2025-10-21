# WoW Translator (Python)

Desktop utility for translating World of Warcraft chat / on-screen text. Provides a floating panel for manual input and an optional OCR workflow that captures a configurable region.

## Features

- Global hotkeys for quick translation (`Alt+Y`, `Ctrl+Alt+Y`)
- OCR screen capture with live translation overlay
- Toggle to hide overlay (`Alt+Shift+R`) so the game remains clickable
- Custom prompts and glossary replacements (`config/settings.json`, `config/wow_glossary.json`)
- Local CTranslate2 translator or Qwen API fallback

## Prerequisites

- Windows 10 or newer
- Python 3.10+

## First-Time Setup

```powershell
powershell -ExecutionPolicy Bypass -File .\run_translator.ps1
```
- Creates `.venv`, upgrades `pip`, installs dependencies from `requirements.txt`
- If OCR is desired, ensure `rapidocr-onnxruntime` is installed (the script will prompt if missing)
- Floating panel appears when ready; press `Esc` to cancel a session

### Optional Flags

- `-NoHotkeys`: run in manual mode without global shortcuts
- `-NoOcr`: skip OCR initialization
- `-Reinstall`: reinstall dependencies inside `.venv`

## Launching Later

Run the same command again; the existing `.venv` is reused. To reinstall OCR components manually:
```powershell
.\.venv\Scripts\python.exe -m pip install rapidocr-onnxruntime
```

## Hotkeys

| Hotkey | Description |
| ------ | ----------- |
| `Alt + Y` | Toggle floating session panel |
| `Ctrl + Alt + Y` | Translate clipboard immediately |
| `Alt + R` | Start/stop OCR region capture |
| `Alt + Shift + R` | Hide overlay & make translation window click-through; press again to restore |
| `Alt + S` | Open prompt editor |
| `Esc` | Cancel current session (panel) |

## OCR Workflow

1. Press `Alt + R`, drag to select the capture region.
2. Translation output appears in the overlay window.
3. Press `Alt + Shift + R` to hide the outline and allow gameplay interactions.
4. Press `Alt + R` again to stop OCR (state resets).

## Configuration

- `config/settings.json`: prompt text, translator provider, OCR interval/region, panel position
- `config/wow_glossary.json`: custom term replacements applied after translation

## Troubleshooting

- **No OCR output**: ensure region is selected; large downloads may take time
- **Missing rapidocr-onnxruntime**: install as shown above or launch with `-NoOcr`
- **Hotkeys inactive**: run PowerShell as administrator or use `-NoHotkeys`
- **Windows blocking gameplay**: toggle passthrough with `Alt + Shift + R`

Reset to defaults by removing `.venv` and the `config/` folder, then rerun the launcher.
