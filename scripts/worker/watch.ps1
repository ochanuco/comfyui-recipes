# Resident chimera watcher for the GPU worker. Registered as a logon task by
# register-watch.ps1; restarts the CLI whenever it exits.
$ErrorActionPreference = "Continue"
$repo = Resolve-Path (Join-Path $PSScriptRoot "..\..")
Set-Location $repo
$env:PYTHONUTF8 = "1"
$log = Join-Path $repo ".local\_nogit\worker\watch.log"
New-Item -ItemType Directory -Force -Path (Split-Path $log) | Out-Null
while ($true) {
    "$(Get-Date -Format s) start" | Out-File -Append -Encoding utf8 $log
    & "$repo\.venv\Scripts\comfy-recipes.exe" watch --interval 30 2>&1 |
        Out-File -Append -Encoding utf8 $log
    "$(Get-Date -Format s) exit $LASTEXITCODE" | Out-File -Append -Encoding utf8 $log
    Start-Sleep -Seconds 10
}
