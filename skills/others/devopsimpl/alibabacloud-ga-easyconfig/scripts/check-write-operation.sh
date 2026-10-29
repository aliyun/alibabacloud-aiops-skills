#!/bin/bash
# check-write-operation.sh
# Intercept Alibaba Cloud CLI write operations and require user confirmation.
#
# Dependencies (minimum versions):
#   - bash >= 4.0
#   - python3 >= 3.6
#   - jq >= 1.5
#
# Classification is fail-safe: every aliyun invocation whose action is not a
# known read verb (describe/list/get/query) is treated as a write operation and
# requires user confirmation. Aliyun commands invoked anywhere in a compound
# command line (pipes, &&, ;, sudo) are classified, not only a leading one.

set -euo pipefail

check_dependency() {
  local cmd="$1"
  local min_version="$2"
  local version_output="$3"

  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "ERROR: required dependency '$cmd' is not installed" >&2
    exit 1
  fi

  local version
  version=$(printf '%s\n' "$version_output" | grep -oE '[0-9]+\.[0-9]+(\.[0-9]+)?' | head -n1 || true)
  if [ -z "$version" ]; then
    echo "WARNING: unable to determine version of '$cmd'; continuing" >&2
    return 0
  fi

  if [ "$(printf '%s\n%s\n' "$min_version" "$version" | sort -V | head -n1)" != "$min_version" ]; then
    echo "ERROR: '$cmd' version $version is older than required $min_version" >&2
    exit 1
  fi
}

check_dependency bash 4.0 "$BASH_VERSION"
check_dependency python3 3.6 "$(python3 --version 2>&1 || true)"
check_dependency jq 1.5 "$(jq --version 2>&1 || true)"

INPUT=$(cat)

python3 - "$INPUT" <<'PY'
import json
import re
import shlex
import sys

READ_VERBS = {"describe", "list", "get", "query"}
IRREVERSIBLE_VERBS = {"delete", "remove", "release", "revoke", "downgrade"}
ACTION_RE = re.compile(r"^[a-z][a-z0-9]*(?:-[a-z0-9]+)+$")
SEGMENT_SPLIT = re.compile(r"\|\||&&|;|\||\n")


def emit(decision, reason):
    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": decision,
            "permissionDecisionReason": reason,
        }
    }))
    sys.exit(0)


raw = sys.argv[1] if len(sys.argv) > 1 else ""
try:
    payload = json.loads(raw) if raw.strip() else {}
except json.JSONDecodeError:
    emit("ask", "Unable to parse the hook payload; user confirmation required.")

command = ""
if isinstance(payload, dict):
    tool_input = payload.get("tool_input") or {}
    if isinstance(tool_input, dict):
        command = tool_input.get("command") or ""

if not command.strip():
    emit("allow", "No shell command to inspect; no confirmation needed.")


def tokenize(segment):
    try:
        return shlex.split(segment, comments=False, posix=True)
    except ValueError:
        return segment.split()


def find_action(tokens):
    index = None
    for position, token in enumerate(tokens):
        if token.rsplit("/", 1)[-1] == "aliyun":
            index = position
            break
    if index is None:
        return None

    candidates = []
    expect_value = False
    for token in tokens[index + 1:]:
        if expect_value:
            expect_value = False
            continue
        if token.startswith("-"):
            expect_value = True
            continue
        candidates.append(token)

    # The first candidate is the service (ga, ecs, ...); the action is the first
    # candidate that looks like a hyphenated CLI action.
    for candidate in candidates[1:]:
        if ACTION_RE.match(candidate):
            return candidate
    return None


actions = []
for segment in SEGMENT_SPLIT.split(command):
    tokens = tokenize(segment.strip())
    while tokens and tokens[0] in ("sudo", "env", "command"):
        tokens = tokens[1:]
    if not tokens:
        continue
    if any(t.rsplit("/", 1)[-1] == "aliyun" for t in tokens):
        actions.append(find_action(tokens))

if not actions:
    emit("allow", "No aliyun CLI invocation detected; no confirmation needed.")

if any(a is None or not ACTION_RE.match(a) for a in actions):
    emit("ask", "Aliyun CLI invocation detected but its action could not be identified; user confirmation required before execution.")

verbs = {a: a.split("-")[0] for a in actions}
writes = sorted({a for a, v in verbs.items() if v not in READ_VERBS})

if not writes:
    emit("allow", "Read-only aliyun operation (%s); no confirmation needed." % ", ".join(sorted(set(actions))))

irreversible = sorted({a for a, v in verbs.items() if v in IRREVERSIBLE_VERBS})
reason = "Write operation (%s) requires user confirmation before execution." % ", ".join(writes)
if irreversible:
    reason += " Includes irreversible operations (%s)." % ", ".join(irreversible)
emit("ask", reason)
PY
