# RAM permissions for alibabacloud-ecs-app-deploy-and-site-build (union of 5 axes, per-axis sections
# are verbatim copies of member specs that each passed the static gate)
website-build-guide
# RAM Policies - ECS Website Build & Deployment Guide

This skill requests **read-only** permissions. It performs exactly two ECS
queries and one caller-identity check, and nothing else.

## Actions used

| Product | Action | RAM action | Purpose |
|---|---|---|---|
| `ecs` (version `2014-05-26`) | `DescribeInstances` | `ecs:DescribeInstances` | List the instances visible in one region, with their state, addresses and bound security groups, so the deployment target can be confirmed. |
| `ecs` (version `2014-05-26`) | `DescribeInstanceStatus` | `ecs:DescribeInstanceStatus` | Take a second, independent read of each instance's state in that region, as the precondition check before the walkthrough assumes a usable target. |
| `sts` (version `2015-04-01`) | `GetCallerIdentity` | none required | Record which account the read-only inventory was produced under, as a report traceability label. |

No other action of any product is called, and none is requested.

## Minimal policy

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
    }
  ]
}
```

`Resource: "*"` is used because instance visibility is scoped by region and by
the account the credentials belong to; restrict it to specific instance ARNs if
your organisation requires it.

## Failure codes

| Code returned | What it means here | What to tell the customer |
|---|---|---|
| `NoPermission` | The RAM identity behind the credentials is missing one of the two ECS actions above. | Name the missing action from the table; the operator applies the minimal policy from the section above in the RAM console themselves. |
| `ImplicitDeny` | A policy or a control guard denies the read even though it looks allowed. | Ask the account administrator to review the effective policies for that identity; this skill cannot inspect them. |
| `InvalidRegionId.NotFound` | The region id supplied does not exist. | Re-confirm the region id with the customer. |
| `Throttling.User` | Rate limited. | The scripts already back off and retry a bounded number of times; if it persists, re-run later. |

## Boundary statement

The actions above are the complete API surface of this skill. Any change to a
cloud resource - instance state, security-group rules, disks, images, panel
settings, uploaded files - is performed by the customer in the console, in the
panel, or on the server, after reading the guidance this skill produces. The
skill neither holds nor requests permission to make such a change.

app-server-deploy-guide
# RAM policy for this package

Least privilege, stated as the exact actions the code runs. `scripts/axes/app_server_deploy_guide/_cli.py`
refuses any action outside `API_WHITELIST` before spawning a process, so this
table, `related_apis.yaml` and the calls in `scripts/` are three views of one
list rather than three lists that happen to agree. The two gated actions are
named here in the lowercase-hyphenated command form the aliyun CLI plugin mode
uses; the same calls appear under their API names in `related_apis.yaml`.

This package is not confined to queries: it can dispatch one inspection
command inside the guest and create one billable snapshot, each only with its
own per-call confirmation. The policy below grants exactly those seven
actions and nothing wider; no product-wide wildcard appears anywhere.

## Granted actions

| RAM action | Class | Where it is called | What it answers |
|---|---|---|---|
| `sts:GetCallerIdentity` | A evidence | `scripts/axes/app_server_deploy_guide/sts_token.py`, called first by `scripts/axes/app_server_deploy_guide/app_server_deploy_guide.py` | Which account and principal is asking. A wrong account or region presents as "the instance is not there" and looks like a broken credential. |
| `ecs:DescribeInstances` | A evidence | `scripts/axes/app_server_deploy_guide/app_server_deploy_guide.py` | Does the target instance exist in this region, its status, type, zone, OS, IPs, image id and bound security groups. |
| `ecs:DescribeInstanceStatus` | A evidence | `scripts/axes/app_server_deploy_guide/app_server_deploy_guide.py` | The readiness gate: Running or not. A non-Running instance is handed to the instance-state tier, not deployed onto. |
| `ecs:DescribeAvailableResource` | A evidence | `scripts/axes/app_server_deploy_guide/app_server_deploy_guide.py` | Whether the wanted instance type has stock in the region or zone right now. A query-moment answer only. |
| `ecs:DescribeInvocations` | A evidence | `scripts/axes/app_server_deploy_guide/app_server_deploy_guide.py`, `poll_probe()` | Fetches back the result of the ONE inspection reading this run dispatched; also historical Cloud Assistant records. |
| `ecs:run-command` | B gated | `scripts/axes/app_server_deploy_guide/app_server_deploy_guide.py`, `run_probe()` | Dispatches one published inspection command inside the guest. Never reached without this call's own confirmation naming that exact command string, and only commands on the whitelist in `guest-inspection-commands.md` are accepted. |
| `ecs:create-snapshot` | C gated | `scripts/axes/app_server_deploy_guide/app_server_deploy_guide.py`, `run_snapshot()` | Creates the pre-cleanup snapshot of one named disk. Never reached without this call's own confirmation naming that exact disk id. Snapshots are billable until a human deletes them in the console. |

No other action is granted, declared in `related_apis.yaml`, or reachable
through the transport layer.

## Minimal policy

Attach only what the run needs. Every action entry is named individually.

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

`Resource` stays open because the evidence calls are collection reads and the
two gated calls are per-target writes already scoped by `RegionId`, instance
id and disk id in the request itself. A tighter policy may pin the instance ARN
(`acs:ecs:<region-id>:<account-id>:instance/<instance-id>`).

The third statement is optional and should be attached only when the operator
accepts that this skill can dispatch one inspection command and create one
billable snapshot. Without it the evidence path keeps working: each gated call
simply fails with `NoPermission` and the report prints that reading as a step
for a human instead. A RAM policy cannot express the per-call confirmation, so
that gate is enforced in code, not in the policy: `require_confirmation()` in
`scripts/axes/app_server_deploy_guide/_cli.py` raises before the CLI is spawned, and a gated action is
attempted once rather than retried, so a confirmation can never be spent
twice.

## Naming caveat

ECS-native RAM action names equal the API operation names under the `ecs`
service prefix; the two gated ones are listed above in CLI command spelling
for the same reason the CLI accepts them that way. Re-verify each action name
in the RAM console against the live service authorization list before granting
-- do not widen a policy from memory, and do not add an action that is not in
the table above.

## When a call is refused

Only these literals come out of this package, and each says what to do next:

| Literal | Meaning | What to do |
|---|---|---|
| `NoPermission` | The principal has no statement allowing that action | Add that one action from the table above |
| `ImplicitDeny` | A control policy or a group policy denies it | Ask the account administrator to lift the deny for that action; do not work around it with a broader grant |
| `ConfirmationRequired` | A class B or class C call reached the transport layer without a confirmation repeating its own command or disk | Tell the operator what that single call does, what it can affect, and whether it is reversible; get their answer, then re-run with that confirmation. A confirmation given for another command, another disk or an earlier run never applies |
| `RefusedBySkillPolicy` | The action is outside `API_WHITELIST` | Do not add a parameter or widen a policy: that action is deliberately not part of this skill, so guide the console path instead |

A credential problem (`InvalidCredential`) is different: fix it with
`aliyun configure`, and never by pasting an AccessKey pair, a token or a
private key into a conversation.

## Capabilities deliberately NOT granted

These belong to other tiers or to a human, and the skill guides instead of
calling:

* any install, uninstall, service start/stop, reboot, or in-guest edit beyond
  the five published inspection commands;
* security group rule review and edits (the guide prints the console path);
* disk capacity cleanup, inode housekeeping, deletion of any file or snapshot
  (the disk-capacity tier and the customer's own console actions own these);
* disk resize and spec change, instance power, image creation and sharing
  execution (each has its own tier or console flow);
* purchasing, refunds, and anything commercial.

The reason is uniform: for those capabilities this tier has no verified
parameter and policy contract, or no approved command whitelist, and an agent
guessing a write call on a customer's production instance is a worse failure
than handing a human an accurate console path.

marketplace-image-guide
# RAM policy notes

Scope: the minimum identity permission this skill needs. The entry script reaches
three ECS read-only actions and nothing else; the transport layer in
`scripts/axes/marketplace_image_guide/_cli.py` refuses any action outside that set before a process is started.

## Actions actually called

| Product | Action | Version | RAM action | Why it is needed |
|---|---|---|---|---|
| ecs | `DescribeInstances` | 2014-05-26 | `ecs:DescribeInstances` | Read the instance type, attached image identifier, lifecycle state, charge mode, zone and resource group. Starting point for every branch. |
| ecs | `DescribeImages` | 2014-05-26 | `ecs:DescribeImages` | Read the image name, operating-system metadata, owner alias, product code, size, status and progress. Decides whether the image is a Marketplace or otherwise paid image. |
| ecs | `DescribeInstanceStatus` | 2014-05-26 | `ecs:DescribeInstanceStatus` | Re-check the lifecycle state, which is the read-only precondition check for a system-disk or operating-system change. |

## Minimum policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeImages",
        "ecs:DescribeInstanceStatus"
      ],
      "Resource": "*"
    }
  ]
}
```

