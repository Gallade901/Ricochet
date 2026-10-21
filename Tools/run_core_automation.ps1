param([string]$Script = 'build_core_mechanics.py', [string]$Log = 'CoreBuild')
$projectRoot = Split-Path -Parent $PSScriptRoot
$scriptPath = Join-Path $PSScriptRoot "editor_scripts/$Script"
& 'C:\Program Files\Epic Games\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' (Join-Path $projectRoot 'Rikoshet.uproject') -run=pythonscript "-script=$scriptPath" -EnablePlugins=EditorToolset -ddc=InstalledNoZenLocalFallback -unattended -nullrhi -nosound -nop4 "-abslog=$projectRoot/Saved/Logs/$Log.log" | Out-Null
$editorExit = $LASTEXITCODE
Select-String -Path "$projectRoot/Saved/Logs/$Log.log" -Pattern 'LogPython: Error:|LogBlueprint: Error:|CORE_.*VERIFIED|Success -' | Select-Object -First 22 | ForEach-Object Line
exit $editorExit
