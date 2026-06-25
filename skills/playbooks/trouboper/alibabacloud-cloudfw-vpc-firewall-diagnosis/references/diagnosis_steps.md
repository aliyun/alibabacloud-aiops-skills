# VPC Firewall Detailed Diagnosis Steps

## Scenario 1: VPC Firewall Creation Failed

### Task 1: Query Firewall List and Precheck Status

```bash
aliyun cloudfw describe-tr-firewalls-v2-list \
  --RegionId <region> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

Check these fields:

- `PrecheckStatus`
- `ResultCode`
- `FirewallId`
- `FirewallSwitchStatus`
- `ProtectedResource`
- `UnprotectedResource`

### Task 2: Query Recent ActionTrail Operations

```bash
aliyun actiontrail lookup-events \
  --StartTime <24-hours-ago> \
  --EndTime <now> \
  --LookupAttribute.1.Key EventName \
  --LookupAttribute.1.Value CreateTrFirewallV2 \
  --MaxResults 10 \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

Extract `errorCode`, `errorMessage`, `eventTime`, and key request parameters from failed events.

### Task 3: Apply Failure-specific Diagnosis

Use [diagnosis_rules.md](diagnosis_rules.md) for these error patterns:

- `ErrorCandidateHasStaticRoute`: static route diagnosis.
- `ErrorTrFirewallEcmpRoute`: ECMP diagnosis.
- `ErrorTrRouteTableContainsRejectRoutes`: rejected route conflict diagnosis.
- `ErrorTrFirewallRouteMapConflict`: route map consistency diagnosis.
- Silent rollback pattern: route table consistency issue.

## Scenario 2: Route Policy Configuration Failed

### Task 1: Query Firewall Task Status

This task must be first for route policy configuration failures.

```bash
aliyun cloudfw describe-firewall-task \
  --TaskType VPC \
  --ChildInstanceId <vpc-id> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

Check:

- `TaskStatus`
- `TaskFinishTimestamp`
- Failure reason or `ErrorDetail` in the response.

### Task 2: Query Route Policy Operations

```bash
aliyun actiontrail lookup-events \
  --StartTime <24-hours-ago> \
  --EndTime <now> \
  --LookupAttribute.1.Key EventName \
  --LookupAttribute.1.Value CreateTrFirewallV2RoutePolicy \
  --MaxResults 10 \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

Also check modification operations when scope updates are involved:

```bash
aliyun actiontrail lookup-events \
  --StartTime <24-hours-ago> \
  --EndTime <now> \
  --LookupAttribute.1.Key EventName \
  --LookupAttribute.1.Value ModifyTrFirewallV2RoutePolicyScope \
  --MaxResults 10 \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

## Scenario 3: Closure Pre-check in Auto-drainage Mode

1. Query the VPC firewall list with `describe-tr-firewalls-v2-list`.
2. Identify the CFW policy route table and route policy ID.
3. Query rollback mapping with `describe-tr-firewall-policy-back-up-association-list`.
4. Query route entries from the CFW policy route table and the rollback target route table.
5. Run:

```bash
python3 scripts/analyze_routes.py auto_rollback <cfw-routes-json> <rollback-routes-json>
```

6. Query ACL policies with `describe-vpc-firewall-control-policy`.
7. Report route risk and ACL risk.

## Scenario 4: Closure Pre-check in Manual-drainage Mode

1. Confirm current and target route table IDs with the user.
2. Query both route tables with `list-transit-router-route-entries`.
3. Run:

```bash
python3 scripts/analyze_routes.py manual_rollback <current-routes-json> <target-routes-json>
```

4. Query ACL policies if the VPC firewall ID is available.
5. Report route risk and ACL risk.

## Specialized Diagnosis Procedures

### Static Route Diagnosis

1. Query transit router route tables:

```bash
aliyun cbn list-transit-router-route-tables \
  --RegionId <region> \
  --TransitRouterId <tr-id> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

2. Query static routes from the candidate or system route table:

```bash
aliyun cbn list-transit-router-route-entries \
  --TransitRouterRouteTableId <route-table-id> \
  --TransitRouterRouteEntryType Static \
  --MaxResults 100 \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

3. Exclude platform-reserved routes such as `100.64.0.0/10` and its subnets.
4. Provide text-only remediation guidance.

### ECMP Diagnosis

1. Query route entries from the relevant route table.
2. Group routes by destination CIDR.
3. Identify destinations with multiple next hops.
4. Compare the route policy candidate list with actual next-hop resources.
5. Report missing next hops.

### Rejected Route Conflict Diagnosis

Query rejected routes explicitly:

```bash
aliyun cbn list-transit-router-route-entries \
  --TransitRouterRouteTableId <system-route-table-id> \
  --TransitRouterRouteEntryStatus Rejected \
  --MaxResults 100 \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

For each rejected route, compare destination CIDR, next-hop resource, and origin instance with active routes for the same CIDR.

### Route Map Consistency Diagnosis

Query CEN route maps:

```bash
aliyun cbn describe-cen-route-maps \
  --CenId <cen-id> \
  --CenRegionId <region> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

Exclude system-built route maps and compare custom route map distribution across system, strategy, and CFW route tables.

## Output Requirements

After diagnosis:

1. State the root cause in one sentence.
2. Provide only key evidence.
3. List recommended manual actions by priority.
4. Avoid unnecessary resource inventory, full request dumps, and executable write commands.