`Resource` is left open because the read actions above are list-style queries that
already filter by region and identifier. No action wildcard is used, and none should
be added: enumerate an action only when the entry script really calls it.

## Identity check

`scripts/axes/marketplace_image_guide/sts_token.py` runs the Alibaba Cloud CLI in plugin mode as
`aliyun sts get-caller-identity` so each report can name the account the facts came
from. It is an identity echo, not a data query, and is deliberately not part of the
declared ECS surface in `related_apis.yaml`.

## What is deliberately not requested

This skill holds no write and no execution permission, by design:

- No action that alters an instance, an image, a disk, a billing relationship, a
  resource group or a RAM principal.
- No action that runs a command inside a customer instance.
- No billing, order, invoice or Marketplace-order action, because no such contract
  was verified for this tier. Order-level questions are answered by the customer
  reading the billing console, or by the ticket route.

Every such step in this package is guidance for the customer to carry out in the
console. See `handoff.md` for the boundary and `console-guides.md` for the cards.

## Handling an authorization failure

When a call comes back with `NoPermission` or `ImplicitDeny`:

1. Name the failing action from the report line, for example `DescribeImages`.
2. State which RAM action is missing, using the table above.
3. Show the minimum policy fragment for that one action.
4. Ask an administrator to grant it, then re-run.

