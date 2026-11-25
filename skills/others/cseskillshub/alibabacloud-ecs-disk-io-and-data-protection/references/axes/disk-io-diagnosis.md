---
name: alibabacloud-ecs-disk-io-diagnosis
description: |
  Diagnose slow or saturated disk I/O on an Alibaba Cloud ECS instance: compute each disk's
  IOPS and throughput ceiling from its class, level and size, compare it with CloudMonitor
  readings, and name the disk and metric that are capped. Use when the complaint is speed,
  latency or I/O load, not free space.
  Triggers:
    - disk reads and writes are slow
    - disk access timeout
    - server frozen or unresponsive
    - high iowait
    - iops or throughput maxed out
    - cloud disk read write limited
    - StoragePerformanceReachLimit with SysDiskIOPS or SysDiskBPS
    - fio benchmark far below advertised iops
  Do NOT use for disk space or inode cleanup (alibabacloud-ecs-disk-capacity-diagnosis), a
  resize that did not take effect (alibabacloud-ecs-disk-expand-diagnosis), or an instance
  stuck during a reboot (alibabacloud-ecs-instance-state-diagnosis).
---

# ECS Disk Performance and I/O Diagnosis

## What this skill answers

A customer reports a symptom: the server hangs, a query times out, an alarm says the cloud
disk is limited. This skill converts that symptom into a per-disk, per-metric verdict:

1. what the disk **should** be able to do, given its category, performance level and size,
   bounded by the instance type;
2. what it **did** do, from monitoring over several windows;
3. which of the two bound it, on which disk, and therefore whether a disk change can help
   at all.

The most common finding is that the disk is not the problem: memory exhaustion surfaces as
saturated I/O. The second most common is a scheduled job in a fixed window. Both are
conclusions this skill is expected to reach out loud rather than quietly.

## Scope gate

Run the routing check before anything else. Free space, inodes, unapplied resizes, instance
lifecycle and connectivity are different axes; answering them with a performance analysis
wastes the customer's time and produces the wrong purchase. See
`references/disk-io-diagnosis__handoff-map.md` for the wording of each hand-off.

A composite complaint ("writes fail and the disk says full") enters here only through the
performance half, and the capacity half is routed away in the same reply.

## Execution model

This skill is **not** restricted to inspect calls. It has three classes of action, and the
class decides whether a confirmation is needed.

### Class 1 - cloud inspection, runs without asking

`ecs:DescribeInstances`, `ecs:DescribeDisks`, `ecs:DescribeInstanceTypes`,
`ecs:DescribeInvocations`, `cms:QueryMetricLast` (through the `DescribeMetricLast` API),
`sts:GetCallerIdentity`. These change nothing, so every one of them runs automatically and
its result is reported.

### Class 2 - one inspection command inside the instance, gated

`run-command` (OpenAPI action `RunCommand`) delivers a single command taken from the
fixed set in `references/disk-io-diagnosis__guest-commands.md`. It is a state-changing API even when the
delivered command only prints information, so:

- **MUST** state, in one block before executing: the instance and region, the exact command
  line, what it returns, that it alters no data, that no rollback is needed, and the blast
  radius.
- **MUST** wait for an explicit customer confirmation, and treat that confirmation as valid
  for **that one command only**. A confirmation given earlier, for another key, or covering
  a batch is not a confirmation.
- **MUST** re-show the block and stop if the command, the instance or the region changes.
- **MUST** refuse any command outside the fixed set and say why, naming what the customer
  should do instead.

### Class 3 - one low-risk reversible write, gated

`create-snapshot` (OpenAPI action `CreateSnapshot`) creates a restore point before a
modification **the customer** performs (a restart to recover from a wedge, a performance
level change). Same gate as Class 2, plus
the billing consequence stated in plain terms. Nothing is removed afterwards by this skill;
the customer is told to clean up unused restore points in the console.

### ABSOLUTE PROHIBITION

The agent **MUST NOT** construct, submit or execute anything beyond the seven actions listed
above, in any form, including a call that merely looks equivalent, a call wrapped in a helper
script, a call presented for the customer to paste, or a call justified as "just to check".

The agent **MUST NOT** execute, generate or hand over a command that:

- kills or restarts a process or service, or reboots and stops an instance;
- removes, empties, rewrites, formats, repairs or repartitions anything on a disk, including
  file-system repair and mount changes;
- writes to or benchmarks a volume (`fio`, `dd`, redirection, truncation), because a mistyped
  device name destroys data;
