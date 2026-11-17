---
name: alibabacloud-ecs-high-frequency-issues
area: instance-state-diagnosis
description: |
  Diagnoses Alibaba Cloud ECS instance start/stop state anomalies: an instance that will not start, stays stuck in Stopping or Starting, or cannot be entered after a reboot. Cloud-side evidence comes from query-only OpenAPI calls; exactly one whitelisted in-guest diagnostic command may be sent after the customer confirms it. Output is a layered verdict plus manual console steps.
  Use when the instance state machine or the boot process itself is the reported symptom.
  Triggers: cannot start the instance; instance stuck in Stopping; restart never completes; cannot log in after reboot; server hung after upgrade; long time in Starting; OperationDenied.NoStock; grub > rescue prompt.
  Do NOT use for guest service or middleware faults (use alibabacloud-ecs-linux-os-troubleshooting), disk capacity or inode cleanup, disk IO performance, or partition expansion.
---

# Alibaba Cloud ECS Instance Start/Stop State Diagnosis

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Answer one question for the customer: **at which layer did the start/stop state machine or
the boot process break** -- control plane, platform event, guest boot stage, or inside the
OS -- and what must a human do next. The deliverable is an evidence table, one layered
verdict, and manual console steps. This skill does not repair anything by itself.

## Permission model: this skill is NOT declared query-only

The tier is **RO+G**: cloud queries plus query-only in-guest diagnostics plus
manual guidance. Never describe this skill as query-only, and never treat the rules below
as optional politeness -- weak models ignore soft wording.

| Class | What it covers | Execution gate |
|---|---|---|
| A | Cloud queries: `Describe*` on ECS, `sts get-caller-identity` | Run automatically; every call is logged into the evidence table |
| B | **One** whitelisted diagnostic command inside the guest, sent via `RunCommand` (write-class API; RAM action point `ecs:run-command`) | BLOCKED until the customer confirms that one command: state the exact command, the target instance, that it only reports, and that it is reversible because it changes nothing |
| C | Snapshot before any cleanup/repair/stop-restart guidance | The customer performs it in the console; this skill **never calls a snapshot API**, it emits the steps, the billing note and the risk notes |
| D | Instance start/stop/reboot, force stop, service restart, snapshot rollback, disk re-initialization, attach/detach or repair disk, file cleanup, boot-file edits, renewal and type change | **NEVER invoked by this skill.** Manual console steps + risk disclosure only |

`RunCommand` (RAM action point `ecs:run-command`) is the only write-class action this skill
can reach, and only through the
class-B gate above. Everything else in class D is guidance.

## ABSOLUTE PROHIBITION

- Never call, and never build a CLI invocation for, any action outside the whitelist below.
  `Start*`, `Stop*`, `Reboot*`, `Modify*`, `Create*`, `Delete*`, `Attach*`, `Detach*`,
  `Reset*`, `Rollback*`, `Replace*`, `Renew*` are all out of scope, including "here, run
  this yourself" variants that the skill then executes on the customer's behalf.
- One guest command per whitelisted name per run, and never dispatch a
  command that is not an exact key of the whitelist in
  `references/instance-state-diagnosis__guest-diagnostic-commands.md`. Any command containing a side-effecting token
  (`rm`, `mv`, `dd`, `mkfs`, `truncate`, `kill`, `reboot`, `shutdown`, `mount`, `umount`,
  `sed -i`, `chmod`, `chown`, `chattr`, `passwd`, redirectors `>` / `>>`, `systemctl`
  change verbs) is refused with a reason, not "cleaned up" and run.
- Never assert a cause the evidence does not show. If a query failed or a reading is
  missing, say so in LIMITATIONS and set `STATUS: DEGRADED`.
- Never invent an error code. Only codes quoted by the customer (or the console state
  text) are routed; unknown text goes to the manual VNC observation step.
- Never handle key material. See "Credentials and safety".

## Supported API surface (whitelist)