Do not broaden the policy to a wildcard to make the error disappear, and do not
conclude that a resource does not exist: an authorization failure and an empty
result are different answers.

Credentials are resolved by the default credential chain of the locally configured
CLI. Never pass an access key pair to this skill, never place one in a command line,
a file or a report, and point the operator at `aliyun configure` instead.

image-boot-repair-diagnosis
# RAM policies for alibabacloud-ecs-image-boot-repair-diagnosis

This file is the authority for what the skill is allowed to call. The
**declared permission surface is strictly read-only**: only the class A
actions below are granted, each named explicitly, product prefix plus full
API name. There is no wildcard entry in any policy in this file, and an
administrator must not add one to make a failure go away. If the scripts and
this file ever disagree, the scripts are the defect.

## Permission model (RO_GUEST: read-only cloud queries + guided manual repair)

| Class | Meaning | Consent before each call | Declared here? |
| --- | --- | --- | --- |
| A | Read-only cloud query: images, instances, lifecycle state, assistant execution history, identity | No | **Yes** |
| B | One side-effect-free guest probe inside a RUNNING instance, dispatched through the Cloud Assistant channel, command taken only from the read-only whitelist in [guest-readonly-commands.md](guest-readonly-commands.md) | **Yes, per command** | No grant (see below) |
| C | Actual repair execution (bootloader regeneration, fstab edits, component installation, snapshots, instance power changes, disk detach/reattach) | Not applicable | **Never.** Manual guidance only |

### Class A actions (automatic)

| RAM action | API version | Used by (entry script) | Purpose |
| --- | --- | --- | --- |
| `ecs:DescribeInstances` | 2014-05-26 | `triage` | Does the instance exist in THIS region for THIS account; its type family, zone, image id, lifecycle state |
| `ecs:DescribeImages` | 2014-05-26 | `triage`, `verify-repair` | Custom-image inventory, `Status` / `Progress` of a creating image, and the image record's NVMe-support feature when the field is present |
| `ecs:DescribeInstanceStatus` | 2014-05-26 | `triage`, `verify-repair` | Lightweight lifecycle state read; anything but Running closes the guest-read door for this round |
| `ecs:DescribeInvocations` | 2014-05-26 | `triage` context, `probe` status read-back | Recent Cloud Assistant execution records (name, status, per-instance error code) and the retained stdout of a consented probe |
| `sts:GetCallerIdentity` | 2015-04-01 | `check-env` and once per run | Account UID label stamped on every report, catching cross-account misdiagnosis |

Prefix note: the RAM action prefix is NOT always derivable from the CLI
product name; for these ECS reads and the STS identity action the
prefix-equals-product convention was verified live on 2026-09-16 with the
evaluation role. Do not extend that convention to unlisted actions.

### Class B operation (one consent per command) - deliberately UNGRANTED here

The guest probe dispatches the whitelisted read-only command over the Cloud
Assistant channel, named by its CLI metadata-mode API `RunCommand`. Its RAM
permission point was NOT verified in the evidence injected for this tier
(the low-risk operations list confirmed only its write-class attribute and
required parameters), so per the governing rule that unverified permission
points are never declared, **no policy statement in this file grants it**.
The operation therefore runs under whatever rights the CUSTOMER's own
credential already holds in their session, always behind the exact-string
disclosure + single-use confirmation token that the entry script prints, and
degrades to "the customer runs it and pastes the reading" the moment the
dispatch is not authorized. No standing grant exists for this skill.

