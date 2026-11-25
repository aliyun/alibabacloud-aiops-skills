# RAM permissions for alibabacloud-ecs-boot-and-login-repair (union of 3 axes, per-axis sections
# are verbatim copies of member specs that each passed the static gate)
keypair-login-config
# RAM policy for this package

Least privilege, stated as the exact actions the code runs. `scripts/axes/keypair_login_config/_cli.py`
refuses any action outside `API_WHITELIST` before spawning a process, so this
table, `related_apis.yaml` and the calls in `scripts/` are three views of one
list rather than three lists that happen to agree. The gated actions are named
here in the lowercase-hyphenated command form the aliyun CLI plugin mode uses;
the same calls appear under their API names in `related_apis.yaml`.

## Granted actions

| RAM action | Class | Where it is called | What it answers |
|---|---|---|---|
| `sts:GetCallerIdentity` | A evidence | `scripts/axes/keypair_login_config/sts_token.py`, called by `scripts/axes/keypair_login_config/keypair_login_diagnosis.py` | Which account and principal is asking. A wrong account or region presents as "the instance is not there" and looks like a broken credential. |
| `ecs:DescribeInstances` | A evidence | `scripts/axes/keypair_login_config/keypair_login_diagnosis.py` | Does the instance exist here, is it `Running`, which OS and image, which security groups are bound, is it locked or expiring, and whether a key pair name is recorded. |
| `ecs:DescribeInstancesFullStatus` | A evidence | `scripts/axes/keypair_login_config/keypair_login_diagnosis.py` | Instance health and scheduled events. A platform-side event is not a credential fault and stops the credential branch early. |
| `ecs:DescribeCloudAssistantStatus` | A evidence | `scripts/axes/keypair_login_config/keypair_login_diagnosis.py` | Whether the Cloud Assistant agent reports, plus its version and last heartbeat. This is the single most decisive read: console passwordless logon and an online password reset both ride on it. |
| `ecs:DescribeInvocations` | A evidence | `scripts/axes/keypair_login_config/keypair_login_diagnosis.py` | Whether remote commands ran recently and how they ended; also the read-back channel for a confirmed inspection request. |
| `ecs:run-command` | B gated | `scripts/axes/keypair_login_config/keypair_login_diagnosis.py`, `run_inspection()` | Dispatches one published inspection reading inside the guest. Never reached without this call's own confirmation naming that exact command. |
| `ecs:create-snapshot` | C gated | `scripts/axes/keypair_login_config/keypair_login_diagnosis.py`, `create_prechange_snapshot()` | Takes the pre-change snapshot of one disk before a restart-dependent step. Never reached without this call's own confirmation naming that exact disk id. |

No other action is granted, declared in `related_apis.yaml`, or reachable through
the transport layer.

## Minimal policy

