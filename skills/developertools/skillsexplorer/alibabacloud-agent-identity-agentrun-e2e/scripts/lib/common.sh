# shellcheck shell=bash
# Common utilities for the alibabacloud-agent-identity-agentrun-e2e skill.
# Sourced by all scripts in this skill; do not execute directly.
#
# Design notes:
# - All log lines go to stderr so that $(...) command substitution stays clean.
# - Never print credential values. Checks are non-empty tests only.
# - Scripts run in fresh shells every time; durable state lives under
#   STATE_DIR, not in exported environment variables.
# - The sample code lives in the agent-identity-dev-kit repo
#   (agent_identity_python_samples/agentrun-e2e_sample); scripts locate it
#   via resolve_project_dir (Phase 0 caches the path).

# --- State ---------------------------------------------------------------

STATE_DIR="${TMPDIR:-/tmp}"
STATE_DIR="${STATE_DIR%/}/alibabacloud-agent-identity-agentrun-e2e"  # ${TMPDIR%/} strips the trailing slash macOS ships
# Created here, at source time, because some state files are written directly
# rather than through the save_* helpers: 00_detect_env.sh records the conda env
# name before any helper runs, so on a first run the directory would not exist.
mkdir -p "$STATE_DIR" || { echo "[FAIL] cannot create the state directory: $STATE_DIR" >&2; exit 1; }
STATE_FILE="$STATE_DIR/project_dir"     # caches the located agentrun-e2e_sample dir
ENV_FILE="$STATE_DIR/env.sh"            # non-secret runtime values (endpoint, names...)
CONDA_ENV_FILE="$STATE_DIR/conda_env"   # selected conda env name (default: base)
SESSION_ID_FILE="$STATE_DIR/session_id" # observability session id, stable per run

# Cloud credentials come from the aliyun CLI profile ("CLI-first", verified
# in the field). There is NO secrets file in this skill, and no script ever
# reads, exports or prints an AccessKey pair: the CLI resolves credentials for
# its own calls, and Python SDKs resolve them through the credential chain's
# cli_profile provider (see py_sdk and oss_provider_snippet below).

# --- Constants -------------------------------------------------------------

SKILL_NAME="alibabacloud-agent-identity-agentrun-e2e"

# Minimum aliyun CLI version: plugin-mode commands (kebab-case, e.g.
# `aliyun sts get-caller-identity`) and `aliyun plugin install` need 3.3.3+.
MIN_CLI_VERSION="3.3.3"

# CLI plugins whose commands this skill calls. A bash array, iterated as
# "${CLI_PLUGINS[@]}": never a space-separated string relying on word
# splitting, which silently collapses to a single element under zsh.
CLI_PLUGINS=(aliyun-cli-sts aliyun-cli-ram)

# Regions. AgentRun / AgentIdentity GA: cn-hangzhou default.
AGENTRUN_REGION="${AGENTRUN_REGION:-cn-hangzhou}"
E2E_OSS_REGION="${E2E_OSS_REGION:-cn-hangzhou}"

PYPI_MIRROR="https://mirrors.aliyun.com/pypi/simple/"

# Common conda installation locations.
CONDA_PATHS=(
  "$HOME/miniforge3/bin/conda"
  "$HOME/miniconda3/bin/conda"
  "$HOME/anaconda3/bin/conda"
  "/opt/homebrew/Caskroom/miniforge/base/bin/conda"
)

# --- Observability ---------------------------------------------------------

# skill_session_id: one id per e2e run, shared by every script through the
# state dir so all cloud calls of a run correlate. Precedence:
#   caller-provided SKILL_SESSION_ID -> cached id -> newly generated one.
# reset_e2e_state drops the cached id, so E2E_FRESH=1 starts a new session.
skill_session_id() {
  if [ -n "${SKILL_SESSION_ID:-}" ]; then
    echo "$SKILL_SESSION_ID"
    return 0
  fi
  if [ -s "$SESSION_ID_FILE" ]; then
    cat "$SESSION_ID_FILE"
    return 0
  fi
  local id
  id=$(uuidgen 2>/dev/null | tr '[:upper:]' '[:lower:]')
  [ -n "$id" ] || id="$(date +%Y%m%d%H%M%S)-$$"
  mkdir -p "$STATE_DIR"
  echo "$id" > "$SESSION_ID_FILE"
  echo "$id"
}

