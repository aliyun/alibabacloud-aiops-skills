# RAM permissions for alibabacloud-ecs-server-migration-on-cloud (union of 4 axes, per-axis sections
# are verbatim copies of member specs that each passed the static gate)

## Grant flow (applies to every axis)

Each axis section below carries its own minimal policy fragment and names the
exact actions it calls. When a read is refused, the dispatcher reports
AUTHORIZATION-GAP with the one missing action; grant that single action from the
matching axis fragment, then re-run the same request unchanged. Do not switch
account or identity to work around a refusal.

Pick the grant path that fits the identity the session runs as (the preflight
`GetCallerIdentity` prints `IdentityType`):

Option A - RAM user (same-account daily use, `IdentityType: RAMUser`):

1. RAM console -> Identities -> Users -> select or create the user the session
   runs as.
2. Permissions -> Policies -> create a custom policy from the axis's minimal
   policy fragment below (script editor).
3. Attach the policy to that user (grant the custom policy on the user's
   Permissions tab).
4. Configure the aliyun CLI with that user's profile (the CLI default credential
   chain). The scripts resolve credentials only through the CLI default chain;
   they take no credential arguments and never print credential material.

Option B - RAM role (temporary or cross-account use, `IdentityType: AssumedRoleUser`):

1. RAM console -> Identities -> Roles -> create a role whose trust policy allows
   `sts:AssumeRole` for the calling identity.
2. Attach the same custom policy (from the axis fragment) to the role.
3. Assume the role and store the temporary session as a named CLI profile; the
   scripts resolve it through the CLI default chain.
4. Effective permission is the intersection of the role policy and any session
   policy passed at AssumeRole: when a refusal persists after the role grant,
   check both places - a session policy that omits the action denies it even
   though the role policy allows it.
5. Temporary credentials expire: on `SecurityTokenExpired` / `InvalidSecurityToken`
   re-run AssumeRole (or the company SSO login helper) to refresh, then retry -
   that is a credential refresh, not a policy change.

Least-privilege rules (all axes):

- Grant only the actions listed in the axis section; add only the one named
  action when a call is refused - do not widen the action list.
- Do not attach `AliyunECSFullAccess`, `AdministratorAccess` or any
  administrator/full-access managed policy as a workaround.
- Prefer a role with a short session over long-lived keys; never share or paste
  credentials anywhere - the scripts never ask for them.
- In-guest reads are not a RAM permission: they ride the consent-gated Cloud
  Assistant dispatch where an axis declares one, and stay off by default.

site-migration-guide
# RAM permissions used by this skill

Every action below is called by `scripts/` and declared in `related_apis.yaml`. Nothing else is
reachable: the layer in `scripts/axes/site_migration_guide/_cli.py` refuses any action that is not in the allow-list, so the
skill cannot widen its own permissions.

## Granted actions

| Product | Action | RAM permission | Why the skill needs it |
|---|---|---|---|
| ecs | DescribeInstances | `ecs:DescribeInstances` | Source and destination inventory: status, region and zone, instance type, image id, billing type, bound security groups, public and private addresses |
| ecs | DescribeInstanceStatus | `ecs:DescribeInstanceStatus` | Confirm the source is healthy before the move and the destination is running after it |
| ecs | DescribeAvailableResource | `ecs:DescribeAvailableResource` | Confirm the destination region and zone actually sell the specification the site needs |
| ecs | DescribeInvocations | `ecs:DescribeInvocations` | Read recorded Cloud Assistant invocation history, which indicates whether in-instance inspection has been possible on that instance |
| sts | GetCallerIdentity | `sts:GetCallerIdentity` | Resolve the account UID in scope, so a cross-account move is not planned against the wrong owner |

