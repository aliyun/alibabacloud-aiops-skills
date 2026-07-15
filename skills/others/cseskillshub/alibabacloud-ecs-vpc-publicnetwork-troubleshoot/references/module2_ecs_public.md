# Module 2: Scenario 1 — ECS Instance Public Network Access/Inbound Failure (ecs_public)

## Script Path

`scripts/ecs_public_troubleshoot.py`

## Input Specification

The script accepts all required information via command-line arguments:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--region-id` | Required | Region ID, e.g., `cn-beijing` |
| `--instance-id` | Required | ECS instance ID, e.g., `i-2ze9461lyugpmm8d013e` |
| `--uid` | Optional | When provided directly, script skips UID query |
| `--available-amount` | Optional | When provided with available balance, script skips BSS API query (**must be used with `--uid`**) |

## Invocation Methods

### Method 1: Pass uid + available_amount (Recommended for ECS Instance ID scenario)

When Step 1 has already obtained uid and available balance via ECS API, pass them directly to avoid redundant API calls:

```bash
python3 scripts/ecs_public_troubleshoot.py \
  --region-id <region_id> \
  --instance-id <instance_id> \
  --uid <UID> \
  --available-amount <AVAILABLE_AMOUNT>
```

### Method 2: Pass uid only (Public IP scenario)

When only uid is passed, script internally calls BSS API to query balance:

```bash
python3 scripts/ecs_public_troubleshoot.py \
  --region-id <region_id> \
  --instance-id <instance_id> \
  --uid <UID>
```

### Method 3: No uid (Fallback)

Script internally queries both uid and balance automatically:

```bash
python3 scripts/ecs_public_troubleshoot.py \
  --region-id <region_id> \
  --instance-id <instance_id>
