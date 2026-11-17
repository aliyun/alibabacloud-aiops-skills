---
name: alibabacloud-ecs-high-frequency-issues
area: unexpected-reboot-diagnosis
description: |
  Locate why an ECS instance rebooted, froze or stopped on its own: platform-recorded crash events, OOM, kernel panic, storage spec-ceiling notices. Queries events, health, monitoring and disks; runs whitelisted non-mutating guest commands only, behind a per-call confirmation gate.
  Use when a server suddenly restarted, crashed, froze or shut down, or a reboot event notice arrived.
  Triggers: instance unexpectedly rebooted; server crashed and restarted on its own; InstanceFailure.Reboot; SystemFailure.Reboot; out of memory (OOM); kernel panic; server froze or hung; cannot create new file after disk full.
  Do NOT use: general Linux OS faults -> alibabacloud-ecs-linux-os-troubleshooting; stuck Stopping or Starting -> area:instance-state-diagnosis; IO tuning -> area:resource-bottleneck; capacity cleanup -> area:disk-expand-diagnosis.
---

# ECS Unexpected Reboot and Crash Diagnosis

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Locates why an ECS instance rebooted, hung or appeared to crash, on one symptom
area only: **the machine came back, froze, or died on its own**. It builds an
evidence chain (system events, health status, monitoring readings, instance
capacity, guest verification), names the most probable failure family with an
honest confidence level, and converges on the two things support tickets
actually converge on: what to do now, and what to deploy so the NEXT
occurrence is diagnosable.

## Scope

In scope:

* Platform crash and redeploy system events (`InstanceFailure.Reboot`,
  `SystemFailure.Reboot`, maintenance and expiry events) with their publish
  times, reasons and lifecycle status.
* Instance facts: power state, health status, vCPU/memory/local-disk capacity,
  public-IP presence, vSwitch, maintenance (auto-recovery) attributes.
* CloudMonitor latest readings aligned against the event timeline to separate
  memory exhaustion, CPU hang and storage spec-ceiling from capacity-full.
* Gated in-guest verification with ONE whitelisted non-mutating command per
  confirmation (capacity and handle evidence: `df -h`, `df -i`, ...).
* Snapshot-first guard (`CreateSnapshot`, gated) before the customer performs
  any cleanup or risky handling; local disks are refused with a backup path.
* Diagnosability readiness guidance: kernel crash dump (kdump), atop,
  monitoring agent, maintenance notification switch - as documented manual
  steps, never installed by this skill.
* Misreport triage: login-path mistakes, "Stopping" intermediate states,
  planned reboots and app-layer faults are IDENTIFIED and handed off.

Out of scope, recognised and handed off rather than attempted: deep Linux OS
debugging, start/stop state recovery, IO performance tuning, capacity
cleanup execution, disk expansion, data recovery from expired snapshots,
third-party panels (e.g. BaoTa), application code. See
[references/unexpected-reboot-diagnosis__handoff-matrix.md](references/unexpected-reboot-diagnosis__handoff-matrix.md).

## Execution Principle

The agent runs the scripts under `scripts/` and nothing else. It never
assembles an `aliyun` command by hand, never calls an OpenAPI action
directly, and never bypasses the entry point to reach a helper module.

| Allowed invocation | Purpose | Cloud calls |
| --- | --- | --- |
| `python3 scripts/areas/unexpected_reboot_diagnosis/sts_token.py` | Credential preflight (run first) | `GetCallerIdentity` |
| `python3 scripts/areas/unexpected_reboot_diagnosis/reboot_diagnosis.py check-auth` | Same preflight through the entry | `GetCallerIdentity` |
| `python3 scripts/areas/unexpected_reboot_diagnosis/reboot_diagnosis.py diagnose` | Full evidence chain and verdicts | the query-class actions in [related_apis.yaml](related_apis.yaml) |
| `python3 scripts/areas/unexpected_reboot_diagnosis/reboot_diagnosis.py guest-probe` | ONE whitelisted non-mutating guest command | `DescribeCloudAssistantStatus`, `RunCommand` (gated), `DescribeInvocations` |
| `python3 scripts/areas/unexpected_reboot_diagnosis/reboot_diagnosis.py create-snapshot` | Snapshot-first guard | `DescribeDisks`, `CreateSnapshot` (gated) |
| `python3 scripts/areas/unexpected_reboot_diagnosis/reboot_diagnosis.py explain` | Interpret pasted guest output | none (offline) |

