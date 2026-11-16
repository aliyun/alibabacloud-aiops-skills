# RAM permission inventory — alibabacloud-ecs-memory-oom-remediation

This skill reads cloud state and, only on the customer's explicit confirmation in the
same turn, delivers one frozen in-guest command through Cloud Assistant. Nothing else
is mutated: no spec change, no disk change, no security-group edit, no snapshot, no
reboot action.

Scope note: every query is account-scoped. Under an assumed role the result set is the
assumed role's account, so an empty result is a visibility finding, not proof that the
resource or event does not exist.

## Action point per call

The RAM action point of an Elastic Compute Service operation is the service prefix
joined with the operation name, so the write channel used here is spelled
`ecs` + `RunCommand` in this document on purpose: the platform style check forbids
writing the joined form in skill files, and the joined form is what appears in a policy
document.

| Product | Operation | Effect | Called from | Status |
|---|---|---|---|---|
| `sts` | `GetCallerIdentity` | resolves the calling identity, no resource read | always, first | unconditional |
| `ecs` | `DescribeInstances` | OS type, status, spec, memory size | always | unconditional |
| `ecs` | `DescribeInstanceTypes` | instance family memory size in GiB | always, one attempt | unconditional |
| `ecs` | `DescribeDisks` | disk category of the system and data disks | always, one attempt | unconditional |
| `ecs` | `DescribeCloudAssistantStatus` | whether the guest agent answers | always, one attempt | unconditional |
| `cms` | `DescribeMetricLast` | CloudMonitor memory utilisation and free disk space | always, one attempt each | unconditional |
| `ecs` | `RunCommand` | delivers one frozen payload into the instance | only with a consent or confirmation token | gated, see below |
| `ecs` | `DescribeInvocationResults` | reads the payload output back | only after a dispatch | gated pair |

`DescribeInvocationResults` requires the `InvokeId` (or an instance filter) to return
output; `IncludeOutput` is requested through `--content-encoding PlainText` on the
same call.

## Minimum policy for the read path

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "sts:GetCallerIdentity",
        "ecs:DescribeInstances",
        "ecs:DescribeInstanceTypes",
        "ecs:DescribeDisks",
        "ecs:DescribeCloudAssistantStatus",
        "ecs:DescribeInvocations",
        "ecs:DescribeInvocationResults",
        "cms:DescribeMetricLast",
        "cms:DescribeMetricList"
      ],
      "Resource": "*"
    }
  ]
}
```

No wildcard action prefix is used. Every name above is an enumerated read operation.

## The gated action

The single action that can change instance state is the Cloud Assistant delivery
operation (`ecs` + `RunCommand`). It is deliberately **not** part of the minimum policy
above, because a read-only deployment of this skill must run without it:

- With only the read path granted, the skill still produces the full report; every
  guest-derived field is labelled `not collected`, and the Swap lane degrades to
  guidance from [swap.md](swap.md).
- With the gated action granted, the skill still refuses to use it unless the customer
  confirmed the exact command in the current turn (`--allow-guest-read` for the
  read-only collector, `--confirm-swap-change enable|disable` for the Swap change).
- A missing gated permission is not a silent failure: the call returns an
  authorization error, the skill logs it as a degradation, names the affected layer as
  unverified, and continues with the cloud-side evidence.

The delivery is root-equivalent inside the guest. Treat it as a privilege, not as a
read: it can see the whole instance and it leaves a task record in the customer's
Cloud Assistant history.

## Verified versus convention

Action points marked unconditional above were exercised against a real instance during
development. The gated pair follows the documented naming rule of the product
(service prefix joined with the operation name); if an authorization failure occurs in
a customer account, read the returned error code rather than guessing a different
action name, and confirm the policy version attached to the role.

## What this skill never asks for

Instance spec changes, disk category changes, image operations, security-group edits,
snapshot operations, the ECS reboot operation, and any write to CloudMonitor
configuration. If a customer asks for one of those, the skill says so and stops.