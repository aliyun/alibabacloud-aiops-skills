# Remote Execution Reference Guide

This document is the single authoritative reference for executing diagnostic commands on remote ECS instances via Alibaba Cloud CLI (`aliyun ecs run-command`). It governs the CLI transport -- the fallback defined by the Remote transport priority in SKILL.md: when the environment exposes a usable remote command execution tool (e.g., an MCP server tool that sends scripts via Cloud Assistant), prefer that tool and skip the CLI-specific mechanics here (installation, flags, quoting, polling); the command-content rules, timeouts, and output size limits still apply. When the CLI transport is used, this document covers prerequisites, command delivery semantics, the execution pattern, error handling, timeout selection, and output size management. The workflow-level decision rules (when to use this channel, fallback classification) live in the WORKFLOW-GUIDE files; everything "how to" for the CLI transport is here.

## Overview

Remote execution allows troubleshooting Windows ECS instances from any machine with the `aliyun` CLI installed, without needing to be logged into the target instance. Commands are sent via the Cloud Assistant API and executed by the Cloud Assistant agent (AliyunService) running on the target instance.

This execution channel is **orthogonal to the diagnostic mode** -- it applies to both:

- **Online diagnosis (remote)**: Commands sent to the target instance being diagnosed, querying its live running system
- **Offline diagnosis (remote)**: Commands sent to the instance where the faulty system disk is mounted as a data disk, performing offline registry/DISM/disk operations on the mounted disk

| Aspect | Local Execution | Remote Execution |
|--------|----------------|------------------|
| Command delivery | `powershell.exe` | `aliyun ecs run-command` |
| Execution context | Current session | Cloud Assistant agent context (SYSTEM) |
| Result retrieval | Immediate stdout | Poll `aliyun ecs describe-invocation-results` |
| Interactive input | Supported | Not supported |
| Output size | Console buffer | Truncated when oversized (see Output Size Management) |
| Timeout | Runs to completion | Configurable (default 60s, max 86400s) |
| Latency | Milliseconds | Seconds (network + API overhead) |

**Offline-specific considerations for remote execution**:

- The target instance for `RunCommand` is the instance that has the faulty disk **mounted**, not the faulty instance itself
- Offline disk cache (`diag-cache`) is written to the remote instance's temp directory
- Registry HIVE load/unload operations execute on the remote instance against the mounted disk
- DISM operations (`Get-WindowsPackage` / `Get-WindowsDriver`) run on the remote instance; output may be large -- keep output small per Output Size Management below
- The cross-step session memory (drive letters, HIVE paths, etc.) refers to paths on the remote instance's view of the mounted disk

## Prerequisites

Verify all of the following before entering the remote execution channel:

