# Diagnosis Rules

This document contains self-contained diagnosis rules for VPC firewall provisioning, route policy, and closure pre-check scenarios.

## Evidence Priority

1. Current state from read-only OpenAPI queries.
2. `ErrorDetail` from task or firewall APIs.
3. Recent ActionTrail events, error codes, and timeline.
4. Precheck result as supporting evidence only.

## Static Route Rule

Trigger patterns:

- `ErrorCandidateHasStaticRoute`
- Precheck or task output indicates static routes in the candidate route table.

Diagnosis:

1. Query route tables with `list-transit-router-route-tables`.
2. Query route entries with `list-transit-router-route-entries`.
3. Filter static routes.
4. Exclude reserved platform routes such as `100.64.0.0/10`.
5. Report the non-exempt static route entries as the likely blocker.

Remediation style: provide text-only console guidance to convert, remove, or recreate routes after user review.

## Rejected Route Conflict Rule

Trigger patterns:

- `ErrorTrRouteTableContainsRejectRoutes`
- Route table contains rejected route entries.

Diagnosis:

1. Query the system route table only.
2. Specify `--TransitRouterRouteEntryStatus Rejected`.
3. Compare each rejected route with active routes for the same CIDR.
4. Identify the resources publishing overlapping routes.

## ECMP Rule

Trigger patterns:

- `ErrorTrFirewallEcmpRoute`
- Same destination CIDR has multiple active next hops.

Diagnosis:

1. Group route entries by destination CIDR.
2. Identify CIDRs with multiple next-hop resources.
3. Compare the actual next-hop list with the route policy candidate list.
4. Report missing or mismatched next-hop resources.

## Route Map Consistency Rule

Trigger patterns:

- `ErrorTrFirewallRouteMapConflict`
- ActionTrail shows route creation followed by immediate deletion without a CEN API error.
- Custom route maps exist on some route tables but not on the CFW route table.

Diagnosis:

1. Query CEN route maps with `describe-cen-route-maps`.
2. Exclude system-built route maps.
3. Compare custom route map distribution across route tables.
4. Report missing custom route maps as a consistency risk.

## Closure Pre-check Route Rule

Auto-drainage mode:

- Filter CFW auto-created split routes only when both conditions are true:
  - `OperationalMode` is true.
  - `TransitRouterRouteEntryDescription` contains `cloud_firewall` case-insensitively.
- Compare remaining CFW business routes with the rollback target route table.

Manual-drainage mode:

- Compare all route entries without auto-route filtering.

Route revoke mode:

- Route loss through rollback is not the primary risk.
- Review residual route tables after closure.

## ACL Risk Rule

- No ACL policy: medium risk for later firewall re-enable because traffic may be denied by default.
- Deny policies exist: medium risk; session or state changes may require validation.
- Allow policies exist and route risk is low: ACL risk may be low, but still require manual review.

## ActionTrail Time Window Rule

- Default query range is the last 24 hours.
- Use a wider range only when explicitly requested by the user.
- Use `lookup-events` with `--LookupAttribute.1.Key` dot notation.

## Forbidden APIs and Operations

- Do not use the invalid `DescribeFirewallV2List` API.
- Do not execute create, modify, delete, attach, detach, enable, disable, add, remove, or similar write operations.
- Do not provide executable write commands as remediation.
