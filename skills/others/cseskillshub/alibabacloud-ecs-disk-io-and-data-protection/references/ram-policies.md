# RAM permissions for alibabacloud-ecs-disk-io-and-data-protection (union of 3 axes, per-axis sections
# are verbatim copies of member specs that each passed the static gate)
disk-io-diagnosis
# RAM actions required by this skill

Every entry below is an action the scripts actually call. There is no wildcard anywhere
in this package, and no action is listed that the code does not use.

## 1. Actions in use

| Cloud product | OpenAPI action | RAM action to grant | Effect | Used by | Purpose |
|---|---|---|---|---|---|
| `sts` | `GetCallerIdentity` | none published for this call | inspect | `scripts/axes/disk_io_diagnosis/sts_token.py` | Confirm which account the ambient credentials belong to |
| `ecs` | `DescribeInstances` | `ecs:DescribeInstances` | inspect | `scripts/axes/disk_io_diagnosis/disk_io_diagnosis.py` | Resolve the instance, its region, zone, instance type and OS family |
| `ecs` | `DescribeDisks` | `ecs:DescribeDisks` | inspect | `scripts/axes/disk_io_diagnosis/disk_io_diagnosis.py` | Enumerate every disk with its category, performance level and size |
| `ecs` | `DescribeInstanceTypes` | `ecs:DescribeInstanceTypes` | inspect | `scripts/axes/disk_io_diagnosis/disk_io_diagnosis.py` | Read the storage-related fields of the instance type |
| `cms` | `DescribeMetricLast` | `cms:QueryMetricLast` | inspect | `scripts/axes/disk_io_diagnosis/disk_io_diagnosis.py` | Read monitoring values for a disk or instance over a window |
| `ecs` | `RunCommand` | none (Class B, no declared grant) | **changes state of the Cloud Assistant channel** | `scripts/axes/disk_io_diagnosis/disk_io_diagnosis.py` (`guest-cmd`) | Deliver one whitelisted inspection command inside the instance |
| `ecs` | `DescribeInvocations` | `ecs:DescribeInvocations` | inspect | `scripts/axes/disk_io_diagnosis/disk_io_diagnosis.py` (`guest-cmd`) | Read back the recorded result of an invocation |
| `ecs` | `CreateSnapshot` | none (Class B, no declared grant) | **creates a billable resource** | `scripts/axes/disk_io_diagnosis/disk_io_diagnosis.py` (`snapshot`) | Take one restore point before a customer-performed change |

The two gated writes above (Cloud Assistant `run-command` and `create-snapshot`, whose OpenAPI
actions are `RunCommand` and `CreateSnapshot` of the `ecs` product, version 2014-05-26) are
class-B operations and are **deliberately granted nothing in the policy below**: the skill
performs them only under whatever write rights the customer's own credentials already hold,
after a per-call confirmation, and it never ships a policy fragment that grants them. A
lowercase hyphenated `ecs:`-prefixed spelling is not a valid RAM action identifier and
must never be pasted into the console; the OpenAPI column records the real operation name.

## 2. The naming trap for CloudMonitor

`DescribeMetricLast` is the OpenAPI action name. The RAM action that authorises it is
`cms:QueryMetricLast`. They are not the same string.

- Grant `cms:QueryMetricLast`.
- Do **not** write `cms:DescribeMetricLast`; that statement matches nothing and the call
  fails as if no permission existed.
- Do not infer the RAM prefix from the CLI product name either; the same class of mismatch
  appears in other products.

