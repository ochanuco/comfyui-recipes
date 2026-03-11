#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
# shellcheck disable=SC1091
source "${SCRIPT_DIR}/_common.sh"

if [[ -f "${LAUNCH_ENV}" ]]; then
  # shellcheck disable=SC1090
  source "${LAUNCH_ENV}"
fi

if [[ ! -d "${COMFYUI_DIR}/.git" || ! -x "${VENV_DIR}/bin/python" ]]; then
  printf 'ComfyUI runtime is not bootstrapped yet.\n' >&2
  printf 'Run ./scripts/bootstrap-comfyui.sh first.\n' >&2
  exit 1
fi

"$(venv_python)" "${SCRIPT_DIR}/render-extra-model-paths.py" \
  --template "${MODEL_TEMPLATE}" \
  --asset-root "${ASSET_ROOT}" \
  --output "${MODEL_OUTPUT}"

args=(--listen "${COMFYUI_HOST:-127.0.0.1}" --port "${COMFYUI_PORT:-8188}")
if [[ -n "${COMFYUI_EXTRA_ARGS:-}" ]]; then
  # shellcheck disable=SC2206
  extra_args=( ${COMFYUI_EXTRA_ARGS} )
  args+=("${extra_args[@]}")
fi
args+=("$@")

cd "${COMFYUI_DIR}"
exec "${VENV_DIR}/bin/python" main.py "${args[@]}"
