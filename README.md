# 魔兽翻译助手（Python 版）

这是一个使用 Python 编写的《魔兽世界》即时翻译工具，对应 AutoHotkey 版本的体验：按下热键后会弹出输入面板捕获你的键盘/输入法内容，实时展示原文与译文，并在回车时把译文写回游戏或当前激活窗口。

## 功能亮点

- 全局热键（必须在“以管理员身份运行”的 PowerShell 中启动）
  - Alt + Y：呼出输入面板并获取焦点，实时捕获中文输入；Enter 发送译文，Ctrl + Enter 保留原文，Esc 取消
  - Alt + R：开启/关闭 OCR 截屏识别，识别结果在独立窗口中显示
  - Alt + S：打开提示词编辑器
  - Ctrl + Alt + Y：直接翻译剪贴板内容
- 输入面板：完全接管键盘/输入法，原窗口不再收到按键；面板可拖动、位置自动记忆
- OCR：拖拽可调的取词框 + 独立结果窗口（原文/译文实时代码展示，不与主输入面板混合）
- 手动模式（无法获得管理员权限时）：面板始终在前台，输入中文照样实时翻译，结果自动复制到剪贴板
- 支持自定义提示词、术语词典；配置存储在 config/settings.json 与 config/wow_glossary.json

## 安装依赖

`ash
pip install -r requirements.txt
pip install paddlepaddle==3.0.0  # 需要 OCR 时安装
```

需要 Python 3.10+。可执行 paddleocr --help 校验 OCR 依赖是否就绪。

## 启动方式

### 热键模式（推荐）

`ash
powershell -ExecutionPolicy Bypass -File "D:\jojo\My Documents\Desktop\WoW_Translator\python_translator\run_translator.ps1"
```

- Alt + Y 呼出输入面板并自动聚焦 → 输入中文 → 面板右侧实时翻译 → Enter 回车后写回游戏窗口并隐藏面板
- 面板可拖拽移动；下次启动自动回到上次位置

### 手动模式（无管理员权限时）

`ash
powershell -ExecutionPolicy Bypass -File "...\run_translator.ps1" -NoHotkeys
```

- 面板直接显示并接管焦点，输入中文实时翻译
- 回车复制译文到剪贴板，方便手动粘贴到游戏

## OCR 工作流

1. Alt + R：进入截图模式，屏幕出现半透明遮罩，左键拖动框选区域（右键或 Esc 取消）
2. 选区确认后会显示可拖动/可缩放的高亮框，定时截图并在 “OCR 翻译” 窗口中展示译文
3. 再次 Alt + R 停止 OCR；若需要重新选区，可再次按 Alt + R 并拖动新区域

## 配置说明

config/settings.json 示例：

```json
{
  "custom_prompt": "你是一个专业的魔兽世界本地化翻译助手。请将以下英文文本翻译为自然、准确的中文，保留专有名词。文本内容：{text}",
  "llm_apis": {
    "qwen": {
      "api_key": "sk-xxxxx",
      "model": "qwen-turbo",
      "max_tokens": 300,
      "temperature": 0.3
    }
  },
  "ocr": {
    "detection_interval": 2500,
    "region": {"x": 320, "y": 220, "width": 420, "height": 210}
  },
  "panel": {
    "position": {"x": 240, "y": 180}
  }
}
```

请将 api_key 替换为自己的 Qwen Key。面板与 OCR 结果窗口都会记住拖动后的位置。

config/wow_glossary.json 维护术语对照表，可按需扩展。

## 注意事项

- 首次启用 OCR 会自动下载模型，视网络情况耗时数十秒
- 由于面板会接管键盘输入，呼出后原窗口不会继续接收按键；按 Esc 或回车结束翻译即可恢复
- 若热键触发后仍在原窗口显示字符，说明脚本没有以管理员权限运行
- 翻译失败或网络异常会在面板下方显示错误提示，同时写入控制台日志，便于排查

欢迎在此基础上继续扩展，如翻译历史记录、与游戏聊天窗口更紧密的联动等。
