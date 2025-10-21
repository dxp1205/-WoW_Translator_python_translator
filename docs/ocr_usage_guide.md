# OCR 版安装与使用指南

本指南适用于仅在本机运行的 OCR 翻译模式，可通过快捷键快速框选游戏聊天窗口并完成实时翻译。

## 1. 环境准备

1. 安装 **Python 3.10**（64 位）。安装时勾选 “Add Python to PATH”。
2. 克隆或解压本仓库到任意磁盘目录，例如 `D:\WoW_Translator\python_translator`。
3. 首次进入目录时建议更新 pip：
   ```powershell
   python -m pip install --upgrade pip
   ```

> 已附带的 `run_translator.ps1` 会自动创建虚拟环境并安装依赖，无需手动配置 venv。

## 2. 首次运行

```powershell
powershell -ExecutionPolicy Bypass -File .\run_translator.ps1
```

脚本动作：
- 自动创建/复用 `.venv` 虚拟环境并安装所需依赖（PySide6、RapidOCR、CTranslate2 等）。
- 启动桌面悬浮翻译面板与 OCR 结果窗口。
- 未以管理员身份运行时会自动进入“手动模式”（无全局热键），可再次执行时以管理员身份提升。

依赖在首次安装时可能需要几分钟，请耐心等待终端完成输出。

## 3. 主要热键

- `Alt + Y`：打开/关闭翻译面板，输入框顶置等待输入。
- `Alt + R`：开启或关闭 OCR 模式；首次开启会要求拖拽选取识别区域。
- `Alt + Shift + R`：在 OCR 激活期间隐藏识别框并让译文窗口穿透（可直接点击游戏界面）；再次按下恢复显示。
- `Alt + S`：打开提示词编辑器，可快速切换/保存自定义 prompt。
- `Ctrl + Alt + Y`：直接读取剪贴板并翻译（无需唤出面板）。

## 4. OCR 使用流程

1. 按 `Alt + R` 启动 OCR，屏幕会出现半透明遮罩。
2. 用鼠标拖拽出聊天窗口范围，松开后识别框会固定在屏幕上，翻译窗口会同步显示在桌面。
3. 若识别框遮挡视线，可按 `Alt + Shift + R` 隐藏框体并让译文窗口不再拦截鼠标。再次按下恢复拖拽。
4. 若需调整位置，直接拖拽识别框边缘或移动译文窗口；调整完成后会自动触发重新识别。
5. 再次按 `Alt + R` 关闭 OCR，所有临时状态（隐藏/锁定）会同步重置。

## 5. 配置说明

- `config/settings.json`
  - `ocr.detection_interval`：OCR 定时截屏间隔，单位毫秒，默认 **3500**。可根据硬件性能自行增减。
  - `panel.position`：翻译面板默认位置。
  - `translator.provider`：`local_opus` 表示走本地模型；如需使用云端 Qwen，可改为 `qwen` 并填写 API Key。
- `config/wow_glossary.json`：专有词表，键为英文、值为中文；可加入常见副本术语增强一致性。

配置文件修改后无需重启脚本，按 `Alt + R` 重新开启 OCR 即可生效。

## 6. 常见问题

| 情况 | 解决办法 |
| ---- | -------- |
| 终端报错 “未安装 rapidocr-onnxruntime” | 运行 `.\.venv\Scripts\python.exe -m pip install rapidocr-onnxruntime` 然后重启脚本 |
| OCR 占用 CPU 较高 | 调高 `detection_interval`、缩小识别区域，或在不需要时按 `Alt + Shift + R` 暂停识别 |
| 翻译窗口遮挡操作 | 使用 `Alt + Shift + R` 切换穿透；关闭 OCR 后状态会自动恢复 |
| 没有检测到文字 | 确认聊天记录有新内容，或检查截图区域是否覆盖正确 |
| 翻译结果不准确 | 更新 `wow_glossary.json` 或在提示词中加入额外说明 |

## 7. 后续建议

- 若计划仅使用热键翻译，可在启动时追加 `-NoOcr` 参数跳过 OCR 模块。
- 建议将脚本创建桌面快捷方式，并勾选“以管理员身份运行”，便于随时启动。
- 如需恢复默认设置，删除 `.venv` 与 `config/` 下的 JSON 文件后重新运行脚本即可。
