---
name: alibabacloud-ecs-high-frequency-issues
area: console-channel-diagnosis
description: |
  Layered diagnosis of ECS console channels: VNC / management terminal and web terminals (Workbench, session manager). Routes a failed login to the layer that breaks - instance, cloud configuration, channel, guest, customer-local - from cloud queries plus one gated non-mutating guest command.
  Use when a console remote connection fails, hangs, is intercepted or shows a black screen.
  Triggers: "VNC cannot connect"; "VNC freezes or hangs at login"; "VNC black screen"; "workbench login blocked"; "web terminal cannot log in"; "session manager cannot connect"; "Connection refused"; "InvalidDependence.GrantAccess".
  Routing note (MANDATORY): route by the objective channel symptom even when the customer also guesses another cause (e.g. "suspected disk IO / memory / network problem") - the customer's guess is not an area signal.
  Do NOT use: Remote Desktop black-screen or resolution faults -> the remote-desktop skill; guest boot or system-file damage -> alibabacloud-ecs-linux-os-troubleshooting; capacity, IO, expansion or start/stop faults -> their own skills.
---

# ECS Console Channel Diagnosis (VNC & Web Terminal)

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Diagnoses the two console access channels when they fail: **VNC / the
management terminal** (the rescue path that needs no guest network) and the
**browser web terminals** (Workbench, session manager, one-click connect).
Customer wording is a symptom ("VNC cannot connect", "the web terminal was
blocked"); this skill converts it into a layered verdict: which of the five
layers - instance state, cloud configuration, the channel, the guest system,
the customer-local path - actually breaks, backed by live cloud evidence and
honest degradation where evidence cannot be gathered.

## Trigger Conditions (mirror of the description)

* Use when a console remote connection fails, hangs, is intercepted or shows
  a black screen.
* Triggers (the description's set, one per line):
  * "VNC cannot connect"
  * "workbench login blocked"
  * "web terminal cannot log in"
  * "session manager cannot connect"
  * "Connection refused"
  * "InvalidDependence.GrantAccess"
* Additional wording this skill also handles, listed here rather than in the
  description for length: "VNC stuck at boot screen", "one-click connect
  does not work", "the resource state does not support this operation",
  "no password box appears", "the terminal dropped and killed my job".
* Do NOT use: Remote Desktop black-screen or resolution faults -> the
  Windows remote-desktop diagnosis skill; guest boot / system-file damage ->
  `alibabacloud-ecs-linux-os-troubleshooting`; disk capacity -> the
  disk-capacity diagnosis skill; IO performance ->
  `area:resource-bottleneck`; expansion ->
  `area:disk-expand-diagnosis`; stuck start/stop ->
  `area:instance-state-diagnosis`.

## Scope

In scope:

* Layered triage of every console login path on one symptom area: connect
  opens / login is refused / login works but the session misbehaves.
* Channel fallback matrix: which rescue channel to switch to and why
  (references/console-channel-diagnosis__channel-matrix.md), including the port-22-only nature of
  one-click connect.
* Error-string triage for the tier's quotable codes `Connection refused`
  and `InvalidDependence.GrantAccess` plus observed login-layer wording
  (references/console-channel-diagnosis__error-codes.md).
* Saturation evidence ("every channel hangs at once") from CloudMonitor
  readings, and one gated whitelisted non-mutating guest reading.
* Recognition and structured handoff when the root cause lives on another
  area: boot failure, system-file damage, capacity, IO, lifecycle state.

Out of scope, recognized and handed off rather than attempted: guest OS
repair (fsck, system libraries, lockout-policy surgery), instance
start/stop/reboot execution, disk detach/attach repair, password reset
execution, security-group rule surgery, cleanup of any kind, Windows
Remote Desktop internals, and anything that changes state. See
[references/console-channel-diagnosis__handoff-playbook.md](references/console-channel-diagnosis__handoff-playbook.md).

## Execution Principle

The agent runs the scripts under `scripts/` and nothing else. It never
assembles a CLI command by hand, never calls an OpenAPI action directly,
and never bypasses the entry point to reach a helper module.

| Allowed invocation | Purpose | Cloud calls |
| --- | --- | --- |
| `python3 scripts/areas/console_channel_diagnosis/sts_token.py` | credential preflight (run first) | `GetCallerIdentity` |
| `python3 scripts/areas/console_channel_diagnosis/console_channel_diagnosis.py check-auth` | same preflight through the entry | `GetCallerIdentity` |
| `python3 scripts/areas/console_channel_diagnosis/console_channel_diagnosis.py diagnose` | layered evidence chain and verdicts | the query actions in [related_apis.yaml](related_apis.yaml) |
| `python3 scripts/areas/console_channel_diagnosis/console_channel_diagnosis.py guest-probe` | ONE whitelisted non-mutating guest command, confirmation gate | `DescribeCloudAssistantStatus`, `RunCommand` (gated), `DescribeInvocations` |
| `python3 scripts/areas/console_channel_diagnosis/console_channel_diagnosis.py explain` | offline reading of customer-pasted output | none |

## Permission Model and Confirmation Gates (MANDATORY)

This skill is NOT a query-only package. It runs cloud queries freely, and
it owns exactly one gated capability: dispatching a single whitelisted,
non-mutating inspection command into the customer's instance through the
Cloud Assistant dispatch action `RunCommand`. The gate is enforced in
code, not just in this document.

1. **Tell-then-confirm gate (hard requirement).** Before ANY `guest-probe`
   run, the agent MUST state to the user, in the conversation: the exact
   command that will run, on which instance, that the command only reads
   state and changes nothing, and that the confirmation applies to THIS
   single call. Only after an explicit yes, invoke `guest-probe` with
   `--user-confirmed` and `--approval-quote "<the customer's verbatim
   yes>"`. One confirmation covers one command; never batch or reuse it.
2. **Frozen guest whitelist.** `guest-probe` accepts ONLY the commands
   listed in
   [references/console-channel-diagnosis__guest-inspection-whitelist.md](references/console-channel-diagnosis__guest-inspection-whitelist.md).
   Anything else - listener listings (`ss`/`netstat`), login history,
   log readers, service or system controls, tunnel-software settings, or
   any command containing shell composition tokens (`;`, `|`, `&&`,
   redirections, quotes, backticks) - is REFUSED with a reason and the
   manual path offered instead. Do not negotiate around the refusal.
3. **Human-only destructive lane.** Instance restart/stop, disk detach or
   attach repair, offline password reset execution, `fsck`, lockout
   clearing, security-group rule edits, tunnel-software configuration,
   cleanup of files and release of grant chains are NEVER executed here,
   even after a confirmation. Output the console path, the risk and (where
   one exists) the official document, and stop there.
4. **Snapshot-first wording.** Whenever a manual restart, disk repair or
   other risky human step is suggested, the guidance MUST start with:
   create a snapshot of the affected disks in the console first (billing
   by stored capacity; creation and deletion are the customer's actions).
   This skill never creates snapshots itself.
5. **API allowlist, enforced in code.** Only the actions declared in
   [related_apis.yaml](related_apis.yaml) may be reached, and only through
   the entry scripts. The shared CLI layer refuses anything else before a
   call is attempted: an undeclared action, any name carrying a mutating
   verb, and the single gated write-class action unless the caller marks it
   as the gated dispatch. The denial of any allowlisted action is reported
   with its `NoPermission` / `ImplicitDeny` code and the minimal fragment
   from [references/ram-policies.md](references/ram-policies.md).

## Credentials

The aliyun CLI default credential chain only (an operator-prepared profile).
Scripts accept an optional `--profile` NAME to select an existing profile;
they never accept, read, prompt for, store or print an AccessKey pair or a
security token, and the agent must not either. If the chain is broken,
rerun `check-auth`; the remedy is the operator's own CLI configuration, not
the conversation.

## Required Inputs

| Input | Required | Notes |
| --- | --- | --- |
| `--region-id` | yes | e.g. `cn-hangzhou`; ask if unknown |
| `--instance-id` | yes | `i-...`; never guess |
| `--channel` | recommended | `vnc` / `workbench` / `session-manager` / `one-click` / `ssh-client` / `browser-app` |
| `--symptom` | recommended | observed screen behaviour (cannot-open, black-screen, stuck-at-boot, no-password-prompt, login-rejected, reset-password-ineffective, blocked, timeout, refused, session-drop, garbled-or-laggy, entry-question; defaults to `unknown`) |
| `--error-text` | when available | the customer's error wording normalized to English; keep the verbatim original in the conversation |
| `--service-port` | when relevant | application or ssh port in question |
| `--alt-channel-works` / `--local-channel-fails` / `--third-party-network` / `--session-drop` | flags | customer-observable layer separators (see playbook) |

Script-level flags, in addition to the inputs above:

| Flag | Subcommand | Notes |
| --- | --- | --- |
| `--profile` | all | select an existing CLI profile by NAME; never carries a credential value |
| `--json` | `diagnose` | same report as structured data, for the agent to relay faithfully |
| `--command` | `guest-probe` | the single whitelisted command line, exactly as listed in the whitelist reference |
| `--os-type` | `guest-probe` | `linux` / `windows`; taken from `DescribeCloudAssistantStatus` when omitted |
| `--user-confirmed` + `--approval-quote` | `guest-probe` | the gate inputs (gate 1 above); both mandatory for a dispatch |
| `--paste` | `explain` | `-` (default) reads the customer's pasted text from stdin; or a path to a local text file |

Ask the three opening questions first: instance id + region? OS family
(Linux/Windows)? Which channel, which screen, and what does the error say
verbatim (a screenshot description is fine)?

## Execution Flow

1. **Clarify.** Collect the required inputs above; normalize the error
   wording onto the canonical patterns in `references/console-channel-diagnosis__error-codes.md`
   without inventing detail.
2. **Preflight.** Run `scripts/areas/console_channel_diagnosis/sts_token.py` (or `check-auth`). A RAM
   sub-user caller is itself a finding for CLI login failures.
3. **Evidence chain.** Run `diagnose` with region, instance and the symptom
   flags. It gathers: power state and health (`DescribeInstances`,
   `DescribeInstancesFullStatus`), internal-channel reachability and
   heartbeat (`DescribeCloudAssistantStatus`), recent in-guest execution
   history (`DescribeInvocations`, past records only), and saturation
   readings (`DescribeMetricLast`: CPUUtilization, memory_usedutilization,
   load_1m).
4. **Route by verdict** (full playbook:
   [references/console-channel-diagnosis__diagnosis-playbook.md](references/console-channel-diagnosis__diagnosis-playbook.md)):
   not-Running or stuck transition -> lifecycle lane; saturation with the
   agent unreachable -> hang lane (snapshot, human restart, atop for the
   next occurrence); boot-screen or never-responding guest -> OS-trouble
   handoff; Workbench works while the customer's own path fails -> local
   egress ladder; `Connection refused` -> port triad; every console channel
   refused -> reset-then-restart ordering and the lockout lane;
   `InvalidDependence.GrantAccess` -> reverse-grant release path.
5. **Optional guest reading (gated).** One whitelisted command per
   tell-then-confirm cycle, typically `df -h` for the "logged in but
   nothing writable" pattern. Agent offline or denied -> degrade to
   customer-run output through `explain`.
6. **Report and converge.** Deliver layered findings, verdicts with
   confidence and evidence, manual steps with snapshot-first wording, and
   explicit handoffs where the root cause lives on another area
   (`references/console-channel-diagnosis__handoff-playbook.md`).

## Observability

MANDATORY: every Alibaba Cloud API call made by this skill is tagged with a
User-Agent in the template

```
AlibabaCloud-Agent-Skills/{skill_name}/{session_id} skill-version/{skill-version}
```

where `{skill_name}` is `area:console-channel-diagnosis` and
`{session_id}` is a 32-character lowercase hex string generated once per run
(`uuid.uuid4().hex[:32]`) by `scripts/areas/console_channel_diagnosis/_cli.py` and attached to EVERY
invocation via the CLI `--user-agent` flag. The same session id is printed
in every report so request ids and audit rows from one conversation can be
tied together.

## Output Contract

The entry script ends with `STATUS: OK | DEGRADED | FAIL` plus a
`NEXT_ACTION:` line. Exit codes: `0` = usable conclusion (OK or DEGRADED),
`1` = no usable conclusion, `2` = usage error.

The agent's final answer MUST:

1. relay the script's sections and verdicts faithfully, including the exact
   `STATUS` and `NEXT_ACTION` lines;
2. quote only values the script returned; anything not returned is stated
   as not returned - never reconstructed from memory;
3. declare auto-filled inputs (UID label derivation, metric period) as the
   report lists them;
4. when a gated command ran, restate the command and its verbatim output
   before interpreting it;
5. keep human-only steps human: console paths and document links, never
   fabricated commands for destructive operations.

## Degradation and Errors

* Permission denials surface as `NoPermission` / `ImplicitDeny` with the
  failing step name; minimal fragments live in
  [references/ram-policies.md](references/ram-policies.md).
* Cloud Assistant offline: the guest evidence leg degrades to "customer
  runs the whitelisted command and pastes the output" -> `explain`. Say so
  explicitly; a hung guest often cannot answer its own agent.
* CloudMonitor returns no datapoint (fresh instance; guest-OS metrics need
  the CloudMonitor agent installed inside): state it; do not substitute
  remembered values.
* Security-group RULE details and in-guest listeners stay outside this
  skill's verified action set: guide the console self-check or the
  customer-paste path; never claim them as checked.
* Transient throttling/5xx is retried with bounded backoff inside the CLI
  layer; persistent failures stay in the degradation log.
* `STATUS: DEGRADED` is still a valid deliverable: report what WAS
  verified and list exactly what could not be.

## Examples

1. Customer: "I click VNC and it says the operation is not supported for
   the resource state, what is broken?"
   Agent runs `diagnose --channel vnc --symptom cannot-open --error-text
   "the current state of the resource does not support this operation"` ->
   reads the power-state layer first -> explains the lifecycle state,
   routes a stuck transition to the instance-state skill.
2. Customer: "Workbench passwordless login says it is blocked; SSH is also
   dead since last night."
   Agent runs `diagnose --channel workbench --symptom blocked` -> memory
   datapoint near 100% -> hang lane: snapshot-first, human restart, atop
   afterwards; optional gated `df -h` reading as corroboration while the
   agent still answers.
3. Customer: "Changing the VPC fails with InvalidDependence.GrantAccess."
   Agent matches the code -> explains the Workbench reverse-access grant
   chain and gives the human console path; no guest command is needed.

## References

| File | Content |
| --- | --- |
| [references/console-channel-diagnosis__diagnosis-playbook.md](references/console-channel-diagnosis__diagnosis-playbook.md) | five-layer model, symptom-to-verdict routing table, ticket-proven root-cause frequencies |
| [references/console-channel-diagnosis__channel-matrix.md](references/console-channel-diagnosis__channel-matrix.md) | login-method comparison, fallback chains, entry paths, per-channel quirks |
| [references/console-channel-diagnosis__error-codes.md](references/console-channel-diagnosis__error-codes.md) | canonical error strings, `Connection refused`, `InvalidDependence.GrantAccess`, login wording triage |
| [references/console-channel-diagnosis__guest-inspection-whitelist.md](references/console-channel-diagnosis__guest-inspection-whitelist.md) | the frozen non-mutating command set and refusal policy |
| [references/console-channel-diagnosis__handoff-playbook.md](references/console-channel-diagnosis__handoff-playbook.md) | handoff templates: OS trouble, instance state, capacity, IO, expansion, remote desktop, human support |
| [references/ram-policies.md](references/ram-policies.md) | exact permission points, query and gated dispatch |

## Important Notes

1. The console channel is usually the MESSENGER, not the fault: most
   tickets on this area end in a guest-layer root cause. Say which layer
   the evidence points at, with its confidence, and hand off cleanly
   instead of retrying the same screen.
2. "Workbench works but my own SSH does not" is evidence AGAINST the
   instance and FOR the customer-side path (the web terminal uses
   Alibaba Cloud's internal path). "Web terminal disconnected" is NOT a
   server reboot; foreground tasks die with the session - nohup/screen is
   the standard answer.
3. A VNC that opens to a login prompt but never shows the password box is
   the classic hung-guest signature; the agent heartbeat and monitoring
   readings confirm or refute it within seconds.
4. Deep in-guest facts (listeners, lockouts, damaged libraries) are NOT
   auto-inspectable in this tier: ask, receive, interpret via `explain`,
   and keep the evidence list for whoever repairs the guest.
5. This skill never reboots, never resets passwords, never edits security
   groups, never releases grant chains, never cleans disks. Recovery is
   the customer's, guided by this report.