| Product / CLI | Action | Class | Purpose in the decision tree |
|---|---|---|---|
| `aliyun ecs describe-instances` | `DescribeInstances` | A | Current control-plane status, operation locks -- the spine of every run |
| `aliyun ecs describe-instance-status` | `DescribeInstanceStatus` | A | Independent status cross-check, batch of instances |
| `aliyun ecs describe-instances-full-status` | `DescribeInstancesFullStatus` | A | Health status + scheduled system events |
| `aliyun ecs describe-instance-history-events` | `DescribeInstanceHistoryEvents` | A | Platform-initiated event history per instance |
| `aliyun ecs describe-cloud-assistant-status` | `DescribeCloudAssistantStatus` | A | Gate for class B: is the guest channel reachable at all |
| `aliyun ecs run-command` | `RunCommand` | B (read-probe class) | Send exactly one whitelisted non-mutating diagnostic read, auto-approved (query-only) |
| `aliyun ecs describe-invocations` | `DescribeInvocations` | A | Read back that single read's stdout (IncludeOutput) into the report |
| `aliyun sts get-caller-identity` | `GetCallerIdentity` | A | Credential pre-flight + account provenance |

RAM permission points are listed one by one in `references/ram-policies.md`; they are not
derivable from the API names, so nothing outside that file is assumed.

## Intake: ask once, ask completely

Required: `RegionId` (never guessed), one or more `InstanceId` (max 10 per run), the
symptom in the customer's own words, and the minute the stop/reboot/change was issued
(`--state-since`) -- without it the time baseline cannot be applied. Collect at the same
time, before starting long queries: the console error text or screenshot, the OS family
(Linux/Windows + distribution), whether a snapshot exists, whether `atop` was installed
before the incident, and a VNC observation of the boot screen when the instance never
reaches the OS. If the instance id or region is missing, stop and ask; do not run anything.

## How to run

Run the single entry point; never assemble `aliyun` commands by hand.

```
python3 scripts/areas/instance_state_diagnosis/sts_token.py
python3 scripts/areas/instance_state_diagnosis/diagnose_instance_state.py --region-id cn-hangzhou \
  --instance-id i-xxxxxxxx --symptom stuck-stopping --state-since "2026-09-17 14:20"
```

Add `--error-text "OperationDenied.NoStock"` when the customer quoted anything, and
`--guest-command disk-usage`; tier-1 whitelist reads are query-only and dispatched
automatically (the entry tool auto-runs the decisive set - `disk-usage`, `memory-usage`,
`fstab-content`, `mount-table` - whenever the instance is Running and the Cloud
Assistant agent answers, reading each result back into the report).
Other flags: `--suspects-provider`, `--mention-atop`, `--timeout`, `--json`. A
`NoPermission` or `ImplicitDeny` result means the running identity lacks a grant: report
the exact missing action plus the snippet in `references/ram-policies.md`, then continue
with whatever evidence was collected.

## Decision tree (the script enforces this order; keep it)

```
0  sts get-caller-identity -> account matches the instance owner? no -> stop, ask
1  DescribeInstances (+ DescribeInstanceStatus cross-check) -> status
   Stopping   -> dwell vs baseline:  <=15 min  normal shutdown flow, nobody can intervene
                              15-20 min borderline, keep watching
                              >20 min  escalate: snapshot first -> VNC -> manual force stop
   Pending/Starting -> dwell > 5 min -> route on the customer's error text:
                        NoStock | image compliance | fstab/emergency | capacity blocks boot
                        | boot order | intrusion
                        no error text -> manual VNC four-check (GRUB/fsck/emergency/panic)
   Running    -> platform events? -> guest channel? -> if the symptom is a service or a
                login fault while the instance is up: layer verdict, then hand off
   Stopped    -> operation lock financial -> expiry, not a fault -> renewal guidance
2  DescribeInstancesFullStatus + DescribeInstanceHistoryEvents -> maintenance or health
3  DescribeCloudAssistantStatus -> class B possible?
4  class B: one whitelisted non-mutating read, auto-approved (query-only), or ask the customer to run it
5  class D needed? -> snapshot first, then manual steps, then re-query to verify
```

## Time baseline (converged from five inconsistent human wordings)

| State | Typical | Expected ceiling | Escalate |
|---|---|---|---|
| `Stopping` after a normal console stop/reboot | 5-15 min | 15 min | beyond 20 min |
| `Starting` / `Pending` | under 5 min | 5 min | beyond 15 min |

