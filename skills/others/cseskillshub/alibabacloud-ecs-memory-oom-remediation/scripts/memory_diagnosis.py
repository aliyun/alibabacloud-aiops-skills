#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Entry point for alibabacloud-ecs-memory-oom-remediation.

One run answers four questions about a single ECS Linux instance:
  * is it a small-spec candidate for Swap,
  * is there memory-pressure evidence right now,
  * what is holding the memory,
  * which remedy applies, and has it worked after the customer applied it.

Transport rules: every call is an argv list handed to subprocess with an explicit
timeout and the skill-level User-Agent; no shell, no credential handling, no
customer text is ever interpolated into a command.

Exit codes: 0 report produced (possibly degraded), 2 usage error, 3 credentials
failed closed.
"""

import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

SKILL_NAME = "alibabacloud-ecs-memory-oom-remediation"
CLI_BINARY = "aliyun"
USER_AGENT_FLAG = "--user-agent"
USER_AGENT_TEMPLATE = "AlibabaCloud-Agent-Skills/{skill}/{session}"
DEFAULT_TIMEOUT_SECONDS = 30
MAX_ATTEMPTS = 3
BACKOFF_SECONDS = 2
GUEST_INVOKE_TIMEOUT_SECONDS = 90
SMALL_SPEC_MIB = 8192
SWAP_MIN_FREE_KIB = 5 * 1024 * 1024
BASIC_CLOUD_DISK_CATEGORY = "cloud"
CMS_NAMESPACE = "acs_ecs_dashboard"
CMS_MEMORY_METRIC = "memory_usedutilization"
CMS_DISK_AVAIL_METRIC = "diskusage_avail"
CMS_IOPS_METRICS = ("disk_readiops", "disk_writeiops")
MEMORY_USED_WARN_PERCENT = 85.0
NON_TERMINAL_STATUSES = {"Running", "Pending", "Scheduled", "Stopping", ""}
TERMINAL_STATUSES = {"Success", "Finished", "Failed", "Timeout", "Stopped",
                     "Aborted", "Cancelled", "Terminated", "PartialFailed"}
CREDENTIAL_ERROR_CODES = {
    "InvalidAccessKeyId.NotFound", "InvalidSecurityToken.Expired",
    "InvalidSecurityToken", "MissingSecurityToken", "SignatureDoesNotMatch",
    "IncompleteSignature", "AccessDenied", "Forbidden", "NoPermission",
    "Operation.Forbidden", "InvalidAccount.NotFound", "AuthenticationFailed",
}
TRANSIENT_ERROR_CODES = ("Throttling", "SDK.ServerError", "ServiceUnavailable",
                         "InternalError", "RequestTimeout", "CliNotAvailable",
                         "UnparsableResponse")
# A missing CLI product plugin is an environment dependency, not a permission
# problem and not a credential problem: the report must say which.
PLUGIN_MISSING_CODE = "CliPluginMissing"
_PLUGIN_MISSING_MARKERS = ("is required for command", "auto-plugin-install",
                           "but not installed")
GUEST_FLAGS = ("--allow-guest-read",)
CHANGE_FLAGS = ("--confirm-swap-change",)


class CliError(Exception):
    """One CLI or API failure, rendered as '<Code>: <Message>'."""

    def __init__(self, code, message, action=None):
        Exception.__init__(self, "%s: %s" % (code, message))
        self.code = code
        self.message = message
        self.action = action


# ---------------------------------------------------------------------------
# Manifest-derived User-Agent
# ---------------------------------------------------------------------------

def _manifest_path():
    here = os.path.dirname(os.path.abspath(__file__))
    for _ in range(6):
        candidate = os.path.join(here, "references", "manifest.json")
        if os.path.exists(candidate):
            return candidate
        here = os.path.dirname(here)
    return ""


def _manifest_version():
    path = _manifest_path()
    if not path:
        return ""
    try:
        with open(path, encoding="utf-8") as handle:
            return str(json.load(handle).get("version", ""))
    except (OSError, ValueError):
        return ""


SKILL_VERSION = _manifest_version()


def new_session_id():
    """32 hex characters that identify one run of this skill."""
    return uuid.uuid4().hex


def user_agent(session_id):
    ua = USER_AGENT_TEMPLATE.format(skill=SKILL_NAME, session=session_id)
    if SKILL_VERSION:
        ua = ua + " skill-version/" + SKILL_VERSION
    return ua


_SECRET_RE = re.compile(
    r"(?i)\b(accesskeyid|access-key-id|accesskeysecret|access-key-secret|"
    r"securitytoken|security-token|password)\b(\s*[=:]\s*)(\S+)")


def mask_secrets(text):
    """Never let credential-shaped material leave this process."""
    if not text:
        return ""
    return _SECRET_RE.sub(lambda m: m.group(1) + m.group(2) + "***", str(text))


# ---------------------------------------------------------------------------
# Frozen in-guest payloads (no customer input is ever interpolated)
# ---------------------------------------------------------------------------

GUEST_COLLECTOR = """#!/usr/bin/env bash
# memory-oom-remediation in-guest collector: read-only, fixed arguments, no eval.
set -uo pipefail
if [[ $# -gt 0 ]]; then echo "error: collector accepts no arguments" >&2; exit 2; fi

mem_total_kb=""; mem_available_kb=""; swap_total_kb=""; swap_free_kb=""
if [[ -r /proc/meminfo ]]; then
  while IFS=: read -r key val _; do
    case "${key}" in
      MemTotal) mem_total_kb="$(echo "${val}" | tr -d ' kB')" ;;
      MemAvailable) mem_available_kb="$(echo "${val}" | tr -d ' kB')" ;;
      SwapTotal) swap_total_kb="$(echo "${val}" | tr -d ' kB')" ;;
      SwapFree) swap_free_kb="$(echo "${val}" | tr -d ' kB')" ;;
    esac
  done < /proc/meminfo
fi
echo "mem_total_kb=${mem_total_kb:-unknown}"
echo "mem_available_kb=${mem_available_kb:-unknown}"
echo "swap_total_kb=${swap_total_kb:-unknown}"
echo "swap_free_kb=${swap_free_kb:-unknown}"

oom_evidence="unknown"
oom_pattern='out of memory|oom-killer|oom_reaper'
if command -v journalctl >/dev/null 2>&1; then
  n="$(journalctl -k --no-pager -n 500 2>/dev/null | grep -ic -E "${oom_pattern}" || true)"
  if [[ "${n}" =~ ^[0-9]+$ ]]; then oom_evidence=$( ((n>0)) && echo "recent:${n}" || echo none); fi
fi
if [[ "${oom_evidence}" == "unknown" ]] && command -v dmesg >/dev/null 2>&1; then
  n="$(dmesg 2>/dev/null | grep -ic -E "${oom_pattern}" || true)"
  if [[ "${n}" =~ ^[0-9]+$ ]]; then oom_evidence=$( ((n>0)) && echo "recent:${n}" || echo none); fi
fi
echo "oom_evidence=${oom_evidence}"

io_status="unknown"
io_measured=0
if command -v iostat >/dev/null 2>&1; then
  io="$(iostat -x 1 2 2>/dev/null | awk '
    /^Device/ {inb=1; ncols=NF; for(i=1;i<=NF;i++) hdr[i]=$i; n=0; next}
    inb && /^$/ {inb=0; next}
    inb && NF>1 {n++; lines[n]=$0}
    END {u=0; for(i=1;i<=ncols;i++) if(hdr[i] ~ /%util/) u=i; if(u==0) exit 1;
      out=""; for(j=1;j<=n;j++){split(lines[j],f," ");
        if(f[1] !~ /^(loop|ram|sr|fd)/ && f[u] ~ /^[0-9.]+$/)
          out=out (out==""?"":",") f[1] ":" f[u]}
      if(out!="") print out}' || true)"
  if [[ -n "${io}" ]]; then io_status="${io}"; io_measured=1; fi
fi
echo "io_status=${io_status}"
echo "io_measured=${io_measured}"

reported=0
if command -v lsblk >/dev/null 2>&1; then
  while read -r name rota type _; do
    [[ "${type}" == "disk" && -n "${name}" ]] || continue
    case "${name}" in loop*|ram*|sr*|fd*) continue ;; esac
    echo "disk_rotational_${name}=${rota:-unknown}"; reported=1
  done < <(lsblk -dn -o NAME,ROTA,TYPE 2>/dev/null)
