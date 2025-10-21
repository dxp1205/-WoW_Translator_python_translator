# 插件翻译版部署与使用指南

本方案将聊天捕获逻辑放入魔兽世界 3.3.5 客户端插件，通过 SavedVariables 与 Python 桥接脚本交换数据，再由本地模型或云端接口完成翻译。适用于希望直接在游戏聊天框查看译文的场景。

## 1. 准备工作

- 完成《OCR 版本安装与使用指南》中提到的环境准备（Python 3.10 + `.venv` 虚拟环境已创建）。
- 确保 `config/settings.json` 中 `translator.provider` 已设为 `local_opus`（默认），或填写有效的 Qwen API Key 以备回退。
- 若使用本地模型，将 `models/opus_mt_en_zh_ct2/` 保持在仓库默认位置，或更新 `llm_apis.local_opus.model_dir` 指向新路径。

## 2. 安装游戏内插件

1. 将 `wow_addon/WoWTranslatorLLM` 整个目录复制到游戏客户端 `Interface/AddOns/` 下。
2. 启动游戏，在角色选择界面勾选 “WoWTranslatorLLM”，首次登录角色后会生成 SavedVariables 文件：
   ```
   WTF/Account/<账号名>/SavedVariables/WoWTranslatorLLM.lua
   ```
3. 插件 Slash 命令：
   - `/wowllm on`：启用聊天捕获（默认开启）。
   - `/wowllm off`：禁用捕获，仅保留历史译文。
   - `/wowllm status`：查看启用状态、队列与待展示译文数量。

## 3. 启动 Python 桥接脚本

1. 在仓库根目录打开 PowerShell：
   ```powershell
   cd D:\jojo\My Documents\Desktop\WoW_Translator\python_translator
   ```
2. 激活虚拟环境（可选）：
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
3. 指定 SavedVariables 路径运行桥接：
   ```powershell
   python -m wow_addon_bridge.bridge --saved-variables "D:\\WoW\\WTF\\Account\\MyAccount\\SavedVariables\\WoWTranslatorLLM.lua"
   ```
   - `--poll-interval` 可调整轮询频率（默认 1.5 秒）。
   - `--once` 仅处理一次队列后退出，方便调试。
4. 日志提示说明：
   - `Using local translator at ...`：成功启用本地 CTranslate2 模型。
   - `Processed chat queue; pending results: ...`：队列翻译完成，并写入 `WoWTranslatorLLM_Results`。

## 4. 与 OCR 版本的区别

| 模式 | 启动命令 | 作用 |
| ---- | -------- | ---- |
| OCR 桌面版 | `powershell -ExecutionPolicy Bypass -File .\run_translator.ps1` | 手动框选屏幕进行 OCR + 翻译，结果在桌面面板显示 |
| 插件翻译版 | `python -m wow_addon_bridge.bridge --saved-variables <路径>` | 捕获游戏聊天并在客户端聊天框回显译文 |

两种模式可并行：OCR 版适合临时读取副本说明，插件版负责持续翻译聊天频道；若不需要某一模式，可单独停止对应程序。

## 5. 配置要点

- `config/settings.json`
  - `translator.provider`：`local_opus`（默认）表示优先使用本地模型；设为 `qwen` 时完全走云端接口。
  - `llm_apis.local_opus`：
    - `source_prefix`：自动补充到待翻译文本前（默认 `>>cmn<< `，确保输出中文）。
    - `target_prefix`：需要时可设定译文前缀，本方案默认为空。
    - 其他字段（`beam_size`、`max_decoding_length` 等）用于控制翻译风格与速度。
- SavedVariables 结构：
  - `WoWTranslatorLLM_Queue`：插件写入的待翻译消息列表。
  - `WoWTranslatorLLM_Results`：桥接脚本写入的译文待展示队列。

## 6. 常见问题

- **聊天框仍显示英文**：确认桥接脚本正在运行，并检查日志是否出现异常；使用 `/wowllm status` 查看队列是否积压。
- **SavedVariables 未更新**：需要保证游戏和桥接脚本对该文件都有读写权限，必要时退出游戏后再运行脚本。
- **翻译结果偏差**：可在 `config/wow_glossary.json` 中新增术语映射，或调整 `source_prefix`、`beam_size` 等参数。
- **回退到云端**：当本地模型初始化失败时，脚本会自动记录告警并切换至 Qwen API，无需人工干预。

按照上述步骤即可完成插件版的布署与运行，实现“游戏内捕获 + Python 翻译 + 聊天框回显”的闭环流程。
