# VPC Firewall Lifecycle

This document summarizes the VPC firewall provisioning lifecycle and the diagnostic evidence used by this skill.

## Stage 1: Precheck

The console starts a VPC firewall precheck before provisioning.

Read-only diagnostic APIs:

```bash
aliyun cloudfw describe-vpc-firewall-precheck-detail \
  --VpcId <vpc-id> \
  --Region <region> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

Key checks include edition support, regional support, quota, transit router state, and route table constraints.

Important diagnostic note: a successful precheck does not guarantee final provisioning success. Always continue to current status and ActionTrail evidence.

## Stage 2: Firewall Asset Provisioning

After precheck, Cloud Firewall creates or updates internal firewall assets and related routing resources.

Read-only diagnostic APIs:

```bash
aliyun cloudfw describe-tr-firewalls-v2-list \
  --RegionId <region> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

Fields to review:

- `FirewallId`
- `PrecheckStatus`
- `FirewallSwitchStatus`
- `UnprotectedResource`
- `ProtectedResource`
- `ResultCode` or related failure fields when available

## Stage 3: Route Policy Configuration

Route policy configuration may fail after assets are created. The first diagnostic API for this scenario is `describe-firewall-task`.

```bash
aliyun cloudfw describe-firewall-task \
  --TaskType VPC \
  --ChildInstanceId <vpc-id> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

Use the task result, `ErrorDetail`, and ActionTrail evidence to identify the root cause.

## ActionTrail Correlation

Use ActionTrail to reconstruct recent operation history:

```bash
aliyun actiontrail lookup-events \
  --StartTime <start-time> \
  --EndTime <end-time> \
  --LookupAttribute.1.Key EventName \
  --LookupAttribute.1.Value CreateTrFirewallV2RoutePolicy \
  --MaxResults 10 \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

ActionTrail provides operation metadata, request parameters, caller identity, error code, and event time. It does not provide historical API responses.

## Common Failure Points

| Failure point | Evidence source | Typical next step |
|---|---|---|
| Region or edition not supported | Precheck detail and firewall list | Explain product limitation and console remediation path. |
| Static route exists in candidate route table | CBN route entries and ActionTrail error code | Identify route entry and provide manual remediation guidance. |
| ECMP next-hop mismatch | CBN route entries and route policy scope | Identify missing next hops. |
| Rejected route exists | CBN rejected route entries | Identify conflicting route publishers. |
| Route map consistency issue | CEN route maps and ActionTrail rollback sequence | Compare custom route maps across route tables. |
| Route policy task failure | `describe-firewall-task` | Use task failure reason as primary evidence. |

## Evidence Priority

1. Current state from read-only OpenAPI queries.
2. `ErrorDetail` from task or firewall status APIs.
3. Recent ActionTrail error code and operation timeline.
4. Precheck details as supporting evidence only.

## Read-only Boundary

This lifecycle document is for diagnosis only. Do not execute or provide write commands for provisioning, route changes, firewall switch changes, or ACL changes.
