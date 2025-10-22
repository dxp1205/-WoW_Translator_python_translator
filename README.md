# 魔兽世界聊天翻译（Python 版）

一个在 Windows 桌面运行的轻量翻译工具：支持浮动面板手动输入，也可通过 OCR 实时捕获游戏聊天窗口。安装过程简单，仅需 Python 3.10。

## 功能亮点

- 全局热键：`Alt+Y` 呼出面板、`Ctrl+Alt+Y` 直接翻译剪贴板。
- OCR 模式：`Alt+R` 框选聊天区域，自动识别并翻译；`Alt+Shift+R` 可瞬间隐藏识别框，游戏窗口保持可点击。
- 自定义提示词与术语表：`config/settings.json`、`config/wow_glossary.json`。
- 翻译后端可选：默认本地 CTranslate2 模型，亦可切换至通义千问 API。

## 快速上手（首次运行）

1. 安装 Python 3.10（64 位），并勾选 “Add Python to PATH”。
2. 克隆或解压仓库到任意目录，例如 `D:\WoW_Translator\python_translator`。
3. 打开 PowerShell，执行：
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\run_translator.ps1
   ```
   - 脚本会自动创建 `.venv` 虚拟环境并安装依赖。
   - 首次启用 OCR 会下载 RapidOCR 与 onnxruntime，耗时视网络情况而定。
4. 桌面浮动面板出现后即可开始使用，按 `Esc` 可取消当前会话。

更多细节（热键、常见问题）请参见《[docs/ocr_usage_guide.md](docs/ocr_usage_guide.md)》。

## 常用参数

- `-NoHotkeys`：仅显示浮动面板，不注册全局热键。
- `-NoOcr`：跳过 OCR 初始化，仅保留快捷翻译功能。
- `-Reinstall`：强制重新安装依赖（当 `.venv` 异常时使用）。

## 二次启动

再次运行 `run_translator.ps1` 即可，无需重复安装。若 OCR 提示缺少 RapidOCR，可手动安装：
```powershell
.\.venv\Scripts\python.exe -m pip install rapidocr-onnxruntime
```

## 热键速查

| 热键 | 说明 |
| ---- | ---- |
| `Alt + Y` | 打开/隐藏翻译面板 |
| `Ctrl + Alt + Y` | 翻译剪贴板文本 |
| `Alt + R` | 开启/关闭 OCR，首次会要求框选区域 |
| `Alt + Shift + R` | 隐藏识别框并让译文窗穿透，再按一次恢复 |
| `Alt + S` | 打开提示词编辑器 |
| `Esc` | 取消当前翻译会话 |

## 配置入口

- `config/settings.json`：提示词、翻译后端、OCR 刷新间隔等。
- `config/wow_glossary.json`：术语替换表，可填写副本/职业常用缩写。

## 故障排查

- **OCR 没有翻译**：确认已框选区域，并耐心等待首次识别完成。
- **CPU 占用高**：合理缩小框选范围，或在不需要时按 `Alt+Shift+R` 暂停识别。
- **热键无效**：以管理员身份启动 PowerShell，或使用 `-NoHotkeys` 手动操作。
- **想恢复默认设置**：删除 `.venv` 与 `config/` 目录，重新运行安装脚本。

如需更多说明，请阅读 `docs/ocr_usage_guide.md`。欢迎根据个人需求扩展提示词、术语表或翻译后端。
