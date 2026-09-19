#!/usr/bin/env python3
"""One-shot configuration preflight for alibabacloud-agent-observability.

Verifies everything an analysis run needs BEFORE any query is issued, so a
misconfigured environment fails here with an actionable fix instead of failing
halfway through a workflow:

  1. cli_version    aliyun CLI >= 3.3.3
  2. plugins        aliyun-cli-sls / aliyun-cli-cms
  3. credentials    a valid profile, and its credential TYPE (AK / STS /
                    RamRoleArn / ...) — never the credential value itself
  4. bindings       --region present, and at least ONE of --project / --workspace
  5. sls_project    the bound SLS project exists
  6. ebpf_logstore  the ebpf-event logstore exists in that project
  7. cms_workspace  the bound CMS 2.0 workspace exists in that region

Configuration only, never data: there are no time-window parameters and no
data-presence probe. Whether a window actually holds rows is the analysis
scripts' job (trace_overview.py reports genai_index_coverage and totals).
There is no auto-discovery mechanism: bindings can only come from the user.

Security: `aliyun configure list` is parsed for the credential TYPE prefix
only; the Credential cell is never echoed. Exit code is 0 for ok/warn, 2 under
--strict when any check failed, and 2 on a hard error (missing --region, no
aliyun on PATH).

Usage:
    python3 preflight.py --region cn-hangzhou [--project P] [--workspace W]
                         [--logstore L] [--strict] [--format json]
"""

import argparse
import json
import os
import re
import subprocess
import sys
import time

import obs_core as c
import sls_event as e
import cms_trace as m

MIN_CLI_VERSION = (3, 3, 3)
REQUIRED_PLUGINS = ("aliyun-cli-sls", "aliyun-cli-cms")
# credential prefixes reported by `aliyun configure list`
KNOWN_CREDENTIAL_TYPES = ("AK", "STS", "RamRoleArn", "EcsRamRole",
                          "ChainableRamRoleArn", "RsaKeyPair", "CredentialsURI")

OK, WARN, FAIL, SKIP = "ok", "warn", "fail", "skipped"
_SEVERITY = {OK: 0, WARN: 1, FAIL: 2, SKIP: 0}

def _run_local(argv, timeout=60):
    """Run a LOCAL aliyun command (no cloud API call, so no --user-agent)."""
    try:
        proc = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except FileNotFoundError:
        raise c.ObsError(
            "aliyun CLI not found on PATH; install it first — see "
            "references/cli-installation-guide.md")
    except subprocess.TimeoutExpired:
        return None, f"{argv[1]} timed out after {timeout}s"
    if proc.returncode != 0:
        return None, (proc.stderr or proc.stdout or "").strip()
    return proc.stdout, None

def check_cli_version():
    out, err = _run_local(["aliyun", "version"])
    if err:
        return FAIL, {"error": err[:200]}, (
            "run the install script or 'aliyun upgrade'; see "
            "references/cli-installation-guide.md")
    m_ = re.search(r"(\d+)\.(\d+)\.(\d+)", out or "")
    if not m_:
        return WARN, {"raw": (out or "").strip()[:80]}, (
            "could not parse the CLI version; verify manually with "
            "'aliyun version'")
    got = tuple(int(x) for x in m_.groups())
    detail = {"version": ".".join(str(x) for x in got),
              "required": ".".join(str(x) for x in MIN_CLI_VERSION)}
    if got < MIN_CLI_VERSION:
        return FAIL, detail, (
            f"aliyun CLI {detail['version']} is older than the required "
            f"{detail['required']}; run 'aliyun upgrade' (CLI >= 3.3.5) or the "
            "install script for a first install")
    return OK, detail, None

def check_plugins():
    out, err = _run_local(["aliyun", "plugin", "list"])
    if err:
        return FAIL, {"error": err[:200]}, (
            "run 'aliyun plugin list' manually to inspect the failure")
    installed = {}
    for line in (out or "").splitlines():
        parts = [p.strip() for p in line.split()]
        if len(parts) >= 2 and parts[0].startswith("aliyun-cli-"):
            installed[parts[0]] = parts[1]
    detail = [{"name": name, "version": installed.get(name),
               "installed": name in installed} for name in REQUIRED_PLUGINS]
    missing = [d["name"] for d in detail if not d["installed"]]
    detail = {"plugins": detail, "missing": missing}
    if missing:
        return FAIL, detail, (
            "run 'aliyun configure set --auto-plugin-install true' then "
            "'aliyun plugin install --names " + " ".join(missing) + "'")
    return OK, detail, None