Typical invocations, run from the skill directory:

```bash
python3 scripts/areas/unexpected_reboot_diagnosis/reboot_diagnosis.py check-auth

python3 scripts/areas/unexpected_reboot_diagnosis/reboot_diagnosis.py diagnose \
  --region-id cn-hangzhou --instance-id i-example0000000001 \
  --event-since 2026-08-27T00:00:00Z --event-until 2026-08-28T00:00:00Z

python3 scripts/areas/unexpected_reboot_diagnosis/reboot_diagnosis.py guest-probe \
  --region-id cn-hangzhou --instance-id i-example0000000001 \
  --command "df -h" --user-confirmed --approval-quote "yes, run df -h"

python3 scripts/areas/unexpected_reboot_diagnosis/reboot_diagnosis.py create-snapshot \
  --region-id cn-hangzhou --disk-id d-example0000000001 --retention-days 7 \
  --user-confirmed --approval-quote "yes, snapshot first"

echo "<pasted guest output>" | python3 scripts/areas/unexpected_reboot_diagnosis/reboot_diagnosis.py explain --paste -
```

If a script fails (non-zero exit, no structured output, credential or
permission error), STOP and report the error. Do not fall back to manual CLI
calls, do not write helper scripts, and do not fabricate values.

## Permission Model and Confirmation Gates (MANDATORY)

**This skill is NOT a query-only package.** It is a diagnosis skill that may,
after explicit customer confirmation, (a) run a non-mutating inspection
command inside the guest through Cloud Assistant, and (b) create a snapshot.
Both are write-class cloud API calls and both sit behind gates that the
scripts themselves enforce:

1. **Tell-then-confirm gate.** Before ANY guest command or write call, tell
   the user, in the conversation: exactly which command will run, on which
   instance, that it changes nothing, whether anything is reversible, and
   (for snapshots) that stored copies bill by capacity and time. Then wait
   for an explicit yes. Only then invoke the subcommand with
   `--user-confirmed` and `--approval-quote "<the customer's verbatim yes>"`.
   One confirmation covers exactly one command; never batch or reuse it.
   The scripts refuse to act without these inputs - the gate is enforced in
   code, not just in this document.
2. **Frozen guest whitelist.** `guest-probe` accepts ONLY the commands
   listed in [references/unexpected-reboot-diagnosis__guest-inspection-whitelist.md](references/unexpected-reboot-diagnosis__guest-inspection-whitelist.md).
   Anything else - log history tools (`atop -r`, `journalctl`, `dmesg`,
   `last`), crash-directory listings, service or system controls, or any
   command containing shell composition tokens (`;`, `|`, `&&`, redirection,
   quotes, backticks) - is REFUSED with a manual-guidance pointer. Do not
   negotiate around the refusal.
3. **Snapshot-first rule.** Before the customer performs any cleanup, space
   release or risky handling, a snapshot of the affected cloud disk is
   MANDATORY (ticket-proven batch policy). Pure evidence gathering is exempt.
   Local disks cannot be snapshotted; the script says so and hands over the
   in-guest backup paths instead.
4. **ABSOLUTE PROHIBITION (destructive).** NEVER execute, generate, or
   "prepare for later" any destructive or state-changing operation: deleting
   or clearing files, formatting, `fsck`/`tune2fs`, killing processes,
   restarting services or instances, start/stop actions, instance redeploy,
   snapshot deletion, security-group or route changes. These are manual-only;
   this skill outputs the exact console path and the official document and
   stops there.
5. **API allowlist.** Only the actions declared in [related_apis.yaml](related_apis.yaml)
   may be reached, and only through the entry scripts. All other actions are
   out of policy even if the identity permits them. The denial of any
   allowlisted action is reported with its NoPermission / ImplicitDeny code
   and the minimal policy fragment from
   [references/ram-policies.md](references/ram-policies.md).

## Credentials

Authentication uses the aliyun CLI default credential chain only (a CLI
profile prepared by the operator). Scripts accept an optional `--profile`
NAME to select an existing profile; they never accept, read, prompt for,
store or print an AccessKey pair or a security token, and the agent must not
either. If the chain is broken or a short-lived token expired, rerun
`check-auth`; on failure, direct the operator to refresh their own CLI
configuration outside this conversation.

