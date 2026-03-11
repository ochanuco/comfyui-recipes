#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_common.sh"

ensure_local_layout
ensure_venv

if [[ ! -d "${COMFYUI_DIR}/custom_nodes" ]]; then
  printf 'ComfyUI runtime not found at %s\n' "${COMFYUI_DIR}" >&2
  printf 'Run ./scripts/bootstrap-comfyui.sh first.\n' >&2
  exit 1
fi

found_nodes=0
while IFS=$'\t' read -r name repo ref path install_requirements; do
  found_nodes=1

  repo_dir="${CUSTOM_NODE_SRC_DIR}/${name}"
  link_path="${COMFYUI_DIR}/custom_nodes/${path}"

  if [[ ! -d "${repo_dir}/.git" ]]; then
    git clone "${repo}" "${repo_dir}"
  fi

  git -C "${repo_dir}" fetch --tags origin
  if git -C "${repo_dir}" show-ref --verify --quiet "refs/remotes/origin/${ref}"; then
    if git -C "${repo_dir}" show-ref --verify --quiet "refs/heads/${ref}"; then
      git -C "${repo_dir}" checkout "${ref}"
    else
      git -C "${repo_dir}" checkout -B "${ref}" "origin/${ref}"
    fi
    git -C "${repo_dir}" pull --ff-only origin "${ref}"
  else
    git -C "${repo_dir}" checkout "${ref}"
  fi

  if [[ -e "${link_path}" && ! -L "${link_path}" ]]; then
    printf 'Refusing to replace non-symlink path: %s\n' "${link_path}" >&2
    exit 1
  fi

  ln -sfn "${repo_dir}" "${link_path}"

  if [[ "${install_requirements}" == "true" && -f "${repo_dir}/requirements.txt" ]]; then
    "$(venv_python)" -m pip install -r "${repo_dir}/requirements.txt"
  fi
done < <(
  "$(venv_python)" - "${CUSTOM_NODE_MANIFEST}" <<'PY'
from __future__ import annotations

import sys
import tomllib
from pathlib import Path

manifest_path = Path(sys.argv[1])
if not manifest_path.exists():
    raise SystemExit(0)

data = tomllib.loads(manifest_path.read_text())
for node in data.get("node", []):
    name = node["name"]
    repo = node["repo"]
    ref = node.get("ref", "main")
    path = node.get("path", name)
    install_requirements = str(bool(node.get("install_requirements", True))).lower()
    print("\t".join([name, repo, ref, path, install_requirements]))
PY
)

if [[ "${found_nodes}" -eq 0 ]]; then
  printf 'No custom nodes configured in %s\n' "${CUSTOM_NODE_MANIFEST}"
fi