- changes a performance level, an instance type, a security group, a policy or a billing
  setting;
- installs or configures an agent, collector or recorder on the instance.

All of those are recovery or change operations. They are output as numbered manual steps with
their impact, their rollback path and a snapshot reminder - never executed here.

**MUST NOT** ask for, accept, store or use an instance password, a private key, an access key
id or an access key secret. Credentials come from the default chain of the environment only.
If the guest channel is unavailable, ask the customer to run a listed command themselves and
paste the output; never trade a password for it.

## Prerequisites

- The `aliyun` CLI is installed and the environment already carries credentials. Verify with
  `python3 scripts/axes/disk_io_diagnosis/sts_token.py`; on failure, tell the operator to run `aliyun configure`.
- Region, instance id (`i-...`) or the instance IP are supplied by the customer. **MUST NOT**
  guess an identifier. A missing region is asked for, never inferred from a name.
- Everything the skill sends to the cloud goes through `scripts/axes/disk_io_diagnosis/disk_io_diagnosis.py`. The
  agent **MUST NOT** compose `aliyun` commands by hand, add parameters, or call any other
  tool path; inside the CLI the scripts use the plugin-mode spelling
  `aliyun sts get-caller-identity` and the RPC spelling `aliyun ecs describe-disks` with the
  PascalCase action name.

## Workflow

### 1. Resolve the instance and read every disk

```
python3 scripts/axes/disk_io_diagnosis/disk_io_diagnosis.py diagnose \
  --region-id <region> --instance-id <i-...> \
  --symptom "<customer wording>" \
  --event-time <YYYY-MM-DDTHH:MM:SS>
```

The script resolves the instance type and OS family, lists **all** disks of the instance, and
computes a ceiling for each. Add `--disk-id` to narrow the analysis, `--ip` instead of
`--instance-id` when the customer only knows an address, `--event-json` for an alarm payload
the customer pasted, and `--diagnosis-report-id` when they quote a diagnosis report.

Repeat `--event-time` for every alarm the customer reports: several timestamps at a similar
time of day are what turn "it happens randomly" into a named window.

### 2. Add measurements when the metric names are known

```
python3 scripts/axes/disk_io_diagnosis/disk_io_diagnosis.py diagnose --region-id <region> --instance-id <i-...> \
  --namespace <namespace> --metric <MetricName>:iops --metric <MetricName>:mbps \
  --windows 1h --windows 1d --windows 7d
```

Suffix each metric with its kind (`:iops`, `:mbps`, `:bytes`) so the comparison is against the
right ceiling; a `:bytes` series is converted to MB/s. Without `--namespace` and `--metric`
the report is ceiling-only and says so. The per-disk metric names are not carried inside this
package (see `references/disk-io-diagnosis__help-topics.md`, gap 6), so they come from the console page the
customer is looking at rather than from a guess.

### 3. Compare and classify

Read the evidence table row by row. Each disk gets exactly one of four verdicts, using the
thresholds fixed in `references/disk-io-diagnosis__disk-performance-baseline.md`: not throttled, near ceiling,
occasional spike, sustained ceiling. System disk and data disks are judged separately and
described separately, because the alarm rarely names the disk and the customer is left
guessing.

### 4. Check the memory chain before proposing any disk change

Confirm the memory watermark on the operating-system monitoring page, and whether a swap area
(Linux) or a page file (Windows) exists and is large enough. If this step is skipped, a disk
upgrade will be sold to fix a memory shortage.

### 5. Inspect inside the instance only when it changes the answer

```
python3 scripts/axes/disk_io_diagnosis/disk_io_diagnosis.py guest-cmd \
  --region-id <region> --instance-id <i-...> --command-key disk-usage
```

Run it once without `--confirm` to produce the disclosure block, show that block to the
customer, and only after an explicit yes re-run the identical command with `--confirm`.
Available keys and the refusal list are in `references/disk-io-diagnosis__guest-commands.md`; the set covers
file system usage, inodes, mount mapping and directory size, and contains no per-process I/O
tool, so process attribution stays a guided manual step.

### 6. Take a restore point before a customer-performed change

```
python3 scripts/axes/disk_io_diagnosis/disk_io_diagnosis.py snapshot --disk-id <d-...>
```

Same confirmation discipline, with the billing consequence stated.

### 7. Report

Deliver the script's report as-is, with its next actions. Where the script degraded, keep the
degradation visible in the reply.

## Interpretation rules

- Utilisation is measured peak over the effective ceiling, where the effective ceiling is
  `min(disk ceiling, instance ceiling)`. When the instance binds it, say that raising the
  disk alone changes nothing.