Attach only what the run needs. Every action entry is named individually, and no
product-wide action wildcard is used anywhere in this policy.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstancesFullStatus",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:run-command",
        "ecs:create-snapshot"
      ],
      "Resource": "*"
    }
  ]
}
```

`Resource` stays open because these are collection reads and per-target writes
scoped by `RegionId`, instance id and disk id in the request itself. Narrow it
further if the account policy requires that.

The third statement is optional and should be attached only when the operator
accepts that this skill can dispatch one inspection command and create one
billable snapshot. Without it the evidence path keeps working: each gated call
simply fails with `NoPermission` and the report prints the reading as a step for
a human instead. A RAM policy cannot express the per-call confirmation, so that
gate is enforced in code, not in the policy: `require_confirmation()` in
`scripts/axes/keypair_login_config/_cli.py` raises `ConfirmationRequired` before the CLI is spawned, and a
gated action is attempted once rather than retried, so a confirmation can never
be spent twice.

## When a call is refused

Only these literals come out of this package, and each says what to do next:

| Literal | Meaning | What to do |
|---|---|---|
| `NoPermission` | The principal has no statement allowing that action | Add that one action from the table above |
| `ImplicitDeny` | A control policy or a group policy denies it | Ask the account administrator to lift the deny for that action; do not work around it with a broader grant |
| `ConfirmationRequired` | A class B or class C call reached the transport layer without a confirmation repeating its own command or disk | Tell the operator what that single call does and what it can affect, get their answer, then re-run with that confirmation; a confirmation given for another command, another disk or an earlier run never applies |
| `RefusedBySkillPolicy` | The action is outside `API_WHITELIST` | Do not add a parameter or widen a policy: that action is deliberately not part of this skill, so guide the console path |

A credential problem (`InvalidCredential`) is different: fix it with
`aliyun configure`, and never by pasting an AccessKey pair, a token or a private
key into a conversation.

## Gated capabilities not granted by this package

These capabilities are deliberately absent, and the skill guides a human through
the console for each of them instead of calling an API:

* the key pair lifecycle: a new pair, an uploaded public key, a binding, a
  replacement, a released binding;
* instance password recovery, online and offline;
* instance power state changes;
* security group rule review and edits;
* snapshot deletion and any other in-guest or in-account change;
* any in-guest edit: sshd configuration changes, service restarts, cleared
  `authorized_keys`, lockout policy changes. Only the published non-mutating
  readings on the class B list are dispatchable, and only with their own
  confirmation. See `guest-evidence-commands.md`.

The reason is uniform: for those capabilities this tier has no verified parameter
and policy contract, or no approved command whitelist, and an agent guessing a
write call on a customer's production instance is a worse failure than handing a
human an accurate console path.

boot-repair-guide
# RAM policies for alibabacloud-ecs-boot-repair-guide

Every action below is enumerated explicitly. This skill never relies on an action wildcard, never asks
for account-wide administrator rights, and requires **no change-level permission**: nothing beyond the
five actions in this file is called by `scripts/`, and the agent must not ask for more.

## Actions actually invoked

| Product | Action | API version | Purpose in this skill |
|---|---|---|---|
| sts | `GetCallerIdentity` | 2015-04-01 | Verify that the credential chain works and record which account produced the report |
| ecs | `DescribeInstances` | 2014-05-26 | Instance status, OS name and version, image id, instance type and family, zone, private and public addresses, billing method |
| ecs | `DescribeInstanceStatus` | 2014-05-26 | Confirm `Running` versus `Stopped`; gate repair-disk work and verify that a reboot took effect |
| ecs | `DescribeAvailableResource` | 2014-05-26 | Stock check for the temporary pay-as-you-go instance used in the data-rescue path |
| ecs | `DescribeInvocations` | 2014-05-26 | Historical Cloud Assistant records for the instance: whether the guest executed anything after the failure, which is evidence about how far the boot process got |
| ecs | `DescribeDisks` | 2014-05-26 | Identify the system disk (id, category, size, status) so repair and rollback guidance targets the real volume |
| ecs | `DescribeSnapshots` | 2014-05-26 | Determine whether a rollback point exists: accomplished snapshots on the system disk gate destructive repair steps |

## Minimal policy

Attach a custom policy that allows exactly the ECS actions above, scoped to the instances and regions
under investigation:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeAvailableResource",
        "ecs:DescribeInvocations",
        "ecs:DescribeDisks",
        "ecs:DescribeSnapshots"
      ],
      "Resource": [
        "acs:ecs:<region-id>:<account-id>:instance/<instance-id>",
        "acs:ecs:<region-id>:<account-id>:disk/<disk-id>",
        "acs:ecs:<region-id>:<account-id>:snapshot/<snapshot-id>"
      ]
    }
  ]
}
```

`DescribeAvailableResource` is a region-level catalog query and cannot be narrowed to one instance ARN;
if your policy enforces instance-level scoping, add a separate statement for it with the region in scope.

`DescribeDisks` and `DescribeSnapshots` are disk- and snapshot-scoped queries: filter by `InstanceId` /
`DiskId` and grant the `disk/*` and `snapshot/*` ARNs shown above, or narrow them to the specific ids
under investigation.

For `sts:GetCallerIdentity` no resource scoping applies: it is callable by any identity in the account and
returns the identity of the caller only.

## When a call is denied

Report the exact action that failed and the snippet the customer needs. Use the literals `NoPermission`
and `ImplicitDeny`, which are what the RAM authorization engine returns; do not paraphrase the failure as
a generic access error, and do not retry a denied call in a loop.

