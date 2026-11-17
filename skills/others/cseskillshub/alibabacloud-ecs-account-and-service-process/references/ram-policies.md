# RAM permissions for alibabacloud-ecs-account-and-service-process (union of 5 axes, per-axis sections
# are verbatim copies of member specs that each passed the static gate)
swas-boundary-guide
# Minimal Read-Only RAM Policy

This skill (`alibabacloud-ecs-swas-boundary-guide`) performs strictly
read-only product-attribution and boundary-guidance work for Simple
Application Server (SWAS) and ECS questions. It requires exactly four
read actions: the STS identity check plus three ECS Describe-class queries.
No wildcards of any form are used in any action name, and no mutating
action is granted or declared anywhere in this skill.

## Required actions

| # | RAM Action | API Version | Endpoint | Purpose (script) |
|---|---|---|---|---|
| 1 | `sts:GetCallerIdentity` | 2015-04-01 | `sts.aliyuncs.com` | Verify the caller identity and derive the account UID traceability label (`scripts/axes/swas_boundary_guide/sts_token.py`, and the identity step inside `scripts/axes/swas_boundary_guide/swas_boundary_guide.py --identify`) |
| 2 | `ecs:DescribeInstances` | 2014-05-26 | `ecs.<region>.aliyuncs.com` | Attribute an instance id / IP to ECS and read its region, zone, instance type and family, CPU/memory, image OS name and OS type, charge type, expiry and security groups (`scripts/axes/swas_boundary_guide/swas_boundary_guide.py --identify`) |
| 3 | `ecs:DescribeInstanceStatus` | 2014-05-26 | `ecs.<region>.aliyuncs.com` | Read-only running-status cross-check for the identified instance (`scripts/axes/swas_boundary_guide/swas_boundary_guide.py --identify`) |
| 4 | `ecs:DescribeAvailableResource` | 2014-05-26 | `ecs.<region>.aliyuncs.com` | Check whether a target region / instance type is purchasable before advising a migration target (`scripts/axes/swas_boundary_guide/swas_boundary_guide.py --migration-check` with `--target-region`) |

All four actions are Describe/Get-class read APIs. They never change any
resource, order, image, disk or configuration.

Note on action 4: the authorization point of
`ecs:DescribeAvailableResource` was not independently verified in this
evidence batch; it is listed here only because ECS Describe-class actions
follow the standard `ecs:<ApiName>` convention, so nothing is invented. If
authorization still fails with `NoPermission` / `ImplicitDeny` while this
policy is attached, look up the current authorization information for that
action in the official ECS API documentation instead of widening the policy.

## Explicitly NOT granted (and never called by this skill)

- Any mutating ECS action of any verb family (instance lifecycle, disk and
  image operations, network and security-group changes, command execution).
  The shared CLI layer additionally refuses any action outside the read
  whitelist at the code layer, so a policy mistake cannot turn this skill
  into a mutating one.
- Any Simple Application Server (swas-open family) action: no SWAS-side
  read action was verified for this skill, so none is declared and none is
  called. SWAS attribution degrades to id-form recognition plus console
  self-service guidance.
