# RAM permissions for alibabacloud-ecs-compliance-and-filing-docs: union of two axes, and each per-axis section below is a verbatim copy of a member specification that already passed the static gate.
idc-address-query
# RAM policies - alibabacloud-ecs-idc-address-query

This skill is **read-only**. It performs only `Describe*` reads on ECS plus a
single STS identity read used to label the owning account for the
cross-account disclosure wording. It performs no state-changing operation of
any kind and never runs a command inside an instance.

## Actions actually called by `scripts/`

| Product | Action | Read/Write | Used by |
|---|---|---|---|
| ecs | `DescribeInstances` | read | `scripts/axes/idc_address_query/idc_address_query.py` (locate by instance id / public IP; returns Region, Zone, Status, IP attributes) |
| ecs | `DescribeInstanceStatus` | read | `scripts/axes/idc_address_query/idc_address_query.py` (confirm lifecycle status of found instances) |
| ecs | `DescribeAvailableResource` | read | `scripts/axes/idc_address_query/idc_address_query.py` (optional zone-availability mode) |
| sts | `GetCallerIdentity` | read | `scripts/axes/idc_address_query/sts_token.py` (resolve the active account id) |

These match `related_apis.yaml` exactly (product `ecs` version `2014-05-26`,
product `sts` version `2015-04-01`).

## Minimal policy

Grant only the actions listed above; do not widen them with any wildcard.

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

## Credential handling

Credentials are resolved exclusively by the aliyun CLI **default credential
chain**. This skill never reads, prints, stores, or asks for an access key id
or secret. Configure credentials out of band with `aliyun configure`.

## Authentication failure output

When a read is not permitted, report the customer-facing literals
`NoPermission` or `ImplicitDeny`, name the exact missing action from the table
above, and point to this minimal policy as the fix. Do not surface any other
authorization label to the customer.

compliance-cert-guide
# Minimal Read-Only RAM Policy

This skill performs strictly read-only ECS queries for compliance-evidence
preparation. It requires exactly two RAM actions; no wildcard action entries
(any product prefix followed by an asterisk) are permitted anywhere in this
skill's policy, and no mutating permission is declared or used.

## Required actions

| # | RAM Action | API (product / version) | Purpose / caller |
|---|---|---|---|
| 1 | `ecs:DescribeInstances` | `ecs` / `2014-05-26` | Instance inventory and the security groups bound to each instance (`scripts/axes/compliance_cert_guide/compliance_inventory.py`, NextToken pagination) |
| 2 | `ecs:DescribeInstanceStatus` | `ecs` / `2014-05-26` | Running-state cross-check for the self-audit table (`scripts/axes/compliance_cert_guide/compliance_inventory.py`, page-number pagination) |

Both actions are Describe-class read queries. The granted set contains no
mutating verb and no command-execution action, so the credential physically
cannot change any resource, run anything inside an instance, or emit new
billable usage.

## Minimal custom policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Sid": "EcsComplianceSelfAuditReadOnly",
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

- Every action is listed explicitly; wildcard entries are prohibited for this
  skill (platform rule 2.2.7).
- `Resource: "*"` is required because these two ECS read APIs are
  account-and-region scoped list queries; they are narrowed by the `RegionId`
  request parameter the script passes, not by resource ARNs.
- `ecs:DescribeAvailableResource` is intentionally NOT granted and NOT used:
  its relevance to the compliance-evidence axis is weak and its RAM
  permission point was never verified for this tier.
- No `Deny` statements are needed; anything not listed above is already
  denied.

## System-policy alternative

`AliyunECSReadOnlyAccess` also covers the two actions above but grants a much
broader read surface than this skill needs. Prefer the custom policy for
least privilege; the system policy is an acceptable shortcut only when
custom-policy creation is not possible.

## Who can grant

Authorization must be performed by the account owner (primary account) or by
a RAM identity that already holds RAM administration rights. A RAM user that
has no permissions yet cannot grant itself: forward this file to the account
administrator, then retry.

## Grant steps (RAM console)

1. Sign in to the RAM console (`ram.console.aliyun.com`).
2. Go to **Identities > Users** (or **Roles** for an assumed-role setup) and
   select the identity that will run the skill.
3. Choose **Grant permissions** and create a **Custom policy** from the JSON
   above (Script mode), then attach it.
4. Verify the policy appears under the identity's **Permissions** tab and
   retry the skill.

## Permission-error verification table

When a call fails, the script prints `[WARN] <Code>: <Message>` and keeps the
literal API code. Map it as follows:

| Error code literal | Meaning | Fix |
|---|---|---|
| `NoPermission` | The RAM identity lacks one of the two listed actions | Grant the minimal policy above and retry |
| `ImplicitDeny` | No matching Allow statement exists (everything else is denied by default) | Same: attach the policy covering the named action |
| `InvalidAccessKeyId` / `SignatureDoesNotMatch` / credential-chain failure | The local CLI profile is misconfigured | The user runs `aliyun configure` themselves; the skill never collects keys |

The failing action name is echoed in the script output, so the exact missing
grant can be identified from the report itself.

## Least-privilege checklist

- Grant only the two actions above; never attach administrator policies.
- Prefer a short-lived RAM role session over long-lived user keys.
- Never share credentials; never place keys in the skill directory (the
  scripts resolve credentials only through the aliyun CLI default chain).