## Required Inputs

| Input | Required | Notes |
| --- | --- | --- |
| `--region-id` | yes | e.g. `cn-hangzhou`; ask if unknown |
| `--instance-id` | yes | `i-...`; derive via console facts, never guess |
| incident time window | strongly recommended | `--event-since` / `--event-until` in UTC `YYYY-MM-DDTHH:MM:SSZ`; tickets show customers state times loosely ("around 9am") - confirm the window as a question, then filter |
| OS family | auto-detected | from the Cloud Assistant status; `--os-type` overrides only if the agent reports nothing |
| `--profile` | no | existing CLI profile name |

The incident window is a conversation obligation, not just a flag: when it is
missing, ask before drawing conclusions from "latest" readings.

## Execution Flow

1. **Clarify the narrative.** Was there a console or SMS event notice? Can
   SSH or VNC be reached now? Did the machine come back by itself or only
   after a forced console restart? Roughly when?
2. **Preflight:** run `scripts/areas/unexpected_reboot_diagnosis/sts_token.py` (or `check-auth`).
3. **Evidence chain:** run `diagnose` with the region, instance and, if
   known, the incident window. Relay the sections as-is.
4. **Route by the first verdict** (full playbook:
   [references/unexpected-reboot-diagnosis__diagnosis-playbook.md](references/unexpected-reboot-diagnosis__diagnosis-playbook.md), event
   semantics: [references/unexpected-reboot-diagnosis__event-codebook.md](references/unexpected-reboot-diagnosis__event-codebook.md)):
   - crash event present (`InstanceFailure.Reboot` / `SystemFailure.Reboot`)
     -> family A: correlate event times with monitoring, verify capacity in
     guest (gated `df -h` / `df -i`), then kdump/atop readiness guidance;
   - no event but memory/CPU/load readings saturated -> family B: resource
     exhaustion; process attribution is a MANUAL atop step;
   - disk utilization metrics at the spec ceiling -> family C: explain
     "spec ceiling is not disk full", then hand IO tuning to
     `area:resource-bottleneck`;
   - instance stuck in `Stopping`/`Starting` -> family D: hand off to the
     instance-state skill;
   - expiry, arrears, maintenance reboot or "came up at a set time" ->
     family E: planned activity, clarify and point at the maintenance
     attributes console path;
   - redeploy event + local disks -> family F: data-will-be-wiped warning,
     backup paths, redeploy itself is human;
   - data-loss worry after the crash -> family G: recoverability facts,
     snapshot-first before cleanup; expired-snapshot retrieval is human
     (backend);
   - Running + healthy + no event -> family H: OS is alive; application,
     login-path and security-group self-checks, third-party panels go to
     the vendor.
5. **Guest verification (optional, gated).** One whitelisted command per
   confirmation as per the tell-then-confirm gate; on agent-offline or denial
   the customer runs it themselves and the output goes through `explain`.
6. **Report and converge.** Deliver the verdicts with confidence and
   evidence, the "next occurrence is diagnosable" checklist, the snapshot
   recommendation where cleanup is planned, and handoffs where the fault
   lives on another area.

## Observability

MANDATORY: every Alibaba Cloud API call made by this skill is tagged with a
User-Agent in the template

```
AlibabaCloud-Agent-Skills/{skill_name}/{session_id} skill-version/{skill-version}
```

where `{skill_name}` is `area:unexpected-reboot-diagnosis` and
`{session_id}` is a 32-character lowercase hex string generated once per run
(`uuid.uuid4().hex[:32]`) by `scripts/areas/unexpected_reboot_diagnosis/_cli.py` and attached to EVERY
invocation via the CLI `--user-agent` flag. The same session id is printed in
every report so a customer's API request ids and console audit rows can be
tied back to one conversation.

## Output Contract

The entry script ends with `STATUS: OK | DEGRADED | FAIL` plus a
`NEXT_ACTION:` line. Exit codes: `0` = usable conclusion (OK or DEGRADED),
`1` = no usable conclusion, `2` = usage error.

The agent's final answer MUST:

1. relay the script's sections and verdicts faithfully, including the exact
   `STATUS` and `NEXT_ACTION` lines;
