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

# State

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

# CLI calls use the configured profile; SDK calls use the default credential
# chain. Ensure both resolve to the intended account; environment overrides can
# change the SDK identity.
# No separate secrets file is used; scripts do not accept or log AccessKey values.

# Constants

SKILL_NAME="alibabacloud-agent-identity-agentrun-e2e"
SKILL_LIB_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SKILL_MANIFEST_FILE="$SKILL_LIB_DIR/../../references/manifest.json"

# Minimum aliyun CLI version: plugin-mode commands (kebab-case, e.g.
# `aliyun sts get-caller-identity`) and `aliyun plugin install` need 3.3.3+.
MIN_CLI_VERSION="3.3.3"

# CLI plugins whose commands this skill calls. A bash array, iterated as
# "${CLI_PLUGINS[@]}": never a space-separated string relying on word
# splitting, which silently collapses to a single element under zsh.
CLI_PLUGINS=(aliyun-cli-sts aliyun-cli-ram)

PYPI_MIRROR="https://mirrors.aliyun.com/pypi/simple/"

# Common conda installation locations.
CONDA_PATHS=(
  "$HOME/miniforge3/bin/conda"
  "$HOME/miniconda3/bin/conda"
  "$HOME/anaconda3/bin/conda"
  "/opt/homebrew/Caskroom/miniforge/base/bin/conda"
)

skill_version() {
  python3 - "$SKILL_MANIFEST_FILE" <<'PYEOF'
import json, re, sys
try:
    with open(sys.argv[1], encoding="utf-8") as handle:
        version = json.load(handle)["version"]
    if not isinstance(version, str) or not re.fullmatch(r"[0-9]+\.[0-9]+\.[0-9]+(?:[-+][0-9A-Za-z.+-]+)?", version):
        raise ValueError("version must be a semantic version string")
except (OSError, UnicodeError, ValueError, KeyError, TypeError) as error:
    sys.exit(f"[FAIL] Cannot read references/manifest.json: {error}")
print(version)
PYEOF
}

# Observability

# skill_session_id: one id per e2e run, shared by every script through the
# state dir so all cloud calls of a run correlate. Precedence:
#   caller-provided SKILL_SESSION_ID -> cached id -> newly generated one.
# reset_e2e_state drops the cached id, so E2E_FRESH=1 starts a new session.
skill_session_id() {
  local id="${SKILL_SESSION_ID:-}"
  if [ -z "$id" ] && [ -s "$SESSION_ID_FILE" ]; then
    id=$(cat "$SESSION_ID_FILE")
  fi
  if [ -z "$id" ]; then
    id=$(python3 -c 'import secrets; print(secrets.token_hex(16))') || return 1
  fi
  [[ "$id" =~ ^[0-9a-f]{32}$ ]] || fail "skill session ID must be 32 lowercase hexadecimal characters"
  printf '%s\n' "$id" > "$SESSION_ID_FILE"
  printf '%s\n' "$id"
}

# ua_string: the User-Agent every CLI and SDK call of this skill carries.
# Template: AlibabaCloud-Agent-Skills/<skill-name>/<session-id>
ua_string() {
  local version session_id
  version=$(skill_version) || return 1
  session_id=$(skill_session_id) || return 1
  printf 'AlibabaCloud-Agent-Skills/%s/%s skill-version/%s\n' "$SKILL_NAME" "$session_id" "$version"
}

# Logging (stderr only)

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

# Project location

# Override the sample directory name with E2E_SAMPLE_NAME when needed.
# The resolver reads this value for each call.

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
    # The Skill directory and kit repository may be siblings.
    # Implemented with find instead of bare globs: zsh aborts on non-matching globs
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
  echo "  If the sample uses a different directory name, set E2E_SAMPLE_NAME accordingly." >&2
  exit 1
}

# State helpers

# save_kv <key> <value>: persist a non-secret value into the state env file.
save_kv() {
  local key="$1" value="$2" escaped_value
  mkdir -p "$STATE_DIR"
  touch "$ENV_FILE"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    # Preserve literal URL characters when replacing an existing state value.
    escaped_value="${value//\\/\\\\}"
    escaped_value="${escaped_value//&/\\&}"
    escaped_value="${escaped_value//|/\\|}"
    sed -i '' "s|^${key}=.*|${key}=${escaped_value}|" "$ENV_FILE" 2>/dev/null \
      || sed -i "s|^${key}=.*|${key}=${escaped_value}|" "$ENV_FILE"
  else
    printf '%s=%s\n' "$key" "$value" >> "$ENV_FILE"
  fi
}

