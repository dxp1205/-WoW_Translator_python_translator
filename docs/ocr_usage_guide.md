# OCR 版本安装与使用指南

本指南适用于直接在 Windows 桌面上运行的 OCR 翻译模式，可通过快捷键框选游戏画面并将识别出的英文内容实时翻译为中文。

## 1. 环境要求

- Windows 10 及以上版本。
- 已安装 Python 3.10（项目附带的 `run_translator.ps1` 会自动创建虚拟环境）。
- 显卡/CPU 满足 PaddleOCR 的最低要求；若首次使用 OCR，模型下载可能需要数分钟并占用数百 MB 磁盘空间。

## 2. 初始化步骤

1. 克隆或下载本仓库到任意目录（例如 `D:\WoW_Translator\python_translator`）。
2. 右键使用 PowerShell 打开上述目录，首次运行：
   ```powershell
   powershell -ExecutionPolicy Bypass -File .\run_translator.ps1
   ```
   - 脚本会检查管理员权限，如缺失会自动切换到“仅 GUI”模式（无全局快捷键）。
   - 会创建 `.venv` 虚拟环境并安装依赖（PySide6、PaddleOCR 等）。
3. 完成后会弹出悬浮面板，表示主程序已启动。

> 若希望禁用快捷键或测试 OCR，可追加参数：`-NoHotkeys -NoOcr`。

## 3. 快捷键与面板说明

- `Alt + Y`：呼出/隐藏翻译面板，实时捕获当前剪贴板或聊天内容。
- `Alt + R`：切换 OCR 框选模式，按住鼠标拖拽即可指定识别区域。
- `Alt + Shift + R`：在 OCR 激活时隐藏识别框并将译文窗口置为穿透/只读状态，再次按下恢复；`Alt + R` 停止后会自动重置。
- `Alt + S`：打开 Prompt 编辑器，修改翻译提示词。
- `Ctrl + Alt + Y`：强制提交面板内容进行翻译。
- 面板支持拖动，关闭后会记住位置；按 `Esc` 可取消当前翻译会话。

## 4. OCR 工作流

1. 按 `Alt + R` 进入框选状态，拖出一个矩形区域覆盖游戏聊天框或屏幕部分。
2. 松开鼠标后，窗口右下角会显示 OCR 识别文本及翻译结果。
3. 再次按 `Alt + R` 停止 OCR；如需重新框选，重复上述操作。
4. 若不希望窗口遮挡，可在 OCR 激活后按 `Alt + Shift + R` 将识别框隐藏并让译文窗口穿透；再次按下即可恢复调整。

## 5. 配置文件

- `config/settings.json`：
  - `custom_prompt`：自定义翻译提示词。
  - `llm_apis.qwen`：填写通义千问 API Key 等参数（当未启用本地模型时生效）。
  - `ocr.region`：OCR 默认框选区域坐标与尺寸，可在停止 OCR 后手动调整。
- `config/wow_glossary.json`：术语表，键为英文，值为中文；程序会在翻译结果中替换关键词。

## 6. 常见问题

- **OCR 面板没有内容**：确认已按 `Alt + R` 并拖出区域；首次下载模型时请耐心等待。
- **翻译为空或报错**：检查网络连接、API Key 是否填写；本地模型缺失时脚本会自动退回云端翻译。
- **快捷键无效**：以管理员身份运行 PowerShell 或使用 `-NoHotkeys` 参数改为纯 GUI 手动模式。
- **面板位置混乱**：删除或编辑 `config/settings.json` 中的 `panel.position` 字段后重启程序。

按以上步骤，即可完成 OCR 版本的安装与体验，如需恢复默认设置，可删除 `.venv` 与 `config/` 内配置后重新运行脚本。
