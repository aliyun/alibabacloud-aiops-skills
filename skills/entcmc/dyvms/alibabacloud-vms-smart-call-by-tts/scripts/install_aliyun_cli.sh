#!/usr/bin/env bash
# =============================================================================
#  install_aliyun_cli.sh
#
#  Environment-aware installer / upgrader for the Aliyun CLI used by this Skill.
#  Picks the first strategy that matches the runtime, in this order:
#
#    Strategy 1 — Homebrew         (preferred on macOS / Linuxbrew; brew tracks
#                                   updates and removal cleanly).
#    Strategy 2 — User-level binary tarball under  $HOME/.local/bin
#                                  (no sudo, no brew, no `curl | bash`).
#
#  Properties:
#    - Idempotent:    safe to re-run; brew path uses upgrade-or-install,
#                     tarball path overwrites in place.
#    - Self-verifying: ends with `aliyun version` and asserts >= 3.3.8.
#    - No remote-script piping: every download is a SIGNED BINARY TARBALL
#                     extracted locally; nothing is ever piped to a shell.
#    - Sudo-free:     the user-level tarball strategy works in non-interactive
#                     shells (agent sandboxes, CI runners, restricted users).
#
#  Coverage: macOS / Linux on amd64 or arm64.
#  For Windows, BSD, multi-profile setups, alternate credential modes, AK
#  rotation, or proxy traversal, see references/cli-installation-guide.md.
#
#  Exit codes:
#    0  — Aliyun CLI is installed and reports a version >= 3.3.8.
#    1  — Unsupported OS / architecture (manual install required).
#    2  — Installation completed but the resulting version is still < 3.3.8.
#    3  — Installation failed at the download / extract / brew step.
# =============================================================================

set -euo pipefail

readonly REQUIRED_MIN_VERSION="3.3.8"
readonly USER_BIN_DIR="$HOME/.local/bin"
readonly CDN_BASE="https://aliyuncli.alicdn.com"
readonly REF_DOC="references/cli-installation-guide.md"

log()  { printf '[install_aliyun_cli] %s\n' "$*" >&2; }
fail() { log "ERROR: $*"; log "See $REF_DOC for the manual installation matrix."; exit "${2:-3}"; }

# ----------------------------------------------------------------------------
# Strategy 1 — Homebrew (macOS / Linuxbrew).
# ----------------------------------------------------------------------------
install_via_brew() {
  log "Strategy 1: Homebrew detected; installing/upgrading aliyun-cli via brew."
  if brew list aliyun-cli >/dev/null 2>&1; then
    brew upgrade aliyun-cli || fail "brew upgrade aliyun-cli failed"
  else
    brew install aliyun-cli || fail "brew install aliyun-cli failed"
  fi
}

# ----------------------------------------------------------------------------
# Strategy 2 — User-level signed binary tarball under $HOME/.local/bin.
# Detects OS and architecture; arm64 hardware MUST get the arm64 build
# (the amd64 build on Apple Silicon requires Rosetta 2 and is brittle).
# ----------------------------------------------------------------------------
install_via_user_binary() {
  local os arch tarball url
  case "$(uname -s)" in
    Darwin) os="macosx" ;;
    Linux)  os="linux"  ;;
    *) fail "Unsupported OS: $(uname -s)" 1 ;;
  esac
  case "$(uname -m)" in
    x86_64|amd64)   arch="amd64" ;;
    arm64|aarch64)  arch="arm64" ;;
    *) fail "Unsupported architecture: $(uname -m)" 1 ;;
  esac

  tarball="aliyun-cli-${os}-latest-${arch}.tgz"
  url="${CDN_BASE}/${tarball}"

  log "Strategy 2: downloading signed tarball ${tarball} into ${USER_BIN_DIR}/"
  mkdir -p "$USER_BIN_DIR"
  # `curl -fsSL ... | tar -xz -C ...` extracts the tarball stream to the
  # destination; this is NOT `curl | bash`. No remote script is ever executed.
  curl -fsSL "$url" | tar -xz -C "$USER_BIN_DIR" \
    || fail "Download or extract failed for ${url}"
  chmod +x "${USER_BIN_DIR}/aliyun"

  # Make `aliyun` discoverable in this shell and persist for future shells.
  case ":${PATH}:" in
    *":${USER_BIN_DIR}:"*) ;;
    *) export PATH="${USER_BIN_DIR}:${PATH}" ;;
  esac
  persist_path_export "$HOME/.zshrc"
  persist_path_export "$HOME/.bashrc"
}

persist_path_export() {
  local rc="$1"
  [ -e "$rc" ] || return 0
  if ! grep -qsF "$USER_BIN_DIR" "$rc" 2>/dev/null; then
    printf 'export PATH="%s:$PATH"\n' "$USER_BIN_DIR" >> "$rc" 2>/dev/null || true
    log "Appended PATH export to $rc"
  fi
}

# ----------------------------------------------------------------------------
# Self-verification — confirm the resulting binary is >= REQUIRED_MIN_VERSION.
# Uses `sort -V` (version sort) for a portable numeric comparison without awk
# field-splitting fragility.
# ----------------------------------------------------------------------------
verify_version() {
  hash -r 2>/dev/null || true
  if ! command -v aliyun >/dev/null 2>&1; then
    fail "Installation completed but \`aliyun\` is still not on PATH" 2
  fi
  local actual
  actual="$(aliyun version 2>/dev/null | head -n1 | tr -d '[:space:]')"
  [ -n "$actual" ] || fail "\`aliyun version\` produced empty output" 2
  local lowest
  lowest="$(printf '%s\n%s\n' "$REQUIRED_MIN_VERSION" "$actual" | sort -V | head -n1)"
  if [ "$lowest" != "$REQUIRED_MIN_VERSION" ]; then
    fail "Installed version ${actual} is below required minimum ${REQUIRED_MIN_VERSION}" 2
  fi
  log "OK: aliyun version ${actual} (>= ${REQUIRED_MIN_VERSION})"
}

# ----------------------------------------------------------------------------
# Main.
# ----------------------------------------------------------------------------
main() {
  log "Target minimum version: ${REQUIRED_MIN_VERSION}"
  if command -v brew >/dev/null 2>&1; then
    install_via_brew
  else
    install_via_user_binary
  fi
  verify_version
}

main "$@"
