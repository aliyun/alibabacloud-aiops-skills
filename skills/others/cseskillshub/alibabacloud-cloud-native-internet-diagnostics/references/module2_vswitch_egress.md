# Module 2: vSwitch Egress Determination (NAT/SNAT) and FC Four Quadrants

Minimum privilege: **read-only**. Only vpc Describe actions are used.

This module decides whether a given vSwitch has a public internet egress via a NAT gateway SNAT rule. It runs inline inside `scripts/cloud_native_internet_diag.py` (no external skill delegation).

## FC Four-Quadrant Rules

Function Compute egress depends on `internetAccess` combined with the VPC configuration returned by `fc:GetFunction`:

| Quadrant | vpcConfig | internetAccess | Conclusion |
|----------|-----------|----------------|------------|
| A | not configured (no vSwitchIds) | true | The function reaches the public internet via a shared public IP; there is **no fixed public egress IP** |
| B | not configured (no vSwitchIds) | false | The function **cannot access the public internet** |
| C | configured (vSwitchIds present) | true | Shared public IP egress (not fixed); VPC internal resources also reachable |
| D | configured (vSwitchIds present) | false | Egress goes through the VPC vSwitch; a **fixed public IP is possible via NAT SNAT** → run the NAT/SNAT check below |

> **Core rule**: only quadrant D (`internetAccess=false` AND vSwitchIds configured) triggers the NAT/SNAT egress check, which runs against every bound vSwitch (any hit means a fixed public egress); quadrants A/B/C conclude directly from GetFunction and skip the VPC queries.

## NAT/SNAT Check Chain

```
vSwitch id
    |
    v
vpc:DescribeVSwitchAttributes  ->  resolve VpcId + CidrBlock (and status)
    |
    v
vpc:DescribeNatGateways (--vpc-id <vpc> --biz-region-id <region>, paginated)
    |                                          ->  NAT gateways in the same VPC
    v                                             collect SnatTableIds
vpc:DescribeSnatTableEntries (--snat-table-id <id>, paginated)
    |                                          ->  entries matching the vSwitch
    v
has_public_egress = any matched entry has a SnatIp and Status == Available
```

Both paginated queries use `--page-size 50` and loop `--page-number` until the accumulated count reaches `TotalCount` (capped at 20 pages).

### Determination Rules

1. **No NAT gateway in the VPC** → the vSwitch has no NAT SNAT public egress.
2. **NAT gateway exists, no SNAT entry covers the vSwitch** → no public egress for this vSwitch (other vSwitches in the VPC may still have egress).
3. **SNAT entry matches the vSwitch with a `SnatIp`** → the vSwitch has a NAT SNAT public egress; workloads obtain a fixed public egress IP (the `SnatIp`). Entries not in status `Available` are reported as unreliable. A match is either `SourceVSwitchId` equals the target vSwitch, or a non-empty `SourceCIDR` that contains the vSwitch `CidrBlock` (CIDR containment, e.g. via the Python `ipaddress` module).
4. **Any sub-query fails with an authorization error** → degrade gracefully: log `[WARN]`, mark the check `inconclusive`, and still emit the report with the warning preserved.

### CLI Command Shapes (verified)

```
aliyun vpc describe-vswitch-attributes --vswitch-id <id> --region <region> --user-agent <UA>
aliyun vpc describe-nat-gateways --vpc-id <vpc> --biz-region-id <region> --page-size 50 --page-number <n> --region <region> --user-agent <UA>
aliyun vpc describe-snat-table-entries --biz-region-id <region> --snat-table-id <id> --page-size 50 --page-number <n> --region <region> --user-agent <UA>
```

## Conclusion Wording Used by the Script

| Situation | Conclusion text (JSON `conclusion` / `egress_check.conclusion`) |
|-----------|------------------------------------------------------------------|
| SNAT Available entry matches | "The vSwitch has a NAT SNAT public egress: SNAT entry (status Available) covers this vSwitch with public IP <ips>; workloads on this vSwitch can reach the public internet via a fixed public IP" |
| SNAT entries exist but none Available | "SNAT entries cover this vSwitch but none is in status Available; public egress is currently unreliable" |
| NAT exists, no entry covers vSwitch | "NAT gateway(s) exist in the VPC but no SNAT entry covers this vSwitch; the vSwitch has no NAT SNAT public egress" |
| No NAT gateway in the VPC | "No NAT gateway found in the VPC of this vSwitch; the vSwitch has no NAT SNAT public egress" |
| Sub-query failed (degraded) | "Egress check inconclusive: ... cannot determine NAT SNAT egress" |
