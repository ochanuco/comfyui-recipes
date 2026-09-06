# Bring ComfyUI's custom_nodes/ to the commits pinned in manifests/worker-nodes.toml.
#   sync-nodes.ps1 -Checkout <dir> -ComfyRoot <dir>
# Prints "changed: True" on its last line when any node was cloned or moved.
param(
    [Parameter(Mandatory = $true)][string]$Checkout,
    [Parameter(Mandatory = $true)][string]$ComfyRoot
)
$ErrorActionPreference = "Stop"
$manifest = Join-Path $Checkout "manifests\worker-nodes.toml"
$python = Join-Path (Split-Path $ComfyRoot -Parent) "python_embeded\python.exe"
if (-not (Test-Path $python)) { throw "not found: $python" }
$nodesDir = Join-Path $ComfyRoot "custom_nodes"
if (-not (Test-Path $nodesDir)) { throw "not found: $nodesDir" }

$reader = @'
import sys, tomllib
for node in tomllib.loads(open(sys.argv[1], encoding="utf-8").read()).get("node", []):
    print("\t".join([node["name"], node["repo"], node["commit"],
                     str(bool(node.get("install_requirements", True)))]))
'@
$readerPath = Join-Path $env:TEMP "worker-nodes-reader.py"
Set-Content -Path $readerPath -Value $reader -Encoding ASCII
$entries = & (Join-Path $Checkout ".venv\Scripts\python.exe") $readerPath $manifest
if ($LASTEXITCODE) { exit $LASTEXITCODE }

$changed = $false
foreach ($line in $entries) {
    $name, $repo, $commit, $requirements = $line -split "`t"
    $dir = Join-Path $nodesDir $name
    $moved = $false
    if (-not (Test-Path (Join-Path $dir ".git"))) {
        git clone --quiet $repo $dir
        if ($LASTEXITCODE) { exit $LASTEXITCODE }
        $moved = $true
    }
    $head = git -C $dir rev-parse HEAD
    if ($head -ne $commit) {
        git -C $dir fetch --quiet origin
        if ($LASTEXITCODE) { exit $LASTEXITCODE }
        git -C $dir checkout --quiet --detach $commit
        if ($LASTEXITCODE) { exit $LASTEXITCODE }
        $moved = $true
    }
    if ($moved -and $requirements -eq "True" -and (Test-Path (Join-Path $dir "requirements.txt"))) {
        & $python -m pip install --quiet -r (Join-Path $dir "requirements.txt")
        if ($LASTEXITCODE) { exit $LASTEXITCODE }
    }
    "{0} {1} {2}" -f $name, $commit.Substring(0, 7), $(if ($moved) { "updated" } else { "ok" })
    $changed = $changed -or $moved
}
"changed: $changed"