```
[WARN] ecs:DescribeInstances denied (NoPermission) — ask the account administrator to attach the
       ecs:DescribeInstances entry from references/ram-policies.md, then re-run the same command.
STATUS: DEGRADED
NEXT_ACTION: Customer grants the missing read permission, or pastes the field values from the console
             instance details page so triage can continue offline.
```

An `ImplicitDeny` means the identity has no statement matching the action at all, which is fixed by
attaching the policy above rather than by editing an explicit deny.

## What this skill deliberately does not have

The boot-failure workflow eventually needs snapshot lifecycle, block-storage handling, image management,
logon credential, instance power state, and operating-system substitution permissions. This release does
not hold them and does not request them, because those operations are performed by the customer in the
console after reviewing the guidance and the stated risk. If the customer wants automation of a repair
step, that is a separate authorization decision: the contract of the specific action must be verified
first, and the skill must state the impact, the reversibility, and the downtime window before each
execution.

## Credential handling

The scripts use the default credential chain of the Alibaba Cloud CLI only. They never read, accept,
print, cache, or forward an access key, a secret key, a security token, a guest password, or a private
key. Error text is masked before it reaches the report: any access key id, security token, or signature
appearing in tool output is replaced with `***`. The only identity value surfaced is the last four
characters of the account id, used as a provenance tag.

system-event-notice-guide
# RAM policies for this skill

The skill performs read-only inspection. The policy below enumerates the exact
actions it calls; no action wildcard is used, and no other ECS action is granted
or needed.

## Minimum policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

`Resource` is left open on the ECS statement because the two list-style reads
take a region and a filter rather than a single pre-named resource, and a call
that returns nothing for an unlisted resource is indistinguishable from a denied
one. When you would rather scope it, the narrowed form for a known instance set is:

```json
{
  "Effect": "Allow",
  "Action": [
    "ecs:DescribeInstances",
    "ecs:DescribeInstanceStatus"
  ],
  "Resource": "acs:ecs:<region-id>:<account-id>:instance/<instance-id>"
}
```

## What each action is used for

| Action | Used by | Purpose in the answer |
|---|---|---|
| `sts:GetCallerIdentity` | `scripts/axes/system_event_notice_guide/sts_token.py` | Confirm the configured identity resolves, and produce a masked account tag for the report header. |
| `ecs:DescribeInstances` | `scripts/axes/system_event_notice_guide/ecs_system_event_notice.py` | Turn an instance ID, a private IP, or a public IP from the notice into the instance record: region, zone, status, billing type, addresses, tags. |
| `ecs:DescribeInstanceStatus` | `scripts/axes/system_event_notice_guide/ecs_system_event_notice.py` | Cross-check the current running status of the resolved instances when the customer says they already rebooted, or that the instance will not start. |

## Not granted, on purpose

Nothing outside the table above is callable by this skill. In particular the
policy contains no action that alters an instance, its disks, its schedule, its
images, its billing, or its operating system, and the scripts never attempt one.
A customer request that needs such a change is answered with console steps and,
if needed, a ticket.

## When a call is denied

The report prints `NoPermission` or `ImplicitDeny` together with the action that
was denied. The usual causes are:

- the policy above was not attached to the identity in use;
- a policy at a higher level explicitly denies the action, so attaching the
  allow above is not enough on its own;
- the identity belongs to a different account or resource group than the
  instance named in the notice;
- the region passed to the script is not the region holding the instance.

Fix it by attaching the minimum policy to that identity, or by re-running the
script with the correct `--region-id`. Do not broaden the policy beyond the
three actions above.

## Axis: linux-permission-repair
# RAM policy required by this skill

The table below is the complete action surface this skill needs; the policy fragment further
down is the whole default grant. One concrete action per line, no wildcard.
`scripts/axes/linux_permission_repair/permission_diagnosis.py` calls nothing else, and the agent must not call anything else.