# ua_string: the User-Agent every CLI and SDK call of this skill carries.
# Template: AlibabaCloud-Agent-Skills/<skill-name>/<session-id>
ua_string() {
  echo "AlibabaCloud-Agent-Skills/${SKILL_NAME}/$(skill_session_id)"
}

# --- Logging (stderr only) -------------------------------------------------

log_ok()   { echo "[OK] $*" >&2; }
log_skip() { echo "[SKIP] $*" >&2; }
log_warn() { echo "[WARN] $*" >&2; }
log_info() { echo "[INFO] $*" >&2; }
log_fail() { echo "[FAIL] $*" >&2; }

# fail <message>: report and stop. Per the skill's Execution Rules, a failed
# command is reported to the user and never retried automatically.
fail() {
  log_fail "$*"
  exit 1
}

# --- Project location --------------------------------------------------------

# The sample directory name can be overridden: the team's uploaded kit repo
# may use a different one. Export E2E_SAMPLE_NAME=<actual-dir-name>; it takes
# effect per call, and is fixed at source time when this file is sourced.

# is_valid_project_dir <dir>: the sample feature files must exist.
is_valid_project_dir() {
  local dir="$1"
  [ -f "$dir/main.py" ] &&
    [ -f "$dir/requirements.txt" ]
}

# resolve_project_dir: locate the user's agentrun-e2e_sample directory.
# Order: cached state file -> walk upward from cwd -> shallow search under cwd.
resolve_project_dir() {
  local cached dir found
  local sample_name="${E2E_SAMPLE_NAME:-agentrun-e2e_sample}"

  if [ -f "$STATE_FILE" ]; then
    cached=$(cat "$STATE_FILE")
    if is_valid_project_dir "$cached"; then
      echo "$cached"
      return 0
    fi
    log_warn "Cached project dir is no longer valid: $cached"
  fi

  dir="$PWD"
  while [ "$dir" != "/" ]; do
    if is_valid_project_dir "$dir/agent_identity_python_samples/$sample_name"; then
      echo "$dir/agent_identity_python_samples/$sample_name"
      return 0
    fi
    if is_valid_project_dir "$dir/$sample_name"; then
      echo "$dir/$sample_name"
      return 0
    fi
    # sibling-repo layout: <dir>/<any-repo>/agent_identity_python_samples/<sample>
    # (skill dir and kit repo side by side — field-verified).
    # Implemented with find, NOT bare globs: zsh aborts on non-matching globs
    # ("no matches found") while bash passes the literal through — find is
    # shell-neutral.
    _sib=$(find "$dir" -maxdepth 3 -type d -path "*/agent_identity_python_samples/$sample_name" 2>/dev/null | head -1)
    if [ -n "$_sib" ] && is_valid_project_dir "$_sib"; then
      echo "$_sib"
      return 0
    fi
    dir=$(dirname "$dir")
  done

  found=$(find "$PWD" -maxdepth 6 -type d -name "$sample_name" \
            -path "*agent_identity_python_samples*" 2>/dev/null | head -1)
  if [ -n "$found" ] && is_valid_project_dir "$found"; then
    echo "$found"
    return 0
  fi

  return 1
}

# save_project_dir <dir>: validate, then cache for later sessions.
save_project_dir() {
  local dir="$1"
  if ! is_valid_project_dir "$dir"; then
    fail "Invalid sample dir: $dir
  Expected to find: main.py, requirements.txt"
  fi
  mkdir -p "$STATE_DIR"
  echo "$dir" > "$STATE_FILE"
  log_ok "Project dir saved: $dir"
}

