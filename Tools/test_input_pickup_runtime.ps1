param()
$ErrorActionPreference='Stop'
$projectRoot=Split-Path -Parent $PSScriptRoot
$logPath=Join-Path $projectRoot 'Saved/Logs/InputPickupRuntime.log'
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' (Join-Path $projectRoot 'Rikoshet.uproject') /Game/RicochetArena/Progression/Lvl_InputPickupAutomation -game -nullrhi -unattended -nosound -nop4 -ddc=InstalledNoZenLocalFallback "-abslog=$logPath" | Out-Null
$gameExit=$LASTEXITCODE
$text=Get-Content -Raw -LiteralPath $logPath
$checks=@([regex]::Matches($text,'INPUT_PICKUP_PASS ([a-z0-9_]+)') | ForEach-Object {$_.Groups[1].Value})
$passed=$gameExit -eq 0 -and $checks.Count -eq 16 -and $text.Contains('INPUT_PICKUP_RUNTIME_VERIFIED') -and -not ($text -match 'INPUT_PICKUP_FAIL|INPUT_PICKUP_RUNTIME_FAILED|Accessed None|Blueprint Runtime Error|LogScript: Error:|LogBlueprint: Error:|LogPlayerController: Error:')
Select-String -LiteralPath $logPath -Pattern 'INPUT_PICKUP_PASS|INPUT_PICKUP_FAIL|INPUT_PICKUP_RUNTIME|Accessed None|Blueprint Runtime Error' | ForEach-Object Line
@{passed=$passed;check_count=$checks.Count;passed_checks=$checks;exit_code=$gameExit} | ConvertTo-Json -Depth 5 | Set-Content -Encoding utf8 (Join-Path $projectRoot 'Saved/Automation/InputPickupFix/runtime_report.json')
if(-not $passed){throw "Input/pickup regression failed. See $logPath"}
Write-Host "All $($checks.Count) input/pickup regression checks passed."
