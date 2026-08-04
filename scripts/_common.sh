#!/usr/bin/env bash

set -euo pipefail

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd -P)"
REPO_ROOT="$(cd -- "${SCRIPT_DIR}/.." && pwd -P)"
LOCAL_DIR="${REPO_ROOT}/.local"
COMFYUI_DIR="${LOCAL_DIR}/ComfyUI"
ASSET_ROOT="${LOCAL_DIR}/assets"
CUSTOM_NODE_SRC_DIR="${LOCAL_DIR}/custom_nodes-src"
VENV_DIR="${REPO_ROOT}/.venv"

UPSTREAM_ENV="${REPO_ROOT}/config/upstream.env"
LAUNCH_ENV="${REPO_ROOT}/config/launch.env"
MODEL_TEMPLATE="${REPO_ROOT}/config/extra_model_paths.yaml.tmpl"
MODEL_OUTPUT="${COMFYUI_DIR}/extra_model_paths.yaml"
CUSTOM_NODE_MANIFEST="${REPO_ROOT}/manifests/custom-nodes.toml"

if [[ -f "${UPSTREAM_ENV}" ]]; then
  # shellcheck disable=SC1090
  source "${UPSTREAM_ENV}"
fi

find_python_cmd() {
  local candidate
  if [[ -x "${VENV_DIR}/bin/python" ]]; then
    if "${VENV_DIR}/bin/python" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)'; then
      printf '%s\n' "${VENV_DIR}/bin/python"
      return 0
    fi
    printf '.venv must use Python 3.12\n' >&2
    return 1
  fi

  for candidate in python3.12 python3 python; do
    if command -v "${candidate}" >/dev/null 2>&1 && "${candidate}" -c 'import sys; raise SystemExit(0 if sys.version_info[:2] == (3, 12) else 1)'; then
      printf '%s\n' "${candidate}"
      return 0
    fi
  done

  printf 'Python 3.12 is required\n' >&2
  return 1
}

ensure_local_layout() {
  mkdir -p "${LOCAL_DIR}" "${ASSET_ROOT}" "${CUSTOM_NODE_SRC_DIR}"
  mkdir -p \
    "${ASSET_ROOT}/checkpoints" \
    "${ASSET_ROOT}/clip" \
    "${ASSET_ROOT}/clip_vision" \
    "${ASSET_ROOT}/configs" \
    "${ASSET_ROOT}/controlnet" \
    "${ASSET_ROOT}/diffusion_models" \
    "${ASSET_ROOT}/embeddings" \
    "${ASSET_ROOT}/ipadapter" \
    "${ASSET_ROOT}/loras" \
    "${ASSET_ROOT}/style_models" \
    "${ASSET_ROOT}/text_encoders" \
    "${ASSET_ROOT}/unet" \
    "${ASSET_ROOT}/upscale_models" \
    "${ASSET_ROOT}/vae" \
    "${ASSET_ROOT}/vae_approx"
}

ensure_venv() {
  local python_cmd
  if [[ -x "${VENV_DIR}/bin/python" ]]; then
    "${VENV_DIR}/bin/python" -m ensurepip --upgrade >/dev/null 2>&1 || true
    return 0
  fi

  # Machines that manage Python through mise or uv often have no system 3.12 at
  # all, so fall back to letting uv fetch one rather than failing the bootstrap.
  if python_cmd="$(find_python_cmd 2>/dev/null)"; then
    "${python_cmd}" -m venv "${VENV_DIR}"
  elif command -v uv >/dev/null 2>&1; then
    uv venv --python 3.12 "${VENV_DIR}"
  else
    printf 'Python 3.12 is required (install it, or install uv to fetch it)\n' >&2
    return 1
  fi

  "${VENV_DIR}/bin/python" -m ensurepip --upgrade >/dev/null 2>&1 || true
}

venv_python() {
  printf '%s\n' "${VENV_DIR}/bin/python"
}