## 3. Minimal policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeDisks",
        "ecs:DescribeInstanceTypes",
        "ecs:DescribeInvocations"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": ["cms:QueryMetricLast"],
      "Resource": "*"
    }
  ]
}
```

The policy above is intentionally **read-only**: it declares grants for the seven inspect
calls only. The two consent-gated writes (`run-command`, `create-snapshot`) carry no grant
here (Class B) - running this skill in its default inspection-only posture needs nothing
more. If, after the per-call disclosure and confirmation, the customer's own administrator
credentials already allow those actions, the subcommands deliver; otherwise they stop at
their confirmation prompt and the report says so instead of pretending the reading exists.
Adding a write grant is an out-of-band customer-side decision, not something this package
ships.

## 4. Two consent-gated writes (Class B) - no declared grant

`run-command` and `create-snapshot` are the only state-changing operations in this package.
Neither carries a grant in the minimal policy above. Both are held behind the confirmation rule in `../SKILL.md`: the exact command or
disk is shown to the customer first, and the script refuses to call the API until the
confirmation flag for that single invocation is set. Everything else in the table above is
an inspect call and runs without a gate.

`RunCommand` is a state-changing API even when the delivered command only prints
information. The command set that may be delivered is fixed in
`guest-commands.md`; anything outside it is refused rather than improvised.

## 5. Credentials

Credentials come from the default chain of the environment running the CLI. This package
never reads, stores, prints or asks for an access key id, an access key secret, a security
token or an instance password. Error text passing through the scripts is scrubbed of
anything shaped like a credential before it is written out.

When the ambient credentials are missing or expired, the operator configures them out of
band with `aliyun configure`; the scripts only report that this is required.

## 6. Permission failures

Two codes appear from Alibaba Cloud authorization: `NoPermission` (an explicit deny or no
matching grant) and `ImplicitDeny` (nothing granted the action). When either appears:

1. Name the single missing action from the table above.
2. Show the corresponding fragment of the minimal policy.
3. State which subcommand was affected.
4. Stop. Do not retry the call in a loop, and do not substitute a broader policy "to make
   it work".

A `NoPermission` on `run-command` is not a reason to ask the customer for an instance
password; report the gap and continue with what the cloud side can still see.

disk-encryption-kms-guide
# RAM policy - alibabacloud-ecs-disk-encryption-kms-guide

This skill is read-only. It declares exactly three permissions, all of them read-only
`Describe` actions on product `ecs`, API version `2014-05-26`. Each line below is the
verified RAM permission point for this tier - taken from the API contract, not derived from
the interface name.

| Permission point | Access level | What the read is used for |
|---|---|---|
| `ecs:DescribeInstances` | Read | Confirm the instance exists in the region, its zone, OS type and lifecycle state, and that the id belongs to ECS at all |
| `ecs:DescribeDisks` | Read | List the system and data disks of an instance or region and read back their encryption-related attributes |
| `ecs:DescribeSnapshots` | Read | Read snapshots and their encryption attributes, so the source-disk inheritance rule can be shown from data instead of asserted |

No other permission point is declared, no action name is written with a wildcard suffix, and
no permission of another product is claimed by this skill.

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
        "ecs:DescribeSnapshots"
      ],
      "Resource": "*"
    }
  ]
}
```

## If a read is refused

A refusal is always one of the two literals below. Answer with the missing permission point
and the snippet above - never by retrying with broader rights.

| Returned literal | Meaning | What to tell the customer |
|---|---|---|
| `NoPermission` | The profile has no explicit allow for that action | Name the action, give the snippet, and say an account administrator must grant it |
| `ImplicitDeny` | Nothing in the effective policy covers the action, or a control denies it | Name the action, give the snippet, and say a resource-directory control may also apply |

Other codes are not permission problems and must be reported exactly as returned:

- `InvalidParameter` / `MissingParameter`: fix the region or the id, then re-read.
- an empty list: that is "nothing visible to this profile", **not** "not encrypted".

Never report an encryption state that was not read.

## Identity check

`scripts/axes/disk_encryption_kms_guide/sts_token.py` performs a caller-identity read through the customer's existing
profile so the report can name which account was inspected. That read is a verification step
on the customer's own session, needs no policy grant of its own, and is therefore not a data
API of this skill and is not listed in `related_apis.yaml`.

## What these reads cannot cover

- One account in one region per call: other regions need their own run.
- No key-management objects, no key policy or rotation state.
- No order, invoice or account-balance data.
- No resource of another product line.
- Nothing inside the guest operating system: volume encryption, filesystem state and
  initialisation of a newly provisioned disk are only ever known from a customer paste-back.

disk-replication-dr-guide
# RAM Permission Declaration

This skill performs **read-only** evidence collection and manual guidance for
Alibaba Cloud ECS disk asynchronous replication / disaster recovery (DR). It
declares ONLY the concrete read actions its scripts actually invoke -- no
wildcard action (an asterisk wildcard is prohibited) and no write action of
any kind.

## 1. Actions actually used

| RAM action | Purpose | Invoked by |
|---|---|---|
| `ecs:DescribeInstances` | List instances of a region (zone, status, charge type) for the DR evidence inventory | `scripts/axes/disk_replication_dr_guide/disk_dr_inventory.py` |
| `ecs:DescribeDisks` | List cloud disks of a region (category, zone, size, automatic-snapshot flag) | `scripts/axes/disk_replication_dr_guide/disk_dr_inventory.py` |
| `ecs:DescribeSnapshots` | List snapshots of a region (existence, type, source disk) as backup evidence | `scripts/axes/disk_replication_dr_guide/disk_dr_inventory.py` |
| `sts:GetCallerIdentity` | Verify the caller identity and derive the account UID label (via the plugin-mode command `aliyun sts get-caller-identity`) | `scripts/axes/disk_replication_dr_guide/sts_token.py` and the identity step of `scripts/axes/disk_replication_dr_guide/disk_dr_inventory.py` |

All four are read-only. The API version used for the ECS actions is
`2014-05-26`; for STS it is `2015-04-01` (same values as declared in
`related_apis.yaml`).

## 2. Read-only boundary