def _parse_configure_list(out):
    """Parse the `aliyun configure list` table. Returns profiles WITHOUT the
    credential value — only the type prefix is kept."""
    profiles = []
    for line in (out or "").splitlines():
        if "|" not in line or set(line.strip()) <= set("-| "):
            continue
        cells = [x.strip() for x in line.split("|")]
        if len(cells) < 4 or cells[0].lower() == "profile":
            continue
        name = cells[0].replace("*", "").strip()
        cred = cells[1]
        prefix = cred.split(":", 1)[0].strip() if ":" in cred else cred.strip()
        cred_type = prefix if prefix in KNOWN_CREDENTIAL_TYPES else \
            (prefix or "unknown")
        profiles.append({
            "profile": name,
            "active": "*" in cells[0],
            "credential_type": cred_type,
            "credential_recognised": prefix in KNOWN_CREDENTIAL_TYPES,
            # the credential cell is deliberately never carried into the output
            "credential_masked": True,
            "valid": cells[2].lower() == "valid",
            "region": cells[3] or None,
        })
    return profiles

def check_credentials():
    out, err = _run_local(["aliyun", "configure", "list"])
    if err:
        return FAIL, {"error": err[:200]}, (
            "run 'aliyun configure list' manually; configure credentials OUTSIDE "
            "this session and never paste AK/SK into the conversation")
    profiles = _parse_configure_list(out)
    detail = {"profiles": profiles, "profile_count": len(profiles)}
    if not profiles:
        return FAIL, detail, (
            "no profile found: obtain credentials from the RAM console and "
            "configure them OUTSIDE this session ('aliyun configure' in a "
            "terminal, or environment variables in the shell profile), then "
            "re-run; never ask the user to paste AK/SK here")
    valid = [p for p in profiles if p["valid"]]
    if not valid:
        return FAIL, detail, (
            "no VALID profile: reconfigure credentials outside this session and "
            "re-run 'aliyun configure list' to confirm")
    notes = []
    for p in valid:
        if p["credential_type"] == "STS":
            notes.append("STS credentials are temporary and expire "
                         "(InvalidSecurityToken.Expired); reconfigure outside "
                         "this session when they do")
        elif p["credential_type"] in ("RamRoleArn", "ChainableRamRoleArn"):
            notes.append("cross-account AssumeRole: the permissions in "
                         "references/ram-policies.md must be granted to the "
                         "ASSUMED ROLE, not to the caller, and the role's trust "
                         "policy must allow this caller")
        if not p["credential_recognised"]:
            notes.append(f"unrecognised credential type '{p['credential_type']}' "
                         "reported verbatim — not fabricated")
    status = WARN if notes else OK
    detail["notes"] = notes
    return status, detail, None

def check_bindings(args):
    # env var fallback (CLI args take precedence)
    region = args.region or os.environ.get("AGENT_OBS_REGION")
    project = args.project or os.environ.get("AGENT_OBS_SLS_PROJECT")
    workspace = args.workspace or os.environ.get("AGENT_OBS_CMS_WORKSPACE")
    missing = []
    if not region:
        missing.append("--region")
    if not project and not workspace:
        missing.append("--project and/or --workspace (at least ONE required)")
    available = [n for n, v in (("ebpf", project), ("loongsuit", workspace))
                 if v]
    absent = [n for n, v in (("ebpf", project), ("loongsuit", workspace))
              if not v]
    detail = {"region": region, "project": project,
              "workspace": workspace,
              "sources_available": available, "sources_missing": absent,
              "missing": missing,
              "env_vars_used": {
                  "AGENT_OBS_REGION": not args.region and bool(region),
                  "AGENT_OBS_SLS_PROJECT": not args.project and bool(project),
                  "AGENT_OBS_CMS_WORKSPACE": not args.workspace and bool(workspace),
              }}
    if missing:
        return FAIL, detail, (
            "ask the user for the SLS project name (the project holding the "
            "'ebpf-event' logstore) and the CMS 2.0 workspace name (console "
            "label 云监控 2.0 工作空间); supplying only one is allowed (the run "
            "auto-narrows and reports the other as an instrumentation gap). "
            "Bindings come from CLI args or env vars (AGENT_OBS_REGION / "
            "AGENT_OBS_SLS_PROJECT / AGENT_OBS_CMS_WORKSPACE; CLI takes precedence). "
            "There is no auto-discovery mechanism — if the user cannot provide "
            "either name, say so plainly and stop; do not guess or construct "
            "resource names")
    if absent:
        return WARN, detail, None
    return OK, detail, None

