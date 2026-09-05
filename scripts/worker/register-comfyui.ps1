# Register the portable ComfyUI as a per-user logon task on the GPU worker.
#   register-comfyui.ps1 -PortableRoot C:\path\to\ComfyUI_windows_portable
param([Parameter(Mandatory = $true)][string]$PortableRoot)
$bat = Join-Path $PortableRoot "run_nvidia_gpu.bat"
if (-not (Test-Path $bat)) { throw "not found: $bat" }
$action = New-ScheduledTaskAction -Execute "cmd.exe" `
    -Argument "/c `"$bat`"" -WorkingDirectory $PortableRoot
$trigger = New-ScheduledTaskTrigger -AtLogOn -User $env:USERNAME
$principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive
$settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) `
    -DontStopIfGoingOnBatteries -AllowStartIfOnBatteries
Register-ScheduledTask -TaskName "comfyui" -Action $action `
    -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
Get-ScheduledTask -TaskName "comfyui" | Select-Object TaskName, State