- This skill never declares, requests or invokes any mutating action. Cloud-side
  operations that change resources -- for example creating or deleting a disk
  replication pair, adding a pair to a consistency group, or performing a DR
  failover -- are executed **by the customer in the console** under the
  customer's own permissions. This skill only explains the steps, the risks
  and the verification method; it never performs them and never asks for extra
  permissions to perform them.
- Granting a broad full-access policy (such as `AliyunECSFullAccess`) to run
  this skill violates the least-privilege principle and is unnecessary: the
  four read actions above are sufficient.

## 3. Minimal custom policy (recommended)

Create a custom RAM policy with exactly this document and grant it to the RAM
user or role whose credential the aliyun CLI uses:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeDisks",
        "ecs:DescribeSnapshots"
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

System-policy alternative: `AliyunECSReadOnlyAccess` covers the three ECS read
actions; the identity check additionally needs `sts:GetCallerIdentity`.

## 4. Who can grant

Authorization must be performed by the Alibaba Cloud account owner, or by a
RAM identity that already holds RAM administration rights. A RAM user without
any grant cannot authorize itself -- forward this file to the account
administrator and retry after the policy is granted.

## 5. Grant steps (console)

1. Log in to the RAM console with the primary account or a RAM administrator identity.
2. In the left navigation pane, choose **Identities > Users** (or **Roles** for an STS role) and locate the target identity.
3. In the **Actions** column, click **Grant Permissions**.
4. In the grant panel, either select `AliyunECSReadOnlyAccess` or switch to **Custom Policy** and select the minimal policy from section 3.
5. Confirm the scope and click **OK**, then verify the policy appears under the identity's **Permissions** tab.

## 6. Permission failure verification

Authorization failures are reported by this skill with the literals
`NoPermission` or `ImplicitDeny` (never any other wording). When such an error
appears in the script output (`[WARN]` lines, the per-region `errors[]`
records), locate the missing action below, grant it, and rerun:

| Error pattern (in `errors[]` / stderr) | Failing query | Missing RAM action | Quick fix |
|---|---|---|---|
| `NoPermission` / `ImplicitDeny` on the instance query | `DescribeInstances` | `ecs:DescribeInstances` | Grant the section-3 policy or `AliyunECSReadOnlyAccess` |
| `NoPermission` / `ImplicitDeny` on the disk query | `DescribeDisks` | `ecs:DescribeDisks` | Grant the section-3 policy or `AliyunECSReadOnlyAccess` |
| `NoPermission` / `ImplicitDeny` on the snapshot query | `DescribeSnapshots` | `ecs:DescribeSnapshots` | Grant the section-3 policy or `AliyunECSReadOnlyAccess` |
| `NoPermission` / `ImplicitDeny` on the identity check | `sts get-caller-identity` | `sts:GetCallerIdentity` | Grant the section-3 identity statement |
| `InvalidAccessKeyId.NotFound` / `SignatureDoesNotMatch` / `SDK.InvalidCredential` | any query | none -- credential chain problem | Run `aliyun configure`; never handle AccessKey material manually |

## 7. Visibility scope

The four actions above return resources of **the authorized account only, in
the regions explicitly passed to the script**. An empty result therefore
means "nothing found in the queried account + region scope", never "the
account has no backups anywhere". Other backup products (for example cloud
backup/HBR), billing data and security-group configuration are outside this
skill's authorized surface and must not be inferred from these queries.

## Axis: disk-pl-change-guide
# RAM Policy Requirements — alibabacloud-ecs-disk-io-and-data-protection (disk-pl-change-guide)

This skill **changes no cloud resource**. Its declared permission surface is
strictly read-only: it reads cloud data through seven query actions — five ECS
Describe actions (`DescribeDisks`, `DescribeInstances`, `DescribeInstanceTypes`,
`DescribeSnapshots`, `DescribeInvocations`), the CloudMonitor metric action, and
the STS identity check — all listed in the policy below. The guest listing
channel is a **Class B consent-gated dispatch** (CLI plugin-mode command
`run-command`, i.e. the `RunCommand` API operation) restricted to the fixed
allowlist of non-mutating guest listing commands in
[guest-diagnostics.md](disk-pl-change-guide__guest-diagnostics.md) §2, one command per explicit
customer confirmation. Like every write-class operation it holds **no place in
this file's declared grant**: it runs only under permissions the customer's own
credentials already carry, and a session limited to the read-only grant below
is a supported mode, not a defect (the guest path then degrades to `NoPermission`
and the customer-run listing steps). `DescribeInvocations` exists only to read
back the result of a confirmed call the customer's own rights allow. Everything
else — every disk type / performance-level change, snapshot, billing or
capacity action on an ESSD or other cloud disk — is performed by the customer
in the console with their own permissions.

