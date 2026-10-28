---
name: alibabacloud-ecs-snapshot-io-impact
description: |
  Diagnoses whether an ECS slowdown is caused by snapshot activity: correlates the
  symptom window with snapshot task windows and CloudMonitor disk BPS/IOPS against the
  instance-type ceiling, then returns a graded verdict. Cloud reads are automatic; the
  in-guest command and the restore-point snapshot each require an explicit per-call
  customer confirmation.
  Use when: snapshot makes the business slow, server lags while a snapshot runs, backup
  window stalls the database, disk IOPS maxed out while snapshotting, this slowdown began
  after a snapshot, MaxTransferRateExceeded, InstancePerformanceReachLimit.
  Do NOT use for snapshot creation failure (alibabacloud-ecs-snapshot-policy-check),
  non-snapshot I/O slowness (alibabacloud-ecs-disk-io-diagnosis), disk full
  (alibabacloud-ecs-disk-capacity-cleanup), rollback
  (alibabacloud-ecs-disaster-recovery-snapshot); other boundaries:
  see references/handoffs.md.
---

# ECS Snapshot I/O Impact

Decides whether a performance symptom on an ECS instance is attributable to snapshot
activity, or runs independently of it. The answer is produced by correlating three time
lines from real API data: the customer's symptom window, the snapshot task windows on that
instance's disks, and the monitored disk throughput during the same period.

## Scope

This tier owns exactly one question: **did the snapshot cause, or amplify, this slowdown?**

In scope:

- Time-window attribution between a reported slowdown and snapshot tasks (manual or
  scheduled) on the instance's disks.
- Headroom judgement: whether disk read/write BPS or IOPS reached the storage ceiling the
  instance type reports, so that a snapshot is the amplifier rather than the root cause.
- Impact guidance for the customer to apply in the console, plus an optional disclosed
  restore point before a customer-performed change.
- Recognising an out-of-scope symptom and handing it off with the evidence already gathered.

Out of scope, handled by identification and hand-off rather than diagnosis: capacity and
inode pressure, expansion that never took effect, instance lifecycle states, snapshot
creation failure, snapshot fees and retention, restore and rollback, and slow disk I/O with
no snapshot overlap. The full map, including how to split the ambiguous "it is slow" case
with the neighbouring performance tier, is in
[references/handoffs.md](references/handoffs.md).

## Permission model

**This skill is not restricted to cloud inspection.** It operates in three classes, and the
class of a step determines whether it runs on its own or waits for the customer.

| Class | What it covers | Gate |
|---|---|---|
| 1 - cloud inspection | The `Describe` and `Get` calls in the read chain below | Automatic; changes nothing |
| 2 - in-guest inspection | Exactly one command from the frozen whitelist in [references/guest-inspection-commands.md](references/guest-inspection-commands.md), delivered through Cloud Assistant | Disclose, then obtain the customer's confirmation for that one command |
| 3 - reversible write | Exactly one restore-point snapshot of one named disk, through the ECS `create-snapshot` action | Disclose, then obtain the customer's confirmation for that one snapshot |

Class 2 is gated even though every whitelisted command only prints information, because the
delivery itself creates an invocation record on the customer's instance.

The write actions this skill can reach are ECS `run-command` (class 2 delivery channel) and
ECS `create-snapshot` (class 3). Their RAM grant strings are recorded in
[references/ram-policies.md](references/ram-policies.md); the minimal policy deliberately
grants them nothing: they run only under write rights the customer's own credentials already
hold, and only after the confirmation flow below.

### ABSOLUTE PROHIBITIONS

- **Never** call any action outside the registry in `scripts/_constants.py`. In particular
  never `Delete*`, `Modify*`, `Reset*`, `Replace*`, `Attach*`, `Detach*`, `Reboot*`,
  `Start*`, `Stop*`, `Authorize*`, `Revoke*`, snapshot deletion, disk release, or any
  instance lifecycle operation.
- **Never** delete a snapshot, even one this skill just created, and even when the customer
  asks. Deleting a temporary restore point is a console step the customer performs, with the
  billing consequence stated first.
- **Never** change an auto snapshot policy, its schedule, or its retention. This tier reads
  the tasks a policy produced; adjusting the policy is the customer's console action, which is
  also the correct remedy for a confirmed overlap.
