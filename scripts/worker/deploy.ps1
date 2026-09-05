# Move the standing worker checkout to origin/<Ref>, refresh the venv and
# restart the work task. Run by deploy-worker.yml on the self-hosted runner.
param(
    [Parameter(Mandatory = $true)][string]$Checkout,
    [string]$Ref = "production",
    [string]$ComfyRoot = $env:COMFYUI_PORTABLE_ROOT
)
$ErrorActionPreference = "Stop"
Set-Location $Checkout
$oldHead = git rev-parse HEAD
git fetch --quiet origin
git checkout --quiet -B $Ref "origin/$Ref"
git log --oneline -1
Stop-ScheduledTask -TaskName "comfyui-recipes-watch" -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process |
    Where-Object { $_.ProcessId -ne $PID -and
        $_.CommandLine -match "comfy-recipes\.exe.* work|[\\/]watch\.ps1" } |
    ForEach-Object { cmd /c "taskkill /PID $($_.ProcessId) /T /F >nul 2>&1" }
$uv = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter uv.exe |
    Select-Object -First 1 -ExpandProperty FullName
& $uv pip install --python .venv\Scripts\python.exe -q -e . pillow numpy opencv-python scipy pytest "websockets>=12"
if ($LASTEXITCODE) { exit $LASTEXITCODE }
if ($ComfyRoot) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\worker\register-nodes.ps1 `
        -Checkout $Checkout -ComfyRoot $ComfyRoot
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
    # A restart is only needed when the node pack or the imaging it wraps
    # actually changed -- ComfyUI reads custom_nodes once, at startup.
    git diff --quiet $oldHead HEAD -- comfy_nodes src/comfyui_recipes/infrastructure/imaging src/comfyui_recipes/domain/yukari/delivery_style.py
    if ($LASTEXITCODE -ne 0) {
        Stop-ScheduledTask -TaskName "comfyui" -ErrorAction SilentlyContinue
        Get-CimInstance Win32_Process |
            Where-Object { $_.CommandLine -match "ComfyUI[\\/]main\.py" } |
            ForEach-Object { cmd /c "taskkill /PID $($_.ProcessId) /T /F >nul 2>&1" }
        Start-ScheduledTask -TaskName "comfyui"
    }
}

& powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\worker\register-watch.ps1
if ($LASTEXITCODE) { exit $LASTEXITCODE }
