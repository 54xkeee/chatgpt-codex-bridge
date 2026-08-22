#!/bin/zsh
set -euo pipefail

readonly CONFIG_FILE="${CHATGPT_CODEX_BRIDGE_CONFIG:?missing bridge config}"
[[ "${CONFIG_FILE}" == /* && -f "${CONFIG_FILE}" && ! -L "${CONFIG_FILE}" ]] || exit 64

value() {
  /usr/bin/plutil -extract "$1" raw -o - "${CONFIG_FILE}"
}

readonly PYTHON_BIN="$(value python_bin)"
readonly GUARD="$(value runtime_guard)"
readonly WORKSPACE="$(value workspace)"
readonly CODEX_BIN="$(value codex_bin)"
readonly SANDBOX="$(value sandbox)"
readonly APPROVAL_POLICY="$(value approval_policy)"
readonly WORKSPACE_NEW_PROJECT_SKILL="$(value workspace_new_project_skill)"

[[ -x "${PYTHON_BIN}" && -f "${GUARD}" && ! -L "${GUARD}" ]] || exit 64
exec "${PYTHON_BIN}" "${GUARD}" \
  --workspace "${WORKSPACE}" \
  --codex-bin "${CODEX_BIN}" \
  --sandbox "${SANDBOX}" \
  --approval-policy "${APPROVAL_POLICY}" \
  --workspace-new-project-skill "${WORKSPACE_NEW_PROJECT_SKILL}"