Calls are made exactly as invoked by `scripts/axes/disk_pl_change_guide/disk_pl_advisor.py` and
`scripts/axes/disk_pl_change_guide/sts_token.py`, and the list below is the same set declared in
`../related_apis.yaml`.

## Minimum custom policy (action-level, no wildcards)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeDisks",
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceTypes",
        "ecs:DescribeSnapshots",
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

The policy above is query-only by design: no statement grants a write action.
The Class B guest dispatch (`run-command` in CLI plugin mode) is deliberately
absent, so revoking or never adding it leaves the cloud-side read path and every
self-check handover fully working, and only `--mode guest` degrades to
`NoPermission`. When the customer chooses to enable the guest listings, they
grant the `RunCommand` API operation (service-prefixed with `ecs:` and the
PascalCase action name when written as a real policy `Action` value — this
document deliberately spells neither the prefixed nor the lowercased variant
inline, only the bare operation name `RunCommand` and the CLI plugin-mode form
`run-command`) on their own credentials, narrowed to the specific
`acs:ecs:<region>:<uid>:instance/<instance-id>` ARNs whose guest listings they
have agreed to provide; `"*"` in the query statements is the minimum shape that
works across regions, not a recommendation to widen the guest grant.

## Action-by-action rationale

| RAM action | API called | CLI form | Used by | Why |
|---|---|---|---|---|
| `ecs:DescribeDisks` | `DescribeDisks` (2014-05-26) | `aliyun ecs describe-disks ...` | assess / bottleneck / verify | disk category, performance level, capacity, status, attachment — the eligibility verdict and the capacity input of the ceiling formulas |
| `ecs:DescribeInstances` | `DescribeInstances` (2014-05-26) | `aliyun ecs describe-instances ...` | assess / bottleneck / guest | resolve the attached instance and its instance type for the min(instance, disk) attribution chain; in guest mode, confirm the instance is visible and is not Windows before any dispatch |
| `ecs:DescribeInstanceTypes` | `DescribeInstanceTypes` (2014-05-26) | `aliyun ecs describe-instance-types ...` | bottleneck | instance-type family / size anchor for the instance-side storage ceiling lookup |
| `ecs:DescribeSnapshots` | `DescribeSnapshots` (2014-05-26) | `aliyun ecs describe-snapshots ...` | assess | existence-only snapshot pre-check before a change (the snapshot itself is taken by the customer in the console) |
| `run-command` (Class B — no declared grant) | `RunCommand` (2014-05-26) | `aliyun ecs run-command ...` | guest only | **consent-gated dispatch, granted by the customer's own credentials, not by this file.** Allowed solely for the five allowlisted non-mutating listing commands, always behind the per-command confirmation gate, always a single `InstanceId.N`. Never used for installs, cleanup, restarts, config edits or any mutation |
| `ecs:DescribeInvocations` | `DescribeInvocations` (2014-05-26) | `aliyun ecs describe-invocations ...` | guest only | bounded poll of the dispatched command until a terminal status, then relay of exit code and output |
| `cms:QueryMetricLast` | `DescribeMetricLast` (cms 2019-01-01) | `aliyun cms describe-metric-last ...` | bottleneck | latest disk IOPS / throughput datapoints vs calculated ceilings. **Note: the RAM action name is `cms:QueryMetricLast`, NOT the API name** |
| `sts:GetCallerIdentity` | `GetCallerIdentity` (sts 2015-04-01) | `aliyun sts get-caller-identity` (plugin mode, lowercase-hyphenated) | pre-check of every cloud mode | account UID traceability label; takes no parameters |

## Permission gaps and the guest grant

The managed ECS and CloudMonitor query policies cover the query actions
above but **not** the Class B `run-command` dispatch; a broad managed ECS policy
would instead over-grant every write action this skill must never hold. That is
why the action-level query-only custom policy above is the required form for
this skill.

When a call is denied the scripts emit `[WARN] <step>: NoPermission ...`
(or `ImplicitDeny`) per the error-handling contract in `../SKILL.md`,
name the exact missing action from this table, and degrade to
`STATUS: DEGRADED`. A missing grant is always surfaced as `NoPermission` /
`ImplicitDeny` — the scripts never reinterpret a denial as "resource not
found", and never substitute a guess for the missing reading.

## Scope and account boundaries

- Queries cover **the authorized account and the requested region only**.
  Cross-account disks (managed/partner accounts) are invisible; the scripts
  then report DEGRADED and ask the customer to confirm account and region
  instead of guessing.
- `ecs RunCommand` reaches only instances visible in that same account and
  region, and only through Cloud Assistant on the instance. Windows
  instances are refused by the script before any dispatch.
- Credentials come exclusively from the aliyun CLI **default credential
  chain** (environment or `~/.aliyun/config.json`). The skill never reads,
  prints, caches, requests, or stores access keys or tokens.
