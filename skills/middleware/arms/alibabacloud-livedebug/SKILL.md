---
name: alibabacloud-livedebug
description: "Live-Debug runtime diagnostics: dynamic logging, method snapshots, dynamic metrics, dynamic spans, and JVM inspection. Use for live-debug ServiceTask on Alibaba Cloud CMS (aliyun cms2 apm service-task): dynamic log/snapshot/metric/span probes, Java JVM commands (OGNL evaluate, decompile, thread info, memory info, inspect object, search type/method, runtime info), disable/clear probes, and query capture results via SLS. Java supports commands + LOG/SNAPSHOT probes; Python supports LOG/SNAPSHOT/METRIC/SPAN/SPAN_TAG probes only. Synonyms: live debug, service task, probe, dynamic logging, method snapshot, take a snapshot, inspect running JVM, runtime diagnostics. Do NOT use for APM/agent onboarding, CMS alerts, RUM, Prometheus rules, or billing."
license: Apache-2.0
compatibility: "aliyun-cli>=3.3.15"
metadata:
  domain: aiops
  owner: agentloop
  contact: agentloop@alibaba-inc.com
---

# Live-Debug Runtime Diagnostics

> **Product scope**: This skill builds and manages **Live-Debug ServiceTask** diagnostics on Alibaba Cloud CMS (`aliyun cms2 apm service-task`) and queries capture results via SLS. It does **not** onboard APM/agents and is **not** a general CloudMonitor (CMS) management skill.

## Prerequisite Check

1. **Check `aliyun` exists** - `which aliyun` (macOS/Linux) or `where aliyun` (Windows).
 - Not found -> ask the user to install the aliyun CLI first: <https://help.aliyun.com/document_detail/121541.html>. Stop and wait.

2. **Check CLI version** - run `aliyun version`. Minimum required: **3.3.15** (see `compatibility` in frontmatter).

 > WARNING: Compare version segments as **integers** (semver): 3.3.4 < 3.3.15 because 4 < 15.
 > Shell verification: `printf '%s\n' "3.3.15" "$(aliyun version)" | sort -V | head -1`
 > If the output equals the current version, the requirement is NOT met.

 - Version OK -> go to step 3.
 - Version too old or unrecognized ->
 1. Run `aliyun upgrade --help` to test whether the `upgrade` subcommand exists.
 - Available -> run `aliyun upgrade -y`, then re-check `aliyun version`.
 - Not available (or the upgrade fails) -> ask the user to reinstall/upgrade the CLI manually from the official guides: install <https://help.aliyun.com/zh/cli/install-cli>, update <https://help.aliyun.com/zh/cli/update-cli>. **Do NOT pipe remote install scripts directly into a shell interpreter** - download the installer, inspect it, then run it deliberately, or use the OS package manager. Stop and wait.
 2. If the upgrade succeeded -> go to step 3.

3. **Check `cms2` plugin** - run `aliyun cms2 apm service-task --help`.
 - Help output OK -> continue.
 - `unknown command` / missing -> the CMS ServiceTask capability is provided by the `aliyuncms2` plugin binary. Confirm it is placed in `~/.aliyun/` (or PATH) and is executable:
   ```bash
   ls -l ~/.aliyun/aliyuncms2
   chmod +x ~/.aliyun/aliyuncms2
   aliyun cms2 apm service-task --help
   ```
   If it still fails, run `aliyun upgrade -y` and retry. If unresolved, **stop** and report the error (append CLI version, OS, and error message).

4. **Check SLS** - run `aliyun sls --help` (required to query capture results).

## Credentials

`aliyun cms2` and `aliyun sls` reuse the aliyun CLI credential system (`aliyun configure`).
Use `--profile <name>` to switch profiles. A **RAM sub-account** with read/write on CMS ServiceTask and query permissions on the target SLS project is recommended.

Required RAM permissions - see [references/ram-policies.md](references/ram-policies.md).

## Observability

### User-Agent Template

Every `aliyun` CLI command (`aliyun cms2`, `aliyun sls`) in this skill **MUST** include the `--user-agent` flag:

```text
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-livedebug/{session-id}"
```

Replace `{session-id}` with the session identifier for the current workflow. The companion scripts append this automatically when `LIVE_DEBUG_SESSION_ID` is set.

Example:

```bash
aliyun cms2 apm service-task list \
 --workspace agentloop-0a1b2c3d4e5f60718293a4b5c6d7e8f9 \
 --service-id 'ggxw4lnjuz@f2fd3a6265a254a052afb' \
 --type live_debug_log_probe \
 --region cn-hangzhou \
 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-livedebug/3f2a8b1c4d5e6f709182a3b4c5d6e7f8"
```

### session-id Rule

1. **Generate once** at the start of each skill-triggered workflow.
2. **Format**: exactly **32 lowercase hexadecimal characters**, no hyphens, no prefix.
3. **Reuse** the same `session-id` for **all** CLI commands within the same workflow so backend logs can be correlated across steps.
4. **Do NOT** regenerate `session-id` between steps of the same request.
5. **Generation** (pick one):

```bash
# Preferred
openssl rand -hex 16

# Alternative
uuidgen | tr -d '-' | tr '[:upper:]' '[:lower:]'
```

## Global Conventions

> **Always run `aliyun cms2 apm service-task <subcommand> --help` first** to get the full flag list and examples.