- Any billing/BSS action: expiry and renewal figures are read by the
  customer in the Billing Management console; this skill does not query
  billing APIs.

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
      "Sid": "ReadOnlyEcsAttributionQueries",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeAvailableResource"
      ],
      "Resource": "*"
    }
  ]
}
```

Notes:

- Every action is listed explicitly; wildcard action entries (any asterisk
  form, at the product or global level) are disallowed for this skill.
- `Resource: "*"` is the minimum possible scope here: these Describe-class
  queries are account/region-level list APIs that do not support
  resource-level authorization for this use case. The read-only effect is
  guaranteed by the action list itself.
- No `Deny` statements are required; anything not listed above is denied by
  default.
- The CLI plugin command for the identity check is lowercase-hyphenated
  (`aliyun sts get-caller-identity`); the ECS RPC actions keep their
  PascalCase names (`aliyun ecs describe-instances ...`). Both forms are the
  correct command style for their product.

## Resource scope

| Aspect | Scope |
|---|---|
| Region | The region the customer names (default `cn-hangzhou`, auto-filled and declared in every report); queries never span regions silently |
| Resources | Only the instance id / IP the customer supplied, plus the availability lookup of the target region they named |
| Data exposed | Instance metadata (id, name, status, region/zone, type and family, CPU/memory, OS name/type, charge type, expiry, public/private IP, security-group ids) and purchasability information -- read data only |
| Mutations | None possible; only Describe/Get-class actions are granted, and the code layer refuses everything else |

## How to grant

Option A -- RAM user (same-account use, recommended for daily operation):

1. RAM console -> Identities -> Users: pick the RAM user to use.
2. Add a custom policy from the JSON above (Permissions -> Policies ->
   policy editor -> Script mode).
3. Attach the policy to the RAM user.
4. Configure the aliyun CLI with that RAM user's credential
   (`aliyun configure`). The scripts resolve credentials exclusively
   through the aliyun CLI default credential chain; they never take AK/SK
   arguments.

Option B -- RAM role (cross-account or temporary access):

1. RAM console -> Identities -> Roles: pick a RAM role trusted by the
   calling account.
2. Attach the policy above to the role.
3. Assume the role and configure the temporary credential as a named CLI
   profile; pass it to the scripts with `--profile <name>`.

Least-privilege checklist:

- Grant only the four actions above. Do not attach a broad ECS-wide or
  account-wide managed policy: this skill needs read access to four Describe
  or Get actions and nothing else.
- Prefer a RAM role with a short session duration over long-lived RAM-user
  AccessKeys.
- Never share credentials; never pass AK/SK to the scripts or store them in
  the skill directory.
- When a query is denied, report the missing action and this file's policy
  snippet verbatim (`NoPermission` / `ImplicitDeny` wording); never retry
  around a denial.

account-transfer-guide
# RAM policy — what this skill needs and why

This skill is a transfer-guidance skill with one confirmation-gated backup
capability. Its calls fall into exactly two layers:

* **Layer A — query-class evidence calls** (`Describe*` / `Get*`): run
  automatically because none of them changes any resource.
* **Layer B — one snapshot-backup action** (`CreateSnapshot`): a write-class
  action, invoked ONLY after the agent tells the user what runs, its impact
  and its reversibility, and the user approves the exact call. The entry
  script enforces this with a per-call `--confirm yes` token.

Everything else — instance release, transfer initiation (which has no OpenAPI
in the verified evidence for this tier), refunds, account cancellation,
snapshot deletion, guest command execution — is out of the whitelist and is
never automated here; the skill only prints manual console steps.

## Layer A — granted actions (query-class)

| RAM action | Purpose in this skill | Where it is called |
| --- | --- | --- |
| `sts:GetCallerIdentity` | Prove the CLI credential chain works; derive the 16-digit account UID that image sharing keys on | `scripts/axes/account_transfer_guide/sts_token.py`, `scripts/axes/account_transfer_guide/transfer_guide.py` (`--precheck`) |
| `ecs:DescribeInstances` | Locate the instance ID for the transfer form; read zone / VPC / vSwitch / security groups / bound EIP / key pair for the five-condition checklist | `scripts/axes/account_transfer_guide/transfer_guide.py` (`--precheck`) |
| `ecs:DescribeInstanceStatus` | Verify the instance running state before and after migration steps | `scripts/axes/account_transfer_guide/transfer_guide.py` (`--precheck`) |
| `ecs:DescribeAvailableResource` | Destination-zone sellability pre-check (the cloud-side counterpart of the "vSwitch cannot be selected" blocker) | `scripts/axes/account_transfer_guide/transfer_guide.py` (`--precheck --target-zone`) |

## Layer B — confirmation-gated backup action (deliberately NOT in the grant below)

| Action name | Product | Key parameter | Gate |
| --- | --- | --- | --- |
| `CreateSnapshot` (write class; grant it by combining the `ecs:` action prefix with this exact name when your organization requires an explicit grant) | ECS | `DiskId` + `RegionId` (both required) | the agent MUST first state what runs / its impact (a snapshot appears and accrues snapshot storage fees until a human deletes it) / its reversibility (a copy; the disk is untouched), obtain the user's approval, and only then re-run with `--confirm yes`. Approval is per call only. |

The minimum policy below is intentionally scoped to Layer A. This skill runs
under the customer's own CLI profile: the snapshot backup either rides on
permissions the customer already holds (support guidance does not require a
new grant for their own disks) or fails closed with an explicit permission
error that the report surfaces — the skill never asks for broader standing
write privileges.

## Minimum policy (Layer A only)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "TransferEvidenceQueries",
      "Effect": "Allow",
      "Action": [
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceStatus",
        "ecs:DescribeAvailableResource"
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

* Every action above is listed explicitly; asterisk-based action wildcards
  (product level or global) are disallowed for this skill — a wildcard grant
  would also cover mutating actions this skill is designed never to call.
* `Resource: "*"` is the minimum feasible scope for these account-visible
  list queries; a tighter policy may pin `acs:ecs:<region-id>:<account-id>:instance/<instance-id>`
  for the ECS rows. The identity action is global.

## Reserved — documented, NOT granted, NOT called in v1

* CloudMonitor metric reads: the API name is `DescribeMetricLast` but the RAM
  permission point is `cms:QueryMetricLast` — **RAM name differs from the API
  name; never derive one from the other**. v1 has no monitoring-reading use
  case in the transfer flow, so this stays at the documentation level only.
* Cloud Assistant command execution actions (`RunCommand` / `InvokeCommand`):
  feasibility evidence lives entirely on the account/instance side; no
  referenced ticket needed in-guest readings, so v1 never dispatches them.
  If a future release ever enables this, the batch low-risk list applies:
  one whitelisted display-only command per call, tell-then-confirm per call,
  anything off the whitelist refused without exception.

## When a call is denied

The scripts report denial with the literals `NoPermission` or `ImplicitDeny`
plus the exact action that was missing, and continue with the remaining
queries (a `[WARN]` line on stderr, an entry in the JSON `errors`/`warnings`
list). Recovery: have the account administrator attach the Layer-A statement
above for the missing action only, then re-run the identical command.

## Credential rules baked into the code

* Credentials resolve exclusively through the aliyun CLI default credential
  chain (profile config or platform-injected environment). The scripts never
  take, read, print, cache or forward AccessKey / Secret / token values;
  every CLI error string passes through a credential-masking filter before
  it can surface anywhere.
* The report contains resource identifiers, zones, statuses and UIDs only,
  so it can be pasted into a support ticket without leaking credential
  material.

business-contact-routing
# RAM policy for this skill

Every action below is read-only and is actually invoked by `scripts/axes/business_contact_routing/routing.py` or
`scripts/axes/business_contact_routing/sts_token.py`. Each entry is a fully qualified, enumerated action name; the
policy contains no abbreviated or group-level action entry.

| Action | Product | Read | Why the skill needs it |
|---|---|---|---|
| `ecs:DescribeInstances` | ecs | yes | Identify which instances the customer ask concerns |
| `ecs:DescribeInstanceStatus` | ecs | yes | Record a power-state snapshot in the hand-off material pack |
| `ecs:DescribeAvailableResource` | ecs | yes | Check sellability when the ask involves purchase or scale |
| `sts:GetCallerIdentity` | sts | yes | Attribute the material pack to the correct account |

The same four actions are declared in `related_apis.yaml`, and the transport layer in
`scripts/axes/business_contact_routing/_cli.py` refuses any action outside that allowlist, so an over-permissive
credential cannot widen what this skill does.

## Smallest usable policy

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
        "sts:GetCallerIdentity"
      ],
      "Resource": "*"
    }
  ]
}
```