def _is_permission_error(msg):
    """Permission failures must be distinguished precisely: a loose substring
    match would mislabel ParameterInvalid-style errors as permission problems
    and send the user off to fix the wrong thing."""
    return any(k in msg for k in ("Forbidden", "NoPermission", "AccessDenied",
                                  "Unauthorized", "not authorized"))

def check_sls(args, cfg):
    """Checks 5 and 6 share one ListLogStores call."""
    if not cfg.project:
        return (SKIP, {"reason": "--project not supplied"}, None), \
               (SKIP, {"reason": "--project not supplied"}, None)
    try:
        stores = e.list_logstores(cfg)
    except c.ObsError as ex:
        msg = str(ex)
        fix = ("grant log:ListLogStores per references/ram-policies.md"
               if _is_permission_error(msg) else
               "confirm the SLS project name and --region with the user")
        return (FAIL, {"error": msg[:400]}, fix), \
               (SKIP, {"reason": "project probe failed"}, None)
    want = (args.logstore.split(",")[0].strip() if args.logstore
            else e.EBPF_LOGSTORE)
    proj_detail = {"project": cfg.project, "logstore_count": len(stores),
                   "logstores": stores[:20]}
    if want in stores:
        ls_status, ls_fix = OK, None
    else:
        ls_status = FAIL
        ls_fix = (f"'{want}' is not in this project: the eBPF collector writes "
                  "runtime facts into that logstore. Confirm the project with "
                  "the user, check that the eBPF producer is installed, or "
                  "override with --logstore")
    ls_detail = {"logstore": want, "present": want in stores,
                 "found": stores[:20]}
    return (OK, proj_detail, None), (ls_status, ls_detail, ls_fix)

def check_workspace(args, cfg):
    if not cfg.workspace:
        return SKIP, {"reason": "--workspace not supplied"}, None
    try:
        workspaces = m.list_workspaces(cfg, workspace_names=[cfg.workspace])
    except c.ObsError as ex:
        msg = str(ex)
        fix = ("grant cms:ListWorkspaces per references/ram-policies.md"
               if _is_permission_error(msg) else
               "confirm the CMS 2.0 workspace name and --region with the user "
               "(the console label is 云监控 2.0 工作空间); there is no "
               "auto-discovery mechanism, so do not guess the name")
        return FAIL, {"error": msg[:400]}, fix
    hit = next((w for w in workspaces
                if w.get("workspaceName") == cfg.workspace), None)
    detail = {"workspace": cfg.workspace, "found": bool(hit),
              "status": (hit or {}).get("status"),
              "sls_project": (hit or {}).get("slsProject"),
              "workspace_id": (hit or {}).get("workspaceId")}
    if not hit:
        return FAIL, detail, (
            f"workspace '{cfg.workspace}' is not in region '{cfg.region}': "
            "confirm the name with the user (the console label is 云监控 2.0 "
            "工作空间); there is no auto-discovery mechanism, so do not guess "
            "or construct the name")
    if (hit or {}).get("status") != "Normal":
        return WARN, detail, None
    return OK, detail, None

CHECKS = [
    ("cli_version", "Aliyun CLI 版本", check_cli_version, False),
    ("plugins", "CLI 插件", check_plugins, False),
    ("credentials", "凭据 profile", check_credentials, False),
]

