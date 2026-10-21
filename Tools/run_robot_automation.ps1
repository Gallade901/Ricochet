param([string]$Script = 'build_test_robot.py', [string]$Log = 'RobotBuild')
$projectRoot=Split-Path -Parent $PSScriptRoot
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' (Join-Path $projectRoot 'Rikoshet.uproject') -run=pythonscript "-script=$projectRoot/Tools/editor_scripts/$Script" '-EnablePlugins=EditorToolset,UMGToolSet' -ddc=InstalledNoZenLocalFallback -unattended -nullrhi -nosound -nop4 "-abslog=$projectRoot/Saved/Logs/$Log.log" | Out-Null
$ueExit=$LASTEXITCODE
Select-String -Path "$projectRoot/Saved/Logs/$Log.log" -Pattern 'LogPython: Error:|LogBlueprint: Error:|ROBOT_.*VERIFIED|Success -' | Select-Object -First 22 | ForEach-Object Line
exit $ueExit
