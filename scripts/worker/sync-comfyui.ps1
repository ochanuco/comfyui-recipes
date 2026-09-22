# Bring the portable ComfyUI checkout to the tag pinned in manifests/worker-nodes.toml.
#   sync-comfyui.ps1 -Checkout <dir> -ComfyRoot <dir>
# Prints "changed: True" on its last line when the checkout moved.
param(
    [Parameter(Mandatory = $true)][string]$Checkout,
    [Parameter(Mandatory = $true)][string]$ComfyRoot
)
$ErrorActionPreference = "Stop"
$manifest = Join-Path $Checkout "manifests\worker-nodes.toml"
$python = Join-Path (Split-Path $ComfyRoot -Parent) "python_embeded\python.exe"
if (-not (Test-Path $python)) { throw "not found: $python" }
if (-not (Test-Path (Join-Path $ComfyRoot ".git"))) { throw "not a git checkout: $ComfyRoot" }

$reader = @'
import sys, tomllib
print(tomllib.loads(open(sys.argv[1], encoding="utf-8").read())["comfyui"]["tag"])
'@
$readerPath = Join-Path $env:TEMP "worker-comfyui-reader.py"
Set-Content -Path $readerPath -Value $reader -Encoding ASCII
$tag = & (Join-Path $Checkout ".venv\Scripts\python.exe") $readerPath $manifest
if ($LASTEXITCODE) { exit $LASTEXITCODE }

$current = git -C $ComfyRoot describe --tags --exact-match 2>$null
$moved = $false
if ($current -ne $tag) {
    git -C $ComfyRoot fetch --quiet --tags origin
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
    git -C $ComfyRoot checkout --quiet --detach --force $tag
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
    Stop-ScheduledTask -TaskName "comfyui" -ErrorAction SilentlyContinue
    Get-CimInstance Win32_Process |
        Where-Object { $_.CommandLine -match "ComfyUI[\\/]main\.py" } |
        ForEach-Object { cmd /c "taskkill /PID $($_.ProcessId) /T /F >nul 2>&1" }
    & $python -m pip install --quiet -r (Join-Path $ComfyRoot "requirements.txt")
    if ($LASTEXITCODE) { exit $LASTEXITCODE }
    $moved = $true
}
"ComfyUI {0} {1}" -f $tag, $(if ($moved) { "updated" } else { "ok" })
"changed: $moved"