def build(args):
    if args.no_cache:
        os.environ["AGENT_OBS_NO_CACHE"] = "1"
    # env var fallback (CLI args take precedence)
    region = args.region or os.environ.get("AGENT_OBS_REGION")
    project = args.project or os.environ.get("AGENT_OBS_SLS_PROJECT")
    workspace = args.workspace or os.environ.get("AGENT_OBS_CMS_WORKSPACE")
    if not region:
        raise c.ObsError(
            "missing required --region: both data sources are region-scoped. "
            "Confirm with the user which region the agent runs in, then re-run")
    cfg = c.Config(project=project, logstore=args.logstore,
                   region=region, workspace=workspace)
    checks = []
    for cid, title, fn, _ in CHECKS:
        status, detail, fix = fn()
        checks.append({"id": cid, "title": title, "status": status,
                       "detail": detail,
                       "evidence": {"command": _command_for(cid),
                                    "cloud_api": False, "user_agent": False},
                       "fix": fix})

    b_status, b_detail, b_fix = check_bindings(args)
    checks.append({"id": "bindings", "title": "数据源绑定", "status": b_status,
                   "detail": b_detail,
                   "evidence": {"command": None, "cloud_api": False,
                                "user_agent": False},
                   "fix": b_fix})

    (p_status, p_detail, p_fix), (l_status, l_detail, l_fix) = check_sls(args, cfg)
    checks.append({"id": "sls_project", "title": "SLS project 可达",
                   "status": p_status, "detail": p_detail,
                   "evidence": {"command": "aliyun sls list-log-stores",
                                "cloud_api": True, "user_agent": True},
                   "fix": p_fix})
    checks.append({"id": "ebpf_logstore", "title": "ebpf-event logstore 存在",
                   "status": l_status, "detail": l_detail,
                   "evidence": {"command": "aliyun sls list-log-stores",
                                "cloud_api": True, "user_agent": True},
                   "fix": l_fix})

    w_status, w_detail, w_fix = check_workspace(args, cfg)
    checks.append({"id": "cms_workspace", "title": "CMS 2.0 工作空间存在",
                   "status": w_status, "detail": w_detail,
                   "evidence": {"command": "aliyun cms list-workspaces "
                                           f"--api-version {m.CMS_API_VERSION}",
                                "cloud_api": True, "user_agent": True},
                   "fix": w_fix})

    summary = {s: sum(1 for k in checks if k["status"] == s)
               for s in (OK, WARN, FAIL, SKIP)}
    overall = max(checks, key=lambda k: _SEVERITY[k["status"]])["status"]
    notes = [
        "preflight checks CONFIGURATION only: it never queries data and has no "
        "time-window parameters. Whether a window holds rows is reported by the "
        "analysis scripts (trace_overview.py totals / genai_index_coverage)",
        "a 'skipped' check means that side is not bound — which is a legal "
        "configuration, not a failure; the analysis run then auto-narrows to the "
        "bound source and reports the other as an instrumentation gap",
    ]
    for k in checks:
        notes.extend(k["detail"].get("notes") or [])
    return {
        "skill": c.SKILL_NAME,
        "checked_at": int(time.time()),
        "region": cfg.region,
        "status": overall,
        "binding": {"region": cfg.region, "project": cfg.project,
                    "workspace": cfg.workspace,
                    "sources_available": b_detail["sources_available"],
                    "sources_missing": b_detail["sources_missing"],
                    "env_vars_used": b_detail.get("env_vars_used", {})},
        "checks": checks,
        "summary": summary,
        "notes": notes,
        "cache": c.cache_stats(),
    }

def _command_for(cid):
    return {"cli_version": "aliyun version",
            "plugins": "aliyun plugin list",
            "credentials": "aliyun configure list"}.get(cid)

_STATUS_LABEL = {OK: "通过", WARN: "警告", FAIL: "失败", SKIP: "跳过"}

def main():
    p = argparse.ArgumentParser(
        description="Verify CLI / plugins / credentials / data-source bindings "
                    "before running any analysis (configuration only, never data)")
    p.add_argument("--region", help="REQUIRED: region shared by both data sources")
    p.add_argument("--project", help="eBPF source: the SLS project holding ebpf-event")
    p.add_argument("--workspace", help="LoongSuit source: the CMS 2.0 workspace name")
    p.add_argument("--logstore", help="override the ebpf logstore name checked "
                                      f"(default {e.EBPF_LOGSTORE})")
    p.add_argument("--strict", action="store_true",
                   help="exit 2 when any check failed (default: exit 0 for ok/warn)")
    p.add_argument("--no-cache", dest="no_cache", action="store_true",
                   help="bypass the local result cache (same as AGENT_OBS_NO_CACHE=1)")
    p.add_argument("--format", choices=["json", "yaml"], default="json",
                   help="output format: json (default, stable machine contract) "
                        "or yaml")
    args = p.parse_args()
    result = build(args)
    c.emit(result, args.format)
    if args.strict and result["status"] == FAIL:
        sys.exit(2)

if __name__ == "__main__":
    c.main_wrapper(main)
