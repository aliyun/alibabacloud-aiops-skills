---
name: alibabacloud-ecs-snapshot-consistency-group
description: |
  Read-only evidence checks and documented rule answers for ECS snapshot consistency groups and multi-disk point-in-time consistency: support scope by environment, region and disk category, why an automatic snapshot policy never yields a consistent group, when a group snapshot is really finished, and the rollback preconditions. Reads Describe APIs only; changes nothing.
  Use when a customer asks about ECS snapshot consistency groups or cross-disk consistency.
  Triggers: "snapshot consistency group", "multi-disk snapshot same time point", "automatic snapshot policy keeps consistency", "create a group automatically", "snapshot stuck creating, uploading to OSS", "consistency group entry missing", "stop the instance to roll back", "NoPermission or ImplicitDeny on DescribeSnapshots".
  Do NOT use for snapshot fees, storage packages, single-disk snapshot management, running a rollback, or in-guest mount errors.
---

# ECS Snapshot Consistency Group (Read-Only)

Answers the snapshot-consistency-group and multi-disk-consistency question with
cloud facts plus documented rules, and nothing else. It is a query and guidance
skill: it reads instances, disks and snapshots, judges them against the official
capability wording, tells the customer what to do in the console, and then
re-reads the facts to confirm what actually happened.

## When to use it

* "Why can I not find the snapshot consistency group entry?" / "Is this feature
  supported in my environment?"
* "I attached the same automatic snapshot policy to all my disks - are they
  consistent now?" / "Can the group be created automatically? Give me a script."
* "It has been saying *creating* / *uploading to OSS* for ages - is it done?" /
  "6 disks took 30 minutes, is that normal?"
* "Do I have to shut the instance down to roll back a group?" / "After the
  rollback one disk does not mount."
* "Where are my snapshots stored? In my own OSS bucket? Why do I not see them in
  this region?"

## Absolute prohibition: this skill is read-only

The skill declares itself read-only, so it must never request, generate or run a
mutating operation - not directly, and not as a command "for the customer to
paste". Blocked families, without exception:

`Create*` `Modify*` `Delete*` `Release*` `Reset*` `Replace*` `Attach*`
`Detach*` `Reboot*` `Start*` `Stop*` `Copy*` `Export*` `Import*` `Revoke*`
`Grant*` `Join*` `Leave*` `Apply*` `Cancel*` `Tag*` `Untag*` `Put*` `Unbind*`
`Bind*`

Enforcement is structural, not advisory: every request passes through
`_ensure_read_only()` in `scripts/snapshot_group_check.py`, which aborts on any
action outside the whitelist below. A read-only skill cannot "just this once"
stop an instance, take the snapshot for the customer, roll a disk back, or clean
up old groups. When asked to do that, refuse, name the boundary, and hand over
the console steps in `references/precheck-checklist.md` instead.

Equally blocked: running anything **inside** a customer instance. In-guest state
(mount tables, filesystems, whether an application-consistency script or its
Cloud Assistant plugin is installed) is never probed. The customer self-checks
it; this skill guides and hands off.

## API whitelist (the complete set)

| Product | Version | Action | Used for |
|---|---|---|---|
| `ecs` | `2014-05-26` | `DescribeInstances` | Instance existence and run/stop state |
| `ecs` | `2014-05-26` | `DescribeDisks` | Disk count, category, size, per-disk automatic policy association |
| `ecs` | `2014-05-26` | `DescribeSnapshots` | Snapshot records, completion status, per-disk creation time |
| `sts` | `2015-04-01` | `get-caller-identity` | Account UID label for the report; changes nothing |

`ecs` is an RPC product: PascalCase action names, regional endpoint resolved
from `--region`. `sts` runs in plugin mode: the lowercase-hyphenated command
`aliyun sts get-caller-identity` against the central endpoint. Nothing outside
this table is called; see `references/ram-policies.md` for the minimal policy.

## Execution principle

Run the entry script. Do **not** assemble `aliyun` commands by hand, and do not
call the OpenAPI through any other path - the script is the single choke point
that supplies timeouts, retry, credential masking and the observability
User-Agent.

Credentials come from the aliyun CLI default credential chain. Never ask for,
accept, pass, echo or store key material; `aliyun configure` is the only setup
guidance this skill gives.

```
# 0. optional: confirm which account is being read
python3 scripts/sts_token.py

# 1. before the customer acts: why is there no group / no consistency
python3 scripts/snapshot_group_check.py --mode precheck \
  --region-id <region> --instance-id <instance-id> \
  --environment <public|gov|dedicated|unknown> \
  --question "<customer's own wording>"

# 2. after the customer created a group or rolled disks back
python3 scripts/snapshot_group_check.py --mode verify \
  --region-id <region> --instance-id <instance-id>

# 3. pure capability/rule question, no cloud read
python3 scripts/snapshot_group_check.py --mode rules \
  --question "<customer's own wording>"
```

