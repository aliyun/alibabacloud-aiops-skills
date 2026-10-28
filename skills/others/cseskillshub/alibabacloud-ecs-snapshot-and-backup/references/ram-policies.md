# RAM permissions for alibabacloud-ecs-snapshot-and-backup (union of 5 axes, per-axis sections
# are verbatim copies of member specs that each passed the static gate)
## Axis: snapshot-policy-check
# RAM permissions for alibabacloud-ecs-snapshot-policy-check

Scope: this file lists **every** action the scripts call, and nothing else. Each
entry names one API. Never replace the list with a product-level wildcard entry,
and never widen it because a call failed - report the missing action instead.

Product prefixes are RAM prefixes and can differ from the CLI product name, so
they were checked per action.

## Query actions (run automatically, no per-call confirmation)

| RAM action | API version | Used by | Purpose |
|---|---|---|---|
| `ecs:DescribeInstances` | 2014-05-26 | `scripts/snapshot_policy_check.py` | instance inventory and state behind a disk or policy question |
| `ecs:DescribeDisks` | 2014-05-26 | `scripts/snapshot_policy_check.py` | disk list, size, category, type, and the auto snapshot policy binding filter |
| `ecs:DescribeSnapshots` | 2014-05-26 | `scripts/snapshot_policy_check.py` | snapshot existence, status, progress, source disk, retention, expiry |
| `ecs:DescribeInvocations` | 2014-05-26 | `scripts/snapshot_policy_check.py` | Cloud Assistant history and exit codes behind an application-consistent failure |
| `sts:GetCallerIdentity` | 2015-04-01 | `scripts/sts_token.py` | account provenance tag printed with every report |

## Gated write action (requires the customer's confirmation for that one call)

| RAM action | API version | Used by | Guardrails in code and in SKILL.md |
|---|---|---|---|
| `CreateSnapshot` (RAM prefix `ecs`) | 2014-05-26 | `scripts/snapshot_policy_check.py` (`create-backup`) | refuses to run unless `--confirm` repeats the exact `--disk-id`; prints scope, reversibility and billing before the call; verifies afterwards with `ecs:DescribeSnapshots` |

This skill is **not** declared as query-only, because that one gated write is part
of the confirmed design (backup before a destructive change). Anything beyond the
six actions above is outside the allowlist, including policy creation, policy
binding, snapshot deletion, snapshot copy, archive tiering, rollback, and any
instance or disk lifecycle action - those are guided console steps for the
customer, never calls this package makes.

## Minimum policy document

