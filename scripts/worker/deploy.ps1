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
    # The claim loop runs in ComfyUI's Python now, not the checkout's venv, so
    # what it imports beyond ComfyUI's own set has to be there. Only the gap is
    # installed: numpy, PIL, cv2 and scipy already come with the box, and
    # reinstalling them is how a working ComfyUI gets broken.
    $embedded = Join-Path (Split-Path $ComfyRoot -Parent) "python_embeded\python.exe"
    $pip = & $embedded -m pip install "websockets>=12"
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
    $pipInstalled = [bool]($pip -match "^Successfully installed")
    "embedded python: $(if ($pipInstalled) { 'installed' } else { 'ok' })"
    # ComfyUI imports both the node packs and the claim loop once, at startup,
    # so any change to the code it loads needs it back, as does a package that
    # was not in its interpreter before. Docs and tests do not.
    git diff --quiet $oldHead HEAD -- comfy_nodes src
    if ($LASTEXITCODE -ne 0 -or $pipInstalled -or ($sync -match "^changed: True")) {
        & powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\worker\restart-comfyui.ps1
    }
}

# Nothing to start: the claim loop lives in the ComfyUI process the restart
# above brought back. register-watch.ps1 stays for running it standalone.
Get-ScheduledTask -TaskName "comfyui" -ErrorAction SilentlyContinue |
    Select-Object TaskName, State