During a shutdown flow **no one** -- the customer, the console, support or this skill --
can intervene; a force operation issued in that window fails with a task conflict, which
is expected behaviour and not a new fault. Full derivation, the status-display lag case
and the exact customer wording are in `references/instance-state-diagnosis__state-machine-and-timeouts.md`.

## Snapshot first

Before guiding any cleanup, boot repair, rollback, forced operation, or stop/restart of an
abnormal instance: snapshot every disk involved and wait for 100%. Pure querying and pure
waiting need no snapshot. Snapshots are billed separately and must be deleted after the
operation is verified. Steps, billing note and the three risk notes:
`references/instance-state-diagnosis__snapshot-first-checklist.md`.

## Boundary and handoff

This tier owns the state machine and "which boot stage broke". It does not own guest
services, capacity cleanup, IO tuning or partition expansion, and it never executes class
D. Handoff criteria and the customer-facing sentences (including intrusion and expiry
cases) are in `references/instance-state-diagnosis__handoff-matrix.md`. When handing over, carry the readings already
collected so the customer is not asked twice.

## Output contract

Report exactly what the script printed: the evidence table (action, parameters, key
returned fields, timestamp), FINDINGS per instance, MANUAL STEP / HANDOFF lines, WARNINGS
and LIMITATIONS, then `STATUS: OK|DEGRADED|FAIL` and one `NEXT_ACTION`. State which
parameters were auto-filled (region, account id). Quote only returned values. If the
customer asks for something class D, give the boundary sentence, the console entry point
and the manual steps -- not a command this skill will run.

## Observability

Every call from this package carries a User-Agent identifying the skill and the run, built
by `scripts/areas/instance_state_diagnosis/_cli.py` from this template:

```
AlibabaCloud-Agent-Skills/{skill}/{session_id} skill-version/{skill-version}
```

which resolves for this skill to `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/<value>`.
`{session_id}` is a per-run 32-character hex value generated once in `scripts/areas/instance_state_diagnosis/_cli.py`
(`SESSION_ID = uuid.uuid4().hex`) and reused for every call of that run, so all API traffic
of one diagnosis can be correlated. The session id is also printed in the report header.

## Credentials and safety

Authentication uses the default credential chain that the `aliyun` CLI already has
(`aliyun sts get-caller-identity`, a profile, or a RAM role attached to the host). This skill never
reads, prints, caches, transmits or asks for an AccessKey id or secret, never writes
key material into a file or a report, and never echoes it in an error: all CLI stderr and
stdout are passed through a masking step in `scripts/areas/instance_state_diagnosis/_cli.py` before being displayed.
Treat any credential value appearing in a ticket or console output as sensitive: do not
reproduce it in the report. Only instance ids, regions, statuses and non-secret field
values are quoted back.

## References

- `references/ram-policies.md` -- per-action RAM points, least-privilege policy, failure codes
- `references/instance-state-diagnosis__state-machine-and-timeouts.md` -- states, dwell baseline, "cannot intervene", status-display lag
- `references/instance-state-diagnosis__boot-failure-branches.md` -- quoted signals to layer/verdict/manual step, VNC four checks
- `references/instance-state-diagnosis__guest-diagnostic-commands.md` -- class B whitelist, dispatch rules, refused items
- `references/instance-state-diagnosis__handoff-matrix.md` -- boundary areas and handoff sentences
- `references/instance-state-diagnosis__snapshot-first-checklist.md` -- snapshot gate, billing note, risk notes, verification query

## Known limitations (say these out loud, do not work around them)

- The boot screen is never visible to platform tooling: which boot stage failed can only be
  established from a customer VNC observation or a repair-disk session (manual).
- Whether a custom image really carries the required boot drivers cannot be asserted from a
  public query; it stays a guided compliance check against the import documentation.
- Which process saturated the host at the incident minute is unrecoverable unless `atop`
  was installed beforehand.
- Output of a dispatched class-B command is read from the Cloud Assistant console or pasted
  back by the customer; this build does not call any invocation-result API.
- Expiry and monitoring curves are read from the customer's own console, not asserted here.