`--region-id` is mandatory for `precheck` and `verify`, and `--instance-id` or
`--disk-ids` must scope the read. Ask the customer for these; never guess a
region, because an empty result in a guessed region looks identical to a missing
resource. Add `--json` for machine-consumable evidence.

## Decision flow

1. **Support scope** ("not there / unsupported / entry missing") → judge three
   elements separately: environment (customer statement - no API exposes it),
   region (isolate first), disk category (`DescribeDisks` facts). Government
   cloud evidence is **LOW CONFIDENCE** - one ticket summary, no official page,
   conversation never retrieved - so relay it as labelled ticket experience,
   never as official fact. If all three indicate support and the entry is still
   missing, hand off.
2. **"Can it be automatic?"** → state the boundary first: policies attach to
   individual disks or instance tags, never to a group, and identical policies
   on several disks produce no shared time point. Groups are manual, and there
   is no automation script for them. Then list the actual per-disk policy
   associations as evidence.
3. **"Is it finished?"** → read `Status`; `accomplished` only. Explain first-run
   full versus later incremental, quoting the ~30-minute 6-disk measurement as an
   example and never as a promise.
4. **Rollback** → state preconditions (stop the instance, and take a fresh
   snapshot of the current state before stopping), have the customer perform it,
   then re-verify facts read-only. In-guest mount trouble after a rollback is not
   a cloud fact: give the self-check and hand off.
5. **Anything adjacent** → recognise and hand off per
   `references/handoff-map.md`, without half-diagnosing it here.

Every report separates **verified API fact** from **documented rule wording**
from **customer self-report**, and prints the knowledge-verification date.

## Output contract

Relay the script's own `Summary`, findings, evidence, limitations and final
status faithfully:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <one concrete next step>
```

* `OK` - every requested read succeeded.
* `DEGRADED` - at least one read failed; each failure prints `[WARN]` and is
  listed under **Limitations** as "not verified from the API". Say which
  conclusions rest on rule wording alone.
* `FAIL` - no usable evidence; report the gap instead of answering around it.

Quote only values the API returned. State the auto-filled scope (account UID,
region) explicitly. An empty result is reported as "no records in region X -
confirm the region", never as "you have nothing". Never conclude that a change
succeeded on the customer's behalf: this skill only re-reads facts.

## Authorization failures

When a read is refused, name the single missing action and give the minimal
policy, using the literals `NoPermission` / `ImplicitDeny` (never any other
authorization wording), e.g.

> `DescribeSnapshots` was denied (NoPermission / ImplicitDeny). Ask your
> administrator to grant the read-only action `ecs:DescribeSnapshots` from
> `references/ram-policies.md`, then re-run this command unchanged.

Then degrade that element to the documented rule wording and label it as such.

## Observability

Each run generates one 32-character hex session id (`uuid4().hex`) and attaches
the same User-Agent to **every** API call of that run, so all calls behind one
diagnosis can be correlated:

```
--user-agent AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}
```

`{skill-name}` resolves to `alibabacloud-ecs-snapshot-consistency-group` and
`{session-id}` to the per-run 32-character hex id, so every emitted call carries
the concrete User-Agent in that template shape.

The session id and the resolved account UID are printed in the report header and
in the JSON evidence for traceability. Every CLI invocation is a bounded
`subprocess.run([...], timeout=...)` argument list - never `shell=True` - with
per-call timeouts, capped backoff retry for transient failures (throttling, 5xx,
timeout), and masking of any credential value that appears in CLI error text.

## References

* `references/group-rules.md` - capability boundaries and rule wording (R1-R8),
  with confidence labels
* `references/precheck-checklist.md` - before/after creation and before/after
  rollback checklists, customer-executed steps
* `references/status-guide.md` - status values, completion criteria, region
  isolation, partial-read degradation
* `references/handoff-map.md` - neighbouring areas, recognition cues, handoff
  scripts
* `references/ram-policies.md` - the exact read-only actions and minimal policy

Official documentation cross-checked on **2026-07-31**:
[snapshot consistency group overview](https://help.aliyun.com/zh/ecs/user-guide/snapshot-consistency-group-overview.md),
[create a snapshot consistency group](https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot-consistent-group.md),
[roll back disks using a snapshot consistency group](https://help.aliyun.com/zh/ecs/user-guide/roll-back-disks-by-using-a-snapshot-consistent-group.md),
[apply an automatic snapshot policy to an instance](https://help.aliyun.com/zh/ecs/user-guide/apply-an-automatic-snapshot-policy-to-the-instance.md).

Product capability scope changes over time. Re-verify the wording above before
relying on it, and keep quoting the verification date in every answer.