- Show the arithmetic: `min(10000, 1800 + 12 x 501 GiB) = 7812 IOPS`. A customer who can
  recompute the number stops arguing with it.
- Several windows (1h, 3h, 12h, 1d, 7d, 14d) are reported together; a 14-day peak and a
  one-hour peak answer different questions.
- CPU is discussed on its average, with spikes called out separately; IOPS is discussed on its
  peak, because one second at the ceiling is real.
- An empty series is a missing host agent or a collection gap, never a healthy reading.
- No measurement at all means no "the disk is fine" statement is permitted.

## Required disclosures

Every report **MUST** carry the limitations that apply to it, in particular:

- CloudMonitor publishes nothing finer than 15 seconds, so a one-second ceiling touch may be
  invisible in the charts; a flat console curve does not refute an alarm.
- No cloud API and no command in this skill attributes I/O to a process, because Linux keeps
  no historical per-process resource record. The answer is a recorder installed before the
  next occurrence.
- An alarm or event was interpreted from a payload the customer pasted; this skill does not
  read the event store or a diagnosis report through an API.
- Any ceiling figure tagged as unconfirmed in `references/disk-io-diagnosis__disk-performance-baseline.md` is
  quoted with its provenance and re-checked against the block storage performance page before
  being presented as a service commitment.
- For disk classes that publish no IOPS guidance, say there is no official figure. Never
  substitute a number from a similar-looking class or another generation.
- Declare every parameter the skill filled in itself, and every assumption about region,
  OS family, metric kind and unit conversion.

## Output contract

The final answer reproduces the script sections in order: scope gate, instance, per-disk
evidence table, interpretation, declared parameters and assumptions, limitations, next
actions. It ends with the script's two contract lines:

- `STATUS: OK` - the axes were comparable and the verdicts follow from the readings.
- `STATUS: DEGRADED` - a real gap exists (missing metric names, no agent data, region or
  permission problem, guest channel unavailable); the report states which gap and what would
  close it, and no single-cause conclusion is drawn across it.
- `STATUS: FAIL` - the resource could not be resolved or the input was rejected; nothing was
  concluded.

Then one `NEXT_ACTION:` line with the single concrete next step for the customer or the
operator. **MUST NOT** invent a value to turn a degraded result into a complete one.

## Observability

- Each run generates one session id: a 32-character hex string from `uuid.uuid4().hex`.
- The User-Agent template is `AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}`. In code it is
  the constant `API_USER_AGENT_TEMPLATE` in `scripts/axes/disk_io_diagnosis/_constants.py`, whose format fields are
  `{skill}` (the skill name) and `{session_id}` (that session id), expanded by
  `build_user_agent()` in `scripts/axes/disk_io_diagnosis/_cli.py`.
- Every cloud call, without exception, carries the expanded value as a flag -
  `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-disk-io-diagnosis/<session-id>` -
  appended in `scripts/axes/disk_io_diagnosis/_cli.py build_command()`, so no call path can omit it.
- The session id is printed in the report header so a customer case and its calls can be
  matched later.
- Every call is bounded by a per-call timeout, retried at most a few times on throttling and
  server-side errors, and executed as an argument list without a command interpreter. All
  error text is scrubbed of credential-shaped values before it is logged or printed.

## When a call is denied

Report the exact missing action from `references/ram-policies.md` and the minimal policy
fragment, name the subcommand that failed, and stop. Alibaba Cloud returns `NoPermission` or
`ImplicitDeny` for these cases; the answer must quote one of those two codes, must not
generalise the problem into a platform fault, and must not widen the policy "to make it
work". A denied `run-command` means the guest-side reading is unavailable, and the report
says exactly that.

## Reference index

| File | Contents |
|---|---|
| `references/disk-io-diagnosis__io-decision-tree.md` | the ordered gates, root-cause catalog, misconceptions to correct |
| `references/disk-io-diagnosis__disk-performance-baseline.md` | ceilings, provenance tags, utilisation verdicts, upgrade limits |
| `references/disk-io-diagnosis__guest-commands.md` | the callable command set, refusal list, confirmation block, degradation wording |
| `references/disk-io-diagnosis__handoff-map.md` | the four hand-off axes, customer wording, the health-inspection boundary |
| `references/disk-io-diagnosis__help-topics.md` | canonical documentation and console links, plus the seven open gaps |
| `references/ram-policies.md` | exact actions in use, the CloudMonitor naming trap, minimal policy |
