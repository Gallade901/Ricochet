param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$logPath = Join-Path $projectRoot 'Saved/Logs/RobotRuntime.log'
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' (Join-Path $projectRoot 'Rikoshet.uproject') /Game/RicochetArena/Robot/Lvl_RobotAutomation -game -nullrhi -unattended -nosound -nop4 -ddc=InstalledNoZenLocalFallback "-abslog=$logPath" | Out-Null
$gameExit = $LASTEXITCODE
$text = Get-Content -Raw -LiteralPath $logPath
$checks = [regex]::Matches($text, 'ROBOT_TEST_PASS ([a-z0-9_]+)')
$passed = $gameExit -eq 0 -and $checks.Count -eq 13 -and $text.Contains('ROBOT_RUNTIME_VERIFIED') -and -not ($text -match 'ROBOT_TEST_FAIL|ROBOT_RUNTIME_FAILED|Accessed None|Blueprint Runtime Error')
Select-String -LiteralPath $logPath -Pattern 'ROBOT_TEST|ROBOT_RUNTIME' | ForEach-Object Line
if (-not $passed) { throw "Robot tests failed. See $logPath" }
Write-Host 'All 13 Blueprint robot gameplay checks passed.'