## Policy document (class A only)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "ReadOnlyImageAndInstanceEvidence",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeImages",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    },
    {
      "Sid": "CallerIdentity",
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

`Resource: "*"` is the minimum expressible scope: these are account+region
list queries whose API authorization does not narrow to single-resource ARNs
for this use. The granted verbs are all Describe/Get-class: the credential
physically cannot change any image, instance, disk or task state.

## Explicitly NOT granted, and never called

| Name | Why |
| --- | --- |
| `ecs:DescribeAvailableResource` | Carried in the generic read pool but no scenario in this tier uses it; dropped from implementation (scope-creep guard) |
| Any task-detail query for image-repair jobs | None was verified to exist; the diagnosis runs on the customer-pasted pipeline log instead |
| Instance power, disk attach/detach, image or snapshot mutation verbs | Class C territory: this skill answers them with manual console steps, never with an API call |

## Authorization failures

When a class A read returns a permission error (`NoPermission`, `ImplicitDeny`
or any `AccessDenied` shape), the entry script logs `[WARN|DEGRADE]`, names
the failing action, prints the policy statement above as the fix, and
continues with the remaining evidence — it never concludes "no data exists"
from "no permission to see it."

image-encryption-cross-account
# RAM permissions required by this skill

This skill is **read-only**. Its scripts invoke three ECS read actions plus the
STS identity call, and it declares only the three ECS permission points below.
No mutating permission point is declared, granted, called, or printed as a
command for the customer to run.

The action names below are the RAM permission points of the APIs the scripts
actually call; they are taken from the `Authorization information` table of each
official API reference page (verified 2026-09-18). A RAM permission point is not
always identical to the API operation name, so do not infer extra entries from
the operation names.

| Permission point | Access level | Resource scope in the official table | Invoked from |
| --- | --- | --- | --- |
| `ecs:DescribeImages` | get | `acs:ecs:{#regionId}:{#accountId}:image/*` and `.../image/{#imageId}` | `scripts/axes/image_encryption_cross_account/image_cross_account_check.py` |
| `ecs:DescribeInstances` | list | `acs:ecs:{#regionId}:{#accountId}:instance/*` and `.../instance/{#instanceId}` | `scripts/axes/image_encryption_cross_account/image_cross_account_check.py` |
| `ecs:DescribeInstanceStatus` | list | all resources (the official table does not support resource-level scoping for it) | `scripts/axes/image_encryption_cross_account/image_cross_account_check.py` |

The identity call `aliyun sts get-caller-identity` (operation `GetCallerIdentity`,
STS API version 2015-04-01) is invoked by `scripts/axes/image_encryption_cross_account/sts_token.py` and by the
identity step of the entry script, and is listed in `related_apis.yaml` because
the scripts really do call it. Its official reference page exposes **no
authorization information**: any caller holding a valid credential may invoke it.
It is therefore not a permission point, needs no entry in the policy below, and
none is declared for it.

Note from the `DescribeImages` reference: when the query targets Alibaba Cloud
published images or shared images (`ImageOwnerAlias` set to `system` or
`others`), the request is not subject to RAM authorization checks. That does not
extend to your own custom images, which do need `ecs:DescribeImages`.

## Minimal policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeImages",
        "ecs:DescribeInstances"
      ],
      "Resource": [
        "acs:ecs:<region-id>:<account-id>:image/*",
        "acs:ecs:<region-id>:<account-id>:instance/*"
      ]
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstanceStatus"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}
```

`Resource` entries are the resource dimension only. The `Action` element lists
named permission points exclusively: never widen it to a product-level wildcard
form, and never add a permission point that is not in the table above. If the
customer prefers a managed policy over an explicit one, attaching the ECS
read-only managed policy to the diagnostic principal is the alternative; state
that it is broader than the table above.

## When a read call is refused

If a call returns `NoPermission` or `ImplicitDeny`:

1. Report the exact permission point that is missing, from the table above.
2. Show the corresponding `Statement` from the minimal policy so the customer
   can attach it.
3. Check whether an explicit `Deny` in another attached policy overrides the
   grant; that produces `ImplicitDeny` even when the grant exists.
4. Continue with the remaining read calls and mark the report `DEGRADED` rather
   than stopping, so the evidence that is available is still delivered.

Never respond to a refusal by proposing a write action, and never ask the
customer for an AccessKey pair: the scripts rely on the default credential chain
resolved by `aliyun configure`.

## Scope boundary

Sharing an encrypted image to another account requires a service role in the
**owner** account (`AliyunECSShareEncryptImageDefaultRole`, or
`AliyunECSShareEncryptSnapshotDefaultRole` for the underlying snapshots) whose
trust policy admits the recipient account's ECS service, plus KMS access for the
key that encrypted the snapshots. That role and its KMS grant belong to the
customer's own production account and are configured through the RAM console as
guided in `guide-steps.md`; this skill's diagnostic principal never needs them
and does not declare them.

## Axis: bt-panel-diagnosis
# RAM policies — alibabacloud-ecs-app-deploy-and-site-build (bt-panel-diagnosis)

Every API action this skill actually calls, its consent class, and the minimal
statements a customer needs. API names are not RAM name guesses: the action
codes below were verified for this scenario (each `Describe*` action's RAM code
is its own name; the product code is `ecs`, API version `2014-05-26`, except
the identity check under product `sts`, version `2015-04-01`).

## Actions actually called

| # | Product | Action (RAM code) | Class | Read/write | Consent | Used by |
| --- | --- | --- | --- | --- | --- | --- |
| 1 | ecs | `ecs:DescribeInstances` | A | read | none, automatic | locate the instance from an id or IP; lifecycle state; bound security-group ids |
| 2 | ecs | `ecs:DescribeInstancesFullStatus` | A | read | none, automatic | health and scheduled events (platform-layer exclusion) |
| 3 | ecs | `ecs:DescribeCloudAssistantStatus` | A | read | none, automatic | whether the guest read-only probes can run at all |
| 4 | ecs | `ecs:DescribeInvocations` | A | read | none, automatic | read back the output of the one consented probe (history, not live) |
| 5 | sts | `sts:GetCallerIdentity` | A | read | none, automatic | stamp every report with the account tail (cross-account guard) |

Plus one gated dispatch, called ONLY through `scripts/axes/bt_panel_diagnosis/bt_panel_diagnosis.py
probe` after the customer confirms that single command:

| # | Product | Action | Class | What it carries | Consent |
| --- | --- | --- | --- | --- | --- |
| 6 | ecs | `RunCommand` | B | one side-effect-free inspection command from the whitelist in [bt-readonly-evidence.md](bt-panel-diagnosis__bt-readonly-evidence.md) — `ls`, `stat`, `wc`, `df`, `findmnt`, `du`; on Windows `Get-Volume`, `Get-ChildItem` | **yes, per command** |

The action in row 6 dispatches nothing this skill has not whitelisted, and the
whitelist holds only commands that read state and write nothing. It is listed
in [../related_apis.yaml](../related_apis.yaml) because the script really
calls it. No standing grant is declared for it here: the probe runs under
whatever rights the customer's own credentials already hold, and the skill
asks permission for exactly one command each time.

## Minimal policy statement (class A — automatic queries)

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

`Resource: "*"` above scopes to the actions' own reach, not to broader
permissions: none of the listed actions can change anything, and the visible
footprint is one region of the calling account (queries only ever see the
current account's resources in the named region — two-account cases like
T-4B98459C stay invisible across the boundary, and the report says so).

## Denied calls: what to output

If any call returns `NoPermission` or `ImplicitDeny`:

1. name the exact missing action from the table above (or `RunCommand` for a
   consented probe);
2. show the customer the statement snippet above, limited to the missing
   action;
3. stop: never substitute a broader policy, never work around with another
   identity.

Authentication and expiry failures degrade the run with `[WARN]` lines and
`STATUS: DEGRADED` or `STATUS: FAIL`; the guidance points at `aliyun
configure` and never asks the customer to paste any credential value.

## Actions this skill neither calls nor assumes

Security-group rule editing, panel or web-service restarts, instance start,
stop or reboot, password resets, snapshot creation, file cleanup, firewall
changes and package installs are outside this skill: they are printed as
manual customer steps (with a snapshot-before-change reminder the customer
acts on themselves), never executed, never assumed granted. The cloud-side
rule-detail, metric, billing and DDoS-record queries were not verified for
this scenario and appear nowhere in the scripts.

## Axis: web-service-runtime-config
# RAM actions this skill needs

Every action below is one that `scripts/` actually issues, and every action the
scripts issue is listed here. No action is a wildcard: granting a whole product
prefix would hand a diagnostic skill far more than it needs, and the two writing
actions are scoped to the single resource the customer names.

The action names on the right of a colon are RAM action names, which do not
always match the API operation name. The CloudMonitor row is the one that
catches people out.

## Actions and their gates

| Cloud API operation | RAM action | Effect class | Gate in this skill |
|---|---|---|---|
| `sts get-caller-identity` (plugin-mode command) | `sts:GetCallerIdentity` | account self-check | automatic |
| `ecs DescribeInstances` | `ecs:DescribeInstances` | describes state | automatic |
| `ecs DescribeSecurityGroupAttribute` | `ecs:DescribeSecurityGroupAttribute` | describes rules | automatic |
| `ecs DescribeDisks` | `ecs:DescribeDisks` | describes attachments | automatic |
| `ecs DescribeInvocations` | `ecs:DescribeInvocations` | describes past command results | automatic |
| `cms DescribeMetricLast` | `cms:QueryMetricLast` | describes monitoring values | automatic |
| `ecs RunCommand` | `ecs:run-command` | **writes**: dispatches a command into the instance | announce, then confirm; one approved non-mutating command per call |
| `ecs CreateSnapshot` | `ecs:create-snapshot` | **writes**: creates a snapshot | announce, then confirm, including the billing note |

Two of the eight are writing operations, which is why this skill does not
describe itself as restricted to cloud-side queries. `RunCommand` exists so a
non-mutating observation can be taken inside the instance after the customer
agrees to that one command; `CreateSnapshot` exists so a manual repair step has
a rollback point before it starts. The commands behind `RunCommand` are frozen
in `scripts/axes/web_service_runtime_config/_constants.py` and validated twice before dispatch.

`InstallCloudAssistant` is **not called by this skill**: it is deliberately absent
from `../related_apis.yaml` and from every grant fragment in this file. Installing
the Cloud Assistant agent only completes after an instance restart, so it is a
guide-only action under [action-classes.json](action-classes.json) — the customer
is pointed at the console install flow and runs it themselves. Every restart-class
and irreversible action is guide-only on the same rule and has no dispatch call
site in `scripts/`; the full class-by-class contract, subordinate to
`action-classes.json`, is [action-authority-matrix.md](action-authority-matrix.md).

## Least-privilege fragment

Grant the diagnostic set on the resources under investigation, and keep the two
writing actions scoped to the instances and disks the customer names:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeSecurityGroupAttribute",
        "ecs:DescribeDisks",
        "ecs:DescribeInvocations",
        "cms:QueryMetricLast"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:run-command"
      ],
      "Resource": "acs:ecs:<region-id>:<account-id>:instance/<instance-id>"
    },
    {
      "Effect": "Allow",
      "Action": [
        "ecs:create-snapshot"
      ],
      "Resource": "acs:ecs:<region-id>:<account-id>:disk/<disk-id>"
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

`sts:GetCallerIdentity` needs no resource scoping: it describes the caller.

## When a call comes back denied

Report the exact action that is missing and point at the fragment above. The two
wordings this skill uses are `NoPermission` and `ImplicitDeny`; the older denial
wording is never used here, so that a reader is not sent looking for a policy
that the console does not show.

An identity that resolves to the wrong account is a different failure from a
missing action, so the report states which one it saw. Never widen a policy to a
wildcard to make a denial go away.

## Not granted, on purpose

No action in this skill can start, stop or reboot an instance, change a security
group rule, resize or delete a disk, delete a snapshot, uninstall a role or
module, or touch a file inside the instance. Those all appear in the report as
manual steps for the customer to perform. See
`references/web-service-runtime-config__handoff-matrix.md` for who owns each of them.

## Unverified items

| Item | State | Why it is left open |
|---|---|---|
| CloudMonitor `popVersion` for `DescribeMetricLast` | empty in `related_apis.yaml` | the batch verification pass recorded the operation and its RAM name but no version; the CLI resolves one itself, so nothing is guessed here |
| CloudMonitor namespace and metric names for CPU, memory and bandwidth | required from the caller | the verification reached "these parameters are mandatory", not their values; `report` degrades the resource area until they are supplied |
| `ecs:DescribeInstanceHistoryEvents` / `ecs:DescribeInstancesFullStatus` | not used | they would prove "the instance was stopped at 00:10", but neither was verified in this batch, so no permission point is invented for them |
| Windows observation cmdlets for IIS role state, application pool state and event logs | not used | not signed into the approved command list, so those readings come from the customer |

## Axis: db-on-ecs-diagnosis
# RAM Policies

Every permission this skill needs, at action granularity. No wildcard action
entry appears anywhere in this package, and no permission is declared that the
scripts do not actually call.

This skill is **not** an inspection-only package: besides its queries it can
dispatch two consent-gated write-class operations - a guest command through
Cloud Assistant that can only carry a non-mutating, whitelisted payload, and a
snapshot that adds a copy and alters no existing data. Each sits behind the
confirmation gate written into `SKILL.md` and enforced inside
`scripts/axes/db_on_ecs_diagnosis/db_on_ecs_diagnosis.py`. Following this suite's read-only convention,
**neither write carries a declared grant in the customer policy below**: both run
only under whatever rights the customer's own credentials already hold, and only
after the operator relays the disclosure and the user approves that single call.
A principal limited to the read-only grant is a supported mode, not a defect -
the guest leg then degrades to a paste-back checklist and the snapshot leg to
console guidance.

## Actions used

| Product | Action | Class | Permission point | Called from |
| --- | --- | --- | --- | --- |
| sts | `GetCallerIdentity` | query | `sts:GetCallerIdentity` | `scripts/axes/db_on_ecs_diagnosis/sts_token.py` |
| ecs | `DescribeInstances` | query | `ecs:DescribeInstances` | `fetch_instances` |
| ecs | `DescribeInstancesFullStatus` | query | `ecs:DescribeInstancesFullStatus` | `fetch_full_status` |
| ecs | `DescribeInstanceTypes` | query | `ecs:DescribeInstanceTypes` | `fetch_instance_type_detail` |
| ecs | `DescribeCloudAssistantStatus` | query | `ecs:DescribeCloudAssistantStatus` | `fetch_assistant_status` |
| ecs | `DescribeInvocations` | query | `ecs:DescribeInvocations` | `poll_invocation` |
| ecs | `RunCommand` | gated write (Class B, no declared grant) | `run-command` (CLI plugin-mode name; API `RunCommand`) | `submit_guest_command` |
| ecs | `CreateSnapshot` | gated write (Class B, no declared grant) | `create-snapshot` (CLI plugin-mode name; API `CreateSnapshot`) | `cmd_create_snapshot` |
| cms | `DescribeMetricLast` | query | `cms:QueryMetricLast` (the RAM point differs from the API name - never derive it from the apiName) | `fetch_metric` |

The same nine API names are declared in [../related_apis.yaml](../related_apis.yaml)
with their versions (the two gated writes are listed there as callable APIs but
deliberately carry no grant in the policy below). The three lists - this table,
the YAML declaration and the calls under `scripts/` - are kept aligned; adding a
call without adding it here is a defect.

## Why the two gated writes are needed

`RunCommand` under the `ecs` RAM code is write-class because it dispatches a
command into a customer instance. This skill uses it only to carry ONE command
from the frozen non-mutating whitelist in `scripts/axes/db_on_ecs_diagnosis/_constants.py` (disk and
inode usage, file-size listing, deleted-but-open file listing, mount table),
after the operator was told the exact command text, the target instance, that
the command writes nothing, and that the acknowledgement covers only that one
dispatch. It never carries a service, firewall, partition, filesystem, process
or package change; anything outside the whitelist is refused even after a
confirmation and is handed to the customer as a paste-back step instead.

`CreateSnapshot` under the `ecs` RAM code is the safety net this tier borrows
from the ticket practice: before any cleanup or space-releasing advice is
acted on, and before forensic evidence is preserved in a suspected intrusion,
a fresh snapshot exists. It is reversible in the sense that it creates an
additional copy and alters no existing data. It bills by stored capacity and
retention time, which is disclosed before the call. The instance does not need
to be stopped.

## Minimal policy, queries only

This is the **only** policy this skill needs declared. It is sufficient for
`check-auth`, the cloud-side legs of `diagnose`, and `explain`. A customer who
grants nothing beyond it still gets the full cloud-side verdict; the guest-reading
leg (`probe`) then degrades to "run it yourself and paste the output back", and
the snapshot leg (`create-snapshot`) degrades to console guidance.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "ecs:DescribeInstances",
        "ecs:DescribeInstancesFullStatus",
        "ecs:DescribeInstanceTypes",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "cms:QueryMetricLast"
      ],
      "Resource": "*"
    }
  ]
}
```