There is no product wildcard and no action wildcard in this list. The policy below is the minimum
that lets the reports succeed; do not replace an enumerated action with a product-wide form such as
`ecs:` followed by a star.

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
    }
  ]
}
```

`Resource` stays open because these are listing and status queries; the `Action` values are the
controlled part.

## Deliberately not granted

The write path of a migration is executed by the customer in the console, so no permission is
declared here for: creating a custom image, copying an image to another region, sharing an image
with another account, purchasing an instance, replacing an instance operating system, transferring
an instance between accounts, taking or deleting a snapshot, creating or mounting a disk, changing
security-group rules, editing DNS records, or any unsubscription and refund step. If a request needs
one of those, the skill states the boundary and prints the documented console procedure instead.

Adding any of them to this file requires a verified API contract, a reviewed permission gate, and a
matching entry in `related_apis.yaml` first. Never add an action from memory.

## Failure handling

- `NoPermission` or `ImplicitDeny` on one action: print the action name, show the matching statement
  from this file, and tell the customer to have an administrator attach it. Then continue with the
  remaining evidence and end with `STATUS: DEGRADED`.
- Missing or unconfigured credentials: tell the customer to run `aliyun configure` themselves. The
  skill never asks for, reads, prints, or stores an AccessKey id, secret, or token; the CLI default
  credential chain is the only supported path, and credential-looking substrings in error text are
  masked before display.
- A RAM permission name can differ from the API name for some products. The five actions above were
  checked to be identical in form; verify any newly added action against the official authorization
  reference instead of deriving the permission from the API name.

onmigration-assessment
# RAM permissions for this skill

Every action listed here is invoked by `scripts/`. No action name is ever
abbreviated to stand for a whole product, and no action outside this page is
attempted.

## Actions actually called

| Action | Why this skill needs it |
| --- | --- |
| `ecs:DescribeInstances` | Source and target inventory: instance type and family, image, network, public address, security groups, expiry |
| `ecs:DescribeInstanceStatus` | Run state before a migration window and after a migration |
| `ecs:DescribeDisks` | Disk category and size: local-disk and encrypted-disk constraints, provisioned size for a shrink question |
| `ecs:DescribeAvailableResource` | Whether the target instance type is still sellable in the target region and zone |
| `ecs:DescribeCloudAssistantStatus` | Whether an in-guest inspection command can reach the instance at all |
| `ecs:DescribeInvocations` | Read back the output of one inspection command |
| `ecs:run-command` | Issue exactly one inspection-only command from the allow-list inside the guest, after the customer confirmed that single command |
| `ecs:create-snapshot` | Snapshot before change: one snapshot of one disk, after the customer accepted the billing impact |
| `sts:GetCallerIdentity` | Confirm which account the credential belongs to, and tag the report with it |

`run-command` and `create-snapshot` above are the CLI plugin-mode spellings that
`scripts/` issues; in the RAM console the same two grants appear under the
matching public ECS API names declared in `related_apis.yaml`.

## Minimal policy

Grant only what the operator needs. For a purely advisory run, drop
`ecs:run-command` and `ecs:create-snapshot` from the statement: the assessment
still works, and in-guest readings then come from the customer.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeDisks",
        "ecs:DescribeAvailableResource",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInvocations"
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

`Resource: "*"` above is the ECS query convention; narrow it to the instance and
disk ARNs in scope when the sub-account should only see one migration.

## The two write actions are gated

- `ecs:run-command` is used for one command at a time, taken from the
  inspection-only allow-list in `scripts/axes/onmigration_assessment/_constants.py`. Before it runs, the
  script prints the exact command, what it reads, and that it changes nothing;
  execution needs an explicit `--confirm yes`, and that confirmation covers only
  that one command. Any command outside the allow-list is refused.
- `ecs:create-snapshot` creates one snapshot of one disk, always before a change
  rather than as a cleanup step, and needs the same explicit confirmation
  because snapshots are billed by stored capacity.

Anything destructive or repairing is never issued by this skill: no deletion,
formatting, file-system repair, boot-loader rebuild, partition change, service or
instance restart, agent uninstall, or snapshot removal. Those steps are written
out for a human operator, with the risk stated.

## When a call comes back refused

A missing grant surfaces as `NoPermission` or `ImplicitDeny`. The report then
states which action is missing and points at the smallest statement above that
adds it. Fixing the grant is a console action taken by the account administrator;
this skill does not modify policies.

## Server Migration Center

Server Migration Center task and source APIs are not called by this skill, so it
requests no permission from that product. Migration task state comes from the
customer's own console and log readings; see `smc-errors.md`.

forced-migration-guide
# RAM policies

This is a **read-only** guide skill. It performs exactly one cloud OpenAPI call on
behalf of the agent, inside the caller's own account and the single `RegionId` you pass.

## Required permission (minimum)

| Action | RAM permission | Access level | Notes |
|---|---|---|---|
| `ecs DescribeInstances` | `ecs:DescribeInstances` | Read | Returns instance status, region/zone, charge type, and bound security groups. |

That single read-only permission is the whole automatic call chain. The `related_apis.yaml`
file declares exactly this action.

## Not requested, not used

- No resource-changing permission of any kind is declared or requested. This skill has no
  capability to alter cloud state; every customer-facing action is a manual step the
  customer performs in their own console.
- `aliyun sts get-caller-identity` is used only as a best-effort identity probe for the
  report header; it requires no ECS permission and only reflects the caller's own account.
- Two adjacent ECS read actions were considered during design but their RAM action names
  were **not confirmed by measurement** in the injected contract, so they are deliberately
  excluded from the automatic call chain. Where useful, they are replaced by console-only
  guidance the customer follows themselves. Do not grant extra ECS permissions for this skill.

## Minimal policy document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances"
      ],
      "Resource": "*"
    }
  ]
}
```