| Action | Needed by | Gate | Why |
|---|---|---|---|
| `ecs:DescribeInstances` | `preflight` | automatic | instance exists in the region, run status, image, charge and expiry time, bound security groups |
| `ecs:DescribeInstancesFullStatus` | `preflight` | automatic | scheduled stop or release and health events, so an event lock is not read as a permission fault |
| `ecs:DescribeCloudAssistantStatus` | `preflight` | automatic | decides whether the in-guest inspection channel exists |
| `ecs:DescribeInvocations` | `guest-run`, `guest-result` | automatic | collects the output of an execution that was already approved and sent |
| `sts:GetCallerIdentity` | `identity`, `preflight` | automatic | identifies the principal behind the cloud-side reads, to separate RAM authorization from guest sudo |
| `run-command` (CLI plugin mode; OpenAPI operation `RunCommand`) | `guest-run --confirm` | **confirmation, per request** | carries exactly one non-mutating command from `guest-diag-whitelist.md` |
| `create-snapshot` (CLI plugin mode; OpenAPI operation `CreateSnapshot`) | `snapshot --confirm` | **confirmation, per request** | optional backup taken before the customer repairs permissions by hand; needs `DiskId` |

Each row is named by the command the CLI actually runs. The CLI is always invoked in plugin mode, so
those names are lowercase-hyphenated; the OpenAPI operation behind each one is stated in
parentheses and declared, with its product code and API version, in `../related_apis.yaml`.

## Minimal policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstancesFullStatus",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInvocations",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

The resource scope above is the usual one for ECS reads; narrow it to the worked region, the
specific `acs:ecs:<region>:<account>:instance/<instance-id>` and the instance's disks when the
customer's own policy allows it. Scope narrowing never changes the action list above.

The fragment above is query-only: the two confirmation-gated actions carry no entry by default.
Where the engagement lets the session itself dispatch them, append one entry per action to the
`Action` list - the ECS action for `run-command` and the ECS action for `create-snapshot`. Each is
the ECS RAM code followed by the operation name declared for `popCode` `ecs` in
`../related_apis.yaml`, quoted on its own line.

## Two actions are mutating, and that is deliberate

This tier pairs non-mutating cloud reads with approved in-guest inspection: the two mutating
actions are part of the confirmed design, each behind the per-request approval gate in
`../SKILL.md` section 3.

* `run-command` (OpenAPI operation `RunCommand`, ECS RAM code) reaches inside the
  instance. It is permitted to carry only the whitelisted
  non-mutating inspection commands; the entry point validates the command in code and refuses
  anything else before a request is built. It never runs a repair.
* `create-snapshot` (OpenAPI operation `CreateSnapshot`, ECS RAM code) only adds a backup.
  It is offered before the customer changes permissions and
  is skipped when the customer declines.

## Anything not listed here is out of scope

No other `ecs`, `sts`, `ram` or `bssopenapi` action is granted, and the skill does not ask for one.
In particular the whole repair surface stays with the customer: changing a guest file mode or owner,
editing sudoers, group membership, a service restart, an instance reboot, and any credential or
password reset are **manual console or in-guest actions** and are never executed or scripted by this
skill. Credential reset is answered with the documented console path in `permission-diagnosis.md`.

## When a call is not authorized

Report the literal code returned, `NoPermission` or `ImplicitDeny`, name the single missing action
from the table above, point at this file, and continue through the manual path in `../SKILL.md`
section 7. Do not request an AccessKey pair, and do not substitute broader actions such as a
wildcard grant to make an error disappear.

## Axis: file-transfer-diagnosis
# RAM policies

This is the permission contract for the scripts listed in `SKILL.md`. Every
action below was verified against the code that dispatches it: the whitelist
in `scripts/axes/file_transfer_diagnosis/_constants.py` (`API_QUERIES`) and the call sites in
`scripts/axes/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py` and `scripts/axes/file_transfer_diagnosis/sts_token.py`. Nothing
is declared here that the scripts do not actually call, and nothing the
scripts call is missing.

