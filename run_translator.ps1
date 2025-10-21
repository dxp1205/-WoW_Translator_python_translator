param(
    [switch]$NoHotkeys,
    [switch]$NoOcr,
    [switch]$Reinstall
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$principal = New-Object Security.Principal.WindowsPrincipal([Security.Principal.WindowsIdentity]::GetCurrent())
$hasAdmin = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $hasAdmin -and -not $NoHotkeys) {
    Write-Warning '?????????????????????????????? (--no-hotkeys)?'
    $NoHotkeys = $true
}

$venvPath = Join-Path $scriptDir '.venv'
$venvPython = Join-Path $venvPath 'Scripts/python.exe'

function Ensure-Venv {
    if (Test-Path $venvPython) { return $false }
    Write-Host 'Creating virtual environment (.venv)...'
    python -m venv .venv
    if (-not (Test-Path $venvPython)) {
        throw 'Failed to create virtual environment. Check that Python 3.10+ is installed and available in PATH.'
    }
    return $true
}

$venvCreated = Ensure-Venv

if ($Reinstall -or $venvCreated) {
    Write-Host 'Installing/upgrading dependencies...'
    & $venvPython -m pip install --upgrade pip
    & $venvPython -m pip install -r requirements.txt
}

$runArgs = @('main.py')
if ($NoHotkeys) { $runArgs += '--no-hotkeys' }
if ($NoOcr) { $runArgs += '--no-ocr' }

Write-Host "Launching translator..." -ForegroundColor Cyan
& $venvPython @runArgs
