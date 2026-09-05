# Point ComfyUI's custom_nodes at this checkout's finalize node pack.
#   register-nodes.ps1 -Checkout <dir> -ComfyRoot <dir>
param(
    [Parameter(Mandatory = $true)][string]$Checkout,
    [Parameter(Mandatory = $true)][string]$ComfyRoot
)
$ErrorActionPreference = "Stop"
$target = Join-Path $Checkout "comfy_nodes\yukari_finalize"
if (-not (Test-Path $target)) { throw "not found: $target" }
$link = Join-Path $ComfyRoot "custom_nodes\yukari_finalize"
if (Test-Path $link) {
    $item = Get-Item $link
    if ($item.LinkType -ne "Junction") { throw "$link exists and is not a junction" }
    if ($item.Target -ne $target) { cmd /c "rmdir `"$link`"" }
}
if (-not (Test-Path $link)) {
    New-Item -ItemType Junction -Path $link -Target $target | Out-Null
}
Get-Item $link | Select-Object FullName, Target