## Consent-gated writes (Class B) - no declared grant

The two write-class operations named in the table above are deliberately absent
from the policy document:

- The guest probe is dispatched through Cloud Assistant via the CLI plugin-mode
  command `run-command` (underlying API `RunCommand`, listed in
  `related_apis.yaml`). It is write-class even though it only carries one
  whitelisted, non-mutating command - which is exactly why it is not granted by
  default.
- The pre-cleanup / evidence snapshot uses the CLI plugin-mode command
  `create-snapshot` (underlying API `CreateSnapshot`); it adds a copy and alters
  no existing data, but it bills by stored capacity, so it too is not granted by
  default.

Both run only under whatever rights the customer's own credentials already hold,
and only after the `SKILL.md` confirmation gate is satisfied for that single call
(`probe` needs `--confirm`, `create-snapshot` needs `--confirm-cost`). Where an
operator genuinely wants the session itself to dispatch them, they may add the
matching write actions to their own policy out-of-band and narrow `Resource` to
the specific instance or disk ARN. That is a customer-side decision outside this
skill's default posture, and RAM cannot scope `RunCommand` down to the frozen
whitelist - that confinement lives in this skill's code, not in the grant.

## Actions this skill never calls

The `Delete`, `Release`, `Remove`, `Modify`, `Replace`, `Reset`, `Attach`,
`Detach`, `Reboot`, `Start`, `Stop`, `Authorize`, `Revoke`, `Bind`, `Unbind`,
`Assign`, `Unassign`, `Join`, `Leave`, `Import`, `Export`, `Cancel`, `Add`,
`Put`, `Tag` and `Untag` families are refused by
`NEVER_ALLOWED_ACTION_PREFIXES` in `scripts/axes/db_on_ecs_diagnosis/_constants.py`, and the refusal
holds even after a customer confirmation. In particular:

