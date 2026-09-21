
# Live-Debug Runtime Diagnostics

> **Product scope**: This skill builds and manages **Live-Debug ServiceTask** diagnostics on Alibaba Cloud CMS (`aliyun cms2 apm service-task`) and queries capture results via SLS. It does **not** onboard APM/agents and is **not** a general CloudMonitor (CMS) management skill.

## Parameter-Completeness Gate (Before Prerequisites)

Apply this gate immediately after routing to Live-Debug, before any prerequisite check, local environment inspection, credential check, workspace/service discovery, output-file creation, or cloud call.

- If the request lacks the application language (Java or Python), region, workspace (or permission to discover it), target service (serviceId or serviceName), or diagnostic target/goal (for example class + method and dynamic log vs snapshot vs thread/memory inspection), state which information is missing and **stop the turn**. Return that clarification as the completed final answer for the current request, not as a request for another message. Use a declarative heading such as `Required inputs for a future run:` followed by the missing fields. The response MUST NOT contain a question mark or any request/invitation phrase, including `please provide`, `provide`, `send`, `reply`, `tell me`, `can you`, `could you`, `请提供`, `请补充`, `提供`, `补充`, `告知`, or `回复`. End exactly with: `No diagnostic or cloud action was executed; this run is complete.` Do not enter an interactive question/HITL tool or leave the task itself in a waiting state. A later request that already contains the listed fields may start a new workflow.
- In that clarification response, mention that Java supports JVM commands plus LOG/SNAPSHOT probes, while Python supports LOG/SNAPSHOT/METRIC/SPAN/SPAN_TAG probes only.
- Do not try to infer the target by enumerating workspaces or services, and do not run `--help`, `aliyun version`, `aliyun configure list`, or any other command first. Discovery starts only after the user supplies enough targeting information or explicitly asks you to discover a named workspace/service.
- A fully specified request may proceed directly. Explicit user constraints such as “the environment is ready” or “do not run `--help`” override the corresponding optional prerequisite probes for that workflow.

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

Required RAM permissions - see [live-debug-ram-policies.md](live-debug-ram-policies.md).

## Observability

Before generating the User-Agent or issuing any cloud request, apply the root [skill version gate](../SKILL.md#shared-conventions): read `references/manifest.json`, require its non-empty string `version`, and stop on any read or validation failure. Use that exact value as `{version}`; never infer a fallback. The companion scripts enforce this gate themselves.

### User-Agent Template

Every `aliyun` CLI command (`aliyun cms2`, `aliyun sls`) in this skill **MUST** include the `--user-agent` flag:

```text
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-management/skill-version/{version}/{session-id}"
```

Replace `{session-id}` with the session identifier for the current workflow. The companion scripts append this automatically when `LIVE_DEBUG_SESSION_ID` is set.

Example:

```bash
aliyun cms2 apm service-task list \
 --workspace agentloop-0a1b2c3d4e5f60718293a4b5c6d7e8f9 \
 --service-id 'ggxw4lnjuz@f2fd3a6265a254a052afb' \
 --type live_debug_log_probe \
 --region cn-hangzhou \
 --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-agentloop-management/skill-version/1.0.0/3f2a8b1c4d5e6f709182a3b4c5d6e7f8"
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

> For a fully specified workflow, normally run `aliyun cms2 apm service-task <subcommand> --help` first to get the full flag list and examples. Skip it when the user explicitly says the environment is ready or forbids `--help`; never run it before the parameter-completeness gate.

- **Read `.arms-info` first**: the target workspace / serviceId / regionId / slsProject / targetIp are read from the `.arms-info` file in the project root (`key=value`); ask the user only for missing values. Before calling any script, export `LIVE_DEBUG_REGION_ID` (and `LIVE_DEBUG_SLS_PROJECT`) from it - do not rely on the local `aliyun configure` default region.
- **Workspace discovery**: when no workspace is given by `.arms-info` or the user, run `aliyun cms2 workspace list` and pick an existing workspace that matches the naming the user requires (e.g. `agentloop-{32 hex chars}`). **Never invent a workspace ID**, and never pass a workspace format the user has explicitly forbidden to `--workspace`.
- **Preserve exact user-provided resource names**: when the user specifies a literal name or prefix plus a generated suffix (for example `eval-livedebug-clear-` + `HHmmss`), materialize that exact value before the create call and reuse it unchanged for create, verification, and cleanup. Do not shorten, normalize, or drop any part of the supplied prefix.
- **Resolve serviceId by name when needed**: if the user only knows a service name / tag, run `aliyun cms2 apm service list` and filter by `serviceName` to resolve the `serviceId` first. If multiple candidates match, list them and ask the user to confirm - do not pick one silently.
- **Clarify vague requests before acting**: enforce the parameter-completeness gate above. Never guess or fabricate a workspace / serviceId / taskId, and never create or delete tasks based on guessed targets.
- **Temporary service body**: for `aliyun cms2 apm service create --body`, `attributes` is a JSON-encoded **string**, not a nested object. For Java use `{"serviceName":"<name>","serviceType":"TRACE","attributes":"{\"language\":\"java\"}"}`; for Python replace `java` with `python`. Construct this correctly on the first attempt so local request decoding does not mask a service-side error that the retry protocol must classify.
- **Prefer `-o json`** for ServiceTask calls (the scripts already do); CLI output is wrapped as `{"success":true,"data":{...}}`.
- **taskConfig is inline flat JSON**: pass a single command/probe object directly as the `--task-config` value; do not wrap it in a `commands`/`probes` array and do not use `@file` indirection. Before the first create attempt, verify the inline object already has `target.instanceIds` for probes (or top-level `instanceIds` for Java commands), no `taskId`, and the exact task type.
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
| Parameter error | `InvalidParameter.*`, `MissingParameter`, `instanceIds is required` | Read the message and re-check the already-inline taskConfig against [live-debug.md](live-debug.md) (flat JSON, `instanceIds` placement, no taskId, correct taskType). If it already conforms, explicitly classify the next call as a **retry** and retry the exact same command unchanged once; do not change quoting style or switch between inline JSON and `@file`. Only when an objective field error exists, correct that field and then retry. |
| Permission error | HTTP 403, `Unauthorized`, `Forbidden`, `NoPermission`, `...denied access... action: log:GetLogStoreLogs` | **Do NOT retry.** Classify the blocked query explicitly as **requiring manual operator intervention**, keep the affected query/work item pending rather than marking it successfully completed, identify which RAM action is missing, give the user a concrete authorization suggestion per [live-debug-ram-policies.md](live-debug-ram-policies.md), and report honestly that the call failed and no data was retrieved. Independent cleanup explicitly requested in the same workflow may still proceed. |
| Not found / region | `ProjectNotExist`, `TaskNotFound` | Check region consistency (the SLS project region must match `--region`) and identifiers, correct, then retry. |

After exhausting retries, report the **last error verbatim** (code, message, requestId) and stop. An honest failure report is the required outcome; fabricated or guessed results are never acceptable.

## Module Routing

| User Intent Keywords | Commands | Module |
|---------------------|----------|--------|
| live-debug, ServiceTask, dynamic logging, log probe, snapshot probe, metric probe, span probe, span tag, disable/clear probes, inspect running JVM, OGNL, decompile, thread info, memory info, runtime diagnostics, query capture results | `apm service-task` scripts in [../scripts/live-debug/](../scripts/live-debug/) | [live-debug.md](live-debug.md) |

Commands not listed above - see `aliyun cms2 apm service-task --help`.