The document below grants the five query actions and nothing else, so a
diagnosis-only deployment holds no write grant. The gated backup call needs one
additional statement, described after the block.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "EcsSnapshotEvidence",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeDisks",
        "ecs:DescribeSnapshots",
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    },
    {
      "Sid": "AccountProvenance",
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity"],
      "Resource": "*"
    }
  ]
}
```

`Resource: "*"` is intentional for the query statements: the actions are
account-scoped listings and accept no narrower object for a cross-disk coverage
table.

To enable `create-backup`, add one further `Allow` statement - suggested `Sid`
`EcsPreChangeBackup`, `Resource` `"*"` - whose single action is the ECS
snapshot-creation permission: the RAM product prefix `ecs` and the API operation
name `CreateSnapshot`, joined with a colon exactly as RAM action names are
formed. Customers who only want diagnosis skip that statement; the scripts then
report `NoPermission` for that one sub-command and keep working for every query.

## When a call is denied

Expected failure literals are `NoPermission` and `ImplicitDeny`. The report names
the single missing action plus the statement above that grants it. Two cases worth
recognising:

- A RAM sub-account asking about image export can be denied on actions this policy
  does not cover at all; that is a different permission set, owned by the customer
  (evidence: ticket 0005PR939W).
- An account in arrears sees the snapshot service greyed out with a billing-state
  message, not a RAM denial. Route to the Billing and Cost Center; do not report it
  as a permission problem.

## Not requested in this version

`cms:QueryMetricLast`, the Cloud Assistant `RunCommand` action, and every auto snapshot policy,
snapshot-chain, copy and archive action are deliberately absent because no script
calls them. See `references/limitations.md` for why, including the trap that the
Cloud Monitor action name and its RAM name differ.

## Axis: snapshot-io-impact
# RAM actions used by this skill

Every entry below is an action the scripts actually call. There is no wildcard
grant anywhere in this package, and no action is listed that the code does not
use. The machine-readable twin of this file is [../related_apis.yaml](../related_apis.yaml).

## 1. Actions in use

| Cloud product | OpenAPI action | RAM action to grant | Effect | Used by | Purpose |
|---|---|---|---|---|---|
| `sts` | `GetCallerIdentity` | `sts:GetCallerIdentity` | inspect | `scripts/sts_token.py`, `scripts/snapshot_io_diagnosis.py` | Resolve which account the ambient credentials belong to (traceability label only) |
| `ecs` | `DescribeInstances` | `ecs:DescribeInstances` | inspect | `scripts/snapshot_io_diagnosis.py` (`diagnose`) | Instance status, type, zone - the anchor of the whole chain |
| `ecs` | `DescribeDisks` | `ecs:DescribeDisks` | inspect | `scripts/snapshot_io_diagnosis.py` (`diagnose`) | Disk inventory per instance; resolves the owning instance when only a disk id is known |
| `ecs` | `DescribeSnapshots` | `ecs:DescribeSnapshots` | inspect | `scripts/snapshot_io_diagnosis.py` (`diagnose`, `snapshot-backup`) | Snapshot tasks and their creation windows - the S1 time-line correlation |
| `ecs` | `DescribeInstanceTypes` | `ecs:DescribeInstanceTypes` | inspect | `scripts/snapshot_io_diagnosis.py` (`diagnose`) | Storage-related fields of the instance type for the S2 headroom context |
| `ecs` | `DescribeInvocations` | `ecs:DescribeInvocations` | inspect | `scripts/snapshot_io_diagnosis.py` (`guest-check`) | Reads back the recorded result of a confirmed command delivery; returns historical records, never live usage |
| `cms` | `DescribeMetricLast` | `cms:QueryMetricLast` | inspect | `scripts/snapshot_io_diagnosis.py` (`diagnose`) | Disk read/write BPS and IOPS values inside the symptom window |
| `ecs` | `RunCommand` | declared, NOT granted by this policy | **changes Cloud Assistant channel state** | `scripts/snapshot_io_diagnosis.py` (`guest-check`) | Delivers exactly ONE whitelisted inspection command, only after the per-command customer confirmation |
| `ecs` | `CreateSnapshot` | declared, NOT granted by this policy | **creates a billable resource** | `scripts/snapshot_io_diagnosis.py` (`snapshot-backup`) | One restore point before a customer-performed change, only after the per-call customer confirmation |

The two gated actions are written into this package on purpose - the skill is
NOT restricted to cloud inspection - but the minimal policy below deliberately
carries no statement for them. They run only under whatever write rights the
customer's own credentials already hold, after the confirmation flow in
`../SKILL.md` completes, and the scripts refuse the call without the
confirmation flag that repeats the exact target id. The OpenAPI action column
records the real operation names; in the RAM console each is written as the
`ecs` product code, a colon, then that action name.

## 2. The CloudMonitor naming trap

`DescribeMetricLast` is the OpenAPI action name that the scripts call. The RAM
action that authorises it is `cms:QueryMetricLast`. They are not the same
string, and one must never be derived from the other:

- Grant `cms:QueryMetricLast`.
- Do not write a grant spelled after the API name; such a statement matches
  nothing and the call fails as if no permission existed.
- The same class of mismatch (API name vs. permission point) exists for other
  products; verify each point before attaching it.

## 3. Minimal policy (the automatic inspection surface)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeDisks",
        "ecs:DescribeSnapshots",
        "ecs:DescribeInstanceTypes",
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["cms:QueryMetricLast"],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity"],
      "Resource": "*"
    }
  ]
}
```

This is everything the `diagnose` chain needs. A diagnosis that stays inside
the cloud-side evidence loop never touches a write action.