`Resource` is unrestricted because a regional list call cannot be narrowed to one instance
ARN, and the skill is filtered by `RegionId` and instance id at call time. Narrow the
statement to a RAM user or role group that owns only the accounts being routed.

## Missing-permission handling

When a call answers `NoPermission` or `ImplicitDeny`:

1. Report which single action was denied, with the request id if the service returned one.
2. State that the material pack is incomplete and print `STATUS: DEGRADED`, naming the
   missing item. Guidance output is never withheld for a permission failure.
3. Show the relevant `Action` line from the table above so the operator can raise a
   least-privilege grant request.
4. Do not retry with broader credentials, a different account, or some other action that is
   not on the allowlist.

The account id is never echoed back in full: `scripts/axes/business_contact_routing/sts_token.py` reduces it to
`acct-tail-<last4>`.

invalid-ticket-triage
# Read actions used by this skill

Only the actions below are declared, and they are exactly the ones `scripts/` can
issue. Anything outside this list is refused in `scripts/axes/invalid_ticket_triage/_cli.py` before a process is
spawned. All three read state; none of them changes state.

| Action | Purpose in this skill | Where |
|---|---|---|
| `ecs:DescribeInstances` | Existence and ownership check of an instance id quoted in a ticket | `scripts/axes/invalid_ticket_triage/triage_invalid_ticket.py` |
| `ecs:DescribeInstanceStatus` | Optional corroboration of the state of ids already returned | `scripts/axes/invalid_ticket_triage/triage_invalid_ticket.py` |
| `sts:GetCallerIdentity` | Label the report with the account the read-only credentials belong to | `scripts/axes/invalid_ticket_triage/sts_token.py` |

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

Notes:

- The `Action` elements list concrete action names. No action wildcard such as an
  `ecs` prefix followed by `*` appears anywhere in this package, and every declared
  action only reads state.
- `Resource` is `*` because these are list-style read calls whose scope is set by the
  `RegionId` parameter rather than by a resource arn. To narrow it further, replace
  `*` with `acs:ecs:<region-id>:<account-id>:instance/*` and keep the `RegionId`
  values aligned; `sts:GetCallerIdentity` cannot be resource-scoped.

## Failure wording when a permission is missing

Report the exact action name and paste the matching statement from the policy above.
The literal codes to quote are `NoPermission`, `ImplicitDeny`, `AccessDenied` and
`InvalidAccessKeyId`. Never ask the customer or the operator for an AccessKey pair or
a session token: credentials come from the Alibaba Cloud CLI default credential chain
(`aliyun configure`), and every error string is masked before it is printed.

