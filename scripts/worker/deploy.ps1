# Move the standing worker checkout to origin/<Ref>, refresh the venv and
# restart the work task. Run by deploy-worker.yml on the self-hosted runner.
param(
    [Parameter(Mandatory = $true)][string]$Checkout,
    [string]$Ref = "production"
)
$ErrorActionPreference = "Stop"
Set-Location $Checkout
git fetch --quiet origin
git checkout --quiet -B $Ref "origin/$Ref"
git log --oneline -1
Stop-ScheduledTask -TaskName "comfyui-recipes-watch" -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process |
    Where-Object { $_.ProcessId -ne $PID -and
        $_.CommandLine -match "comfy-recipes\.exe.* work|[\\/]watch\.ps1" } |
    ForEach-Object { taskkill /PID $_.ProcessId /T /F 2>&1 | Out-Null }
$uv = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter uv.exe |
    Select-Object -First 1 -ExpandProperty FullName
& $uv pip install --python .venv\Scripts\python.exe -q -e . pillow numpy opencv-python scipy pytest "websockets>=12"
if ($LASTEXITCODE) { exit $LASTEXITCODE }
& powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\worker\register-watch.ps1
if ($LASTEXITCODE) { exit $LASTEXITCODE }