* snapshot or disk deletion, and instance or service restart - always human
  steps with the risk statement;
* security-group rule edits, even to "fix" a blocked database port - the
  console or another tier owns that change;
* database account, grant or authentication-mode changes - the report emits
  the check procedure and stops;
* `InvokeCommand` and `DescribeCommands` - not verified for this tier;
* order, renewal and bill APIs - commercial questions are recognised and
  handed over, never queried here.

Do not add any of them to a policy for this skill.

## Denied calls

A denied call surfaces with the code the platform returned, `NoPermission` or
`ImplicitDeny`. The report names the specific missing action from the table
above and points here for the fragment that supplies it; the recovery is a
policy change in the customer's account, never a request for an AccessKey
pair. This package does not accept, read, store or forward credential
material: the local CLI default credential chain is the only authentication
path, refreshed by the operator with `aliyun sts get-caller-identity`.

## Credential and data-handling rules baked into the code

* Credential names (`AccessKeyId`, `AccessKeySecret`, `SecurityToken`,
  `Signature`) appear in `_cli.py` exclusively as redaction targets; every
  error string passes through that redaction before it is printed.
* The report carries resource identifiers, statuses, sizes and usage
  percentages only, so it can be pasted into a ticket without leaking secret
  data; the account label keeps only the trailing four digits.
