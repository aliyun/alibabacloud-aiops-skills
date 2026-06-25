# Closure Pre-check Guide

This guide covers VPC firewall closure pre-check for auto-drainage and manual-drainage modes.

## Objective

Before closing VPC firewall drainage, determine whether business routes may be lost and whether ACL policy state creates additional risk.

## Mandatory Principles

- Route comparison must be performed by `scripts/analyze_routes.py`.
- Do not manually infer route loss from counts only.
- Save API responses to JSON files before running the script.
- Provide text-only remediation guidance; do not provide executable write commands.

## Scenario 3: Auto-drainage Mode

### Required Data

1. VPC firewall ID.
2. Transit router route policy ID.
3. CFW policy route table route entries.
4. Rollback target route table route entries, identified by `OriginalRouteTableId`.
5. ACL policy count and relevant deny policies.

### Required API Sequence

1. Query the VPC firewall list:

```bash
aliyun cloudfw describe-tr-firewalls-v2-list \
  --RegionId <region> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

2. Query the rollback target route table:

```bash
aliyun cloudfw describe-tr-firewall-policy-back-up-association-list \
  --FirewallId <firewall-id> \
  --TrFirewallRoutePolicyId <route-policy-id> \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

3. Query route entries for the CFW policy route table and the rollback target route table:

```bash
aliyun cbn list-transit-router-route-entries \
  --TransitRouterRouteTableId <route-table-id> \
  --MaxResults 100 \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

4. Run the route analysis script:

```bash
python3 scripts/analyze_routes.py auto_rollback <cfw-routes-json> <rollback-routes-json>
```

5. Query ACL policies:

```bash
aliyun cloudfw describe-vpc-firewall-control-policy \
  --VpcFirewallId <vpc-firewall-id> \
  --PageSize 50 \
  --CurrentPage 1 \
  --profile <profile> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-cloudfw-vpc-firewall-diagnosis
```

### Output Requirements

Report both options for user decision:

- Route rollback impact.
- Route revoke impact if applicable.
- ACL policy risk.
- Required manual verification before closure.
- Manual console remediation guidance.

## Scenario 4: Manual-drainage Mode

### Required Data

1. Current route table ID.
2. Target route table ID after closure.
3. Route entries from both route tables.
4. ACL policy count and deny policy risk.

### Required Flow

1. Ask the user for current and target route table IDs.
2. Query route entries for both route tables using `list-transit-router-route-entries`.
3. Run the analysis script:

```bash
python3 scripts/analyze_routes.py manual_rollback <current-routes-json> <target-routes-json>
```

4. Query ACL policies if the VPC firewall ID is available.
5. Report route loss risk and ACL risk.

## Route Revoke Mode

When route revoke mode is used, route rollback loss is not the primary risk. The main risk is residual empty route tables that may require user review in the CEN console.

Run:

```bash
python3 scripts/analyze_routes.py route_revoke <route-tables-json>
```

## Risk Decision Rules

| Finding | Risk level | Meaning |
|---|---|---|
| Business routes missing from rollback target | High | Traffic to those CIDRs may become unroutable after closure. |
| Missing route next hop is VPC, VPN, or VBR | High | Key network connectivity may be affected. |
| No missing business route | Low | No route-loss risk found by route comparison. |
| No ACL policy exists | Medium | Re-enabling firewall later may default-deny traffic without prepared policy. |
| Deny ACL policies exist | Medium | Session or state changes during closure may require careful validation. |

## Report Template

```text
Notice: This tool is a read-only diagnostic assistant. It only provides analysis and configuration guidance and will not perform any configuration changes.
Please apply all configuration changes manually in the Alibaba Cloud Console or through your own approved process.

Conclusion:
- Route rollback risk: <High/Medium/Low>
- ACL risk: <High/Medium/Low>

Evidence:
- Missing routes: <count and key CIDRs>
- ACL policies: <count and risk summary>

Recommended manual actions:
1. Review the listed route entries in the CEN console.
2. Add missing routes to the rollback or target route table only after manual approval.
3. Review ACL policies before closure and before later re-enable operations.
4. Monitor business connectivity after closure.
```
