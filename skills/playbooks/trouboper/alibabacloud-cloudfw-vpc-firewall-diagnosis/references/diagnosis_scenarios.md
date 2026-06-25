# Diagnosis Scenarios

This document summarizes supported VPC firewall diagnostic scenarios.

## Core Diagnostic Strategy

- ActionTrail is used for operation history: caller, time, API name, request parameters, and error code.
- Read-only OpenAPI calls are used for current state: firewall status, task status, precheck result, and route table data.
- ActionTrail does not store historical API responses.
- Precheck results can be incomplete or stale; do not use them as the only evidence.

## Scenario 1: VPC Firewall Creation Failed

Symptoms:

- VPC firewall creation fails.
- Firewall status remains incomplete or unknown.
- Precheck may pass but the final provisioning still fails.

Mandatory first API:

```bash
aliyun cloudfw describe-tr-firewalls-v2-list \
  --RegionId <region> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

Follow-up evidence:

- Recent ActionTrail events.
- Precheck detail if needed.
- Route table state when route-related error codes appear.

## Scenario 2: Route Policy Configuration Failed

Symptoms:

- VPC firewall is created but route policy configuration fails.
- Drainage task reports failure or remains stuck.

Mandatory first API:

```bash
aliyun cloudfw describe-firewall-task \
  --TaskType VPC \
  --ChildInstanceId <vpc-id> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

Follow-up evidence:

- ActionTrail route policy operations.
- CBN route entries and route tables.
- Route policy candidate scope.

## Scenario 3: Closure Pre-check in Auto-drainage Mode

Symptoms:

- User wants to close firewall drainage and needs impact assessment.
- The firewall uses an automatically managed route rollback target.

Required flow:

1. Query firewall and route policy metadata.
2. Query rollback target route table mapping.
3. Query route entries from CFW and rollback route tables.
4. Run `scripts/analyze_routes.py auto_rollback`.
5. Query ACL policies.
6. Report route and ACL risk.

## Scenario 4: Closure Pre-check in Manual-drainage Mode

Symptoms:

- User manually controls the route table used after closure.
- Current and target route table IDs must be compared.

Required flow:

1. Confirm current and target route table IDs.
2. Query both route tables.
3. Run `scripts/analyze_routes.py manual_rollback`.
4. Query ACL policies when firewall ID is available.
5. Report route and ACL risk.

## Scenario 5: Route Revoke Closure

Symptoms:

- The closure method removes routes instead of rolling them back.
- The main concern is residual empty route tables or billing impact.

Required flow:

1. Query related route tables.
2. Run `scripts/analyze_routes.py route_revoke`.
3. Provide console-only guidance for reviewing residual route tables.

## Common Root Cause Mapping

| Symptom or error | Likely root cause | Evidence |
|---|---|---|
| Static route blocker | Candidate route table contains non-exempt static routes | CBN route entries |
| Rejected route blocker | Overlapping routes are published by different resources | Rejected and active route entries |
| ECMP mismatch | Route policy scope misses one or more ECMP next hops | Grouped route entries by CIDR |
| Silent rollback | Route map or route table consistency check fails | ActionTrail rollback sequence and route map comparison |
| Closure route loss | Rollback or target route table lacks business routes | `analyze_routes.py` output |
| ACL re-enable risk | No ACL policies or risky deny policies exist | ACL policy query |

## Report Requirements

- Start with the read-only declaration.
- State the conclusion first.
- Provide compact evidence.
- Provide text-only manual remediation guidance.
- Do not output executable write commands.