* Guest command output is transient in-memory text; nothing the customer
  holds is written to disk by this skill, and no command carrying output
  redirection is ever dispatched.

## Axis: ssl-cert-deployment
# RAM policy — permissions for the ECS SSL certificate deployment triage skill

This skill dispatches four observation-class list calls (including the
certificate-service inventory) plus one identity call without any gate, and exactly two confirmation-gated calls
(`RunCommand` for ONE whitelisted information-only guest reading, and
`CreateSnapshot` for the pre-change backup of one named disk). This file is
the complete, per-action declaration: nothing outside it is ever called, and
no wildcard is granted or requested.

## Authorized actions

The table lists every action with its exact PascalCase name. The RAM-console
string for any row is built from the `Prefix` cell plus the action name (for
example the `ecs` prefix plus `DescribeInstances` gives the standard
`ecs`-prefixed RAM action for that call).

| Prefix | Action | Class | Gate | Purpose in this skill | Where it is called |
| --- | --- | --- | --- | --- | --- |
| ecs | `DescribeInstances` | evidence | none | region, guest kind, instance state and the public addresses that anchor the DNS-drift comparison | `scripts/axes/ssl_cert_deployment/ssl_cert_deployment_report.py` |
| ecs | `DescribeInstanceStatus` | evidence | none | lifecycle state of the named instance | `scripts/axes/ssl_cert_deployment/ssl_cert_deployment_report.py` |
| ecs | `DescribeInvocations` | evidence | none | fetch the result of ONE confirmed guest reading | `scripts/axes/ssl_cert_deployment/ssl_cert_deployment_report.py` |
| cas | `ListUserCertificateOrder` | evidence | none | certificate inventory and state (issued / expired / pending, validity window) for the console-free inventory read | `scripts/axes/ssl_cert_deployment/ssl_cert_deployment_report.py` |
| ecs | `RunCommand` | gated dispatch | user confirmation per the SKILL.md User Confirmation section | dispatch ONE whitelisted information-only guest reading (never arbitrary input; the script refuses anything else) | `scripts/axes/ssl_cert_deployment/ssl_cert_deployment_report.py` |
| ecs | `CreateSnapshot` | gated write | user confirmation per the SKILL.md User Confirmation section | pre-change backup of one named disk, required before guiding any in-server certificate change | `scripts/axes/ssl_cert_deployment/ssl_cert_deployment_report.py` |
| sts | `GetCallerIdentity` | identity | none | prove the credential chain and label the account (settles wrong-account and cross-account questions) | `scripts/axes/ssl_cert_deployment/sts_token.py` |

