#!/usr/bin/env bash
# 00_detect_env.sh — detect/install the local toolchain (conda, aliyun CLI),
# select a Python >= 3.10 environment, verify cloud credentials.
# Everything idempotent; results persisted into the skill state directory.
set -euo pipefail
cd "$(dirname "$0")"
source lib/common.sh

# E2E_FRESH=1: start a from-zero run — wipe business state from any previous
# run (env.sh keys like E2E_RAM_APP_ID leak via load_e2e_env otherwise).
# The wheels cache is kept (crcmod manylinux wheel is unobtainable elsewhere).
if [ "${E2E_FRESH:-0}" = "1" ]; then
  reset_e2e_state
fi

log_info "=== environment detection ==="

# --- conda -------------------------------------------------------------------
if ! conda_root >/dev/null 2>&1; then
  log_info "conda not found — installing miniforge via Homebrew..."
  command -v brew >/dev/null 2>&1 || fail "Homebrew not found; install conda manually and re-run"
  brew install --cask miniforge
fi
CONDA_ROOT=$(conda_root) || fail "conda still unavailable after install attempt"
log_ok "conda root: $CONDA_ROOT"

# --- select a python >= 3.10 env ----------------------------------------------
PY=""
if "$CONDA_ROOT/bin/python3" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
  PY="$CONDA_ROOT/bin"
  echo "base" > "$CONDA_ENV_FILE"
else
  for envdir in "$CONDA_ROOT"/envs/*/bin; do
    if [ -x "$envdir/python3" ] && "$envdir/python3" -c 'import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)' 2>/dev/null; then
      PY="$envdir"
      echo "$(basename "$(dirname "$envdir")")" > "$CONDA_ENV_FILE"
      break
    fi
  done
fi
if [ -z "$PY" ]; then
  log_info "no python>=3.10 env — creating 'agent-e2e' (python=3.11)..."
  "$CONDA_ROOT/bin/conda" create -y -n agent-e2e python=3.11 >/dev/null 2>&1 || fail "conda create failed"
  echo "agent-e2e" > "$CONDA_ENV_FILE"
  PY="$CONDA_ROOT/envs/agent-e2e/bin"
fi
log_ok "python: $PY/python3 ($("$PY/python3" -V 2>&1))"

# --- aliyun CLI ----------------------------------------------------------------
if ! command -v aliyun >/dev/null 2>&1 && ! [ -x "$HOME/bin/aliyun" ]; then
  log_info "aliyun CLI not found — installing via Homebrew..."
  brew install aliyun-cli
fi
if ! command -v aliyun >/dev/null 2>&1 && [ -x "$HOME/bin/aliyun" ]; then
  export PATH="$HOME/bin:$PATH"
fi
command -v aliyun >/dev/null 2>&1 || fail "aliyun CLI unavailable after install attempt"

# Plugin-mode commands (kebab-case) need a recent CLI, and the plugins must be
# present BEFORE the first call: the CLI otherwise prompts to install them and
# a non-interactive shell dies on "failed to read user input: EOF".
require_cli_version
ensure_cli_plugins

# --- credentials (CLI-first) -----------------------------------------------------
init_conda >/dev/null 2>&1 || true
verify_cli

log_ok "observability session id: $(skill_session_id)"
log_ok "environment ready (state: $STATE_DIR)"