# reset_e2e_state: clear settings and artifacts for a new run.
# Keep the project path, selected conda environment, and reusable wheel cache.
# Preserve pending resource records until cleanup completes.
reset_e2e_state() {
  if grep -Eq '^E2E_CREATED_(OSS_BUCKET|OSS_OBJECT|CEDAR)=.+' "$ENV_FILE" 2>/dev/null; then
    fail "cleanup pending; existing creation records were preserved"
  fi
  unset SKILL_SESSION_ID
  rm -f "$ENV_FILE" "$SESSION_ID_FILE" "$STATE_DIR"/*.zip "$STATE_DIR"/probe.json 2>/dev/null
  log_ok "state reset: env.sh, session id and prior build artifacts removed (wheels cache kept)"
}

# load_e2e_env: load saved non-secret values when environment values are unset
# or empty. Read each line at the first '=' to preserve URL query parameters
# and other values containing '='.
load_e2e_env() {
  local key val
  if [ -f "$ENV_FILE" ]; then
    while IFS='=' read -r key val; do
      case "$key" in ''|\#*) continue ;; esac
      if [ -z "${!key:-}" ]; then
        export "$key=$val"
      fi
    done < "$ENV_FILE"
  fi
  export AGENTRUN_REGION="${AGENTRUN_REGION:-cn-hangzhou}"
  export E2E_OSS_REGION="${E2E_OSS_REGION:-cn-hangzhou}"
}

# Cloud CLI

ALIYUN="${ALIYUN:-aliyun}"

# cli_version: the CLI's semantic version (e.g. 3.3.15), empty if unparsable.
cli_version() {
  # Read all output to avoid SIGPIPE when the CLI also prints usage text.
  "$ALIYUN" --version 2>&1 | sed -n '1p' | sed -E 's/[^0-9]*([0-9]+\.[0-9]+\.[0-9]+).*/\1/'
}