1. **aliyun CLI installed with the ECS plugin**: `aliyun version`. If not installed, provide installation guidance (below) and wait for user confirmation. ECS commands run in **plugin mode** -- both subcommands and flags are kebab-case (`aliyun ecs run-command`, `--biz-region-id`, `--command-content`). The commands are provided by the `aliyun-cli-ecs` plugin; on aliyun CLI 3.x, when the plugin is missing every `aliyun ecs <subcommand>` fails with "'...' is not a valid built-in command". Check with `aliyun plugin list`; if the plugin is absent, install it with `aliyun plugin install --names aliyun-cli-ecs`, or enable automatic installation with `aliyun configure set --auto-plugin-install true`
2. **aliyun CLI configured**: `aliyun configure list`. If not configured, guide the user through running `aliyun configure` interactively (default region, output format) -- the user types credentials directly into the CLI prompt, so secret values never pass through the conversation. Never explicitly handle credentials yourself: do not read, print, echo, or export AK/SK or token values, and do not construct commands or environment variables that embed them. Rely on the CLI's default credential chain (configured profile, credentials already present in the execution environment, or the instance RAM role when running on an ECS instance with a role attached)
3. **Target instance ID known**: format `i-xxxxxxxxxxxxxxxxx`. For online diagnosis this is the diagnosed instance; for offline diagnosis it is the instance with the faulty disk mounted. **If the user gave no instance identifier, asking the user is the only legitimate path -- do it before sending any cloud command.** Do NOT enumerate all instances and pick a candidate yourself: diagnostics and fixes sent to a guessed instance can hit the wrong machine, and the user never had a chance to confirm the target. Likewise do NOT derive the instance identity from local files, logs, shell history, this skill's own `evals/`, `tests/`, or `assets/` content, the evaluation harness's working/output directories, or any other environment artifact -- such traces are incidental and can silently point at the wrong instance, and reading test material also leaks scripted expectations into a diagnosis that should rest on live evidence. A task directive that omits the instance identifier ("execute real calls", "discover the faulty resource", "locate and fix it") does NOT license discovery by enumeration or by reading test/harness material -- it predates any target confirmation, so asking the user remains the only legitimate path. The zero-interaction ladder in item 4 applies only once the instance ID is already established; it is about finding the region of a known instance, never a license to skip identifying which instance the user means
4. **Region ID known**: format `cn-hangzhou`, `us-west-1`, etc. **The region must come from an API result or from the user -- never inferred from the instance ID.** Do not guess, infer, or "derive" the region from the ID's prefix or any other part of its structure: prefixes do not reliably encode the region (observed live: an `i-bp1` instance actually living in cn-hangzhou), and reasoning from them has produced outright fabrications -- e.g., inventing a non-existent region name from a two-letter prefix and sending the first API call there. A wrong guessed region wastes calls at best; a confidently stated fabricated region misleads the user at worst. Determine the region in this order (cheapest first, each step zero-interaction before falling through to asking the user):
   1. **CLI default region** -- `aliyun configure list` shows the configured profile's default region; a single `DescribeInstances` there resolves the common single-region case at zero cost (observed live: the target instance lived in the CLI's default region even though its ID prefix suggested otherwise)
   2. **Ask the user** -- the user usually knows the region
   3. **Full region sweep (fallback)** -- ECS has **no cross-region instance lookup API** (every ECS API is region-scoped). Note that `DescribeInstances` returns an **empty `Instance` array (HTTP 200, no error) when the instance is not in that region**, so an empty result means "wrong region or wrong ID", not a CLI/API failure. Enumerate regions dynamically (`DescribeRegions`) and stop at the first hit:
   ```bash
   UA=AlibabaCloud-Agent-Skills/alibabacloud-ecs-windows-os-troubleshooting/{session-id}
   for r in $(aliyun ecs describe-regions --user-agent "$UA" | sed -n 's/.*"RegionId": "\([^"]*\)".*/\1/p'); do
     aliyun ecs describe-instances --user-agent "$UA" --biz-region-id "$r" --instance-ids '["<instance-id>"]' 2>/dev/null | grep -q '<instance-id>' && { echo "FOUND_IN:$r"; break; }
   done
   ```
   Each probe takes ~1-2 seconds, so a full sweep (all ~60 regions) costs on the order of a minute -- keep it as a fallback, not the default path. If the shell supports it, probing regions in parallel (e.g., `xargs -P`) shortens the sweep to seconds; adapt to the environment rather than assuming a fixed toolset