No wildcard on actions is used; the policy lists the specific read action only.

## Credential handling

The skill relies solely on the **default credential chain** already configured for the
`aliyun` CLI (for example `aliyun configure` profiles or standard environment variables).
It never reads, writes, prints, stores, or transmits any access key, secret, or token.

## On permission failure

If the read query returns `NoPermission` or `ImplicitDeny`, the report names the single
missing read action above and asks you to grant it to the caller, then re-run. It does not
guess a cause and never falls back to any other action.

instance-clone-guide
# Minimal Read-Only RAM Policy

This skill performs strictly read-only fact queries plus manual guidance. It
requires two ECS describe actions and the STS identity action. No wildcard
action entries are used anywhere in this file; every action is listed
explicitly by name.

The skill NEVER acts on behalf of the customer for any change: images,
regional image copies, image shares, operating-system changes, clone
wizards, purchases and snapshots are all produced by the customer in the
console. Those capabilities are therefore NOT granted and NOT callable by
this skill.

## Required actions

| # | RAM Action | API Version | Purpose |
|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | 2015-04-01 | Verify the caller identity and derive the account UID traceability label (`scripts/axes/instance_clone_guide/sts_token.py`, `scripts/axes/instance_clone_guide/clone_readiness_check.py`) |
| 2 | `ecs:DescribeInstances` | 2014-05-26 | Instance existence, status, zone, type, image ID, IPs and bound security groups for one account in one region (`scripts/axes/instance_clone_guide/clone_readiness_check.py`) |
| 3 | `ecs:DescribeInstanceStatus` | 2014-05-26 | Runtime status confirmation for the clone target instances, `InstanceId.N` batch form (`scripts/axes/instance_clone_guide/clone_readiness_check.py`) |

The permission-point names above (rows 2 and 3) are quoted VERBATIM from the
verified API contracts for this tier. RAM permission-point names are NOT
always the interface name prefixed with the product; never derive them from
an API name by pattern.

## Pending permission point (API intentionally not used)

`DescribeAvailableResource` (ecs, 2014-05-26) is a read-only query that
passed contract verification for this tier, but the contract did NOT supply
its permission-point name. Because deriving a permission name from an API
name is not permitted, this skill does not call or declare that query until the
permission point is confirmed through the contract process. Target-zone
inventory checks stay customer self-service in the console purchase page.

## Full policy document

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

- Read-only guarantee: the granted action set contains only Describe/Get
  query verbs, so the credential physically cannot change any cloud
  resource; this matches the skill's declared boundary in SKILL.md.
- `Resource: "*"` is the minimum possible scope for these account-level
  reads; region narrowing happens through the `RegionId` request parameter,
  not the policy.