- **Never** execute, stage or deliver a command that is not the assembled result of a
  whitelist key. No ad hoc shell, no script bodies, no loops, no line built by concatenating
  customer text, and never a compound line. A request to run anything else is refused in
  words; the refusal is not converted into "run this yourself" with a command line attached.
- **Never** generate a mutating command for the customer to paste, and never offer a
  workaround that reaches the same effect by another route.
- **Never** accept, request, read, echo or store an access key, a secret, a token or an
  instance password. Credentials resolve from the default chain of the configured CLI only.
  A Cloud Assistant failure is never a reason to ask for a password.

### Confirmation contract (mandatory)

Before any class 2 or class 3 step, show the customer, and only then act:

1. the exact target (instance or disk id, and region);
2. the exact command line, or the exact write action;
3. what it returns, or what it creates;
4. whether anything changes, and how far - a class 2 delivery changes nothing inside the
   guest but records one invocation; a class 3 snapshot adds a billable resource;
5. how it is undone, or that nothing needs undoing.

Then stop and wait for an explicit yes for **that one action at that one moment**.

A confirmation does not carry to the next command, the next resource, or the next run. It is
not implied by a general request to investigate, by "check whatever you need", or by
approval given earlier in the conversation. When the target or a path argument changes, the
disclosure and the confirmation are repeated. Both gated subcommands enforce this in code:
they refuse to act unless `--confirm` repeats the exact target id, so a skipped gate fails
closed and prints the disclosure instead of executing.

## Prerequisites

- The `aliyun` CLI on `PATH`, with credentials resolvable from its default chain.
- RAM actions as in [references/ram-policies.md](references/ram-policies.md). Note that the
  CloudMonitor read is authorised by a permission point whose name differs from the API name;
  the reason is in that file and it cannot be derived.
- CloudMonitor collection enabled for the instance, otherwise the metric rows come back empty
  and the verdict degrades.
- For class 2: the Cloud Assistant agent installed and online on the target, Linux only.
- A symptom window. Without one, the last 24 hours are used and the report declares that
  substitution.

## Usage

Run the single entry point; do not assemble CLI calls by hand.

```bash
python3 scripts/sts_token.py

python3 scripts/snapshot_io_diagnosis.py diagnose \
  --region-id cn-hangzhou --instance-id i-xxxxxxxx \
  --window-start 2026-02-10T14:00:00Z --window-end 2026-02-10T15:00:00Z \
  --symptom "orders queue up every night around 14:20"

python3 scripts/snapshot_io_diagnosis.py diagnose \
  --region-id cn-hangzhou --disk-id d-xxxxxxxx --json
```

Gated steps - each prints its disclosure and stops unless confirmed:

```bash
python3 scripts/snapshot_io_diagnosis.py guest-check \
  --region-id cn-hangzhou --instance-id i-xxxxxxxx --command-key mount-map

python3 scripts/snapshot_io_diagnosis.py guest-check \
  --region-id cn-hangzhou --instance-id i-xxxxxxxx \
  --command-key disk-usage --confirm i-xxxxxxxx

python3 scripts/snapshot_io_diagnosis.py snapshot-backup \
  --region-id cn-hangzhou --disk-id d-xxxxxxxx --confirm d-xxxxxxxx
```

Ids are never guessed, and `--instance-id` or `--disk-id` is required. Region comes from the
customer or from the resource record, never from a default assumption left undeclared.

## Evidence chain

`diagnose` walks these steps and prints each raw value it relies on. A failed step is recorded
in the degradation log; it is never silently skipped and never filled in.

| Step | Call | Contribution |
|---|---|---|
| 0 | `sts:GetCallerIdentity` | Account label for traceability; degrades without stopping the run |
| 1 | `ecs DescribeInstances` | Status, instance type and zone - the anchor of the chain |
| 2 | `ecs DescribeDisks` | Which disks belong to the instance, their category and size |
| 3 | `ecs DescribeSnapshots` | Task spans, status and progress - the correlation core |
| 4 | `ecs DescribeInstanceTypes` | Storage-related fields used as the ceiling reference |
| 5 | `cms DescribeMetricLast` | Disk read/write BPS and IOPS inside the symptom window |

A disk-only request resolves its owning instance from the attachment record before continuing.
`DescribeInvocations` reads back the recorded result of a confirmed class 2 delivery; it
returns history, not live state, which is why a current in-guest reading needs the delivery
channel at all.

