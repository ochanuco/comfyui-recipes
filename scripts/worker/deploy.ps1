# Move the standing worker checkout to origin/<Ref>, refresh the venv and
# restart the work task. Run by deploy-worker.yml on the self-hosted runner.
param(
    [Parameter(Mandatory = $true)][string]$Checkout,
    [string]$Ref = "production",
    [string]$ComfyRoot = $env:COMFYUI_PORTABLE_ROOT,
    [int]$DrainSeconds = 300
)
$ErrorActionPreference = "Stop"
Set-Location $Checkout
# Ask the worker to finish the request it is running before the checkout moves
# under it. It removes the file as its last act, so the wait ends on the
# worker's own word. The kill below stays for a worker already gone or wedged.
$drain = Join-Path $Checkout ".local\_nogit\worker\drain"
New-Item -ItemType Directory -Force -Path (Split-Path $drain) | Out-Null
Set-Content -Path $drain -Value "deploy" -Encoding ASCII
$deadline = (Get-Date).AddSeconds($DrainSeconds)
while ((Test-Path $drain) -and (Get-Date) -lt $deadline) { Start-Sleep -Seconds 5 }
if (Test-Path $drain) {
    # A left-behind file would drain the next worker the moment it starts.
    Remove-Item $drain -Force -ErrorAction SilentlyContinue
    Write-Output "drain: timed out after $DrainSeconds s"
} else {
    Write-Output "drain: worker left on its own"
}

Stop-ScheduledTask -TaskName "comfyui-recipes-watch" -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process |
    Where-Object { $_.ProcessId -ne $PID -and
        $_.CommandLine -match "comfy-recipes\.exe.* work|[\\/]watch\.ps1" } |
    ForEach-Object { cmd /c "taskkill /PID $($_.ProcessId) /T /F >nul 2>&1" }

$oldHead = git rev-parse HEAD
git fetch --quiet origin
git checkout --quiet -B $Ref "origin/$Ref"
git log --oneline -1
$uv = Get-ChildItem "$env:LOCALAPPDATA\Microsoft\WinGet\Packages" -Recurse -Filter uv.exe |
    Select-Object -First 1 -ExpandProperty FullName
& $uv pip install --python .venv\Scripts\python.exe -q -e . pillow numpy opencv-python scipy pytest "websockets>=12"
if ($LASTEXITCODE) { exit $LASTEXITCODE }
if ($ComfyRoot) {
    & powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\worker\register-nodes.ps1 `
        -Checkout $Checkout -ComfyRoot $ComfyRoot
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
    $sync = & powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\worker\sync-nodes.ps1 `
        -Checkout $Checkout -ComfyRoot $ComfyRoot
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
    $sync
    # ComfyUI reads custom_nodes once, at startup: restart only when the deploy
    # changed a node pack or the imaging it wraps.
    git diff --quiet $oldHead HEAD -- comfy_nodes src/comfyui_recipes/infrastructure/imaging src/comfyui_recipes/domain/yukari/delivery_style.py
    if ($LASTEXITCODE -ne 0 -or ($sync -match "^changed: True")) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\worker\restart-comfyui.ps1
    }
}

& powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\worker\register-watch.ps1
if ($LASTEXITCODE) { exit $LASTEXITCODE }