The policy follows the "what one called action needs" principle: one
statement per called action, no grouping, and no product-namespace wildcards
anywhere. Two classes mirror `SKILL.md` ("What this skill may and may not
do"):

- **Class A** — the read-only cloud queries every diagnosis run needs.
- **Class B** — the gated in-guest command channel. Optional, attached at
  the customer's own discretion; see its section below.

## Class A — read-only queries (required)

| RAM action | OpenAPI product / version | Called by | Why |
|---|---|---|---|
| `sts:GetCallerIdentity` | Sts / 2015-04-01 | `scripts/axes/file_transfer_diagnosis/sts_token.py` | Identity preflight: confirms credentials resolve and names the account the results belong to. |
| `ecs:DescribeInstances` | Ecs / 2014-05-26 | `scripts/axes/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py` | Instance basics for the evidence report: status, OS type, public and internal addresses, declared bandwidth, security group ids. |
| `ecs:DescribeInstancesFullStatus` | Ecs / 2014-05-26 | `scripts/axes/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py` | Lifecycle state and scheduled events, so a transfer fault is not confused with an instance event. |
| `ecs:DescribeCloudAssistantStatus` | Ecs / 2014-05-26 | `scripts/axes/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py` | Whether the Cloud Assistant agent is reachable, which decides if the Class B channel is even possible. |
| `ecs:DescribeInvocations` | Ecs / 2014-05-26 | `scripts/axes/file_transfer_diagnosis/ecs_file_transfer_diagnosis.py` | Recent command records and the result of one approved command. |

Attach this minimal policy to the RAM role or RAM user that the ambient CLI
profile already resolves to (`aliyun` reads its credentials from the profile
or the instance role; the scripts never take, read, echo or store a key or
secret):

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "EcsFileTransferDescribeInstances",
      "Effect": "Allow",
      "Action": ["ecs:DescribeInstances"],
      "Resource": "*"
    },
    {
      "Sid": "EcsFileTransferDescribeInstancesFullStatus",
      "Effect": "Allow",
      "Action": ["ecs:DescribeInstancesFullStatus"],
      "Resource": "*"
    },
    {
      "Sid": "EcsFileTransferDescribeCloudAssistantStatus",
      "Effect": "Allow",
      "Action": ["ecs:DescribeCloudAssistantStatus"],
      "Resource": "*"
    },
    {
      "Sid": "EcsFileTransferDescribeInvocations",
      "Effect": "Allow",
      "Action": ["ecs:DescribeInvocations"],
      "Resource": "*"
    },
    {
      "Sid": "EcsFileTransferStsIdentity",
      "Effect": "Allow",
      "Action": ["sts:GetCallerIdentity"],
      "Resource": "*"
    }
  ]
}
```

`Resource` stays at the account level because these ECS read actions
authenticate service-wide; scoping through region conditions is left to the
account's own policy standards. Do not broaden any action entry with a
wildcard suffix — the five actions above are the complete surface the
diagnosis runs need.

## Class B — gated command channel (optional, not in the minimal policy)

The in-guest inspection path uses the Cloud Assistant command-delivery
operation RunCommand (Ecs / 2014-05-26); the scripts refer to it internally
by its dispatch token `ecs:run-command`, bounded by the command whitelist
embedded in `scripts/axes/file_transfer_diagnosis/_constants.py` (`GUEST_COMMAND_WHITELIST`).

A command submission is not a read, so this class is deliberately absent
from the Class A example above. The confirmation gate in `SKILL.md`
("Confirmation gate for in-guest commands") always applies: exact command
line stated, single-instance scope, no-effect statement, and one approval
per command. Granting the operation is a decision for the customer's own
account administrator, made per account and per role; the skill never asks
the customer for a key or secret to work around a denial.

When the identity lacks the submission permission, nothing breaks: the
`guest-plan` entry point prints the denial with the literals `NoPermission`
or `ImplicitDeny` as returned and falls back to customer-run guidance, so
the Class A policy alone is sufficient for a complete report; Class B only
adds the in-guest evidence lane.

## Scope and denial notes

- Every result reflects only the account the preflight resolved to. An empty
  answer means "nothing found for this account", never "nothing wrong".
- When a Class A query is denied, the run degrades gracefully: the missing
  reading is recorded under Gaps in the report and the remaining queries
  continue. Name the missing action from the table above and link back to
  this file, as `SKILL.md` ("Authorization errors") requires.
- Policy maintenance: a managed custom policy keeps at most five versions;
  remove the oldest version before creating a new one if the limit is hit.