Step 4 scans the instance-type record generically for numeric storage fields, because the field
names are not uniform across instance families. The candidate values are printed with their
field names so a reviewer can see exactly what the headroom ratio was computed against. No
ceiling is ever supplied from memory.

## Verdict and status

The verdict is one of four branches, defined with their evidence rules in
[references/knowledge.md](references/knowledge.md): `SNAPSHOT_WINDOW_AMPLIFIER`,
`SNAPSHOT_WINDOW_CORRELATED_HEADROOM_UNCLEAR`, `NOT_ATTRIBUTABLE_TO_SNAPSHOT`,
`EVIDENCE_INSUFFICIENT`.

Correlation is not causation, and the report keeps them apart. Overlapping windows alone
support B2 at most. Only B1 names the snapshot as the dominant contributor, and only because
the readings show there was no headroom left.

Every answer ends with the two contract lines the script emitted:

```text
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <single next step>
```

`DEGRADED` is a real finding with a named gap; relay it as such. `FAIL` means no usable
evidence. Never upgrade one into the other to make an answer look decisive, and never restate
the guidance section as though a change had been made.

## Evidence discipline

- Every figure in the answer traces to a returned field in this run, or to arithmetic on
  figures that do. Absence is written as absence.
- An empty metric table is a gap, not an idle disk: it can mean nothing was produced, that a
  metric name or dimension does not match the console series, or that collection is off. Say
  which of these the report can rule out.
- Declare substitutions: a defaulted window, a disk-derived instance id, an instance-level
  series used because no disk id was given.
- Do not quote snapshot concurrency counts, throttling percentages or rate limits. No official
  performance document for this tier was verified, so the package carries none - see the
  open-items section of [references/knowledge.md](references/knowledge.md).
- Time is reported in UTC and echoed as returned, so a customer comparing console views sees the
  same numbers.
- When the customer's own description conflicts with the readings, print both and stop. Their
  observation may be right and outside what cloud metrics sample.

## Known limitations

1. No cloud API measures block-device latency as the guest experiences it. The whitelist
   commands report capacity and file-handle context only, so a latency figure has to come from
   the customer running a tool themselves and pasting the output.
2. Attribution depends on the window the customer supplies. A vague "it is slow" yields a
   defaulted window whose verdict is only as good as that guess, which the report declares.
3. The scan covers snapshot tasks within a bounded look-back, so no overlap means none in that
   range - not none ever.
4. Representative ticket evidence was not supplied for this tier. The symptom-to-cause table is
   built from the tier's trigger wording and the API surface, so its ordering is unverified.
5. Windows guests are not served by the class 2 channel in this release; there the guidance
   stays manual.
6. Metrics, namespaces and the near-ceiling ratio are working values echoed in every report for
   review, not published limits.

## Observability

Each run generates one 32-character lowercase hexadecimal session id from `uuid.uuid4().hex`
and attaches the same value to **every** outbound call through the CLI `--user-agent` flag, so
one diagnosis is traceable end to end:

```text
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-snapshot-io-impact/<session-id>
```

The template `AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}` lives in one constant
(`USER_AGENT_TEMPLATE` in `scripts/_constants.py`) and is applied in the shared transport layer
(`scripts/_cli.py`), so no call path can omit it. The id opens the printed report, the JSON
payload and any escalation, and it is never derived from customer content.

Every invocation also carries a per-call timeout (`--timeout`, default 30 seconds), runs as an
argument list rather than a shell string, retries only transient conditions with jittered
backoff, and masks credential-shaped values out of any error text before it is logged, printed
or embedded in a report.

## References

| File | Contents |
|---|---|
| [references/knowledge.md](references/knowledge.md) | Symptom-to-cause table, the four branches, window and headroom arithmetic, allowed and forbidden claims, pre-answer checklist |
| [references/handoffs.md](references/handoffs.md) | Boundary map, how to split the case with the neighbouring performance tier, hand-off wording, requests to decline |
| [references/guest-inspection-commands.md](references/guest-inspection-commands.md) | Frozen whitelist, path rules, refusal tiers, the disclosure template, Windows exclusion |
| [references/ram-policies.md](references/ram-policies.md) | Actions actually called, minimal policy, the CloudMonitor naming trap, permission failures |
| [related_apis.yaml](related_apis.yaml) | Machine-readable twin of the action set, one entry per action actually invoked |
