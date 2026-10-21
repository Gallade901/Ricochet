param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$logPath = Join-Path $projectRoot 'Saved/Logs/CoreRuntime.log'
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' (Join-Path $projectRoot 'Rikoshet.uproject') /Game/RicochetArena/CoreMechanics/Lvl_CoreAutomation -game -nullrhi -unattended -nosound -nop4 -ddc=InstalledNoZenLocalFallback "-abslog=$logPath" | Out-Null
$gameExit = $LASTEXITCODE
$runtimeText = Get-Content -Raw -LiteralPath $logPath
$passed = $gameExit -eq 0 -and $runtimeText.Contains('CORE_RUNTIME_VERIFIED') -and -not ($runtimeText -match 'CORE_TEST_FAIL|CORE_RUNTIME_FAILED|Accessed None|Blueprint Runtime Error')
Select-String -LiteralPath $logPath -Pattern 'CORE_TEST|CORE_RUNTIME' | ForEach-Object Line
if (-not $passed) { throw "Core gameplay tests failed. See $logPath" }
Write-Host 'All 12 Blueprint gameplay checks passed.'