# require_project_dir: resolve or stop with guidance for the agent.
require_project_dir() {
  local dir
  if dir=$(resolve_project_dir); then
    echo "$dir"
    return 0
  fi
  log_fail "Cannot locate the sample project (expected name: ${E2E_SAMPLE_NAME:-agentrun-e2e_sample})."
  echo "  Run the skill's Phase 0 first: ask the user for the local path of the sample," >&2
  echo "  or clone https://github.com/aliyun/agent-identity-dev-kit.git" >&2
  echo "  and point the skill at <repo>/agent_identity_python_samples/<sample-dir>." >&2
  echo "  If the team uploaded it under a different name, set E2E_SAMPLE_NAME accordingly." >&2
  exit 1
}

# --- State helpers -----------------------------------------------------------

# save_kv <key> <value>: persist a non-secret value into the state env file.
save_kv() {
  local key="$1" value="$2"
  mkdir -p "$STATE_DIR"
  touch "$ENV_FILE"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i '' "s|^${key}=.*|${key}=${value}|" "$ENV_FILE" 2>/dev/null \
      || sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
  else
    echo "${key}=${value}" >> "$ENV_FILE"
  fi
}

# reset_e2e_state: wipe cross-run business state for a FRESH from-zero run
# (stale env.sh keys from a previous run leak into the next one via
# load_e2e_env — e.g. an old E2E_RAM_APP_ID silently re-triggered the callback
# backfill against the previous run's RAM app). Keeps:
#   - project_dir / conda_env (current toolchain pointers, re-written each run)
#   - wheels/ (crcmod manylinux wheel is unobtainable elsewhere — packaging.md
#     section 4; it is a pure local build cache, carries no cloud state)
# Removes env.sh (all business keys), prior build zip and probe files.
reset_e2e_state() {
  rm -f "$ENV_FILE" "$SESSION_ID_FILE" "$STATE_DIR"/*.zip "$STATE_DIR"/probe.json 2>/dev/null
  log_ok "state reset: env.sh, session id and prior build artifacts removed (wheels cache kept)"
}

# load_e2e_env: export the non-secret values assembled by earlier scripts.
# Caller-provided values WIN over stored state: a variable already set
# in the environment (e.g. E2E_MCP_TOOL passed on the command line) must not
# be silently overridden by a stale stored value (the 08-16 ghost-tool-name
# incident). Values are read line-wise so '=' inside values (URL query keys)
# survives.
load_e2e_env() {
  [ -f "$ENV_FILE" ] || return 0
  local key val
  while IFS='=' read -r key val; do
    case "$key" in ''|\#*) continue ;; esac
    if [ -z "${!key:-}" ]; then
      export "$key=$val"
    fi
  done < "$ENV_FILE"
}

# --- Cloud CLI ----------------------------------------------------------------

ALIYUN="${ALIYUN:-aliyun}"

# cli_version: the CLI's semantic version (e.g. 3.3.15), empty if unparsable.
cli_version() {
  "$ALIYUN" --version 2>&1 | head -1 | sed -E 's/[^0-9]*([0-9]+\.[0-9]+\.[0-9]+).*/\1/'
}