- **Read `.arms-info` first**: the target workspace / serviceId / regionId / slsProject / targetIp are read from the `.arms-info` file in the project root (`key=value`); ask the user only for missing values. Before calling any script, export `LIVE_DEBUG_REGION_ID` (and `LIVE_DEBUG_SLS_PROJECT`) from it - do not rely on the local `aliyun configure` default region.
- **Workspace discovery**: when no workspace is given by `.arms-info` or the user, run `aliyun cms2 workspace list` and pick an existing workspace that matches the naming the user requires (e.g. `agentloop-{32 hex chars}`). **Never invent a workspace ID**, and never pass a workspace format the user has explicitly forbidden to `--workspace`.
- **Resolve serviceId by name when needed**: if the user only knows a service name / tag, run `aliyun cms2 apm service list` and filter by `serviceName` to resolve the `serviceId` first. If multiple candidates match, list them and ask the user to confirm - do not pick one silently.
- **Clarify vague requests before acting**: if the request lacks the application language (Java vs Python - the supported capabilities differ), region, workspace, target service, or the diagnostic goal (e.g. dynamic logging vs snapshot vs thread/memory info), ask for the missing pieces first. Never guess or fabricate a workspace / serviceId / taskId, and never create or delete tasks based on guessed targets.
- **Prefer `-o json`** for ServiceTask calls (the scripts already do); CLI output is wrapped as `{"success":true,"data":{...}}`.
- **taskConfig is flat JSON**: pass a single command/probe object; do not wrap it in a `commands`/`probes` array.
- **To disable a probe, use Delete** (`delete_task.sh` / `delete_all_probes.sh`); creating an `enabled:false` task does not stop a dispatched probe.

## Execution Safety

Destructive mutations (deleting tasks/probes) follow a Two-Phase Execution Protocol:

1. **Phase A (Plan)**: output the exact delete commands, targets, and impact - then **stop and wait**.
2. **Phase B (Execute)**: run the delete only after the user's **next** message contains explicit approval (`yes`, `confirm`, `proceed`, `go ahead`).

Exception: when the user's **initial prompt** already explicitly requests deleting a probe/task created in the **same** workflow (common in eval cleanup), show a one-line delete plan inline and execute in the same turn. Never interpret silence as approval.

Read-only operations (create/list/get, SLS result queries) execute directly.

## Error Handling & Retry

Failed CLI calls exit non-zero and print a JSON envelope with an error code, e.g. `{"success":false,"code":"Throttling.User","message":"...","requestId":"..."}` (SLS uses `errorCode`/`errorMessage`). **Parse the code and follow this table - never abandon the workflow silently, and never fabricate a taskId, task status, or capture results.**

Recovery protocol (applies to every failed command):

1. **Run each mutation as its own command invocation.** Do not chain multiple `aliyun` mutations with `&&`/`;` in one shell command, and do not wrap them in retry loops (`for`/`until`) that swallow errors - a failure must surface individually so it can be diagnosed.
2. **Classify out loud, then act.** When a command fails, first state the returned error `code` and its class from the table below (e.g. "`InternalError` -> transient server fault, retrying"), then execute the recovery as a **separate** follow-up command.
3. **Retry the same command unchanged.** For transient classes (throttling / server error), re-run the exact same command with identical flags after a short `sleep`; do not reorder, reword, or "fix" flags that were not at fault.

| Error class | Typical codes / signals | Action |
|---|---|---|
| Throttling | `Throttling`, `Throttling.User`, HTTP 429, "flow control" | Transient rate limiting. Wait briefly (e.g. `sleep 5`), then **retry the same command unchanged**. Back off and retry up to 3 attempts. |
| Server error | `InternalError`, `ServiceUnavailable`, HTTP 5xx | Transient server fault. Wait briefly and **retry the same command**, up to 3 attempts. |
| Parameter error | `InvalidParameter.*`, `MissingParameter`, `instanceIds is required` | Read the message, re-check the taskConfig against [references/live-debug.md](references/live-debug.md) (flat JSON, `instanceIds` placement, no taskId, correct taskType). Fix any real mistake and retry; if the parameters are verified correct, retry once anyway - transient validation faults happen. |
| Permission error | HTTP 403, `Unauthorized`, `Forbidden`, `NoPermission`, `...denied access... action: log:GetLogStoreLogs` | **Do NOT retry.** Identify which RAM action is missing, give the user a concrete authorization suggestion per [references/ram-policies.md](references/ram-policies.md), and report honestly that the call failed and no data was retrieved. |
| Not found / region | `ProjectNotExist`, `TaskNotFound` | Check region consistency (the SLS project region must match `--region`) and identifiers, correct, then retry. |

After exhausting retries, report the **last error verbatim** (code, message, requestId) and stop. An honest failure report is the required outcome; fabricated or guessed results are never acceptable.

## Module Routing

| User Intent Keywords | Commands | Module |
|---------------------|----------|--------|
| live-debug, ServiceTask, dynamic logging, log probe, snapshot probe, metric probe, span probe, span tag, disable/clear probes, inspect running JVM, OGNL, decompile, thread info, memory info, runtime diagnostics, query capture results | `apm service-task` scripts in [scripts/live-debug/](scripts/live-debug/) | [references/live-debug.md](references/live-debug.md) |

Commands not listed above - see `aliyun cms2 apm service-task --help`.