# require_cli_version: enforce MIN_CLI_VERSION. Plugin-mode commands do not
# exist on older CLIs, so this is a hard gate rather than a warning.
require_cli_version() {
  local have
  have=$(cli_version)
  [ -n "$have" ] || fail "cannot parse the aliyun CLI version ('$ALIYUN --version')"
  # sort -V puts the smaller version first; reject versions below the minimum.
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
# Avoid `aliyun plugin list`: that call reaches the network, and a
# transient failure there would make an installed plugin look missing.
cli_plugin_installed() {
  [ -x "${HOME}/.aliyun/plugins/$1/$1" ]
}

# ensure_cli_plugins: make plugin-mode commands safe to call.
#
# With a plugin absent, the CLI asks "Do you want to
# install it? [Y/n]" and then aborts with "failed to read user input: EOF" in a
# non-interactive shell. Two layers guard against it:
#   1. auto_plugin_install=true in the CLI profile — the only thing that
#      suppresses the prompt. Set it in the profile before installing plugins.
#      The setting persists; Phase 1 explains the change to the user.
#      `aliyun configure set --auto-plugin-install false` undoes it.
#   2. a best-effort pre-install, so the first cloud call is not slowed down.
# A failed pre-install is a warning: layer 1 still covers it, and
# the subsequent cloud call reports any remaining error.
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
# not read directly from the profile by this skill. For required RAM operations,
# use a profile with the permissions listed in references/ram-policies.md.
# Commands use plugin mode (kebab-case); ensure_cli_plugins must have run.
verify_cli() {
  command -v "$ALIYUN" >/dev/null 2>&1 || \
    fail "aliyun CLI not found. Install it first: brew install aliyun-cli"
  local out account ua
  ua=$(ua_string) || fail "cannot initialize cloud request attribution"
  out=$("$ALIYUN" sts get-caller-identity --user-agent "$ua" 2>&1) || {
    log_fail "aliyun CLI call failed:"
    echo "$out" >&2
    echo "  Fix: run 'aliyun configure' (AK mode), then re-run this script." >&2
    exit 1
  }
  account=$(echo "$out" | sed -n 's/.*"AccountId": *"\([0-9]*\)".*/\1/p')
  [ -n "$account" ] || fail "Could not parse AccountId from sts get-caller-identity"
  save_kv ACCOUNT_ID "$account"
  log_ok "CLI verified (account ${account})"
}

# oss_provider_snippet: emit the Python preamble that lets oss2 authenticate
# through the SDK credential chain. ProviderAuthV4 retrieves credentials from
# the SDK client instead of accepting credential values as script parameters.
# Consumers use: auth = oss_auth(); oss2.Bucket(auth, endpoint, name, region=...)
oss_provider_snippet() {
  cat <<'PYEOF'
import os
import oss2
from oss2.credentials import Credentials, CredentialsProvider
from alibabacloud_credentials.client import Client as _CredClient


class CliProfileCredentialsProvider(CredentialsProvider):
    """Adapt SDK-resolved credentials for oss2 without credential parameters."""

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
# failing on `import alibabacloud_credentials`.
ensure_oss_deps() {
  python3 -c "import oss2, alibabacloud_credentials" 2>/dev/null && return 0
  python3 -m pip install -q oss2 alibabacloud-credentials \
    || fail "failed to install the OSS dependencies (oss2, alibabacloud-credentials)"
}

# py_sdk <script.py> [args...]: run python with the e2e SDK deps available
# (auto-installed into the active conda env on first use; idempotent).
# Credentials are resolved by the SDK's default chain; see Execution Rule 3
# in SKILL.md for the intended account requirement.
# SKILL_UA / SKILL_SESSION_ID are exported so scripts can tag their SDK calls.
# Tea SDK interfaces:
#   methods are snake_case (get_identity_provider, list_policies ...);
#   arguments MUST be XxxRequest objects built with snake_case fields —
#   passing a bare string raises 'str' object has no attribute 'validate';
#   read responses via resp.body; to_map() uses the API's response field names.
py_sdk() {
  init_conda || fail "conda env unavailable — run scripts/00_detect_env.sh first"
  export SKILL_SESSION_ID
  SKILL_SESSION_ID=$(skill_session_id) || fail "cannot initialize the skill session"
  export SKILL_UA
  SKILL_UA=$(ua_string) || fail "cannot initialize cloud request attribution"
  python3 -c "import alibabacloud_agentidentity20250901" 2>/dev/null || \
    python3 -m pip install -q alibabacloud-agentidentity20250901 alibabacloud-ram20150501 \
      alibabacloud-ims20190815 \
      || fail "failed to install AgentIdentity SDK"
  python3 "$@"
}

# Conda

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


current_cli_account() {
  local identity ua
  ua=$(ua_string) || fail "cannot initialize cloud request attribution"
  identity=$("$ALIYUN" sts get-caller-identity --user-agent "$ua") \
    || fail "cannot verify the active CLI account"
  printf '%s' "$identity" | python3 -c 'import json,sys; account=json.load(sys.stdin).get("AccountId"); sys.exit("AccountId missing from STS response") if not account else print(account)'
}

# Emit the fixed creation markers used by the OSS and Cedar scripts.
created_state_snippet() {
  cat <<'PYEOF'
import json
import os
from pathlib import Path
import subprocess

_created_fields = {
    "E2E_CREATED_OSS_BUCKET": 3,
    "E2E_CREATED_OSS_OBJECT": 4,
    "E2E_CREATED_CEDAR": 5,
}
_created = {}
for line in Path(os.environ["E2E_ENV_FILE"]).read_text().splitlines():
    key, separator, value = line.partition("=")
    if separator and key in _created_fields and value:
        record = json.loads(value)
        if (not isinstance(record, list) or len(record) != _created_fields[key]
                or not all(isinstance(item, str) and item for item in record)
                or record[0] != os.environ["ACCOUNT_ID"]):
            raise RuntimeError("Created-resource record is invalid or belongs to another account")
        _created[key] = record


def created_here(key, region, *names):
    return _created.get(key) == [os.environ["ACCOUNT_ID"], region, *names]


def save_created(key, region=None, *names):
    record = [os.environ["ACCOUNT_ID"], region, *names] if region else None
    if key not in _created_fields or (record and len(record) != _created_fields[key]):
        raise RuntimeError("Invalid created-resource key or identifiers")
    value = json.dumps(record, ensure_ascii=True, separators=(",", ":")) if record else ""
    subprocess.run(["bash", "-c", 'source "$1"; save_kv "$2" "$3"',
                    "e2e-state", os.environ["E2E_COMMON_FILE"], key, value], check=True)
    if record:
        _created[key] = record
    else:
        _created.pop(key, None)
PYEOF
}

# Verify the account before creating or deleting recorded test resources.
prepare_created_state() {
  local active_account
  active_account=$(current_cli_account) || fail "cannot verify resource ownership"
  [ "$active_account" = "${ACCOUNT_ID:-}" ] \
    || fail "active CLI account differs from saved state; no resource was changed"
  export ACCOUNT_ID E2E_ENV_FILE E2E_COMMON_FILE SKILL_UA
  E2E_ENV_FILE="$ENV_FILE"
  E2E_COMMON_FILE="$SKILL_LIB_DIR/common.sh"
  SKILL_UA=$(ua_string) || fail "cannot initialize cloud request attribution"
  touch "$ENV_FILE"
  created_state_snippet | python3 - || fail "created-resource state is invalid"
}

initialize_skill_observability() {
  ua_string >/dev/null || fail "cannot initialize cloud request attribution"
}

# Restore the saved Python environment when it is already available.
init_conda >/dev/null 2>&1 || true