```

The script automatically completes all detection steps without manual step-by-step execution:
- Step 3: Query ECS basic info (branch determination)
- Step 4: Check account UID and overdue status (**if `--uid` + `--available-amount` provided, reuses passed values, skips `GetCallerIdentity` and `BSS` API calls**)
- Step 5: Check ECS security group rules
- Step 6: Check VSwitch network ACL
- Step 7: Check VPC IPv4 Gateway and route configuration
- Branch A: DDoS blackhole status + Cloud Firewall CFW
- Branch B: VPC route table NAT target + NAT Gateway existence + SNAT entries + DDoS(eip) + CFW

## Output JSON Structure

The script outputs a JSON object with the following top-level fields:

| Field | Type | Description |
|-------|------|-------------|
| `scenario` | string | Fixed value `"ecs_public"` |
| `branch` | string | `"A"` (direct public) or `"B"` (NAT Gateway) |
| `ecs` | object | ECS instance basic info |
| `account` | object | Account UID and overdue status |
| `security_group` | object | Security group rule check results |
| `vswitch` | object | VSwitch and network ACL info |
| `vpc` | object | VPC IPv4 Gateway info |
| `route_table` | object \| null | Main route table 0.0.0.0/0 route info (non-null only when IPv4 Gateway is enabled) |
| `branch_result` | object | Branch A or B specific detection results |
| `errors` | array | Errors collected during execution |

### `ecs` Object Fields

| Field | Description |
|-------|-------------|
| `instance_id` | Instance ID |
| `instance_name` | Instance name |
| `private_ip` | Private IP |
| `public_ip` | Public IP (null if none) |
| `eip_ip` | Bound EIP (null if none) |
| `internet_charge_type` | Billing mode raw value, e.g., `PayByTraffic`, `PayByBandwidth`; when instance has no public IP but bound EIP, queried via `DescribeEipAddresses` |
| `internet_charge_type_status` | Billing mode status: `"Normal"` or `"Abnormal"` (abnormal when overdue + pay-by-traffic) |
| `security_groups` | Security group ID array |
| `vswitch_id` | VSwitch ID |
| `vpc_id` | VPC ID |
| `has_public_ip` | boolean, whether instance has public IP or EIP |
| `branch` | `"A"` or `"B"` |

### `account` Object Fields

| Field | Description |
|-------|-------------|
| `uid` | Account UID |
| `available_amount` | Available balance |
| `is_owed` | boolean, whether account is overdue |
| `status` | `"Normal"` or `"Abnormal"` |

### `security_group` Object Fields

| Field | Description |
|-------|-------------|
| `sg_ids` | Security group ID array |
| `has_icmp_0_0_0_0` | boolean, whether 0.0.0.0/0 ICMP ingress accept rule exists |
| `has_egress_drop` | boolean, whether egress Drop rule exists |
| `status` | Branch A: `"Normal"` (has ICMP allow) or `"Abnormal"`; Branch B: `"Normal"` (no egress Drop) or `"Abnormal"` (has egress Drop) |

### `vswitch` Object Fields

| Field | Description |
|-------|-------------|
| `vswitch_id` | VSwitch ID |
| `cidr_block` | VSwitch CIDR block |
| `network_acl_id` | Bound network ACL ID (empty string if none) |
| `has_acl` | boolean, whether ACL is bound |
| `route_table_id` | Main route table ID |
| `status` | `"Normal"` (no ACL) or `"Abnormal"` |

### `vpc` Object Fields

| Field | Description |
|-------|-------------|
| `vpc_id` | VPC ID |
| `support_ipv4_gateway` | boolean, whether IPv4 Gateway is enabled |
| `ipv4_gateway_id` | IPv4 Gateway ID |
| `status` | `"Normal"` (not enabled) or `"Abnormal"` (enabled) |

### `route_table` Object Fields (only exists when `support_ipv4_gateway = true`)

| Field | Description |
|-------|-------------|
| `has_0_0_0_0` | boolean, whether 0.0.0.0/0 route exists |
| `next_hop_type` | Next hop type, e.g., `Ipv4Gateway`, `NatGateway` |
| `next_hop_id` | Next hop ID |
| `status` | `"Normal"` or `"Abnormal"` |

### Branch A `branch_result` Structure

| Field | Description |
|-------|-------------|
| `ddos.ip_status` | DDoS status, e.g., `normal` |
| `ddos.status` | `"Normal"` or `"Abnormal"` |
| `cfw.has_cfw` | boolean, whether CFW is enabled |
| `cfw.status` | `"Normal"` (not enabled) or `"Abnormal"` (enabled) |

### Branch B `branch_result` Structure

| Field | Description |
|-------|-------------|
| `route_table` | Whether main route table points to NAT (same as `route_table` structure) |
| `nat_gateway.has_nat` | boolean, whether internet-type NAT Gateway exists |
| `nat_gateway.nat_gateway_id` | NAT Gateway ID |
| `nat_gateway.snat_table_id` | SNAT table ID |
| `nat_gateway.network_type` | Network type |
| `nat_gateway.status` | `"Normal"` or `"Abnormal"` |
| `snat.has_snat` | boolean, whether SNAT entry matching VSwitch CIDR exists |
| `snat.matched_snat.source_cidr` | Matched SourceCIDR |
| `snat.matched_snat.snat_ip` | SNAT egress IP |
| `snat.status` | `"Normal"` or `"Abnormal"` |
| `ddos` | NAT Gateway EIP DDoS status (same as Branch A) |
| `cfw` | NAT Gateway EIP CFW status (same as Branch A) |

## Status Determination Logic (for table rendering)

Use the `status` field from JSON output directly for the table "Status" column:

| Table Field | Data Source | Determination Logic |
|-------------|-------------|---------------------|
| Account UID | `account.uid` | Always Normal |
| Account Overdue | `account.is_owed` | `is_owed=true` → Abnormal |
| ECS Instance ID | `ecs.instance_id` | Always Normal |
| ECS Private IP | `ecs.private_ip` | Always Normal |
| ECS Public IP | `ecs.public_ip` + `eip_ip` | Always Normal |
| ECS Public IP Billing Mode | `ecs.internet_charge_type` + `ecs.internet_charge_type_status` | Overdue (`is_owed=true`) AND pay-by-traffic (`PayByTraffic`) → Abnormal; otherwise → Normal |
| ECS IP DDoS Status | `branch_result.ddos.ip_status` | `!= "normal"` → Abnormal |
| ECS Security Group | `security_group.has_icmp_0_0_0_0` (Branch A)<br/>`security_group.has_egress_drop` (Branch B) | Branch A: `false` → Abnormal (missing ICMP ingress allow)<br/>Branch B: `true` → Abnormal (egress Drop rule exists) |
| ECS VSwitch | `ecs.vswitch_id` | Always Normal |
| ECS VSwitch Network ACL | `vswitch.has_acl` | `true` → Abnormal |
| ECS VPC | `ecs.vpc_id` | Always Normal |
| ECS VPC IPv4 Gateway Mode | `vpc.support_ipv4_gateway` + `route_table.next_hop_type` | `true` AND route table does not point to `Ipv4Gateway` → Abnormal; `true` AND points to `Ipv4Gateway` → Normal (configured correctly) |
| VPC Main Route Table 0.0.0.0/0 → IPv4 Gateway | `route_table.next_hop_type` | `!= "Ipv4Gateway"` → Abnormal (conditional output) |
| ECS Public IP CFW Security Diversion | `branch_result.cfw.has_cfw` | `true` → Abnormal |

### Branch B Specific Fields

| Table Field | Data Source | Determination Logic |
|-------------|-------------|---------------------|
| VPC Route Table 0.0.0.0/0 → NAT Gateway | `branch_result.route_table.next_hop_type` | `!= "NatGateway"` → Abnormal |
| VPC Has NAT Gateway | `branch_result.nat_gateway.has_nat` | `false` → Abnormal |
| NAT Gateway Has SNAT | `branch_result.snat.has_snat` | `false` → Abnormal |
| NAT Gateway SNAT EIP Address | `branch_result.snat.matched_snat.snat_ip` | Always Normal |
| NAT Gateway EIP DDoS | `branch_result.ddos.ip_status` | `!= "normal"` → Abnormal |
| EIP CFW Security Diversion | `branch_result.cfw.has_cfw` | `true` → Abnormal |

## Failure Handling

The script handles all API call error capture internally:
- Any sub-query failure is recorded in the `errors` array but does not crash the script
- Critical prerequisite step failures (e.g., ECS basic info query) cause the script to exit with error JSON
- DDoS/CFW query failures return `status: "Normal"` with an `error` field attached, avoiding blocking the overall detection