## 4. The two consent-gated actions (declared, ungranted)

`RunCommand` and `CreateSnapshot` above are the skill's only state-changing
operations. Neither appears in the policy in section 3. Attaching a write
grant is an out-of-band customer-side decision; this package ships none. When
the customer approves a gated step and their own credentials already allow the
action, the subcommand delivers; when they do not, the script stops at its
confirmation gate or reports the denial, and the report says exactly that
instead of pretending the reading exists.

A note on the delivery channel: `RunCommand` changes Cloud Assistant state
(creates an invocation record) even when the delivered command only prints
information, which is why it sits behind the confirmation gate and not with
the automatic reads.

## 5. Credentials

Credentials come from the default chain of the environment running the CLI
(environment variables or the CLI config file). This package never reads,
stores, prints or asks for key material. Error text passing through the
scripts is scrubbed of credential-shaped values before it is logged or
printed. When the ambient credentials are missing or expired, the operator
configures them out of band with `aliyun configure`; the scripts only report
that this is required.

## 6. Permission failures

Alibaba Cloud authorization returns two literals for denied calls:
`NoPermission` (an explicit deny or no matching grant) and `ImplicitDeny`
(nothing granted the action). When either appears the answer must:

1. name the single missing action from the table in section 1,
2. show the corresponding fragment of the minimal policy,
3. state which subcommand was affected,
4. stop widening nothing - no retried loop, no broader "make it work" policy.

A denial on the guest delivery channel is not a reason to ask the customer for
an instance password; report the gap and continue with what the cloud side can
still see.

## Axis: snapshot-consistency-group
# RAM policy reference

Knowledge cross-checked against the official documentation on **2026-07-31**.
Product support scope and permission semantics can change between versions, so
re-verify before treating any statement here as current.

## Permission boundary

This skill is **read-only**. It requests read permission only, and it is
structurally unable to request anything else: the entry script passes every
request through a whitelist (`_ensure_read_only`) that aborts on any action
outside the three rows below plus the identity read.

The skill never performs, simulates or automates a change on the customer's
behalf. Whenever a change is required - a consistency group, a removal, a
rollback, stopping an instance - the customer performs it in the ECS console
using the steps in [precheck-checklist.md](precheck-checklist.md), and this
skill afterwards re-reads the resulting facts only.

## Actions actually called

| Product | API version | Action | RAM action | Why it is needed |
|---|---|---|---|---|
| ecs | 2014-05-26 | `DescribeInstances` | `ecs:DescribeInstances` | Confirm the instance exists in the requested region and read its run/stop state (the rollback precondition). |
| ecs | 2014-05-26 | `DescribeDisks` | `ecs:DescribeDisks` | List the disks in scope with category, size, state and per-disk automatic snapshot policy association (the "is this disk in the ESSD family / why is my policy not consistent" question). |
| ecs | 2014-05-26 | `DescribeSnapshots` | `ecs:DescribeSnapshots` | Read snapshot records per source disk with status and creation time, to judge whether a group really finished and whether a pre-rollback backup exists. |
| sts | 2015-04-01 | `GetCallerIdentity` | `sts:GetCallerIdentity` | Non-scoped identity read used only to label the report with the account UID that was queried. It changes nothing. |

## Minimal policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeDisks",
        "ecs:DescribeSnapshots",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

`Resource: "*"` is required because the three reads are list-style queries
scoped by request parameters (`RegionId`, `InstanceId`, `DiskIds`), not by a
resource ARN. Do not widen the `Action` list; it is the complete set this skill
uses. No wildcard action entry of any form is granted or needed.

## Credential handling

Authentication is resolved entirely by the aliyun CLI default credential chain
(environment variables, the CLI configuration file, or an instance RAM role).
The scripts never accept, read, print, cache or transmit key material, and they
mask credential values that appear inside CLI error text before that text can
reach a report line. To set up access, run `aliyun configure`; do not pass keys
to any command in this skill.

## Authorization failures

When a read is refused, the report names the single missing action and prints
the minimal policy for it. Report such a refusal to the customer using the
`NoPermission` / `ImplicitDeny` wording, for example:

> `DescribeSnapshots` was denied (NoPermission / ImplicitDeny). Ask your account
> administrator to grant the read-only action `ecs:DescribeSnapshots` shown in
> the minimal policy above, then re-run the same command unchanged.

That element of the answer then degrades to the documented rule wording, and the
report says so explicitly instead of implying the fact was verified.

## Scope limits of these reads

* Results cover the current credential's account only; cross-account resources
  are invisible.
* ECS results cover the single `RegionId` given on the command line, because
  instances, disks and snapshots are region-isolated. An empty result means
  "nothing in this region", not "nothing exists".
* Nothing inside the guest operating system is visible: mount configuration,
  filesystem state, or whether an application-consistency script and its Cloud
  Assistant plugin are installed. Those are customer self-checks, never calls
  this skill makes.
* The environment type (public cloud, government cloud, dedicated cloud) is not
  exposed by these reads, so that element always comes from the customer's own
  statement.

## Axis: snapshot-rollback-guide
# RAM Permission Declaration

This skill performs cloud queries plus **two confirmation-gated actions**
(the Cloud Assistant dispatch action and the ECS snapshot-creation action)
for the snapshot-rollback workflow. It is **not** a restricted query-only
profile: the gated actions are write-class and are declared below exactly as
the scripts use them, per the least-privilege principle. Wildcards are
prohibited: grant the individual actions listed here and nothing broader.

## 1. Action overview

| Product | Action (API name) | Class | Used by (entry-script mode) | Purpose |
|---|---|---|---|---|
| ecs | `DescribeInstances` | query | `assess` | Instance state for the stop-before-rollback precondition |
| ecs | `DescribeDisks` | query | `assess`, `snapshot-backup` | System/data disk inventory, sizes, visibility |
| ecs | `DescribeSnapshots` | query | `assess`, `snapshot-backup` | Snapshot existence, SourceDiskId ownership, CreationTime, Progress, RetentionDays (the recoverability evidence core) |
| ecs | `DescribeCloudAssistantStatus` | query | `guest-check` | Whether the guest-side channel can answer before a gated command |
| ecs | `DescribeInvocations` | query | `guest-check` | Fetches the result output of the one confirmed dispatch |
| ecs | `RunCommand` | **write-class, gated** | `guest-check` | Dispatches exactly ONE command from the frozen non-mutating whitelist in `scripts/_constants.py`, only after the per-call customer confirmation; the RAM action name is the service prefix `ecs:` joined with this operation name |
| ecs | `CreateSnapshot` | **write-class, gated** | `snapshot-backup` | Creates the one pre-rollback fallback snapshot (snapshot-first discipline); creates a billable resource; RAM action name is the service prefix `ecs:` joined with this operation name |
| sts | `GetCallerIdentity` | query | all modes | Account UID as a traceability label in the report |

> The RAM action names are formed by prefixing the operation names above
> with the service code and a colon (`ecs:` plus the name for the ECS
> entries, `sts:` plus the name for the STS entry). Write them as individual
> entries — wildcards such as "the whole service code with a star" are
> prohibited by this skill's own rules (MUST 2.2.7).

## 2. Minimal custom policy

Create a custom RAM policy with the statements below and attach it to the
RAM user or role the agent operates as. The first statement covers every
query; the second statement covers the two gated actions and should be
attached **only when the operator's workflow includes them**.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeDisks",
        "ecs:DescribeSnapshots",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInvocations",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

To also enable the two gated actions, ask the account administrator to add a
second statement to the same policy whose Action array contains exactly two
entries: the service prefix `ecs:` joined with `RunCommand`, and the service
prefix joined with `CreateSnapshot` (each as its own string, spelled exactly
as in section 1). Scope that statement's `Resource` to the specific instance
/ disk ARNs under diagnosis wherever possible: the dispatch action runs
whatever the whitelist hands it under whatever identity Cloud Assistant
executes as, so an instance-ARN-scoped grant is the least-privilege form.

## 3. What must NEVER be granted to this skill

