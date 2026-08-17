<#
.SYNOPSIS
    Put IPAdapter on the Windows ComfyUI box: the custom node and its two models.

.DESCRIPTION
    Reference-image conditioning. It carries the LOOK of an input image without
    copying its composition, which is the one thing the prompt cannot do: this
    project's costume drifts every time the pose changes, and the whole reason
    the recipe is a stack of per-pose splices is that tags are a single argument
    about the whole picture. See docs/render-notes.md, 2026-08-17.

    Three things land:

      custom_nodes\ComfyUI_IPAdapter_plus        the node (git clone)
      models\clip_vision\CLIP-ViT-H-14-...       2.5 GB, the image encoder
      models\ipadapter\ip-adapter-plus_sdxl...   0.8 GB, the adapter itself

    ip-adapter-PLUS is the higher-detail variant and vit-h is the encoder it was
    trained against; the pair has to match or the node loads and the output is
    noise. Both SHA256s below are the ones in manifests/models-sha256.txt, taken
    from the mac's own copies before they were deleted, so what lands here is
    bit-for-bit what this repo was built against. The script verifies and
    refuses to leave a file in place that hashes wrong.

    Downloads resume, so a killed transfer can be restarted with the same
    command.

.PARAMETER ComfyRoot
    The ComfyUI directory -- the one holding main.py and models\. For a
    portable install this is ...\ComfyUI_windows_portable\ComfyUI

.PARAMETER SkipNode
    Fetch the models only, leaving custom_nodes alone.

.EXAMPLE
    .\fetch-ipadapter-windows.ps1 -ComfyRoot C:\Users\chanu\ComfyUI_windows_portable_nvidia\ComfyUI_windows_portable\ComfyUI
#>

#Requires -Version 5.1

param(
    [Parameter(Mandatory = $true)]
    [string]$ComfyRoot,

    [switch]$SkipNode
)

$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

$NodeRepo = 'https://github.com/cubiq/ComfyUI_IPAdapter_plus.git'

# Both files live in h94/IP-Adapter. The image encoder is stored there under a
# generic name (models/image_encoder/model.safetensors) and is renamed on the
# way in, because ComfyUI lists clip_vision models by filename and
# `model.safetensors` says nothing about which encoder it is.
$Files = @(
    @{
        Dest   = 'clip_vision\CLIP-ViT-H-14-laion2B-s32B-b79K.safetensors'
        Url    = 'https://huggingface.co/h94/IP-Adapter/resolve/main/models/image_encoder/model.safetensors'
        Sha256 = '6ca9667da1ca9e0b0f75e46bb030f7e011f44f86cbfb8d5a36590fcd7507b030'
        Size   = '2.5 GB'
    },
    @{
        Dest   = 'ipadapter\ip-adapter-plus_sdxl_vit-h.safetensors'
        Url    = 'https://huggingface.co/h94/IP-Adapter/resolve/main/sdxl_models/ip-adapter-plus_sdxl_vit-h.safetensors'
        Sha256 = '3f5062b8400c94b7159665b21ba5c62acdcd7682262743d7f2aefedef00e6581'
        Size   = '0.8 GB'
    }
)

function Write-Step($message) {
    Write-Host ""
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Get-RemoteFile {
    <# Resumable download via curl.exe, which ships with Windows 10 1803+. #>
    param([string]$Url, [string]$Destination)

    $dir = Split-Path -Parent $Destination
    if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }

    & curl.exe --location --fail --retry 3 --retry-delay 5 `
        --continue-at - --output $Destination $Url
    if ($LASTEXITCODE -ne 0) {
        throw "download failed (curl exit $LASTEXITCODE): $Url"
    }
}

if (-not (Test-Path (Join-Path $ComfyRoot 'main.py'))) {
    throw "no main.py under $ComfyRoot -- point -ComfyRoot at the ComfyUI directory itself"
}
if (-not (Get-Command curl.exe -ErrorAction SilentlyContinue)) {
    throw "curl.exe not found. It ships with Windows 10 1803 and later."
}

if (-not $SkipNode) {
    Write-Step "ComfyUI_IPAdapter_plus"
    $nodeDir = Join-Path $ComfyRoot 'custom_nodes\ComfyUI_IPAdapter_plus'
    if (Test-Path $nodeDir) {
        Write-Host "    already there; pulling"
        & git -C $nodeDir pull --ff-only
    } else {
        & git clone --depth 1 $NodeRepo $nodeDir
        if ($LASTEXITCODE -ne 0) { throw "git clone failed" }
    }
    # The node has no requirements.txt of its own; it runs on what ComfyUI
    # already has. Nothing to install into python_embeded.
}

foreach ($file in $Files) {
    $target = Join-Path $ComfyRoot "models\$($file.Dest)"
    Write-Step "$($file.Dest) ($($file.Size))"

    if (Test-Path $target) {
        $have = (Get-FileHash -Path $target -Algorithm SHA256).Hash.ToLower()
        if ($have -eq $file.Sha256) {
            Write-Host "    already correct"
            continue
        }
        Write-Host "    present but hashes wrong; resuming/replacing"
    }

    Get-RemoteFile -Url $file.Url -Destination $target

    $have = (Get-FileHash -Path $target -Algorithm SHA256).Hash.ToLower()
    if ($have -ne $file.Sha256) {
        Remove-Item $target -Force
        throw "hash mismatch for $($file.Dest): got $have, wanted $($file.Sha256). Removed."
    }
    Write-Host "    verified"
}

Write-Step "done"
Write-Host "Restart ComfyUI for the node to load, then check that the IPAdapter"
Write-Host "nodes are present:"
Write-Host "    curl -s http://<host>:8188/object_info | findstr IPAdapter"
