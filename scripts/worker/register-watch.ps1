# Register watch.ps1 as a per-user logon task on the GPU worker and start it.
$script = Join-Path $PSScriptRoot "watch.ps1"
Stop-ScheduledTask -TaskName "comfyui-recipes-watch" -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process |
    Where-Object { $_.ProcessId -ne $PID -and
        $_.CommandLine -match "comfy-recipes\.exe.* watch|[\\/]watch\.ps1" } |
    ForEach-Object { taskkill /PID $_.ProcessId /T /F 2>&1 | Out-Null }
$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$script`""
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries
# Registering needs elevation; the runner has none, so an existing task is
# only restarted.
if (-not (Get-ScheduledTask -TaskName "comfyui-recipes-watch" -ErrorAction SilentlyContinue)) {
    Register-ScheduledTask -TaskName "comfyui-recipes-watch" -Action $action `
        -Trigger $trigger -Principal $principal -Settings $settings | Out-Null
}
Start-ScheduledTask -TaskName "comfyui-recipes-watch"
Get-ScheduledTask -TaskName "comfyui-recipes-watch" | Select-Object TaskName, State
