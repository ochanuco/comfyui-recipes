# Restart the portable ComfyUI. Stopping the task alone leaves main.py running.
$ErrorActionPreference = "Stop"
Stop-ScheduledTask -TaskName "comfyui" -ErrorAction SilentlyContinue
Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -match "ComfyUI[\\/]main\.py" } |
    ForEach-Object { cmd /c "taskkill /PID $($_.ProcessId) /T /F >nul 2>&1" }
Start-ScheduledTask -TaskName "comfyui"