- No Deny statements are required; anything not listed above is denied by
  default.
- When a query comes back with `NoPermission` or `ImplicitDeny`, this skill
  stops and reports which action is missing plus the smallest policy
  fragment above. It never attempts an alternative path.

## Data boundary of these permissions

| Aspect | Scope |
|---|---|
| Account | ONLY the account behind the configured credential; another account's resources (a routine case in cross-account clone tickets) are invisible and become customer self-check items |
| Region | ONLY the `--region-id` passed per run; other regions require an explicit second run |
| Objects | Instance-side facts only; image/snapshot task progress and disk association inside an image are NOT exposed by these actions and are read by the customer from the console |

## How to grant

Option A -- RAM user (recommended for daily operation):

1. RAM console: select an existing RAM user, or add a new one.
2. Add a custom policy from the JSON above (policy editor, script mode).
3. Grant that policy to the RAM user.
4. Configure the aliyun CLI with that RAM user's credential through the
   default credential chain (`aliyun configure`). The scripts never take
   credential arguments.

Option B -- RAM role (cross-account or temporary access):

1. Add a RAM role trusted by the calling account and grant the policy above
   to that role.
2. Assume the role, store the temporary session in a named CLI profile, and
   pass it to the scripts with `--profile <name>`.

Least-privilege checklist:

- Grant only the three actions above; add no administrative policy.
- Prefer a RAM role with a short session duration over long-lived access
  keys.
- For the OTHER account in a cross-account clone, repeat the same minimal
  policy there and switch CLI profiles; never use another account's
  credential inside a run of this skill.
- The scripts resolve credentials exclusively through the aliyun CLI default
  credential chain; they never read, print or forward keys.

## Axis: instance-relocation-guide
# Requested permissions

This skill is read-only. It asks for four specific actions and nothing else.
There is no wildcard in the action list, and no state-changing action is
requested.

| Action | Read or write | Used by | Why the skill needs it |
| --- | --- | --- | --- |
| `ecs:DescribeInstances` | read | `scripts/axes/instance_relocation_guide/relocation_preflight.py` | Region, zone, instance type, charge mode, expiry, image id, addresses and security groups of the instance being relocated |
| `ecs:DescribeInstanceStatus` | read | `scripts/axes/instance_relocation_guide/relocation_preflight.py` | Lightweight state confirmation before a change window is scheduled |
| `ecs:DescribeAvailableResource` | read | `scripts/axes/instance_relocation_guide/relocation_preflight.py` | Capacity of the destination region or zone for the planned instance type |
| `sts:GetCallerIdentity` | read | `scripts/axes/instance_relocation_guide/sts_token.py` | Confirms a usable credential and attributes the report to an account |

## Minimal policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeAvailableResource"
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

`Resource` is open on purpose: the three ECS reads above are account- and
region-scoped list queries, so an instance-level scope would hide results rather
than narrow risk. The action list stays explicit.

## Request attribution

Every call made under these permissions carries the skill User-Agent described
in [../SKILL.md](../SKILL.md), which includes the session id generated for that
execution, so a request can be traced back to one report. Authentication stays in
the default credential chain; no key, secret or token value is read, written or
displayed by this skill.

## Boundary of the permission model

The steps this skill recommends are carried out by the customer in the console,
under the customer's own permissions, after reading the risk notice. That is a
deliberate boundary, not a limitation of the policy above: this skill neither
requests nor performs any state-changing operation, and it does not execute
commands inside the guest operating system.

## When a call is denied

A denial is reported, not worked around.

| Returned code | What it means | What the skill prints |
| --- | --- | --- |
| `NoPermission` | The policy held by the identity does not allow that action | The missing action plus the corresponding `Action` line from the policy above |
| `ImplicitDeny` | No statement allows the action, so it is denied by default | A request to add a read-only policy covering that action |

Either case ends the affected section with `STATUS: DEGRADED` and keeps the
remaining checks going. Never ask the customer for an access key, a secret or
a token; authentication stays in the default credential chain of the CLI.
