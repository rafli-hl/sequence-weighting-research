# Run from PowerShell. Ubuntu WSL and work/.venv-wsl must already be installed.
param([string]$RunName = ("pilot-" + (Get-Date -Format "yyyyMMdd-HHmmss")))
$ErrorActionPreference = 'Stop'
if ($RunName -notmatch '^[A-Za-z0-9_-]+$') { throw 'RunName must contain letters, digits, underscores or hyphens.' }
$Workspace = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$LinuxWorkspace = (& wsl.exe -d Ubuntu -- wslpath -a $Workspace).Trim()
if ($LASTEXITCODE -ne 0) { throw 'Could not resolve workspace in Ubuntu.' }
$LinuxPython = "$LinuxWorkspace/work/.venv-wsl/bin/python"
$Source = "$LinuxWorkspace/outputs/sequence-weighting-pilot"
$Runs = "$LinuxWorkspace/work/runs/$RunName"
function Invoke-LocalPython {
    param([string[]]$Arguments)
    & wsl.exe -d Ubuntu -- env "MPLCONFIGDIR=$LinuxWorkspace/work/.matplotlib" $LinuxPython @Arguments
    if ($LASTEXITCODE -ne 0) { throw "Local runtime failed (exit $LASTEXITCODE)." }
}
Invoke-LocalPython -Arguments @("$Source/check_runtime.py", '--output', "$Source/RUNTIME_CHECK.json")
Invoke-LocalPython -Arguments @("$Source/pilot.py", '--validate-only')
Invoke-LocalPython -Arguments @("$Source/pilot.py", '--output', "$Runs/mixed-random-s42")
Invoke-LocalPython -Arguments @("$Source/pilot.py", '--weighting', 'uniform', '--output', "$Runs/mixed-uniform-s42")
Invoke-LocalPython -Arguments @("$Source/report.py", "$Runs/mixed-random-s42", "$Runs/mixed-uniform-s42", '--output', "$Source/results-$RunName")