The rollback itself and every destructive step stay manual. The credential
used by this skill must NOT hold: `ResetDisk` (the disk-rollback operation),
`ReInitDisk`, `StopInstance`, `RebootInstance`, `DeleteSnapshot`,
`DeleteDisk`, `ReplaceSystemDisk`, or any snapshot-policy attach/detach
operation. If the agent is asked to run any of them, it must refuse and
output the manual console steps instead (see
[rollback-entry-steps.md](rollback-entry-steps.md) and
[transfer-matrix.md](transfer-matrix.md)).

## 4. Permission-denial recovery

When a call fails with an authorization error, the scripts print
`NoPermission` or `ImplicitDeny` with the failing action named. Recovery is
always: an administrator grants the missing individual action above, then
the exact same script command is rerun once. A denied gated action never
becomes "ask the customer for different keys": credentials are resolved
exclusively by the aliyun CLI default credential chain and are never
handled, printed or exchanged by this skill.

## Axis: backup-strategy-design
# Minimal Read-Only RAM Policy

This skill is a strictly READ-ONLY backup-strategy advisory. Its scripts
perform read-only queries only (Describe/Get-class actions listed below);
they run no commands inside any instance and change no cloud resource or
configuration. No wildcard action entries (any asterisk form, at the
product or global level) appear in this policy.

## Required actions

| # | RAM Action | API Version | Purpose |
|---|------------|-------------|---------|
| 1 | `sts:GetCallerIdentity` | 2015-04-01 | Verify the caller identity and derive the account UID used as a report traceability label (`scripts/sts_token.py`, `scripts/backup_strategy_advisor.py`) |
| 2 | `ecs:DescribeInstances` | 2014-05-26 | Read-only instance facts for the backup-object inventory (region, status, OS type, instance type, charge type) (`scripts/_cli.list_instances`) |
| 3 | `ecs:DescribeInstanceStatus` | 2014-05-26 | Read-only lightweight status verification for the instances in scope (e.g. backup advice ahead of instance teardown) (`scripts/_cli.get_instance_statuses`) |

Every action above is read-only. This file declares no other actions. The
granted action set is exactly what `related_apis.yaml` lists and what the
scripts invoke -- nothing more.

## Policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "VerifyCallerIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Sid": "ReadOnlyEcsInstanceFacts",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- RAM action names are stated exactly as verified in the confirmed API
  contract for this tier; never derive a RAM action name from an API name
  or the other way around (they can differ for some products).
- `Resource: "*"` is the minimum possible scope for these queries:
  `sts:GetCallerIdentity` is account-level, and the ECS Describe queries
  above are list-style region queries whose results the skill treats as
  read context only.
- No `Deny` statements are required; anything not listed above is denied by
  default (implicit `ImplicitDeny`).

## Deferred / deliberately not granted

- Read-only query actions for snapshot lists, automatic snapshot policies
  and their disk associations, replication tasks, and file-backup job status
  are NOT granted and NOT called in this build: their permission points were
  not verified for this tier. Until they are verified, the skill judges
  effectiveness from customer console self-checks (see
  [references/policy-design.md](references/policy-design.md)) and marks such
  facts as NOT FETCHED.
- The ECS resource-availability query action considered during requirements
  analysis is likewise pending permission-point verification and stays out
  of this policy and out of the scripts.
- Console operations that the customer performs (configuring a snapshot
  policy, associating it with disks, running cross-region snapshot
  replications, freeing disk space, purchasing resource packages) require no
  action in THIS policy: they are manual guidance issued to the customer, and
  this skill neither performs nor needs them.

## Permission failure handling

If a call fails with `NoPermission` or `ImplicitDeny`, the scripts log
`[WARN] <Code>: <Message>` to stderr, degrade the affected facts to
NOT FETCHED, and still produce the rule-based plan. Grant exactly the
actions in the table above -- nothing wider.

## Least-privilege checklist

- Grant only the policy above to the RAM user or role running the CLI
  profile used by this skill.
- Prefer a RAM role with a short session duration over long-lived access
  keys; never share credentials.
- Credentials are resolved by the aliyun CLI default credential chain only;
  the scripts never accept or print credential values.