instance-tag-metadata-guide
# RAM permission points for this skill

Every action below is one the scripts in `scripts/` actually call, and nothing
listed here is unused. There is no wildcard grant: no entry stands for every
action of a product, and no entry names an action this skill does not issue.
This skill is read-only; it requests no permission whose name begins with a
change verb, and it has no code path that could use one.

## 1. Actions actually called

| Product | CLI invocation | API action | RAM action point | Why it is needed |
|---|---|---|---|---|
| ecs | `aliyun ecs describe-instances` | `DescribeInstances` | `ecs:DescribeInstances` | Authoritative ownership facts: resource group id, tag array, region, zone, status, VPC / vSwitch, attached security groups and the instance metadata-option values |
| ecs | `aliyun ecs describe-instance-status` | `DescribeInstanceStatus` | `ecs:DescribeInstanceStatus` | Independent lightweight status reading used by `--status-check` to cross-check the listing |
| sts | `aliyun sts get-caller-identity` | `GetCallerIdentity` | `sts:GetCallerIdentity` | Credential pre-flight and the account-scope label printed on every report |

ECS actions belong to API version `2014-05-26`; STS belongs to `2015-04-01`
(central endpoint `sts.aliyuncs.com`, plugin-mode lowercase-hyphenated command).

### Parameters the scripts send

| Action | Parameters |
|---|---|
| `DescribeInstances` | `RegionId`, `InstanceIds` (JSON array, batched at 100), `ResourceGroupId`, `Tag.1.Key`, `Tag.1.Value`, `InstanceName`, `MaxResults`, `NextToken` |
| `DescribeInstanceStatus` | `RegionId`, `InstanceId.1..N`, `PageNumber`, `PageSize` |
| `GetCallerIdentity` | none |

## 2. Minimal custom policy

Copy this to the RAM console for the sub-account or the role the agent runs as.
It contains exactly the three action points above -- nothing else is required
for any mode of this skill.

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

System-policy alternative: `AliyunECSReadOnlyAccess` plus `AliyunSTSAssumeRoleAccess`
is sufficient for the read path. `AliyunECSFullAccess` is NOT needed and using
it defeats the least-privilege point of this file.

## 3. Scope of a grant: account level versus resource-group level

This is the single most misunderstood point in the tickets behind this skill,
so it is stated here explicitly:

- A grant attached at **resource-group** scope covers calls that are issued
  against that group. A grant attached at **account** scope covers calls that
  are not group-scoped. Neither substitutes for the other.
- Some console pages issue calls that carry no resource group at all. A
  group-scoped grant therefore cannot satisfy them and the page shows a
  permission error even though the intended operation is allowed. See
  [resourcegroup-authorization.md](resourcegroup-authorization.md).
- If the customer's own question is about authoring or narrowing a policy
  document, that belongs to `alibabacloud-ecs-ram-policy-diagnosis`; this
  skill only states which read actions it needs for itself.

## 4. Who can attach a grant

Only the account owner (or an identity that already holds RAM administration
rights) can attach a policy or grant it to a resource group. A sub-account that
is currently denied cannot fix itself: forward this file to the administrator,
attach the policy, then re-run the same command. Console path: **Resource
Management console -> Resource Groups -> target group -> Permissions**, or
**RAM console -> Identities -> user or role -> Permissions**; the documented
walk-through is
[grant a RAM identity permissions at resource-group scope](https://help.aliyun.com/zh/resource-management/resource-group/user-guide/add-ram-authorization).

## 5. What a denial means for this skill

| Reported code | Interpretation | Action |
|---|---|---|
| `NoPermission` on an ECS read | the action point above is not attached to the calling identity at the scope the call used | report the code, keep the remaining reads going, ask for the grant in section 2 |
| `NoPermissionType: ImplicitDeny` with `PolicyType: ResourceGroupLevelIdentityBasedPolicy` | the target resource group carries no allow for that action; an account-level Allow on the identity does not cover it | relay the rule from [resourcegroup-authorization.md](resourcegroup-authorization.md); the grant is the customer's own step |
| A named permission point for a console listing call | that call is issued without a group; the error does not prove the operation is blocked | relay both documented options; never call a tag-specific action to "work around" it |
| `InvalidAccessKeyId`, `SignatureDoesNotMatch`, `SDK.InvalidCredential`, chain failures | the credential profile is unusable | tell the customer to re-run `aliyun configure`; never accept a key or secret in chat |

The script records a failing read as `[WARN] <Code>: <Message>` on stderr, adds
it to the report's degradation log, and continues; a permission gap is never
silently turned into a "no resources" conclusion.

