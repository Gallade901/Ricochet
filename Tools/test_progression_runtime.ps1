param()
$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$logPath = Join-Path $projectRoot 'Saved/Logs/ProgressionRuntime.log'
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' (Join-Path $projectRoot 'Rikoshet.uproject') /Game/RicochetArena/Progression/Lvl_ProgressionAutomation -game -nullrhi -unattended -nosound -nop4 -ddc=InstalledNoZenLocalFallback "-abslog=$logPath" | Out-Null
$gameExit = $LASTEXITCODE
$text = Get-Content -Raw -LiteralPath $logPath
$checks = [regex]::Matches($text, 'PROGRESSION_PASS ([a-z0-9_]+)') | ForEach-Object { $_.Groups[1].Value }
$passed = $gameExit -eq 0 -and $text.Contains('PROGRESSION_RUNTIME_VERIFIED') -and -not ($text -match 'PROGRESSION_FAIL|PROGRESSION_RUNTIME_FAILED|Accessed None|Blueprint Runtime Error|LogScript: Error:|LogBlueprint: Error:|LogPlayerController: Error:')
Select-String -LiteralPath $logPath -Pattern 'PROGRESSION_PASS|PROGRESSION_FAIL|PROGRESSION_RUNTIME|Accessed None|Blueprint Runtime Error' | ForEach-Object Line
$report = @{ passed = $passed; passed_checks = @($checks); check_count = @($checks).Count; exit_code = $gameExit }
$reportDir = Join-Path $projectRoot 'Saved/Automation/Progression'
$report | ConvertTo-Json -Depth 8 | Set-Content -Encoding utf8 (Join-Path $reportDir 'runtime_report.json')
if (-not $passed) { throw "Progression tests failed. See $logPath" }
Write-Host "All $(@($checks).Count) progression gameplay checks passed."
