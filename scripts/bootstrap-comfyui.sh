#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_common.sh"

ensure_local_layout

if [[ -e "${COMFYUI_DIR}" && ! -d "${COMFYUI_DIR}/.git" ]]; then
  printf 'Path exists but is not a ComfyUI git checkout: %s\n' "${COMFYUI_DIR}" >&2
  exit 1
fi

if [[ ! -d "${COMFYUI_DIR}/.git" ]]; then
  git clone "${COMFYUI_REPO}" "${COMFYUI_DIR}"
fi

"${SCRIPT_DIR}/update-comfyui.sh"