5. **Target instance Running AND Windows (mandatory gate -- implements the SKILL.md Windows-Only Gate for the remote channel)**:
   ```bash
   aliyun ecs describe-instances --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-windows-os-troubleshooting/{session-id} --biz-region-id <region-id> --instance-ids '["<instance-id>"]'
   ```
   Check `Status` = `Running` and `OSType` = `windows` in the response (an empty result here means wrong region or wrong ID -- see item 4). Both checks ride this single call and are hard gates with different failure semantics:
   - **`OSType` != `windows` -> exit the diagnostic flow entirely**. The whole procedure body of this skill is PowerShell-based Windows diagnosis; on a non-Windows instance those commands fail outright or produce misleading output, and a non-Windows GuestOS is outside the skill's declared scope. Do NOT enter any WORKFLOW-GUIDE, do NOT send any `RunCommand`, and do NOT offer channel fallbacks -- this is a scope boundary, not a channel failure. Tell the user the verified facts (instance ID, region, actual `OSType` value) and the reason the flow stops (this skill supports Windows ECS instances only), then end. The API result is authoritative: it wins even when the user asserted the instance is Windows or the instance name suggests it
   - **`Status` != `Running` -> channel blocker (not a scope exit)**: this channel is unusable until the user starts or repairs the instance via console -- an instance that cannot boot at all (e.g., system disk released; start attempts fail with `InvalidInstance.NotFoundSystemDisk`) is an instance-level blocker no command can fix
   - **`AccessDenied` / `Forbidden.RAM` -> authorization failure, stop and hand over to the user (HITL)**: the CLI identity lacks the RAM Action for this API (here `ecs:DescribeInstances`). This is not transient and not a parameter problem -- an immediate retry with the same identity fails the same way, so retrying first and asking later is prohibited, even when a retry happens to succeed once (a stray success does not mean permission was granted; continuing without the user's knowledge hides a real authorization gap). Name the exact missing Action, point the user at the required_permissions list declared for this skill (Section Authorization Flow on AccessDenied), and END the turn. Send the gate call again only after the user explicitly confirms the grant; if the second attempt is still denied, report the failure and stop instead of retrying further
   
   The Cloud Assistant agent status is not directly visible in `DescribeInstances`; a successful `RunCommand` invocation confirms the agent is operational

Store the verified `RegionId` and `InstanceId` as session context and reuse them for all subsequent remote commands in this diagnostic session. From the same `describe-instances` response, also capture the platform context snapshot fields (`InstanceType`, `PublicIpAddress` / `EipAddress`, `InternetMaxBandwidthOut` / `InternetMaxBandwidthIn`, `SecurityGroupIds`, VPC/private-IP attributes, `ZoneId`, `CreationTime` / `StartTime`) into session context -- they drive platform-side triage at no extra API cost (see [platform-evidence.md](references/online/platform-evidence.md) Section L1).

**Installation** (only if the CLI is missing):

- Linux: `curl --connect-timeout 10 --max-time 60 -fsSL https://aliyuncli.alicdn.com/aliyun-cli-install.sh | bash`
- macOS: `brew install aliyun-cli`
- Windows: download from https://help.aliyun.com/document_detail/121544.html and add to PATH

**Required RAM permissions**: remote-channel APIs only, declared per-action with least privilege (no wildcard policies); the direct execution channel requires no RAM permissions.

## CLI Flag Reference (Tested)

Flag names are **not uniform across plugin subcommands**: most take `--biz-region-id` for the region, but the monitor-data APIs have no region request parameter at all and select the regional endpoint via the global `--region` override. All rows below were verified against `aliyun-cli-ecs 0.7.8` via `aliyun ecs <subcommand> --help`; rows marked * were also exercised end-to-end in a live diagnostic session. The `describe-instance-types` / `describe-images` rows were verified against core CLI `3.4.11` with live calls. When a flag is rejected, read the `Did you mean:` hint in the error output and check `--help` rather than guessing.

| Subcommand | Tested invocation |
| --- | --- |
| `describe-instances` * | `aliyun ecs describe-instances --biz-region-id <region-id> --instance-ids '["<instance-id>"]'` -- from PowerShell 5.1 the JSON quotes MUST be escaped (`'[\"<instance-id>\"]'`) or the call fails with `400 InvalidParameter`; see Section Operator-Shell Quoting below |
| `run-command` * | `aliyun ecs run-command --biz-region-id <region-id> --type RunPowerShellScript --command-content '<script>' --instance-id <instance-id> --name <name> --timeout <seconds>` |
| `describe-invocation-results` * | `aliyun ecs describe-invocation-results --biz-region-id <region-id> --invoke-id <t-prefixed-invocation-id>` |
| `describe-invocations` | `aliyun ecs describe-invocations --biz-region-id <region-id> --instance-id <instance-id>` |
| `describe-regions` * | `aliyun ecs describe-regions` (no flags needed) |
| `describe-instance-monitor-data` * | `aliyun ecs describe-instance-monitor-data --region <region-id> --instance-id <id> --start-time <iso8601> --end-time <iso8601>` -- **rejects `--biz-region-id`** |
| `describe-disk-monitor-data` | `aliyun ecs describe-disk-monitor-data --region <region-id> --disk-id <disk-id> --start-time <iso8601> --end-time <iso8601>` |
| `describe-instance-history-events` * | `aliyun ecs describe-instance-history-events --biz-region-id <region-id> --instance-id <id>` |
| `get-instance-screenshot` | `aliyun ecs get-instance-screenshot --biz-region-id <region-id> --instance-id <id>` |
| `describe-security-group-attribute` | `aliyun ecs describe-security-group-attribute --biz-region-id <region-id> --security-group-id <sg-id>` |
| `describe-disks` | `aliyun ecs describe-disks --biz-region-id <region-id> --instance-id <id>` -- or filter by `--disk-ids '["d-..."]'` when the DiskId is known |
| `describe-instance-types` * | `aliyun ecs describe-instance-types --instance-types <instance-type>` -- no region parameter; response field `NvmeSupport`  in  {`unsupported`, `supported`, `required`} (NVMe applicability gate, [driver.md](references/offline/driver.md) Step 6.0) |
| `describe-images` * | `aliyun ecs describe-images --biz-region-id <region-id> --image-id <image-id>` -- NVMe driver support is `Features.NvmeSupport`  in  {`unsupported`, `supported`}; the field may be absent on old images |

Note: `--instance-id` on `run-command` is a repeatable list (`--instance-id id1 id2 ...`, up to 50), not the API's `InstanceId.N` array form. The global `--user-agent` option (declared in the Observability section below) works appended after the subcommand.

### Operator-Shell Quoting for JSON Arguments

All invocations in the table above are tested from Git Bash, where single quotes are literal and `--instance-ids '["i-..."]'` arrives intact. When the shell running the aliyun CLI is **Windows PowerShell** instead, JSON array arguments break -- this failure has repeated across test runs, so treat it as a known trap and get it right on the first attempt instead of burning a retry:

**Correct-form quick reference** (`--instance-ids` used as the example; applies to every JSON-array flag):

| Operator shell | Correct form | Raw/other form result |
| --- | --- | --- |
| Git Bash | `--instance-ids '["i-..."]'` | -- |
| Windows PowerShell 5.1 | `--instance-ids '[\"i-...\"]'` | raw form -> `400 InvalidParameter` |
| PowerShell 7.3+ | `--instance-ids '["i-..."]'` | 5.1 backslash form -> corrupted JSON |

**Recognition signature**: on PowerShell 5.1 the raw form does NOT produce a "malformed JSON" message -- the API returns a generic `400 InvalidParameter / The specified parameters are not valid` from the ECS endpoint (reproduced: `aliyun ecs describe-instances --biz-region-id cn-hangzhou --instance-ids '["i-..."]'` -> 400 InvalidParameter; same call with `'[\"i-...\"]'` -> 200 with empty instance list). Whenever a JSON-array flag (`--instance-ids`, `--disk-ids`, ...) fails with `400 InvalidParameter` while the operator shell is PowerShell 5.1, diagnose the quoting FIRST before suspecting the parameter values, the region, or the instance.

- **Windows PowerShell 5.1** passes native arguments through C-runtime re-tokenization: the embedded double quotes in `["i-..."]` toggle quote state and are stripped, so `aliyun.exe` receives `[i-...]` -- invalid JSON -- and the API rejects it with `400 InvalidParameter`. The command text looks correct, which is exactly why the first attempt fails and only the retry (escaped quotes) succeeds. Correct form on 5.1: escape each inner double quote with a backslash inside a single-quoted PowerShell string -- `--instance-ids '[\"i-...\"]'` (the backslash is literal in single-quoted strings; the exe-side parser converts `\"` back to `"`). This works because instance IDs contain no spaces -- an argument that both contains spaces and needs embedded quotes cannot be expressed reliably in 5.1 at all
- **PowerShell 7.3+** escapes embedded quotes natively (`PSNativeCommandArgumentPassing`), so pass the raw form `--instance-ids '["i-..."]'` there -- the 5.1 backslash form would deliver literal backslashes and corrupt the JSON again. When the version is unknown, check `$PSVersionTable.PSVersion.Major` before choosing the form
- **Prefer quote-free flag forms where the plugin offers them**: `run-command` accepts the repeatable `--instance-id id1 id2 ...` (see note above), which contains no quotes at all and is immune to this failure class in every shell. Check `--help` for a repeatable form before hand-writing JSON
- **`--command-content` from a PowerShell operator shell**: the Section 12 single-quote wrapping rule is a bash rule and does not apply. Use the documented Base64 mode (`--content-encoding Base64`) instead -- it sidesteps PowerShell string escaping and exe re-tokenization entirely
- **Failure classification**: a stripped-quote rejection is a script-layer (operator-side) error -- fix the quoting and retry the same call. It is not a channel failure, says nothing about the target instance, and must not trigger channel fallback

This is the operator-side twin of WORKFLOW-GUIDE's target-side rule (PowerShell 5.1 on the target instance strips embedded double quotes from arguments passed to native exe tools inside collection scripts): same mechanism, different side of the connection.

## Observability (UA Template and Session-id Rules)

Every `aliyun` CLI call in this channel must be attributable to this skill and to one troubleshooting session. Alibaba Cloud records the User-Agent header per request and keeps Cloud Assistant invocation history, so a consistent UA plus a stable session-id turns a scatter of API calls into one correlated diagnostic run in cloud-side logs (ActionTrail, `aliyun ecs describe-invocations`) -- without them, these calls are indistinguishable from unknown automation touching the instance.

### UA Template

Every CLI invocation in this channel -- send, poll, and describe alike -- carries the platform-standard UA declaration:

```
--user-agent AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}
```

Filled for this skill (SKILL_NAME is the `name` from SKILL.md frontmatter):

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-windows-os-troubleshooting/{session-id}
```

- `AlibabaCloud-Agent-Skills`: fixed platform prefix shared by all agent skills -- do not modify it
- `alibabacloud-ecs-windows-os-troubleshooting`: the SKILL_NAME token, taken literally from SKILL.md frontmatter `name` -- keep it in sync when the skill is renamed
- `{session-id}`: generated once per troubleshooting session, per the rules below
- Filled example: `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-windows-os-troubleshooting/20260814T063025-3f7a`

### Session-id Rules

1. **Generate once per session**: when the remote execution channel is entered -- before the FIRST `aliyun` CLI call, including the prerequisite gate calls in the Prerequisites section above -- generate exactly one session-id -- UTC timestamp plus a short random lowercase-hex suffix. Example: `20260814T063025-3f7a`. Use whatever randomness source the environment offers (e.g., `printf '%04x' $((RANDOM % 65536))` in bash, `'{0:x4}' -f (Get-Random -Maximum 65536)` in PowerShell); the exact suffix source does not matter, uniqueness within the session does
2. **Store in session context**: record it beside `RegionId` and `InstanceId`, and reuse the same value unchanged for every CLI call in this session -- never regenerate per call
3. **Regenerate only on a new task**: a new, unrelated troubleshooting request from the user starts a fresh session-id; retries and continued diagnosis of the same problem keep the existing one
4. **Cover the full chain**: send, poll, and describe calls all carry the same session-id so the entire invocation chain groups under one identifier in cloud-side logs

## Command Delivery Semantics (MUST read before sending)

`CommandContent` carries the script text; `ContentEncoding` tells the server how that content is encoded:

- **Default: plaintext** -- pass the script as-is in `--command-content` and omit `--content-encoding` (server default is `PlainText`). Follow the shell quoting rules of WORKFLOW-GUIDE Section 12 (wrap the full text in single quotes; escape inner single quotes as `''`). Tested: both single-line and multi-line scripts are delivered intact as plaintext -- the direct channel's Base64 requirement for multi-line scripts does NOT apply to `RunCommand`, because the script travels as one API parameter instead of a shell command line. Tested quoting shortcut: write the PowerShell payload using only double-quoted string literals (no single quotes anywhere inside), then the whole payload wraps cleanly in bash single quotes with zero escaping
- **Alternative: Base64** -- only when shell quoting is impractical (e.g., the script itself contains single quotes that are painful to escape), Base64-encode the script and MUST set `--content-encoding Base64`
- **Never mix**: Base64-encoded content sent with `PlainText` encoding is executed as the literal Base64 string and fails

For Windows instances `--type RunPowerShellScript` is required. A single invocation supports up to 50 instances via the repeatable list `--instance-id id1 id2 ...`, though diagnostics normally target one instance.

## Script Encoding (UTF-8 Output)

PowerShell collection scripts MUST set the output encoding to UTF-8 at the very top of the script, before any diagnostic commands:

```powershell
try {
    [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
    $OutputEncoding = [System.Text.Encoding]::UTF8
} catch {
    Write-Host ("WARN utf8-output-encoding: " + $_.Exception.Message)
}
```

Why: Windows PowerShell defaults console output to the system ANSI codepage (GBK on Chinese-locale ECS instances), so Chinese service descriptions, event log messages, and file paths arrive as mojibake after Base64 decoding on the operator side, destroying the localized error text that triage depends on. Setting `[Console]::OutputEncoding` fixes what the console host captures; `$OutputEncoding` fixes piping between PowerShell and native exe tools.

The try/catch guard matters: on hosts running in ConstrainedLanguage mode (or where the .NET type access is restricted), the static property access `[System.Text.Encoding]::UTF8` throws -- the script must degrade to the default codepage with a WARN line instead of dying at line 1 and losing every subsequent diagnostic step. All bundled scripts in `references/online/scripts/` carry this block right after `$ErrorActionPreference = 'Stop'`; scripts you write yourself for ad-hoc commands must follow the same pattern.

## Core Execution Pattern (send -> poll -> decode)

1. **Send**:
   ```bash
   aliyun ecs run-command \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-windows-os-troubleshooting/{session-id} \
     --biz-region-id <region-id> \
     --type RunPowerShellScript \
     --command-content '<powershell-script-plaintext>' \
     --instance-id <instance-id> \
     --name "ecs-troubleshoot" \
     --timeout 120
   ```
   The `--user-agent` value follows the UA template declared in the Observability section above; replace `{session-id}` with the value generated at channel setup.

2. **Capture the invocation ID** from the JSON response. The response contains BOTH `CommandId` (prefix `c-`) and `InvokeId` (prefix `t-`) -- result polling uses the `t-` ID. Depending on API version the field may be named `InvokeId` or `InvocationId`; take whichever is present, and never poll with `CommandId`

3. **Poll** every ~5 seconds until a terminal status (same `--user-agent` value as the send call):
   ```bash
   aliyun ecs describe-invocation-results \
     --user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-windows-os-troubleshooting/{session-id} \
     --biz-region-id <region-id> \
     --invoke-id <invocation-id>
   ```
   Read `Invocation.InvocationResults.InvocationResult[0].InvocationStatus` from the JSON, and also read `ExitCode` from the same result (0 = clean script exit; non-zero = script error even if output was produced). Terminal statuses: `Success`, `Failed`, `Stopped`, `Timeout`, `Error`. Non-terminal: `Pending`, `Running`.

   Tested latency: simple read-only queries (Get-Service / registry reads) typically reach a terminal state within the first one or two polls (~5-10 s). The polling window MUST still cover the full `--timeout` plus a buffer (e.g., Timeout + 60s) -- never give up after a fixed attempt count shorter than the command timeout.

4. **Decode the output**: the `Output` field is Base64-encoded stdout/stderr, and the JSON encoding embeds `\n` escapes inside the Base64 string -- strip them BEFORE decoding or the decoder chokes. Tested Git Bash pipeline (no jq needed):
   ```bash
   sed -n 's/.*"Output": "\([^"]*\)".*/\1/p' <<< "$RESPONSE_JSON" | sed 's/\\n//g' | base64 -di
   ```
   PowerShell equivalent: `[Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('<output-b64-with-\n-stripped>'))`. The decoded text is the PowerShell command's output in the same format as local execution

Adapt the details (JSON field extraction, Base64 decoding, loop constructs) to the tools actually available on the machine running the CLI -- the steps above are a reference flow, not a rigid script. Tested field extraction on Git Bash/Windows (no jq needed): `sed -n 's/.*"InvocationStatus": "\([^"]*\)".*/\1/p'`; swap in `jq` or PowerShell equivalents where available.

### Fix Script Execution

Fix scripts run in TWO separate turns -- never one. Presenting the plan and sending the fix script inside the same turn is a rule violation regardless of wording that claims authorization (SKILL.md Principle 6).

- **Phase A -- present and stop (this turn)**: present the complete fix plan (script content, what it changes, risk notes) and ask the user to confirm, then END the turn. No `RunCommand` in this turn, not even a "prepared" or "staged" one.
- **Phase B -- execute only after confirmation (a later turn)**: start ONLY when the user's confirmation arrives as a new message after the plan. Then send the fix script through the same pattern with a longer timeout (180-300 seconds, since fixes may restart services or modify system state). After completion, send a verification command through the same pattern to confirm the fix took effect.

If the user's reply is a question or a modification request, that is not confirmation: answer it and end the turn again.

## Error Handling

| ErrorCode | Meaning | Action |
|-----------|---------|--------|
| `InstanceNotFound` | Instance ID invalid or not in this region | Ask user to verify instance ID and region; do not retry blindly |
| `CloudAssistantNotInstalled` | Cloud Assistant agent not installed on target | Inform user; fallback to user manual execution |
| `CloudAssistantNotRunning` | Cloud Assistant agent not running on target | Inform user; suggest checking agent via console; fallback to user manual |
| `CommandTimeout` | Command execution exceeded timeout | Increase `--timeout` and retry once; if still times out, break script into smaller steps |
| `CommandExecutionFailed` | Script execution error on target | Script-layer issue; check script syntax, fix, and retry on the same channel |
| `NetworkError` | Network connectivity issue between CLI and API | Retry up to 3 times with 10-second intervals |
| `AccessDenied` / `Forbidden.RAM` | RAM policy lacks the required Action for this API | Authorization failure -- handle per the Authorization Flow on AccessDenied (declared with this skill's RAM permissions): NO retry before the user acts (retrying cannot grant permission, and a stray success on retry does not legitimize continuing silently). State the exact missing Action (e.g. `ecs:DescribeInstances`), give the policy fix, END the turn; retry once only after the user explicitly confirms the grant |
| `Forbidden` | Insufficient permissions to call RunCommand | Same authorization flow as `AccessDenied`: inform the user the RAM policy needs `ecs:RunCommand`, END the turn, retry only after the user confirms the grant |

Read `Code` / `Message` directly from the error JSON response. Classify the failure per the Collection Fallback Chain in the corresponding WORKFLOW-GUIDE: channel-layer failures (delivery/retrieval cannot complete) degrade the channel; script-layer failures (non-zero exit code with clear error output) are fixed in the script and retried on the same channel; timeout failures get one timeout increase before chunking or degrading. Authorization failures (`AccessDenied` / `Forbidden.RAM` / `Forbidden`) are the one exception: they are never channel-layer failures and never degrade -- they route exclusively to the authorization flow in the rows above (state the missing Action, request the grant, END the turn).

`aliyun ecs describe-invocations` lists past invocations for an instance (useful for audit and history).

## Timeout Guidelines

| Script Type | Recommended Timeout | Rationale |
|-------------|-------------------|-----------|
| Single diagnostic step | 60-120 seconds | Most queries complete in seconds |
| Event log queries | 120-180 seconds | Large log scans take longer |
| Complete diagnostic script | 300-600 seconds | Multiple steps, may include WMI queries |
| Fix scripts | 120-300 seconds | May restart services |
| Disk/storage operations | 300-600 seconds | chkdsk, defrag, etc. |
| Network diagnostics | 120-180 seconds | May include connectivity tests with timeouts |

## Output Size Management

Cloud Assistant **truncates command output when it is too large -- truncation has been observed at roughly 10+ KB; the exact limit is undocumented, so treat it as "output will be truncated when oversized" and keep every script's output small**. Strategies:

1. **Limit fields**: `Select-Object` only necessary fields (per the WORKFLOW-GUIDE output style rules)
2. **Limit rows**: `-First N`
3. **Narrow time windows**: for event log queries, prefer hours over days
4. **Break into chunks**: execute one diagnostic step at a time instead of the entire script

**Symptom commands are exempt from output filtering**: for commands whose per-line output IS the diagnostic signal -- `ping`, `tracert`, `pathping`, `Test-NetConnection`, `netsh wfp ...` -- return the FULL raw output without `Select-Object` / `findstr` / pattern filtering. These outputs are small (a 4-reply ping is well under 2 KB, far below the truncation threshold). Filtering them destroys localized error text ("General failure" and its OS-language localized equivalents) which is the primary triage signal. Field/row limiting applies to state-table commands (Get-NetAdapter, Get-NetRoute, event log queries), not to symptom commands.

**Never discard errors or exit codes from collection commands -- analyze them**: error text and exit codes are diagnostic evidence and are frequently the root cause itself; suppressing them removes the most direct signal (same failure class as filtering localized ping output). Concretely: (1) always read `ExitCode` alongside `Output` -- a non-zero exit with useful-looking output is still a failure that must be explained, not ignored; (2) never append `2>$null` / `2>/dev/null` / `| Out-Null` to diagnostic commands -- exe tools (`netsh`, `reg`, `dism`, `sc`) write their only error clues to stderr; (3) `-ErrorAction SilentlyContinue` is acceptable only for ad-hoc state-table collection where a missing cmdlet on old systems is expected -- the resulting absence of output is then itself a finding to state explicitly; the skill's bundled collection scripts (`references/online/scripts/*.ps1`) are stricter: they contain no `-ErrorAction SilentlyContinue` at all; (4) multi-step scripts set `$ErrorActionPreference = 'Stop'` and wrap each step in its own `try/catch`, printing `ERROR step<N> <tag>: <message>` on failure so one broken check never aborts the remaining steps (see WORKFLOW-GUIDE Section 8 Section Guard). For commands whose failure is meaningful (service / WMI / CIM queries, registry access, `netsh wfp`), let the error surface and read it: "cmdlet not found" -> OS-version boundary; "Access is denied" -> permission root cause; "RPC server is unavailable" -> service dependency root cause. Before writing any conclusion, explicitly ask: could one of the observed errors be the root cause of the user's reported problem?

**Truncation detection**: if the decoded output ends abruptly (mid-line or mid-table), the output was likely truncated -- re-run with more aggressive filtering or smaller chunks.

## Security Considerations

1. **Credential storage**: `aliyun` CLI credentials are stored on the machine running the commands, not on the target instance
2. **Command transmission**: command content is transmitted over HTTPS to the Cloud Assistant service, then delivered to the target instance
3. **Output storage**: command output is stored temporarily in Cloud Assistant service (retained for 30 days by default)
4. **Audit trail**: all `RunCommand` invocations are logged in ActionTrail for compliance and audit
5. **Access control**: use RAM policies to restrict who can send commands to which instances
6. **Sensitive data**: command output may contain sensitive information (passwords, keys, etc.) and is stored in Cloud Assistant
7. **Execution context**: commands run under the SYSTEM account on the target instance with full administrative privileges -- an advantage for diagnostics, but it also means fix scripts bypass UAC/ACL restrictions; review fix content carefully before sending