The two gated rows carry the `ecs` product prefix like every other ECS row
when entered in the RAM console. They are the only actions in this skill
that are not pure observation, and the entry script refuses to dispatch
them unless the operator passes the confirmation flags for that exact
region and target. `RunCommand` itself is a write-class channel, but the
payload is always one whitelisted, information-only command.

No wildcard permission string is declared, requested or used anywhere in
this package: prefix wildcards such as `ecs` plus colon plus star would
also cover the mutating actions this skill is designed never to call
(instance restart or stop, security group edits, snapshot or file removal,
certificate order submission), and action-suffix wildcards are refused by
the same rule.

## Minimal policy fragment

The fragment below covers the evidence sweep and the identity check, the
modes that run without a gate:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeInvocations",
        "cas:ListUserCertificateOrder",
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

When the customer opts into the gated flows, add the two gated ECS action
names from the table above (`RunCommand` and `CreateSnapshot`, each with
the same `ecs` product prefix convention used in the fragment) to the
Action list, or attach them through a separate statement scoped to the
specific disk, instance and region involved. If the gated actions are not
granted, the whole evidence report still works, and the two gated modes
report `NoPermission` with this file as the recovery pointer.

`Resource: "*"` is acceptable for the sweep because every call is scoped by
the region and resource id supplied on the command line. A tighter policy
may replace it with `acs:ecs:<region-id>:<account-id>:instance/<instance-id>`,
`acs:ecs:<region-id>:<account-id>:disk/<disk-id>` and
`acs:ecs:<region-id>:<account-id>:snapshot/*` as appropriate.

## Scenario-to-action mapping

| Decision-tree branch | Actions used |
| --- | --- |
| T0 identity and scope | `GetCallerIdentity`, `DescribeInstances`, `DescribeInstanceStatus` |
| T1 issuance or renewal failure | `DescribeInstances` (region lens); endpoint ownership uses public DNS only, no cloud action |
| T2 deployment not effective | `DescribeInstances`; certificate view comes from the outside-in TLS check, no cloud action |
| T3 certificate body faults | same as T2; the file-metadata reading goes through the gated `RunCommand` plus `DescribeInvocations` when the customer approves |
| T4 HTTPS unreachable | `DescribeInstances` (address baseline); security group and DNS records stay console-side self-checks |
| T5 product-rule questions | none (offline knowledge, plus the console for the customer) |
| Pre-change backup (gated) | `CreateSnapshot` |

## Not declared, on purpose

The certificate-service inventory is now read through `cas:ListUserCertificateOrder`
(declared above). DNS record queries (`alidns:DescribeDomainRecords`) and security
group rule queries (`ecs:DescribeSecurityGroupAttribute`) exist as read-only APIs
but this area does not call them, so they stay absent from the manifest and the
policy and the corresponding checks remain console self-service steps. Unverified
actions are never guessed into a policy.

## When a call is denied

The scripts report denial with the literals `NoPermission` or `ImplicitDeny`
plus the exact missing action name, and never with a generic permission
wording. The recovery is always identical: ask the account administrator to
attach the fragment above (or the one missing action from it), then re-run
the identical command. The skill does not ask for, read, store or pass any
credential material — the local CLI default credential chain is the only
source, and refreshing it is done with `aliyun sts get-caller-identity` by the operator.

## Credential and data-handling rules baked into the code

* Key material never appears as a command argument anywhere; the transport
  layer additionally redacts credential-looking key/value pairs from every
  error string before it is printed.
* The report contains resource identifiers, certificate dates, issuers and
  states only — never private keys and never file contents (the approved
  guest readings print metadata, not data).
* The printed account label keeps only the trailing four digits of the
  account id.
