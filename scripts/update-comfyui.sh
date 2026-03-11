#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_common.sh"

ensure_local_layout
ensure_venv

if [[ ! -d "${COMFYUI_DIR}/.git" ]]; then
  printf 'ComfyUI runtime not found at %s\n' "${COMFYUI_DIR}" >&2
  printf 'Run ./scripts/bootstrap-comfyui.sh first.\n' >&2
  exit 1
fi

git -C "${COMFYUI_DIR}" fetch --tags origin
if git -C "${COMFYUI_DIR}" show-ref --verify --quiet "refs/remotes/origin/${COMFYUI_REF}"; then
  if git -C "${COMFYUI_DIR}" show-ref --verify --quiet "refs/heads/${COMFYUI_REF}"; then
    git -C "${COMFYUI_DIR}" checkout "${COMFYUI_REF}"
  else
    git -C "${COMFYUI_DIR}" checkout -B "${COMFYUI_REF}" "origin/${COMFYUI_REF}"
  fi
  git -C "${COMFYUI_DIR}" pull --ff-only origin "${COMFYUI_REF}"
else
  git -C "${COMFYUI_DIR}" checkout "${COMFYUI_REF}"
fi

"$(venv_python)" -m pip install -r "${COMFYUI_DIR}/requirements.txt"
"$(venv_python)" "${SCRIPT_DIR}/render-extra-model-paths.py" \
  --template "${MODEL_TEMPLATE}" \
  --asset-root "${ASSET_ROOT}" \
  --output "${MODEL_OUTPUT}"
"${SCRIPT_DIR}/install-custom-nodes.sh"

printf 'ComfyUI is synced at %s\n' "${COMFYUI_DIR}"