# require_cli_version: enforce MIN_CLI_VERSION. Plugin-mode commands do not
# exist on older CLIs, so this is a hard gate rather than a warning.
require_cli_version() {
  local have
  have=$(cli_version)
  [ -n "$have" ] || fail "cannot parse the aliyun CLI version ('$ALIYUN --version')"
  # sort -V puts the smaller version first; if the minimum wins, we are too old.
  if [ "$(printf '%s\n%s\n' "$MIN_CLI_VERSION" "$have" | sort -V | head -1)" != "$MIN_CLI_VERSION" ]; then
    fail "aliyun CLI $have is older than the required $MIN_CLI_VERSION.
  Upgrade it, then re-run: brew upgrade aliyun-cli
  (without Homebrew, download the latest release from
   https://github.com/aliyun/aliyun-cli/releases and replace the binary.)"
  fi
  log_ok "aliyun CLI $have (>= $MIN_CLI_VERSION)"
}

# cli_plugin_installed <name>: presence check against the CLI's on-disk plugin
# store, testing the BINARY the CLI actually resolves (<dir>/<name>) — a leftover
# directory without the binary yields "plugin binary not found" at call time.
# Deliberately NOT `aliyun plugin list`: that call reaches the network, and a
# transient failure there would make an installed plugin look missing.
cli_plugin_installed() {
  [ -x "${HOME}/.aliyun/plugins/$1/$1" ]
}

# ensure_cli_plugins: make plugin-mode commands safe to call.
#
# The hazard being closed: with a plugin absent, the CLI asks "Do you want to
# install it? [Y/n]" and then aborts with "failed to read user input: EOF" in a
# non-interactive shell. Two layers guard against it:
#   1. auto_plugin_install=true in the CLI profile — the only thing that
#      suppresses the prompt. Field-tested: passing --auto-plugin-install on the
#      command line does NOT suppress it, the profile setting must be written.
#      Persistent and machine-wide, so Phase 1 tells the user (Rule 12);
#      `aliyun configure set --auto-plugin-install false` undoes it.
#   2. a best-effort pre-install, so the first cloud call is not slowed down.
# A failed pre-install is a WARNING, not an error: layer 1 still covers it, and
# the subsequent cloud call reports any genuine problem with real context.
ensure_cli_plugins() {
  local p out
  local -a missing=()

  "$ALIYUN" configure set --auto-plugin-install true >/dev/null 2>&1 \
    && log_ok "CLI auto-plugin-install enabled (no interactive prompt on missing plugins)" \
    || log_warn "could not set auto-plugin-install; a missing plugin may prompt and fail on EOF"

  for p in "${CLI_PLUGINS[@]}"; do
    if cli_plugin_installed "$p"; then
      log_skip "CLI plugin present: $p"
    else
      missing+=("$p")
    fi
  done
  [ "${#missing[@]}" -gt 0 ] || return 0

  log_info "pre-installing CLI plugins: ${missing[*]}"
  out=$("$ALIYUN" plugin install --names "${missing[@]}" 2>&1) || true
  for p in "${missing[@]}"; do
    if cli_plugin_installed "$p"; then
      log_ok "CLI plugin ready: $p"
    else
      log_warn "pre-install of $p did not complete; the CLI will install it on first use"
      echo "$out" | tail -3 >&2
    fi
  done
}

# verify_cli: ensure the aliyun CLI works and capture the account id into the
# state file. Credentials live in the CLI profile (aliyun configure) and are
# never read by this skill. Note: OAuth login mode works for reads but CANNOT
# perform RAM writes (attach-policy-to-role...) — AK mode is required here.
# Commands use plugin mode (kebab-case); ensure_cli_plugins must have run.
verify_cli() {
  command -v "$ALIYUN" >/dev/null 2>&1 || \
    fail "aliyun CLI not found. Install it first: brew install aliyun-cli"
  local out account
  out=$("$ALIYUN" sts get-caller-identity --user-agent "$(ua_string)" 2>&1) || {
    log_fail "aliyun CLI call failed:"
    echo "$out" >&2
    echo "  Fix: run 'aliyun configure' (AK mode), then re-run this script." >&2
    exit 1
  }
  account=$(echo "$out" | sed -n 's/.*"AccountId": "\([0-9]*\)".*/\1/p')
  [ -n "$account" ] || fail "Could not parse AccountId from sts get-caller-identity"
  save_kv ACCOUNT_ID "$account"
  log_ok "CLI verified (account ${account})"
}

# oss_provider_snippet: emit the Python preamble that lets oss2 authenticate
# through the aliyun CLI credential chain. The skill must not handle AccessKey
# material, so the static two-argument oss2 authenticator is not used;
# ProviderAuthV4 pulls each credential from the chain's cli_profile provider
# instead (field-verified against OSS V4 signing).
# Consumers use: auth = oss_auth(); oss2.Bucket(auth, endpoint, name, region=...)
oss_provider_snippet() {
  cat <<'PYEOF'
import os
import oss2
from oss2.credentials import Credentials, CredentialsProvider
from alibabacloud_credentials.client import Client as _CredClient


class CliProfileCredentialsProvider(CredentialsProvider):
    """Feed oss2 from the aliyun CLI credential chain; no AK/SK in this skill."""

    def __init__(self):
        self._client = _CredClient()

    def get_credentials(self):
        c = self._client.get_credential()
        return Credentials(c.access_key_id, c.access_key_secret, c.security_token)


def oss_auth():
    return oss2.ProviderAuthV4(CliProfileCredentialsProvider())


OSS_UA = os.environ.get("SKILL_UA", "")
PYEOF
}

# ensure_oss_deps: install what oss_provider_snippet needs. It imports BOTH
# oss2 and alibabacloud_credentials (it authenticates through the credential
# chain), so both must be probed — guarding on oss2 alone leaves the preamble
# dying on `import alibabacloud_credentials`.
ensure_oss_deps() {
  python3 -c "import oss2, alibabacloud_credentials" 2>/dev/null && return 0
  python3 -m pip install -q oss2 alibabacloud-credentials \
    || fail "failed to install the OSS dependencies (oss2, alibabacloud-credentials)"
}

# py_sdk <script.py> [args...]: run python with the e2e SDK deps available
# (auto-installed into the active conda env on first use; idempotent).
# Credentials are NOT passed in: alibabacloud_credentials.Client() resolves
# them through its chain, whose cli_profile provider reads the same
# ~/.aliyun/config.json profile the CLI uses (verified: the chain reports
# default/cli_profile/static_ak with no ALIBABA_CLOUD_* variable set).
# SKILL_UA / SKILL_SESSION_ID are exported so scripts can tag their SDK calls.
# Tea-SDK calling paradigm (one-shot — never probe blind):
#   methods are snake_case (get_identity_provider, list_policies ...);
#   arguments MUST be XxxRequest objects built with snake_case fields —
#   passing a bare string raises 'str' object has no attribute 'validate';
#   read responses via resp.body.to_map() (camelCase keys).
py_sdk() {
  init_conda || fail "conda env unavailable — run scripts/00_detect_env.sh first"
  export SKILL_SESSION_ID
  SKILL_SESSION_ID=$(skill_session_id)
  export SKILL_UA
  SKILL_UA=$(ua_string)
  python3 -c "import alibabacloud_agentidentity20250901" 2>/dev/null || \
    python3 -m pip install -q alibabacloud-agentidentity20250901 alibabacloud-ram20150501 \
      alibabacloud-ims20190815 \
      || fail "failed to install AgentIdentity SDK"
  python3 "$@"
}

# --- Conda -------------------------------------------------------------------

conda_root() {
  local p
  for p in "${CONDA_PATHS[@]}"; do
    if [ -f "$p" ]; then
      dirname "$(dirname "$p")"
      return 0
    fi
  done
  return 1
}

# init_conda: put the selected conda env's bin dir at the front of PATH.
init_conda() {
  local root env bin
  root=$(conda_root) || return 1
  env="base"
  if [ -f "$CONDA_ENV_FILE" ]; then
    env=$(cat "$CONDA_ENV_FILE")
  fi
  if [ "$env" = "base" ]; then
    bin="$root/bin"
  else
    bin="$root/envs/$env/bin"
  fi
  [ -x "$bin/python3" ] || return 1
  export PATH="$bin:$PATH"
  hash -r 2>/dev/null || true
  return 0
}

# require_vars <name...>: verify variables are set and non-empty (values never printed).
require_vars() {
  local missing=0 var val
  for var in "$@"; do
    val=$(eval echo "\${$var:-}")
    if [ -z "$val" ]; then
      log_fail "MISSING: $var"
      missing=$((missing + 1))
    else
      log_ok "$var"
    fi
  done
  if [ "$missing" -gt 0 ]; then
    fail "$missing required variable(s) missing — fix before proceeding"
  fi
}