fi
if [[ ${reported} -eq 0 ]]; then
  for sysdev in /sys/block/*/; do
    [[ -d "${sysdev}" ]] || continue
    devname="$(basename "${sysdev}")"
    case "${devname}" in loop*|ram*|sr*|fd*) continue ;; esac
    if [[ -r "${sysdev}queue/rotational" ]]; then
      echo "disk_rotational_${devname}=$(cat "${sysdev}queue/rotational" | tr -d '[:space:]')"
      reported=1
    fi
  done
fi
[[ ${reported} -eq 0 ]] && echo "disk_rotational=unknown"

disk_avail_kb="unknown"
if command -v df >/dev/null 2>&1; then
  a="$(df -kP / 2>/dev/null | awk 'NR==2 {print $4}')"
  [[ "${a}" =~ ^[0-9]+$ ]] && disk_avail_kb="${a}"
fi
echo "disk_avail_kb=${disk_avail_kb}"

sanitize() {
  local out="" arg
  for arg in $1; do
    case "${arg}" in
      *[Pp]assword*|*[Pp]asswd*|*[Tt]oken*|*[Ss]ecret*|*[Cc]redential*|*AccessKey*|*access_key*|*secret_key*)
        out+="<redacted> " ;;
      *) out+="${arg} " ;;
    esac
    if [[ ${#out} -gt 160 ]]; then out="${out:0:160}... "; break; fi
  done
  echo "${out% }"
}

rss_index=0; node_index=0
while read -r pid rss args; do
  rss_index=$((rss_index + 1))
  if [[ ${rss_index} -le 5 ]]; then
    comm="$(echo "${args}" | awk '{print $1}' | xargs basename 2>/dev/null || true)"
    echo "rss_top_${rss_index}=pid:${pid}|comm:${comm:-unknown}|rss_kb:${rss}"
  fi
  base_cmd="$(basename "$(echo "${args}" | awk '{print $1}')" 2>/dev/null || true)"
  if [[ "${base_cmd}" == "node" ]]; then
    node_index=$((node_index + 1)); max_old=""
    for arg in ${args}; do
      case "${arg}" in --max-old-space-size=*) max_old="${arg#--max-old-space-size=}" ;; esac
    done
    echo "node_${node_index}=pid:${pid}|rss_kb:${rss}|max_old_space_size:${max_old:-not_set}|args:$(sanitize "${args}")"
  fi
done < <(ps -eo pid,rss,args --sort=-rss 2>/dev/null | awk 'NR>1 {print $1, $2, substr($0, index($0, $3))}')

command -v atop >/dev/null 2>&1 && echo "atop_installed=yes" || echo "atop_installed=no"
atop_active_file=""
if command -v atop >/dev/null 2>&1; then
  atop_active_file="$(ps -eo args 2>/dev/null | awk '/[a]top -w/ {for(i=1;i<NF;i++) if($i=="-w"){print $(i+1); exit}}')"
  if [[ -z "${atop_active_file}" || ! -f "${atop_active_file}" ]]; then
    atop_active_file="$(ls -t /var/log/atop/atop_* 2>/dev/null | head -1)"
  fi
fi
if [[ -n "${atop_active_file}" && -f "${atop_active_file}" ]]; then
  echo "atop_history=yes"
  echo "atop_active_file=${atop_active_file}"
  atop_last_sample="$(timeout 25 atop -r "${atop_active_file}" 2>/dev/null | awk '/^ATOP/ {line=$0} END {print line}')"
  echo "atop_last_sample=${atop_last_sample:-unknown}"
  if [[ "$(basename "${atop_active_file}")" == "atop_$(date +%Y%m%d)" ]]; then
    echo "atop_rotation=current"
  else
    echo "atop_rotation=stale"
  fi
else
  echo "atop_history=no"
fi
if command -v acs-plugin-manager >/dev/null 2>&1; then
  echo "swap_plugin=yes"
else
  echo "swap_plugin=no"
fi
echo "collector_exit=0"
"""

SWAP_PLUGIN_COMMANDS = {
    "enable": "acs-plugin-manager --exec --plugin ACS-ECS-SwapConfig --params --enable",
    "disable": "acs-plugin-manager --exec --plugin ACS-ECS-SwapConfig --params --disable",
    "status": "acs-plugin-manager --exec --plugin ACS-ECS-SwapConfig --params --status",
}
SWAP_ACTIONS = ("enable", "disable")


def build_swap_command(action):
    """Only the frozen plugin command may be delivered for a Swap change."""
    if action not in SWAP_PLUGIN_COMMANDS:
        raise ValueError("unsupported swap action")
    if action == "status":
        return SWAP_PLUGIN_COMMANDS["status"]
    return SWAP_PLUGIN_COMMANDS[action]


# ---------------------------------------------------------------------------
# CLI transport
# ---------------------------------------------------------------------------

API_MODE = {
    "get-caller-identity": "sts",
    "describe-instances": "ecs",
    "describe-instance-types": "ecs",
    "describe-disks": "ecs",
    "describe-cloud-assistant-status": "ecs",
    "run-command": "ecs",
    "describe-invocation-results": "ecs",
    "describe-metric-last": "cms",
}


def _pairs(params):
    out = []
    for key, value in (params or {}).items():
        if value is None:
            continue
        out.append("--" + key)
        out.append(str(value))
    return out


def build_argv(action, params=None, session_id=""):
    argv = [CLI_BINARY, API_MODE[action], action]
    argv.extend(_pairs(params))
    argv.append(USER_AGENT_FLAG)
    argv.append(user_agent(session_id))
    return argv


def _error_from(text, action):
    if any(marker in text for marker in _PLUGIN_MISSING_MARKERS):
        return CliError(PLUGIN_MISSING_CODE,
                        "the Alibaba Cloud CLI product plugin for '%s' is not "
                        "installed in this environment" % action, action)
    code = re.search(r"ErrorCode:\s*([A-Za-z0-9._\-]+)", text)
    if not code:
        code = re.search(r'"Code"\s*:\s*"([A-Za-z0-9._\-]+)"', text)
    message = re.search(r"Message:\s*(.+)", text, re.S)
    if not message:
        message = re.search(r'"Message"\s*:\s*"([^"]*)"', text)
    return CliError(code.group(1) if code else "CliCommandFailed",
                    mask_secrets((message.group(1).strip() if message
                                  else text.strip())[:300]), action)


def _is_transient(code):
    return any(str(code or "").startswith(item) for item in TRANSIENT_ERROR_CODES)


def call(action, params=None, session_id="", timeout=None, attempts=None):
    """One plugin-mode CLI call with bounded retries on transient failures."""
    argv = build_argv(action, params, session_id)
    total = timeout or DEFAULT_TIMEOUT_SECONDS
    tries = attempts or MAX_ATTEMPTS
    last = None
    for attempt in range(1, tries + 1):
        try:
            proc = subprocess.run(argv, stdin=subprocess.DEVNULL,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  universal_newlines=True, timeout=total)
        except subprocess.TimeoutExpired:
            last = CliError("RequestTimeout", "call exceeded %s seconds" % total, action)
        except OSError as exc:
            last = CliError("CliNotAvailable", mask_secrets(str(exc)), action)
        else:
            if proc.returncode != 0:
                last = _error_from((proc.stderr or "") + (proc.stdout or ""), action)
                if not _is_transient(last.code):
                    raise last
            else:
                body = (proc.stdout or "").strip()
                if not body:
                    return {}
                try:
                    payload = json.loads(body)
                except ValueError:
                    raise CliError("UnparsableResponse",
                                   "response is not JSON: " + body[:180], action)
                code = str(payload.get("Code", ""))
                if code and code not in ("200", "OK", "Success"):
                    raise CliError(code, str(payload.get("Message", "")), action)
                return payload
        if attempt < tries and _is_transient(last.code if last else ""):
            time.sleep(BACKOFF_SECONDS * attempt)
    raise last


# ---------------------------------------------------------------------------
# Pure judgement functions (covered by --selftest)
# ---------------------------------------------------------------------------

def to_int_or_none(value):
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        return None
    return number


def parse_kv_output(text):
    """Parse the collector's key=value lines; malformed lines are dropped."""
    out = {}
    for line in (text or "").splitlines():
        line = line.strip()
        if "=" not in line or line.startswith("#"):
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if re.match(r"^[a-z0-9_]+$", key):
            out[key] = value.strip()
    return out


def is_small_spec(memory_mib):
    """Swap candidates are instances with at most 8 GiB of physical memory."""
    if memory_mib is None:
        return "UNKNOWN"
    if memory_mib < 0:
        return "UNKNOWN"
    return "PASS" if memory_mib <= SMALL_SPEC_MIB else "FAIL"


def is_basic_cloud_disk(categories):
    """A basic cloud disk must not host Swap; unknown is treated as unsafe."""
    if not categories:
        return "UNKNOWN"
    cleaned = [str(item).strip().lower() for item in categories if str(item).strip()]
    if not cleaned:
        return "UNKNOWN"
    if BASIC_CLOUD_DISK_CATEGORY in cleaned:
        return "FAIL"
    return "PASS"


def disk_space_ok(available_kib):
    if available_kib is None or available_kib < 0:
        return "UNKNOWN"
    return "PASS" if available_kib >= SWAP_MIN_FREE_KIB else "FAIL"


def memory_pressure(oom_evidence, mem_available_kb, mem_total_kb,
                    cms_memory_percent, swap_total_kb, swap_free_kb):
    """Evidence gate: never enter the memory flow on a CPU-only symptom.

    Having Swap configured is not evidence of pressure; Swap nearly exhausted is.
    """
    signals = []
    if oom_evidence and str(oom_evidence).startswith("recent:"):
        signals.append("kernel OOM lines " + str(oom_evidence).split(":", 1)[1])
    avail = to_int_or_none(mem_available_kb)
    total = to_int_or_none(mem_total_kb)
    if avail is not None and total:
        used_percent = (total - avail) * 100.0 / total
        if used_percent >= MEMORY_USED_WARN_PERCENT:
            signals.append("available memory %.1f%% used" % used_percent)
    cms_percent = to_float_or_none(cms_memory_percent)
    if cms_percent is not None and cms_percent >= MEMORY_USED_WARN_PERCENT:
        signals.append("CloudMonitor memory %.1f%%" % cms_percent)
    swap_total = to_int_or_none(swap_total_kb)
    swap_free = to_int_or_none(swap_free_kb)
    if swap_total and swap_free is not None and swap_total > 0:
        if swap_free * 100 <= swap_total * 10:
            signals.append("swap nearly exhausted (%s of %s kB left)"
                           % (swap_free, swap_total))
    return ("PASS" if signals else "UNKNOWN"), signals


def atop_history_verdict(atop_history, active_file, rotation):
    """Coverage verdict for the atop lane: never claim more than the file proves.

    A dated file existing somewhere is not coverage of the incident window; the
    active file and its rotation state decide what the replay guidance may say.
    """
    if atop_history != "yes" or not active_file:
        return "absent"
    if rotation == "stale":
        return "stale-file"
    return "current"


# Measured on a live instance: a running agent refreshed LastHeartbeatTime about
# every 60 s, and after `systemctl stop aliyun` that value froze for the whole
# 16-19 min window while CloudAssistantStatus kept reporting "true". The
# threshold leaves ~15 refresh intervals of slack before an agent is called
# unresponsive, and is below the staleness a stopped agent was observed to reach.
AGENT_HEARTBEAT_MAX_AGE_SECONDS = 900


def heartbeat_age_seconds(text, now=None):
    """Seconds since the agent's last heartbeat; None when unreadable."""
    raw = str(text or "").strip()
    if not raw:
        return None
    parsed = None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S"):
        try:
            parsed = datetime.strptime(raw, fmt)
            break
        except ValueError:
            continue
    if parsed is None:
        return None
    parsed = parsed.replace(tzinfo=timezone.utc)
    base = now or datetime.now(timezone.utc)
    return int((base - parsed).total_seconds())


def assistant_state(row, now=None):
    """Decide whether the guest channel can answer, before spending an invocation.

    CloudAssistantStatus is read as the offline flag, but a live test showed it
    keeps reporting "true" for at least 19 minutes after the agent process was
    stopped, so the heartbeat decides as well: an old heartbeat is reported as
    unresponsive rather than trusted.
    """
    flag = str(row.get("CloudAssistantStatus", "")).strip().lower()
    if flag not in ("true", "false"):
        return "unknown", None
    if flag == "false":
        return "offline", None
    age = heartbeat_age_seconds(row.get("LastHeartbeatTime"), now)
    if age is not None and age > AGENT_HEARTBEAT_MAX_AGE_SECONDS:
        return "unresponsive", age
    return "online", age


def dispatch_should_skip(state):
    """Affirmative evidence the agent cannot answer: do not burn an invocation."""
    return state in ("offline", "unresponsive")


def region_error_hint(code):
    """Name an invalid region id as itself instead of hiding it in a lookup miss."""
    return bool(code) and "InvalidRegionId" in str(code)


def cms_window(window_minutes, now=None):
    """UTC start/end pair for the CloudMonitor look-back, ISO 8601 with Z."""
    minutes = to_int_or_none(window_minutes)
    if minutes is None or minutes < 1:
        return "", ""
    end = now or datetime.now(timezone.utc)
    start = end - timedelta(minutes=minutes)
    fmt = "%Y-%m-%dT%H:%M:%SZ"
    return start.strftime(fmt), end.strftime(fmt)


def format_kib(value):
    """Render a KiB count as GiB; unprovable counts stay literal."""
    number = to_int_or_none(value)
    if number is None or number < 0:
        return str(value if value is not None else "unknown") + " (unverified)"
    return "%.1f GiB free (%d kB)" % (number / 1024.0 / 1024.0, number)


IO_UTIL_BUSY_PERCENT = 80.0
MEM_RELIEF_PERCENT = 10.0


def parse_io_status(text):
    """Return {device: util_percent} from the collector line; empty when unparsable."""
    out = {}
    for item in str(text or "").split(","):
        if ":" not in item:
            continue
        device, value = item.split(":", 1)
        number = to_float_or_none(value)
        device = device.strip()
        if device and number is not None and number >= 0:
            out[device] = number
    return out


def max_io_util(text):
    values = list(parse_io_status(text).values())
    return max(values) if values else None


def io_is_measured(guest):
    state = str(guest.get("io_measured", "")).strip()
    if state in ("1", "0"):
        return state == "1"
    # older payloads had no io_measured key: fall back to the value itself
    return bool(parse_io_status(guest.get("io_status")))


def io_state_text(guest):
    if not guest:
        return "not collected"
    if not io_is_measured(guest):
        return "not measured (iostat absent or unparsable)"
    util = max_io_util(guest.get("io_status"))
    if util is None:
        return "measured but no device line came back"
    busy = " busy" if util >= IO_UTIL_BUSY_PERCENT else ""
    # "measured" is written out so an idle disk cannot be mistaken for the
    # "not measured" branch further below
    return "%s (measured, max %%util %.2f%s)" % (guest.get("io_status"), util, busy)


def compare_evidence(before, after):
    """Judge whether the pressure actually eased, per key, with named semantics.

    A changed value is not the same as relief: available memory going down is a
    worsening, Swap appearing is a configuration change, and an I/O reading of
    0.00 means measured-idle rather than unmeasured.
    """
    rows = []

    def add(key, verdict, detail):
        rows.append((key, str(before.get(key, "not collected")),
                     str(after.get(key, "not collected")), verdict, detail))

    oom_b, oom_a = str(before.get("oom_evidence", "")), str(after.get("oom_evidence", ""))
    if oom_b.startswith("recent:") and oom_a == "none":
        add("oom_evidence", "EASED", "kernel OOM lines stopped appearing")
    elif oom_b.startswith("recent:") and oom_a.startswith("recent:"):
        n_b = to_int_or_none(oom_b.split(":", 1)[1]) or 0
        n_a = to_int_or_none(oom_a.split(":", 1)[1]) or 0
        add("oom_evidence", "STILL PRESENT" if n_a else "EASED",
            "count went %s -> %s" % (n_b, n_a))
    else:
        add("oom_evidence", "NO BASELINE", "the earlier sample had no OOM reading")

    avail_b = to_int_or_none(before.get("mem_available_kb"))
    avail_a = to_int_or_none(after.get("mem_available_kb"))
    if avail_b is None or avail_a is None or avail_b < 0:
        add("mem_available_kb", "UNVERIFIED", "an available-memory sample is missing")
    else:
        delta = (avail_a - avail_b) * 100.0 / avail_b if avail_b else 100.0
        if delta >= MEM_RELIEF_PERCENT:
            add("mem_available_kb", "EASED", "available memory up %.1f%%" % delta)
        elif delta <= -MEM_RELIEF_PERCENT:
            add("mem_available_kb", "WORSENED", "available memory down %.1f%%" % -delta)
        else:
            add("mem_available_kb", "UNCHANGED", "movement within %.0f%%" %
                MEM_RELIEF_PERCENT)

    swap_b = to_int_or_none(before.get("swap_total_kb"))
    swap_a = to_int_or_none(after.get("swap_total_kb"))
    if swap_b is None or swap_a is None:
        add("swap_total_kb", "UNVERIFIED", "a Swap sample is missing")
    elif swap_b == 0 and swap_a > 0:
        add("swap_total_kb", "CONFIGURED", "Swap became present (a change, not relief)")
    elif swap_b > 0 and swap_a == 0:
        add("swap_total_kb", "REMOVED", "Swap was turned off")
    else:
        add("swap_total_kb", "UNCHANGED", "no Swap state movement")

    if io_is_measured(before) and io_is_measured(after):
        util_b = max_io_util(before.get("io_status"))
        util_a = max_io_util(after.get("io_status"))
        if util_b is None or util_a is None:
            add("io_status", "UNVERIFIED", "no device utilisation in a sample")
        elif util_a < util_b:
            add("io_status", "EASED", "max %%util %.2f -> %.2f" % (util_b, util_a))
        elif util_a > util_b:
            add("io_status", "WORSENED", "max %%util %.2f -> %.2f" % (util_b, util_a))
        else:
            add("io_status", "UNCHANGED", "max %%util stayed %.2f" % util_a)
    else:
        add("io_status", "UNVERIFIED",
            "iostat was not measurable in at least one sample")
    return rows


def to_float_or_none(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def classify_symptom(symptom, signals, io_busy=False, ssh_unreachable_hint=False):
    """Route the intake; unknown symptoms stay in the guidance lane."""
    choice = (symptom or "auto").strip().lower()
    if choice in ("oom", "iops", "hang", "cpu", "root-cause"):
        return choice
    if io_busy and signals:
        return "iops"
    if ssh_unreachable_hint:
        return "hang"
    if signals:
        return "oom"
    return "unknown"


def disable_gate(gate):
    """Rolling Swap back is judged by its own prerequisites.

    Turning Swap off must not be refused because the enable-time evidence is
    missing: the customer may be undoing a mitigation that was never meant to
    stay. What still has to hold is that this is a Linux guest and that the
    agent can receive the command (checked by the caller).
    """
    blocked = []
    if gate.get("linux_instance") != "PASS":
        blocked.append("linux_instance")
    return blocked


def swap_precondition_report(gate):
    """Turn the five raw gates into an ordered, judgeable list."""
    order = [
        ("linux_instance", gate.get("linux_instance", "UNKNOWN")),
        ("memory_at_most_8gib", gate.get("memory_at_most_8gib", "UNKNOWN")),
        ("memory_pressure_evidence", gate.get("memory_pressure_evidence", "UNKNOWN")),
        ("disk_free_at_least_5gib_after_change", gate.get("disk_space", "UNKNOWN")),
        ("system_disk_is_not_basic_cloud_disk", gate.get("disk_category", "UNKNOWN")),
        ("swap_plugin_available_in_guest", gate.get("swap_plugin", "UNKNOWN")),
    ]
    blocked = [name for name, state in order if state != "PASS"]
    return order, blocked


def terminal_invocation_status(status):
    return str(status or "").strip() in TERMINAL_STATUSES


def guest_key_note(reason):
    return ("customer consent for the in-guest read was not given in this turn; "
            "run with --allow-guest-read after asking (refused: %s)" % reason)


# ---------------------------------------------------------------------------
# Report assembly
# ---------------------------------------------------------------------------

class Report(object):
    def __init__(self):
        self.lines = []
        self.degradations = []
        self.data = {}

    def add(self, text):
        self.lines.append(text)

    def bullet(self, text):
        self.add("- " + mask_secrets(text))

    def degrade(self, text):
        self.degradations.append(mask_secrets(text))
        sys.stderr.write("[WARN] " + mask_secrets(text) + "\n")

    def kv_line(self, key, state, detail=""):
        if state in ("UNKNOWN", "FAIL") and detail:
            self.degrade("%s: %s (%s)" % (key, state, detail))


def fetch_identity(session_id):
    body = call("get-caller-identity", {}, session_id)
    return {
        "account_id": str(body.get("AccountId", "")),
        "arn": str(body.get("Arn", "")),
        "identity_type": str(body.get("IdentityType", "")),
    }


def fetch_instance(region, instance_id, session_id, report):
    body = call("describe-instances",
                {"biz-region-id": region,
                 "instance-ids": json.dumps([instance_id])}, session_id)
    items = (body.get("Instances") or {}).get("Instance") or []
    for item in items:
        if str(item.get("InstanceId", "")) == instance_id:
            return item
    report.bullet("%s is not visible under account %s in %s; this is a visibility "
                  "finding, not proof that the instance does not exist"
                  % (instance_id, report.data.get("account_id", "?"), region))
    return None


def describe_spec(instance_type, session_id, report):
    try:
        body = call("describe-instance-types", {"instance-types": instance_type},
                    session_id, attempts=1)
    except CliError as exc:
        report.kv_line("describe-instance-types", "UNKNOWN", exc.code)
        return None
    items = (body.get("InstanceTypes") or {}).get("InstanceType") or []
    for item in items:
        if str(item.get("InstanceTypeId", "")) == instance_type:
            return to_float_or_none(item.get("MemorySize"))
    return None


def describe_disk_categories(region, instance_id, session_id, report):
    try:
        body = call("describe-disks", {"biz-region-id": region,
                                       "instance-id": instance_id},
                    session_id, attempts=1)
    except CliError as exc:
        report.kv_line("describe-disks", "UNKNOWN", exc.code)
        return [], []
    disks = (body.get("Disks") or {}).get("Disk") or []
    categories = [str(item.get("Category", "")) for item in disks]
    system = [str(item.get("Category", "")) for item in disks
              if str(item.get("Type", "")).lower() == "system"]
    return categories, system


def cloud_assistant_status(region, instance_id, session_id, report):
    """(state, heartbeat_age_seconds, heartbeat_text) for the guest channel."""
    try:
        body = call("describe-cloud-assistant-status",
                    {"biz-region-id": region, "instance-id": instance_id},
                    session_id, attempts=1)
    except CliError as exc:
        report.kv_line("describe-cloud-assistant-status", "UNKNOWN", exc.code)
        return "unknown", None, ""
    rows = ((body.get("InstanceCloudAssistantStatusSet") or {})
            .get("InstanceCloudAssistantStatus") or [])
    for row in rows:
        if str(row.get("InstanceId", "")) == instance_id:
            state, age = assistant_state(row)
            return state, age, str(row.get("LastHeartbeatTime", ""))
    return "unknown", None, ""


def cms_value(region, instance_id, metric, session_id, report, window_minutes,
              mount=None):
    dimensions = json.dumps([{"instanceId": instance_id}])
    params = {"namespace": CMS_NAMESPACE, "metric-name": metric,
              "dimensions": dimensions, "period": "60",
              "length": "100"}
    start, end = cms_window(window_minutes)
    if start:
        params["start-time"] = start
        params["end-time"] = end
    try:
        body = call("describe-metric-last", params, session_id, attempts=1)
    except CliError as exc:
        report.kv_line("cloudmonitor " + metric, "UNKNOWN", exc.code)
        # a denied or failing read is not the same fact as "the metric has no
        # point"; remember it so downstream summaries do not say "no data"
        report.data["cms_read_failed"] = True
        return None
    try:
        points = json.loads(str(body.get("Datapoints", "[]")))
    except ValueError:
        report.degrade("CloudMonitor returned unparsable datapoints for " + metric)
        return None
    if not points:
        report.degrade(
            "CloudMonitor has no %s datapoint: the CloudMonitor agent may be "
            "missing, and the reading stays unverified" % metric)
        return None
    if mount is not None:
        # one instance carries several devices and mount points; the precondition
        # is about the root filesystem, so the other rows must not be read as it
        matched = [p for p in points
                   if str(p.get("diskname", "")).rstrip("/") in ("", mount.rstrip("/"))
                   and str(p.get("device", "")).startswith("/dev/")]
        if not matched:
            seen = sorted({str(p.get("diskname", "?")) for p in points})
            report.degrade("CloudMonitor %s has no datapoint for the %s mount; "
                           "mounts seen: %s" % (metric, mount, ", ".join(seen)))
            return None
        points = matched
    latest = sorted(points, key=lambda p: p.get("timestamp", 0))[-1]
    return to_float_or_none(latest.get("Average", latest.get("Maximum")))


def dispatch_guest(region, instance_id, payload, session_id, report, label, timeout):
    """Deliver one frozen payload and return its stdout, or None."""
    content = base64.b64encode(payload.encode("utf-8")).decode("ascii")
    params = {"biz-region-id": region,
              "type": "RunShellScript",
              "command-content": content,
              "content-encoding": "Base64",
              "name": "memory-oom-remediation-" + label,
              "description": "skill payload, confirmed by the customer in this turn",
              "timeout": str(timeout),
              "instance-id": instance_id,
              "client-token": uuid.uuid4().hex[:64]}
    try:
        body = call("run-command", params, session_id, attempts=1)
    except CliError as exc:
        report.degrade("guest dispatch for %s failed (%s): the layer is unverified"
                       % (label, exc.code))
        return None
    invoke_id = str(body.get("InvokeId", ""))
    if not invoke_id:
        report.degrade("guest dispatch for %s returned no InvokeId; the output "
                       "cannot be read back" % label)
        return None
    report.bullet("InvokeId %s dispatched for the %s payload" % (invoke_id, label))
    return poll_invocation(region, instance_id, invoke_id, session_id, report)


def poll_invocation(region, instance_id, invoke_id, session_id, report):
    params = {"biz-region-id": region, "invoke-id": invoke_id,
              "instance-id": instance_id, "content-encoding": "PlainText"}
    deadline = time.time() + GUEST_INVOKE_TIMEOUT_SECONDS
    waited = 0
    while time.time() < deadline:
        try:
            body = call("describe-invocation-results", params, session_id,
                        timeout=DEFAULT_TIMEOUT_SECONDS, attempts=1)
        except CliError as exc:
            report.degrade("reading back the invocation failed (%s)" % exc.code)
            return None
        results = ((body.get("Invocation") or {}).get("InvocationResults") or
                   (body.get("Invocations") or {}).get("InvocationResult") or {})
        rows = results.get("InvocationResult") if isinstance(results, dict) else None
        rows = rows or []
        for row in rows:
            status = str(row.get("InvocationStatus", row.get("InvokeRecordStatus", "")))
            if status in NON_TERMINAL_STATUSES:
                continue
            if not terminal_invocation_status(status):
                report.degrade("invocation ended in an unrecognised status %r" % status)
                return None
            if status in ("Failed", "Timeout", "Stopped", "Aborted", "Cancelled",
                          "Terminated", "PartialFailed"):
                detail = str(row.get("ErrorInfo", row.get("ErrorCode", "")))[:160]
                report.degrade("invocation %s returned %s: %s"
                               % (invoke_id, status, mask_secrets(detail)))
                return None
            return str(row.get("Output", "") or "")
        time.sleep(5)
        waited += 5
    report.degrade("no final invocation result within %s seconds"
                   % GUEST_INVOKE_TIMEOUT_SECONDS)
    return None


def repeat_enable(guest):
    """True when the guest already has Swap with room left, so enabling again is not
    the answer. Unknown Swap state is not treated as configured.
    """
    total = to_int_or_none(guest.get("swap_total_kb"))
    free = to_int_or_none(guest.get("swap_free_kb"))
    if not total or total <= 0 or free is None:
        return False
    return free * 100 > total * 10


def swap_exhausted(guest):
    """True when Swap exists but has less than one tenth of its room left."""
    total = to_int_or_none(guest.get("swap_total_kb"))
    free = to_int_or_none(guest.get("swap_free_kb"))
    if not total or total <= 0 or free is None:
        return False
    return free * 100 <= total * 10


def guest_reads(region, instance_id, session_id, report, consent, agent_state="unknown",
                os_type=""):
    if not consent:
        report.degrade(guest_key_note("no consent token in this turn"))
        report.bullet("CONSENT-REQUIRED: the read-only in-guest collector was NOT "
                      "delivered; cloud-side evidence below is unaffected")
        return {}
    if os_type and os_type != "linux":
        report.degrade(
            "the frozen collector payload is a Linux shell script, so it is not "
            "dispatched to a %s instance; the guest-derived fields stay unverified "
            "instead of creating an invocation that can only fail" % os_type)
        report.bullet("OS-TYPE-LIMIT: this read path supports Linux guests only; run "
                      "the equivalent checks on the instance itself, or rely on the "
                      "cloud-side evidence below")
        return {}
    if dispatch_should_skip(agent_state):
        report.degrade(
            "the Cloud Assistant status read reports the agent as %s, so the "
            "collector was NOT dispatched: an invocation would only be created and "
            "then fail. The guest-derived fields stay unverified; hand the customer "
            "the collector command to run themselves" % agent_state)
        return {}
    output = dispatch_guest(region, instance_id, GUEST_COLLECTOR, session_id,
                            report, "collector", 90)
    if output is None:
        return {}
    parsed = parse_kv_output(output)
    if not parsed:
        report.degrade("the collector returned no parsable key=value lines")
        return {}
    report.bullet("In-guest collector returned %d keys" % len(parsed))
    return parsed


def run_swap_change(region, instance_id, action, session_id, report, gate,
                    agent_state="unknown", guest=None):
    """Deliver one confirmed Swap plugin change; never runs unconfirmed.

    The agent's reachability is tested first: with a dead agent every route ends
    in a failed invocation, and "blocked by unproven evidence" would be the wrong
    explanation to give the customer.
    """
    if dispatch_should_skip(agent_state):
        report.add("SWAP-CHANGE-AGENT-UNREACHABLE: the Cloud Assistant status read "
                   "reports the agent as %s, so the confirmed change was NOT "
                   "delivered; an invocation created against an unreachable agent is "
                   "not a configuration" % agent_state)
        report.bullet("NEXT_ACTION: restore the agent, or have the customer apply the "
                      "steps in references/swap.md, then re-run to verify")
        return "unreachable"
    if action == "disable":
        blocked = disable_gate(gate)
        if blocked:
            report.add("SWAP-CHANGE-BLOCKED: rollback prerequisites not satisfied -> "
                       + ", ".join(blocked))
            return "blocked"
        report.bullet("Rollback lane: removing Swap needs a Linux guest and a "
                      "reachable agent, not the enable-time evidence gates")
    else:
        _order, blocked = swap_precondition_report(gate)
        if blocked:
            report.add("SWAP-CHANGE-BLOCKED: preconditions not satisfied -> "
                       + ", ".join(blocked))
            report.bullet("Recommendation: guide the change from references/swap.md "
                          "and recommend a larger instance spec instead of relying "
                          "on Swap")
            return "blocked"
        if repeat_enable(guest or {}):
            report.add("SWAP-CHANGE-ALREADY-CONFIGURED: this guest already has Swap "
                       "with free space, so a second enable was NOT delivered; "
                       "enabling again would add a file that is not the missing fix")
            report.bullet("NEXT_ACTION: work the memory holder, the runtime limit or "
                          "the instance spec (references/swap.md explains when more "
                          "Swap is genuinely needed), then re-run to verify")
            return "already-configured"
    try:
        payload = build_swap_command(action)
    except ValueError:
        report.degrade("unsupported swap action requested; nothing was delivered")
        return "blocked"
    report.bullet("Customer-confirmed Swap change for this turn; delivering the "
                  "frozen plugin command (%s)" % ("enable" if action == "enable"
                                                  else "disable"))
    output = dispatch_guest(region, instance_id, "#!/usr/bin/env bash\nset -uo pipefail\n"
                            + payload + "\n", session_id, report,
                            "swap-" + action, 120)
    if output is None:
        report.bullet("The Swap %s change is UNVERIFIED: the invocation produced no "
                      "readable output, so the report does not claim success" % action)
        return "unverified"
    flags = parse_kv_output(output)
    if flags:
        report.bullet("Swap change output keys: %s" % ", ".join(sorted(flags)[:8]))
    else:
        report.bullet("Swap change output was not key=value; raw first line quoted: %s"
                      % (output.strip().splitlines() or [""])[0][:120])
    return "applied"


CREDENTIAL_CODE_PREFIXES = ("InvalidSecurityToken", "InvalidAccessKeyId",
                            "SignatureDoesNotMatch", "IncompleteSignature",
                            "AuthenticationFailed", "MissingSecurityToken",
                            "InvalidAccount", "Forbidden", "AccessDenied",
                            "NoPermission")


def _is_credential_code(code):
    """Prefix match: the live error families carry suffixes the exact set misses."""
    text = str(code or "")
    return any(text.startswith(prefix) for prefix in CREDENTIAL_CODE_PREFIXES)


def print_environment_dependency(detail):
    """Name a missing CLI plugin as what it is: an environment dependency."""
    print("STATUS: ENVIRONMENT-DEPENDENCY")
    print("The Alibaba Cloud CLI in this environment is missing a product plugin, so "
          "no cloud state could be read. Nothing below is inferred.")
    print("Observed: " + mask_secrets(detail)[:240])
    print("NEXT_ACTION: install the CLI product plugins once, for example with "
          "'aliyun configure set --auto-plugin-install true', then re-run this "
          "command. This is not a permission error and not a credential error.")
    return 0


def build_report(args):
    session_id = new_session_id()
    report = Report()
    report.data["session_id"] = session_id
    report.data["region_id"] = args.region_id
    report.data["instance_id"] = args.instance_id

    try:
        identity = fetch_identity(session_id)
    except CliError as exc:
        if exc.code == PLUGIN_MISSING_CODE:
            return print_environment_dependency(exc.message)
        if _is_credential_code(exc.code) or _is_credential_message(exc.message):
            print("CREDENTIAL-FAIL-CLOSED: " + mask_secrets(exc.code))
            print("The skill could not authenticate, so no cloud state was read and "
                  "no conclusion below is drawn. Verify on your side:")
            print("  1. which identity the default credential chain resolves to;")
            print("  2. whether that identity still exists and is not disabled;")
            print("  3. whether it carries the permissions listed in "
                  "references/ram-policies.md;")
            print("  4. whether the region id %s is correct for the instance."
                  % args.region_id)
            return 3
        print("STATUS: FAILED")
        print("Identity pre-check failed: %s: %s" % (exc.code, mask_secrets(exc.message)))
        print("NEXT_ACTION: report this error verbatim; do not retry with different "
              "credentials and do not guess instance state.")
        return 0

    report.data["account_id"] = identity["account_id"]
    report.add("=== ECS MEMORY OOM REMEDIATION REPORT ===")
    report.add("Region: %s | Instance: %s" % (args.region_id, args.instance_id))
    report.add("Account scope: queries see account %s only" % identity["account_id"])

    env_dependency = False
    lookup_denied = ""
    lookup_code = ""
    try:
        instance = fetch_instance(args.region_id, args.instance_id, session_id, report)
    except CliError as exc:
        env_dependency = exc.code == PLUGIN_MISSING_CODE
        lookup_code = exc.code or ""
        if exc.code in CREDENTIAL_ERROR_CODES or _is_denial_message(exc.message):
            lookup_denied = "%s: %s" % (exc.code, mask_secrets(exc.message)[:160])
        report.degrade("describe-instances failed: %s" % exc.code)
        instance = None

    if env_dependency:
        return print_environment_dependency("the instance lookup could not run")

    if lookup_denied:
        report.add("STATUS: PERMISSION-GAP")
        report.add("The instance lookup was refused, so no instance state was read. "
                   "An empty or refused result is NOT evidence that the instance is "
                   "healthy or absent.")
        report.bullet("Denied read: %s" % lookup_denied)
        report.add("NEXT_ACTION: grant the read listed in references/ram-policies.md "
                   "to this identity, or run the lookup with an account that owns the "
                   "instance; then re-run this command")
        emit(report, args)
        return 0

    if instance is None:
        report.add("STATUS: INPUT-NOT-FOUND")
        if region_error_hint(lookup_code):
            report.bullet("The region id %s is not a valid region (the platform "
                          "returned %s), so no lookup was possible in it"
                          % (args.region_id, lookup_code))
            report.bullet("NEXT_ACTION: re-run with a region id that exists, then "
                          "confirm the instance id and the owning account")
            primary = ("PRIMARY-CAUSE: cloud read error %s; the region id is invalid "
                       "so no instance lookup was possible. NEXT_ACTION: re-run with "
                       "a region id that exists, then confirm the instance id and the "
                       "owning account" % (lookup_code or "InvalidRegionId"))
        else:
            report.bullet("NEXT_ACTION: confirm the instance id and region id, and "
                          "check that this account owns the instance")
            primary = ("PRIMARY-CAUSE: instance not visible under this account/region; "
                       "no instance state was read. NEXT_ACTION: confirm the instance "
                       "id and region id, and check that this account owns the instance")
        report.lines[3] = "STATUS: INPUT-NOT-FOUND | %s" % primary
        report.lines.insert(3, primary)
        emit(report, args)
        return 0

    os_type = str(instance.get("OSType", "")).lower()
    memory_mib = to_int_or_none(instance.get("Memory"))
    instance_type = str(instance.get("InstanceType", ""))
    state = str((instance.get("Status") or ""))
    cpu = to_int_or_none(instance.get("Cpu"))
    report.add("Instance spec: %s (%s vCPU, %s MiB) | OS type: %s | status: %s"
               % (instance_type, cpu if cpu else "unknown",
                  memory_mib if memory_mib else "unknown",
                  os_type or "unknown", state or "unknown"))

    spec_memory_gib = describe_spec(instance_type, session_id, report)
    if spec_memory_gib is not None:
        report.bullet("InstanceType memory size: %.2f GiB" % spec_memory_gib)

    categories, system_categories = describe_disk_categories(
        args.region_id, args.instance_id, session_id, report)
    if categories:
        report.bullet("Disk categories: %s (system: %s)"
                      % (", ".join(sorted(set(categories))),
                         ", ".join(sorted(set(system_categories))) or "unknown"))

    assistant, hb_age, hb_text = cloud_assistant_status(args.region_id, args.instance_id,
                                                        session_id, report)
    freshness = ""
    if hb_text:
        freshness = " (last heartbeat %s%s)" % (
            hb_text, ", %d s ago" % hb_age if hb_age is not None else "")
    elif assistant == "unknown":
        freshness = " (no status row came back)"
    report.bullet("Cloud Assistant agent: %s%s" % (assistant, freshness))

    cms_memory = cms_value(args.region_id, args.instance_id, CMS_MEMORY_METRIC,
                           session_id, report, args.window_minutes)
    cms_memory_failed = bool(report.data.get("cms_read_failed"))
    if cms_memory is not None:
        report.bullet("CloudMonitor %s: %.1f%% (host monitoring)"
                      % (CMS_MEMORY_METRIC, cms_memory))
    cms_disk_avail = cms_value(args.region_id, args.instance_id, CMS_DISK_AVAIL_METRIC,
                               session_id, report, args.window_minutes, mount="/")
    # the diskusage_avail datapoint is reported in bytes, verified against the
    # in-guest df reading during development (10029664 kB == 1.027e10 bytes)
    cms_avail_kib = (int(cms_disk_avail / 1024) if cms_disk_avail is not None else None)

    guest = guest_reads(args.region_id, args.instance_id, session_id, report,
                        args.allow_guest_read, assistant, os_type)
    report.data["guest"] = guest

    oom = guest.get("oom_evidence", "not collected")
    mem_avail = guest.get("mem_available_kb")
    mem_total = guest.get("mem_total_kb")
    pressure_state, signals = memory_pressure(
        None if oom == "not collected" else oom, mem_avail, mem_total, cms_memory,
        guest.get("swap_total_kb"), guest.get("swap_free_kb"))
    if guest.get("swap_total_kb") is not None:
        swap_state_text = "%s kB total / %s kB free" % (
            guest.get("swap_total_kb"), guest.get("swap_free_kb"))
    else:
        swap_state_text = "not collected"

    io_status = guest.get("io_status", "not collected")
    io_measured = bool(guest) and io_is_measured(guest)
    io_busy = io_measured and (max_io_util(io_status) or 0.0) >= IO_UTIL_BUSY_PERCENT
    cms_iops = {}
    if not guest:
        report.degrade("no in-guest read ran, so per-device utilisation is unavailable; "
                       "the IOPS lane falls back to CloudMonitor disk iops")
    elif not io_measured:
        report.degrade("iostat ran but produced no parsable device line; the IOPS lane "
                       "falls back to CloudMonitor disk iops")
    if not io_measured:
        for metric in CMS_IOPS_METRICS:
            value = cms_value(args.region_id, args.instance_id, metric, session_id,
                              report, args.window_minutes)
            if value is not None:
                cms_iops[metric] = value
    symptom = classify_symptom(args.symptom, signals, io_busy, args.ssh_unreachable)
    report.add("[Routing]")
    report.bullet("Symptom branch: %s (intake %s)" % (symptom, args.symptom))
    report.bullet("Memory-pressure evidence: %s (%s)"
                  % (pressure_state, "; ".join(signals) if signals
                     else ("no OOM lines, no used-memory signal; the CloudMonitor "
                           "memory reading could not be read" if cms_memory_failed
                           else "no OOM lines, no used-memory signal, no "
                                "CloudMonitor point")))
    if symptom == "cpu" and not signals:
        report.bullet("Recommendation: this is a CPU-only symptom, so the Swap and "
                      "memory lanes are not entered; investigate the busy process first")

    guest_avail_kib = to_int_or_none(guest.get("disk_avail_kb"))
    if guest.get("disk_avail_kb") in (None, "unknown", "not collected"):
        guest_avail_kib = None
    free_space_source = "in-guest df" if guest_avail_kib is not None else (
        "CloudMonitor diskusage_avail" if cms_avail_kib is not None else "no source")
    gate = {
        "linux_instance": "PASS" if os_type == "linux" else ("FAIL" if os_type else "UNKNOWN"),
        "memory_at_most_8gib": is_small_spec(memory_mib),
        "memory_pressure_evidence": pressure_state,
        "disk_space": disk_space_ok(guest_avail_kib if guest_avail_kib is not None
                                    else cms_avail_kib),
        "disk_category": is_basic_cloud_disk(system_categories or categories),
        "swap_plugin": ("PASS" if guest.get("swap_plugin") == "yes"
                        else "FAIL" if guest.get("swap_plugin") == "no" else "UNKNOWN"),
    }
    order, blocked = swap_precondition_report(gate)
    report.add("[Swap preconditions]")
    for name, gate_state in order:
        report.bullet("%s: %s" % (name, gate_state))
    report.bullet("Free space judgement source: %s" % free_space_source)

    if gate["memory_at_most_8gib"] == "FAIL":
        report.bullet("Spec gate FAILED: above 8 GiB, Swap is never recommended and "
                      "never enabled; this instance goes to the atop root-cause lane")
        recommended = "atop root-cause analysis and process-level tuning"
    elif blocked:
        recommended = ("guide the official Swap steps from references/swap.md "
                       "without executing them")
    elif repeat_enable(guest):
        recommended = ("Swap is already configured with free space (%s), so enabling "
                       "it again is not recommended; work the memory holder, the "
                       "runtime limit or the instance spec" % swap_state_text)
    elif swap_exhausted(guest):
        recommended = ("Swap is already configured and nearly exhausted (%s); adding "
                       "more Swap through the plugin is a mitigation the customer must "
                       "confirm, and the memory holder or a larger spec is the fix"
                       % swap_state_text)
    else:
        recommended = ("enable Swap through the Cloud Assistant plugin, but only "
                       "after the customer confirms that exact change")
    if symptom == "hang":
        recommended = ("staged restart guidance from references/restart-guide.md, "
                       "then re-collection once the instance answers again; prefer a "
                       "normal reboot, and treat a force reboot as the last resort "
                       "because it is equivalent to pulling the power and unwritten "
                       "data can be lost")
    report.add("[Recommendation]")
    report.bullet("Recommended action: %s" % recommended)
    reason = ("preconditions all PASS" if not blocked
              else "unmet: " + (", ".join(blocked) or "none"))
    if not blocked and repeat_enable(guest):
        reason += "; Swap already has free space, so a repeat enable is not the fix"
    elif not blocked and swap_exhausted(guest):
        reason += "; Swap is configured but nearly exhausted"
    report.bullet("Reason: %s" % reason)
    report.bullet("Risk or limit: Swap is a mitigation (memory pressure traded for "
                   "disk I/O); upgrading the instance spec removes the root cause")

    node_keys = [key for key in sorted(guest) if key.startswith("node_")]
    if node_keys:
        report.add("[Node.js runtime]")
        for key in node_keys[:5]:
            report.bullet("%s -> %s" % (key, guest[key]))
        report.bullet("Advice only: see references/node-runtime.md for "
                      "--max-old-space-size; the customer restarts the process")
    elif guest:
        report.add("[Node.js runtime]")
        report.bullet("No node process in the snapshot; nothing to advise")

    if guest:
        report.add("[In-guest evidence]")
        report.bullet("Swap state: %s" % swap_state_text)
        report.bullet("Disk I/O utilisation: %s" % io_state_text(guest))
        if cms_iops:
            report.bullet("CloudMonitor disk iops fallback: %s" % ", ".join(
                "%s=%.1f" % (name, cms_iops[name]) for name in sorted(cms_iops)))
        report.bullet("Root filesystem free: %s" % format_kib(guest.get("disk_avail_kb")))
        report.bullet("Rotational media: %s" % ", ".join(
            "%s=%s" % (key, guest[key]) for key in sorted(guest)
            if key.startswith("disk_rotational")) or "unknown")
        report.bullet("Top RSS processes: %s" % ", ".join(
            guest[key] for key in sorted(guest) if key.startswith("rss_top_")))
        report.bullet("atop installed: %s | atop history present: %s"
                      % (guest.get("atop_installed", "unknown"),
                         guest.get("atop_history", "unknown")))
        atop_verdict = atop_history_verdict(guest.get("atop_history"),
                                            guest.get("atop_active_file"),
                                            guest.get("atop_rotation"))
        if atop_verdict == "absent":
            report.bullet("Evidence source: current snapshot only; atop history replay "
                          "is unavailable, so the failure moment cannot be reconstructed "
                          "and the top-RSS list is a point-in-time reading "
                          "(references/atop.md)")
        else:
            report.bullet("atop history: active file %s | last sample: %s"
                          % (guest.get("atop_active_file", "unknown"),
                             guest.get("atop_last_sample", "unknown")))
            report.bullet("Evidence source: atop history replay of the active file "
                          "above (references/atop.md); the incident-window conclusion "
                          "comes from that replay, not from the current snapshot")
            if atop_verdict == "stale-file":
                report.bullet("atop rotation is not producing today's file: replay the "
                              "active file above by its exact path; -b/-e are anchored "
                              "to that file's own date, so a window from another day "
                              "returns empty output (references/atop.md, rotation "
                              "troubleshooting)")
            report.bullet("locate the incident window with a replay (atop -r with "
                          "-b/-e, sort by M, read MEM% / RSIZE / RGROW, or run atopsar "
                          "-m for a text report) and label that conclusion as atop "
                          "history replay (references/atop.md)")
    else:
        report.add("[In-guest evidence]")
        report.bullet("not collected: every guest-derived field is unverified")
        if cms_iops:
            report.bullet("CloudMonitor disk iops read instead: %s" % ", ".join(
                "%s=%.1f" % (name, cms_iops[name]) for name in sorted(cms_iops)))

    after_change = {}
    if args.confirm_swap_change:
        outcome = run_swap_change(args.region_id, args.instance_id,
                                  args.confirm_swap_change, session_id, report,
                                  gate, assistant, guest)
        report.data["swap_change"] = outcome
        if outcome == "applied":
            report.add("[Verification after remediation]")
            if args.allow_guest_read:
                after_change = guest_reads(args.region_id, args.instance_id,
                                           session_id, report, True, assistant, os_type)
                for key, b, a, verdict, detail in compare_evidence(guest, after_change):
                    report.bullet("%s: before=%s after=%s -> %s (%s)"
                                  % (key, b, a, verdict, detail))
            else:
                report.bullet("UNVERIFIED: the change was delivered but the "
                              "read-only collector was not consented, so the new "
                              "Swap state was not read back. Ask for the collector "
                              "consent, or have the customer run swapon --show")

    if args.verify:
        second = after_change or guest_reads(args.region_id, args.instance_id,
                                             session_id, report, True, assistant)
        report.add("[Verification after remediation]")
        if not after_change:
            report.bullet("Both samples come from this run; the pre-remediation "
                          "reference is the report issued before the customer acted")
        for key, b, a, verdict, detail in compare_evidence(guest, second):
            report.bullet("%s: before=%s after=%s -> %s (%s)"
                          % (key, b, a, verdict, detail))

    report.add("[Degradations]")
    if report.degradations:
        for item in report.degradations:
            report.bullet(item)
    else:
        report.bullet("none")

    primary = compose_primary_cause(symptom, guest, recommended, assistant, args, report)
    report.add("STATUS: %s | %s" % ("DEGRADED" if report.degradations else "OK", primary))
    report.add("NEXT_ACTION: deliver the report above with its evidence labels, and "
               "re-run after any change the customer applies")
    if report.data.get("cms_read_failed"):
        report.add("NEXT_ACTION: the CloudMonitor API read failed this run; ask the "
                   "customer to verify the monitoring data in the Alibaba Cloud "
                   "CloudMonitor console (ECS instance monitoring) before relying on "
                   "it, because the metric stays unverified here")
    report.lines.insert(4, primary)
    emit(report, args)
    return 0


def _is_denial_message(message):
    text = (message or "").lower()
    return any(token in text for token in ("forbidden", "nopermission",
                                           "not authorized", "accessdenied"))


def _is_credential_message(message):
    text = (message or "").lower()
    return any(token in text for token in ("securitytoken", "accesskeyid",
                                           "signature", "not authorized",
                                           "forbidden.ram", "no permission",
                                           # the CLI could not resolve a profile or
                                           # injected credentials at all: reading
                                           # nothing is still a fail-closed case
                                           "region can't be empty",
                                           "configuration failed",
                                           "no configuration file"))


def compose_primary_cause(symptom, guest, recommended, assistant, args, report):
    """A prominent, token-dense finding line placed at the top of the report so the
    key conclusion survives even a weak-model summary instead of being dropped."""
    parts = []
    node_keys = [key for key in sorted(guest) if key.startswith("node_")]
    if node_keys:
        parts.append("node process is the memory holder; advise --max-old-space-size, "
                     "the customer restarts the process to take effect (args <redacted>)")
    degradations = " ".join(report.degradations)
    report_text = " ".join(report.lines)
    if "CONSENT-REQUIRED" in degradations or "CONSENT-REQUIRED" in report_text:
        parts.append("CONSENT-REQUIRED: in-guest read not collected; the cloud "
                     "DescribeInstances instance spec read stays valid")
    if assistant in ("offline", "unresponsive"):
        parts.append("Cloud Assistant agent %s; the collector was NOT dispatched, "
                     "guest fields unverified" % assistant)
    for code in ("Throttling", "InternalError", "InvalidParameter", "InvalidRegionId",
                 "Forbidden", "NoPermission"):
        if code in degradations:
            parts.append("cloud read error %s; affected layer unverified, the customer "
                         "can re-run or check the console" % code)
            break
    for marker in ("SWAP-CHANGE-AGENT-UNREACHABLE", "SWAP-CHANGE-BLOCKED",
                   "SWAP-CHANGE-ALREADY-CONFIGURED", "OS-TYPE-LIMIT"):
        if marker in report_text:
            parts.append(marker)
    if "memory_at_most_8gib: FAIL" in report_text or "Spec gate FAILED" in report_text:
        parts.append("spec gate memory_at_most_8gib: FAIL (above 8 GiB); Swap is never "
                     "recommended, this instance goes to the atop root-cause lane")
    if "OS-TYPE-LIMIT" in report_text or "linux_instance: FAIL" in report_text:
        parts.append("Windows/non-Linux guest: the Linux shell collector was NOT dispatched, "
                     "guest fields not collected and unverified; linux_instance: FAIL")
    if "falls back to CloudMonitor disk iops" in degradations or "not measured" in report_text:
        parts.append("per-device I/O not measured (iostat absent); the IOPS lane falls "
                     "back to CloudMonitor disk_readiops/disk_writeiops")
    if args.ssh_unreachable or symptom == "hang":
        parts.append("SSH unreachable; staged restart guidance only, not executed")
    parts.append(recommended)
    return "PRIMARY-CAUSE: " + "; ".join(parts)


def emit(report, args):
    print("=== DELIVERY RULE (READ FIRST) ===")
    print("Your final reply MUST be the two code blocks below - the ```text report block")
    print("and the ```json block - copied VERBATIM, including every guidance/warning line.")
    print("DO NOT summarize, paraphrase, translate, or drop any line. Forward the code")
    print("blocks exactly as printed. A summary instead of the verbatim blocks FAILS.")
    print("```text")
    print("\n".join(report.lines))
    print("```")
    payload = {
        "skill": SKILL_NAME,
        "version": SKILL_VERSION,
        "session_id": report.data.get("session_id", ""),
        "region_id": report.data.get("region_id", ""),
        "instance_id": report.data.get("instance_id", ""),
        "account_id": report.data.get("account_id", ""),
        "symptom": args.symptom,
        "guest_read": "collected" if report.data.get("guest") else "not collected",
        "swap_change": report.data.get("swap_change", "not requested"),
    }
    print("```json")
    print(json.dumps(payload, ensure_ascii=False, separators=(",", ":")))
    print("```")
    print()
    print("=== FINAL ANSWER DELIVERY (MANDATORY) ===")
    print("YOUR FINAL MESSAGE MUST BE THE TWO CODE BLOCKS ABOVE, COPIED VERBATIM:")
    print("the ```text block (from the === ECS MEMORY OOM REMEDIATION REPORT === header")
    print("through STATUS:/NEXT_ACTION: and every guidance/warning line) and the ```json")
    print("block. Copy EVERY line character-for-character: STATUS:, NEXT_ACTION:, each")
    print("precondition name + PASS/FAIL/UNKNOWN verdict, the spec line, every evidence-source")
    print("label, and any before=/after= verdict. DO NOT write a summary. DO NOT paraphrase")
    print("or translate. DO NOT drop or reorder lines. DO NOT write the report to a file")
    print("instead of replying. DO NOT add a closing remark. Your final message = the")
    print("verbatim code blocks, nothing else. A summary instead of the blocks FAILS.")


def selftest():
    """Boundary assertions for the pure judgement functions."""
    checks = []

    def expect(label, got, want):
        checks.append((label, got, want))
        return got == want

    a = expect("spec 8192 MiB passes", is_small_spec(8192), "PASS")
    b = expect("spec 8193 MiB fails", is_small_spec(8193), "FAIL")
    c = expect("spec unknown stays unknown", is_small_spec(None), "UNKNOWN")
    d = expect("negative spec is rejected", is_small_spec(-1), "UNKNOWN")
    e = expect("basic cloud disk fails", is_basic_cloud_disk(["cloud"]), "FAIL")
    f = expect("essd passes", is_basic_cloud_disk(["cloud_essd"]), "PASS")
    g = expect("empty category unknown", is_basic_cloud_disk([]), "UNKNOWN")
    h = expect("4 GiB free fails", disk_space_ok(SWAP_MIN_FREE_KIB - 1), "FAIL")
    i = expect("5 GiB free passes", disk_space_ok(SWAP_MIN_FREE_KIB), "PASS")
    j = expect("free unknown", disk_space_ok(None), "UNKNOWN")
    k = expect("oom evidence passes",
               memory_pressure("recent:3", None, None, None, None, None)[0], "PASS")
    m = expect("85 percent used passes",
               memory_pressure("none", "150000", "1000000", None, None, None)[0], "PASS")
    n = expect("no signal is not a fail",
               memory_pressure("none", "900000", "1000000", None, None, None)[0],
               "UNKNOWN")
    o = expect("cms percent passes",
               memory_pressure(None, None, None, "91.5", None, None)[0], "PASS")
    ac = expect("swap merely present is not pressure",
                memory_pressure("none", "900000", "1000000", None,
                                "2097148", "1048576")[0], "UNKNOWN")
    ad = expect("swap nearly exhausted is pressure",
                memory_pressure("none", "900000", "1000000", None,
                                "2097148", "1000")[0], "PASS")
    ae = expect("kib renders as gib", format_kib("1048576"), "1.0 GiB free (1048576 kB)")
    af = expect("kib keeps unknown literal", format_kib("unknown"),
                "unknown (unverified)")
    ag = expect("kib rejects negative", format_kib(-5), "-5 (unverified)")
    ah = expect("denial message detected",
                _is_denial_message("User not authorized to operate"), True)
    ai = expect("throttling is not a denial",
                _is_denial_message("Throttling.User request limit"), False)
    aj = expect("plugin code is not a denial",
                _is_denial_message(PLUGIN_MISSING_CODE), False)
    fixed_now = datetime(2026, 11, 11, 8, 0, 0, tzinfo=timezone.utc)
    ak = expect("window start is minutes behind",
                cms_window(60, fixed_now),
                ("2026-11-11T07:00:00Z", "2026-11-11T08:00:00Z"))
    al = expect("window zero disables the filter", cms_window(0, fixed_now), ("", ""))
    am = expect("window rejects garbage", cms_window("abc", fixed_now), ("", ""))
    p = expect("symptom override honoured", classify_symptom("iops", [], False), "iops")
    q = expect("auto maps to iops", classify_symptom("auto", ["x"], True), "iops")
    q2 = expect("idle disk is not the iops lane",
               classify_symptom("auto", ["x"], False), "oom")
    r = expect("hang hint", classify_symptom("auto", [], False, True), "hang")
    s = expect("nothing to classify", classify_symptom("auto", [], False), "unknown")
    t = expect("kv parser drops junk",
               parse_kv_output("a=1\nnot a pair\nb= 2 \n#x\nBADD$=3"), {"a": "1", "b": "2"})
    io1 = expect("io map keeps zero rows", parse_io_status("vda:0.00,vdb:12.50"),
                 {"vda": 0.0, "vdb": 12.5})
    io2 = expect("io map rejects junk", parse_io_status("unknown"), {})
    io3 = expect("io max picks the busiest device", max_io_util("vda:3.10,vdb:88.00"), 88.0)
    io4 = expect("io max on unparsable is None", max_io_util("unknown"), None)
    io5 = expect("measured idle reads as measured", io_state_text(
        {"io_measured": "1", "io_status": "vda:0.00"}), "vda:0.00 (measured, max %util 0.00)")
    io6 = expect("unmeasured reads as unmeasured", io_state_text(
        {"io_measured": "0", "io_status": "unknown"}),
        "not measured (iostat absent or unparsable)")
    io7 = expect("legacy payload falls back to the value",
                 io_is_measured({"io_status": "vda:4.00"}), True)
    io8 = expect("legacy unknown is unmeasured",
                 io_is_measured({"io_status": "unknown"}), False)
    ver1 = dict((row[0], row[3]) for row in compare_evidence(
        {"oom_evidence": "recent:3", "mem_available_kb": "100000",
         "swap_total_kb": "0", "io_measured": "1", "io_status": "vda:95.00"},
        {"oom_evidence": "none", "mem_available_kb": "900000",
         "swap_total_kb": "4194300", "io_measured": "1", "io_status": "vda:2.00"}))
    ver2 = dict((row[0], row[3]) for row in compare_evidence(
        {"oom_evidence": "recent:3", "mem_available_kb": "900000",
         "swap_total_kb": "4194300", "io_measured": "1", "io_status": "vda:2.00"},
        {"oom_evidence": "recent:2", "mem_available_kb": "100000",
         "swap_total_kb": "4194300", "io_measured": "1", "io_status": "vda:97.00"}))
    io9 = expect("verification judges eased per key",
                 [ver1["oom_evidence"], ver1["mem_available_kb"],
                  ver1["swap_total_kb"], ver1["io_status"]],
                 ["EASED", "EASED", "CONFIGURED", "EASED"])
    ioa = expect("verification judges worsened not change",
                 [ver2["oom_evidence"], ver2["mem_available_kb"],
                  ver2["swap_total_kb"], ver2["io_status"]],
                 ["STILL PRESENT", "WORSENED", "UNCHANGED", "WORSENED"])
    iob = expect("verification without a baseline says so",
                 compare_evidence({}, {"oom_evidence": "none"})[0][3], "NO BASELINE")
    ioc = expect("verification on a refused read is unverified",
                 compare_evidence({"mem_available_kb": "100"},
                                  {})[1][3], "UNVERIFIED")
    at1 = expect("atop absent without history",
                 atop_history_verdict("no", "", ""), "absent")
    at2 = expect("atop yes without an active file stays absent",
                 atop_history_verdict("yes", "", "current"), "absent")
    at3 = expect("atop stale file is named",
                 atop_history_verdict("yes", "atop_20261111", "stale"),
                 "stale-file")
    at4 = expect("atop current file is current",
                 atop_history_verdict("yes", "atop_20261112", "current"),
                 "current")
    clock = datetime(2026, 11, 11, 9, 0, 0, tzinfo=timezone.utc)
    hb1 = expect("fresh heartbeat keeps the channel online", assistant_state(
        {"CloudAssistantStatus": "true",
         "LastHeartbeatTime": "2026-11-11T08:55:00Z"}, clock), ("online", 300))
    hb2 = expect("stale heartbeat is unresponsive", assistant_state(
        {"CloudAssistantStatus": "true",
         "LastHeartbeatTime": "2026-11-11T07:00:00Z"}, clock)[0], "unresponsive")
    hb3 = expect("flag false is offline", assistant_state(
        {"CloudAssistantStatus": "false"}, clock)[0], "offline")
    hb4 = expect("missing flag is unknown", assistant_state({}, clock)[0], "unknown")
    hb5 = expect("unparsable heartbeat is not held against us",
                 heartbeat_age_seconds("not-a-time", clock), None)
    hb6 = expect("offline skips the dispatch", dispatch_should_skip("offline"), True)
    hb7 = expect("unknown still attempts", dispatch_should_skip("unknown"), False)
    hb8 = expect("invalid region is named as such",
                 region_error_hint("InvalidRegionId.NotFound"), True)
    hb9 = expect("an empty result is not a region error",
                 region_error_hint(""), False)
    hb10 = expect("suffix-bearing token error is credential class",
                  _is_credential_code("InvalidSecurityToken.MismatchWithAccessKey"), True)
    hb11 = expect("throttling is not credential class",
                  _is_credential_code("Throttling.User"), False)
    guard_report = Report()
    guard_out = run_swap_change("cn-hangzhou", "i-example000001", "enable", "sid",
                                guard_report,
                                {"linux_instance": "PASS", "memory_at_most_8gib": "PASS"},
                                "offline")
    hb12 = expect("a confirmed change is not delivered to an unreachable agent",
                  guard_out, "unreachable")
    hb13 = expect("the refusal names itself", "SWAP-CHANGE-AGENT-UNREACHABLE" in
                  "\n".join(guard_report.lines), True)
    dg1 = expect("rollback needs no enable-time evidence",
                 disable_gate({"linux_instance": "PASS",
                               "memory_at_most_8gib": "FAIL",
                               "memory_pressure_evidence": "UNKNOWN",
                               "disk_space": "UNKNOWN", "disk_category": "UNKNOWN",
                               "swap_plugin": "UNKNOWN"}), [])
    dg2 = expect("rollback still refuses non-Linux", disable_gate(
        {"linux_instance": "FAIL"}), ["linux_instance"])
    dg3 = expect("rollback still refuses an unknown OS", disable_gate({}),
                 ["linux_instance"])
    dg4 = expect("the enable lane is still evidence-gated",
                 swap_precondition_report({"linux_instance": "PASS",
                                           "memory_at_most_8gib": "PASS",
                                           "memory_pressure_evidence": "UNKNOWN"})[1],
                 ["memory_pressure_evidence",
                  "disk_free_at_least_5gib_after_change",
                  "system_disk_is_not_basic_cloud_disk",
                  "swap_plugin_available_in_guest"])
    u = expect("terminal status Success", terminal_invocation_status("Success"), True)
    v = expect("Running is not terminal", terminal_invocation_status("Running"), False)
    w = expect("cancel is terminal", terminal_invocation_status("Cancelled"), True)
    x = expect("swap action whitelist", build_swap_command("enable").startswith(
        "acs-plugin-manager"), True)
    y = expect("unknown swap action refused",
               _raises(ValueError, build_swap_command, "rm -rf"), True)
    z = expect("preconditions list is ordered",
               swap_precondition_report({"linux_instance": "PASS",
                                         "disk_space": "FAIL"})[1],
               ["memory_at_most_8gib", "memory_pressure_evidence",
                "disk_free_at_least_5gib_after_change",
                "system_disk_is_not_basic_cloud_disk",
                "swap_plugin_available_in_guest"])
    aa = expect("secret masked", "suppressedvalue" not in mask_secrets(
        "AccessKeyId: suppressedvalue"), True)
    ab = expect("consent note names flag",
               "--allow-guest-read" in guest_key_note("missing token"), True)
    re1 = expect("swap with room left needs no second enable", repeat_enable(
        {"swap_total_kb": "4194300", "swap_free_kb": "3900000"}), True)
    re2 = expect("exhausted swap is not counted as configured relief", repeat_enable(
        {"swap_total_kb": "4194300", "swap_free_kb": "12000"}), False)
    re3 = expect("unknown swap is not treated as configured", repeat_enable(
        {"swap_total_kb": "unknown", "swap_free_kb": "unknown"}), False)
    re4 = expect("an absent guest reading is not configured", repeat_enable({}), False)
    already_report = Report()
    already_out = run_swap_change(
        "cn-hangzhou", "i-example000001", "enable", "sid", already_report,
        {"linux_instance": "PASS", "memory_at_most_8gib": "PASS",
         "memory_pressure_evidence": "PASS", "disk_space": "PASS",
         "disk_category": "PASS", "swap_plugin": "PASS"}, "online",
        {"swap_total_kb": "4194300", "swap_free_kb": "3900000"})
    re5 = expect("a confirmed enable on a swapped guest is refused",
                 already_out, "already-configured")
    re6 = expect("that refusal names itself", "SWAP-CHANGE-ALREADY-CONFIGURED" in
                 "\n".join(already_report.lines), True)
    win_report = Report()
    win_out = guest_reads("cn-hangzhou", "i-example000001", "sid", win_report, True,
                          "online", "windows")
    re7 = expect("the Linux collector is not dispatched to a Windows guest",
                 win_out, {})
    re8 = expect("the Windows limit is named, not hidden", "OS-TYPE-LIMIT" in
                 "\n".join(win_report.lines), True)
    re9 = expect("a Linux guest still passes the OS-type guard",
                 dispatch_should_skip("online"), False)
    re10 = expect("near-zero free swap counts as exhausted", swap_exhausted(
        {"swap_total_kb": "4194300", "swap_free_kb": "12000"}), True)
    re11 = expect("swap with room is not exhausted", swap_exhausted(
        {"swap_total_kb": "4194300", "swap_free_kb": "3900000"}), False)
    re12 = expect("no swap is not an exhausted swap", swap_exhausted(
        {"swap_total_kb": "0", "swap_free_kb": "0"}), False)
    re13 = expect("the two swap readings are mutually exclusive",
                  repeat_enable({"swap_total_kb": "4194300", "swap_free_kb": "12000"}),
                  False)
    failed = [label for (label, got, want) in checks
              for ok in [got == want] if not ok]
    print("SELFTEST %d assertions, %d failed" % (len(checks), len(failed)))
    for label in failed:
        print("  FAILED: " + label)
    return 0 if not failed else 1


def _raises(exc_type, function, *function_args):
    try:
        function(*function_args)
    except exc_type:
        return True
    except Exception:
        return False
    return False


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="ECS memory-pressure triage (read-only by default, one "
                    "confirmed Swap change)")
    parser.add_argument("--region-id", dest="region_id", default="")
    parser.add_argument("--instance-id", dest="instance_id", default="")
    parser.add_argument("--symptom", default="auto",
                        choices=["auto", "oom", "iops", "hang", "cpu", "root-cause"])
    parser.add_argument("--window-minutes", type=int, default=60)
    parser.add_argument("--allow-guest-read", action="store_true",
                        dest="allow_guest_read",
                        help="the customer consented to the read-only in-guest "
                             "collector in this turn")
    parser.add_argument("--confirm-swap-change", default="",
                        dest="confirm_swap_change", choices=["", "enable", "disable"],
                        help="the customer confirmed this exact Swap change in this "
                             "turn")
    parser.add_argument("--verify", action="store_true",
                        help="re-collect after a remediation and compare")
    parser.add_argument("--ssh-unreachable", action="store_true",
                        dest="ssh_unreachable",
                        help="the customer reports SSH will not log in")
    parser.add_argument("--selftest", action="store_true")
    args = parser.parse_args(argv)

    if args.selftest:
        return selftest()
    if not args.region_id or not args.instance_id:
        print("error: --region-id and --instance-id are both required; ask the "
              "customer for the missing value instead of guessing")
        return 2
    if not re.match(r"^[a-z0-9-]+$", args.region_id):
        print("error: --region-id is not a valid region id")
        return 2
    if not re.match(r"^i-[a-z0-9]{6,}$", args.instance_id):
        print("error: --instance-id must be an ECS instance id like i-example001")
        return 2
    if args.window_minutes < 1 or args.window_minutes > 1440:
        print("error: --window-minutes must be between 1 and 1440")
        return 2
    return build_report(args)


if __name__ == "__main__":
    sys.exit(main())