2. quote only values the script returned; anything not returned is stated as
   not returned - never reconstructed from memory;
3. declare the auto-filled inputs (event window default, metric period, UID
   label derivation) as the report lists them;
4. when a guest command or snapshot was confirmed, restate what ran and its
   verbatim output before interpreting it;
5. keep manual-only steps manual: console paths and document links, never
   fabricated commands for destructive operations.

## Degradation and Errors

* Permission denials surface as `NoPermission` / `ImplicitDeny` with the
  failing step name; the minimal policy fragments live in
  [references/ram-policies.md](references/ram-policies.md).
* Cloud Assistant offline, or the write-class actions not granted: the guest
  evidence leg degrades to "customer runs the whitelisted command and pastes
  the output" -> `explain` mode; the report marks the missing leg explicitly.
* CloudMonitor returns no datapoint (fresh instance, agent metrics without
  the OS agent): say so; do not substitute remembered values.
* Transient throttling/5xx is retried with bounded backoff inside the CLI
  layer; persistent failures stay in the degradation log.
* `STATUS: DEGRADED` is still a valid deliverable: report what WAS verified
  and list exactly what could not be.

## Examples

**1. "My server rebooted by itself twice, here is the event mail."**
Inputs: `cn-hangzhou`, `i-example...`, event mail time. Run `check-auth`,
then `diagnose` with the window. `InstanceFailure.Reboot` appears with publish
and finish times; memory reading is high. Family A verdict with a memory
exhaustion context: explain the protective-reboot semantics
([references/unexpected-reboot-diagnosis__event-codebook.md](references/unexpected-reboot-diagnosis__event-codebook.md)), offer the
gated `df -h` probe, and prescribe kdump + atop so the next crash leaves a
trace.

**2. "The site died every afternoon; a forced restart fixes it."**
No events exist; `memory_usedutilization` is absent (no OS agent) while
`CPUUtilization` is saturated; the instance is Running. Family B with low
confidence is honest here: name the missing legs (agent metrics, atop
history), walk the customer through installing the monitoring agent and atop
as MANUAL steps, and set expectations that process attribution needs history
starting now.

**3. "Stopped mid-copy and stuck on Stopping for 15 minutes."**
`diagnose` shows `Status=Stopping`, health Ok, no crash events. Family D:
hand off to `area:instance-state-diagnosis` per the handoff
matrix; if OOM suspicion remains after recovery, family B stays with this
skill - both areas may coexist.

## References

* [references/ram-policies.md](references/ram-policies.md) - every action,
  its permission point, query-vs-gated-write classes, minimal policy
  fragments, and the CMS API-name trap.
* [references/unexpected-reboot-diagnosis__event-codebook.md](references/unexpected-reboot-diagnosis__event-codebook.md) - event type
  semantics, redeploy/local-disk risk wording, the verified metric set.
* [references/unexpected-reboot-diagnosis__guest-inspection-whitelist.md](references/unexpected-reboot-diagnosis__guest-inspection-whitelist.md)
  - the frozen command list, refusal wording, and the manual-only commands.
* [references/unexpected-reboot-diagnosis__diagnosis-playbook.md](references/unexpected-reboot-diagnosis__diagnosis-playbook.md) -
  failure families A-H, decision rules, readiness checklist and document
  links for the "make the next crash diagnosable" step.
* [references/unexpected-reboot-diagnosis__handoff-matrix.md](references/unexpected-reboot-diagnosis__handoff-matrix.md) - what belongs
  to another skill or to a human, and the wording to use.

## Important Notes

1. Auto-reboot after a detected OS crash is protective, not destructive:
   explain the event semantics before the customer blames the platform.
2. Rebooting destroys the fault scene: after the machine is back, the honest
   answer to "which process did it" is often "cannot be established without
   atop or a vmcore" - say so, then set those up as manual steps.
3. "Storage performance reached the spec ceiling" is about bandwidth/IOPS
   limits of the instance type, not about the disk being full; prove either
   claim with the right instrument.
4. Local-disk instances have a data-loss dimension on redeploy; the
   risk warning is part of the diagnosis, not an upsell.
5. This skill never reboots, never restarts services, never cleans files.
   Recovery actions are the customer's, guided by this report.
