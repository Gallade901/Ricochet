param(
    [ValidateSet('create', 'verify')]
    [string]$Action = 'verify'
)
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$editor = 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe'
$scriptName = if ($Action -eq 'create') { 'create_BP_TestCube.py' } else { 'verify_BP_TestCube.py' }
$scriptPath = Join-Path $PSScriptRoot "editor_scripts/$scriptName"
$logPath = Join-Path $projectRoot "Saved/Logs/Ricochet_$Action.log"
& $editor (Join-Path $projectRoot 'Rikoshet.uproject') -run=pythonscript "-script=$scriptPath" -ddc=InstalledNoZenLocalFallback -unattended -nullrhi -nosound -nop4 "-abslog=$logPath"
if ($LASTEXITCODE -ne 0) { throw "Unreal failed ($LASTEXITCODE). See $logPath" }
Write-Host "Unreal completed. Log: $logPath"
