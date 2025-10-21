param(
    [string]$SavedVariables = '\\nongjinzhanNAS\web_packages\pe\WTF\Account\dxp1205\SavedVariables\WoWTranslatorLLM.lua',
    [switch]$Once,
    [double]$PollInterval = 1.5
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$venvPath = Join-Path $scriptDir '.venv'
$venvPython = Join-Path $venvPath 'Scripts/python.exe'

function Ensure-Venv {
    if (Test-Path $venvPython) { return $false }
    Write-Host '未检测到 .venv，正在创建虚拟环境...' -ForegroundColor Yellow
    python -m venv .venv
    if (-not (Test-Path $venvPython)) {
        throw '虚拟环境创建失败，请确认已安装 Python 3.10+'
    }
    return $true
}

$venvCreated = Ensure-Venv

if ($venvCreated) {
    Write-Host '首次使用，正在安装依赖...' -ForegroundColor Yellow
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r requirements.txt
}

if (-not $SavedVariables) {
    Write-Host '请使用 -SavedVariables 指定 WoWTranslatorLLM.lua 的路径。' -ForegroundColor Cyan
    exit 1
}

if (-not (Test-Path $SavedVariables)) {
    Write-Warning "未找到文件：$SavedVariables"
    exit 1
}

$bridgeArgs = @('-m', 'wow_addon_bridge.bridge', '--saved-variables', $SavedVariables)
if ($Once) { $bridgeArgs += '--once' }
if ($PollInterval -ne 1.5) { $bridgeArgs += @('--poll-interval', $PollInterval) }

Write-Host "启动桥接脚本..." -ForegroundColor Green
& $venvPython @bridgeArgs
