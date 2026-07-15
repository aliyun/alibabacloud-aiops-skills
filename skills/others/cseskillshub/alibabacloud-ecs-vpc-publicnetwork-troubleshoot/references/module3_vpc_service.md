# Module 3: Scenario 2 — VPC Cloud Service Cannot Access Public Network (vpc_service_public)

## Script Path

`scripts/vpc_service_public_troubleshoot.py`

## Input Specification

The script accepts all required information via command-line arguments:

| Parameter | Required | Description |
|-----------|----------|-------------|
| `--region-id` | Required | Region ID, e.g., `cn-beijing` |
| `--vswitch-id` | Required | VSwitch ID, e.g., `vsw-2ze4an6iacrvkp9bwb6py` |
| `--uid` | Optional | Customer account UID (auto-obtained from `sts_create.py` GetCallerIdentity if not provided; skips internal query when provided) |

> **Scenario 2 Input Validation**: The primary inputs for this scenario are **vswitch_id and region_id**. UID is auto-obtained via GetCallerIdentity if not provided by the user. Region_id is auto-detected via `scripts/region_detector.py` if not provided. If the user only provides a VSwitch ID, the system will auto-detect the region before proceeding.

## Invocation

The script uses the SDK default credential chain. Invoke directly:

```bash
python3 scripts/vpc_service_public_troubleshoot.py \
  --region-id <region_id> \
  --vswitch-id <vswitch_id> \
  [--uid <UID>]
```

The script automatically completes all detection steps without manual step-by-step execution:
- Steps 1 & 3: Query VSwitch basic info + network ACL check
- Step 2: Check account UID and overdue status
- Step 4: Check if VPC has a NAT Gateway
- Step 5: Check if main route table has 0.0.0.0/0 pointing to NAT Gateway
- Step 6: Check if SNAT entries cover the VSwitch CIDR
- Step 7: Get SNAT EIP address details
- Step 8: Check EIP DDoS blackhole status
- Step 9: Check EIP Cloud Firewall CFW status
- Step 10: Query VPC IPv4 Gateway mode via CLI (`SupportIpv4Gateway`)

## Output JSON Structure

The script outputs a JSON object with the following top-level fields:

| Field | Type | Description |
|-------|------|-------------|
| `scenario` | string | Fixed value `"vpc_service"` |
| `vswitch` | object | VSwitch and network ACL info |
| `account` | object | Account UID and overdue status |
| `ipv4_gateway` | object | VPC IPv4 Gateway mode info |
| `nat_gateway` | object | NAT Gateway info |
| `route_table` | object | Main route table 0.0.0.0/0 route info |
| `snat` | object | SNAT entry check results |
| `eip` | object | EIP address details |
| `ddos` | object | EIP DDoS blackhole status |
| `cfw` | object | EIP Cloud Firewall CFW status |
| `errors` | array | Errors collected during execution |

### `ipv4_gateway` Object Fields

| Field | Description |
|-------|-------------|
| `support_ipv4_gateway` | boolean, whether VPC has IPv4 Gateway enabled |
| `status` | `"Normal"` (not enabled) or `"Abnormal"` (enabled) |

### `vswitch` Object Fields

| Field | Description |
|-------|-------------|
| `vswitch_id` | VSwitch ID |
| `cidr_block` | VSwitch CIDR block |
| `vpc_id` | VPC ID |
| `zone_id` | Availability Zone ID |
| `network_acl_id` | Bound network ACL ID |
| `has_acl` | boolean, whether ACL is bound |
| `route_table_id` | Main route table ID |
| `status` | `"Normal"` or `"Abnormal"` |

### `account` Object Fields

| Field | Description |
|-------|-------------|
| `uid` | Account UID |
| `available_amount` | Available balance |
| `is_owed` | boolean, whether account is overdue |
| `status` | `"Normal"` or `"Abnormal"` |

### `nat_gateway` Object Fields

| Field | Description |
|-------|-------------|
| `has_nat` | boolean, whether internet-type NAT Gateway exists |
| `nat_gateway_id` | NAT Gateway ID |
| `snat_table_id` | SNAT table ID |
| `network_type` | Network type (`internet` or `intranet`) |
| `status` | `"Normal"` or `"Abnormal"` |

### `route_table` Object Fields

| Field | Description |
|-------|-------------|
| `has_0_0_0_0` | boolean, whether 0.0.0.0/0 route exists |
| `next_hop_type` | Next hop type, e.g., `NatGateway` |
| `next_hop_id` | Next hop ID |
| `status` | `"Normal"` or `"Abnormal"` |

### `snat` Object Fields

| Field | Description |
|-------|-------------|
| `has_snat` | boolean, whether SNAT entry matching VSwitch CIDR exists |
| `matched_snat.source_cidr` | Matched SourceCIDR |
| `matched_snat.snat_ip` | SNAT egress IP |
| `status` | `"Normal"` or `"Abnormal"` |

### `eip` Object Fields

| Field | Description |
|-------|-------------|
| `has_eip` | boolean, whether EIP was found |
| `eip_info.ip_address` | EIP address |
| `eip_info.bandwidth` | Bandwidth size |
| `eip_info.status` | EIP status (`Available`/`InUse`) |
| `eip_info.charge_type` | Billing mode |
| `status` | `"Normal"` or `"Abnormal"` |

### `ddos` Object Fields

| Field | Description |
|-------|-------------|
| `ip_status` | DDoS status, e.g., `normal` |
| `status` | `"Normal"` or `"Abnormal"` |

### `cfw` Object Fields

| Field | Description |
|-------|-------------|
| `has_cfw` | boolean, whether CFW is enabled |
| `status` | `"Normal"` (not enabled) or `"Abnormal"` (enabled) |

## Status Determination Logic (for table rendering)

Use the `status` field from JSON output directly for the table "Status" column:

| Table Field | Data Source | Determination Logic |
|-------------|-------------|---------------------|
| Account UID | `account.uid` | Always Normal |
| Account Overdue | `account.is_owed` | `is_owed=true` → Abnormal |
| Cloud Service VSwitch ID | `vswitch.vswitch_id` | Always Normal |
| Cloud Service VSwitch CIDR | `vswitch.cidr_block` | Always Normal |
| VSwitch Network ACL | `vswitch.has_acl` | `true` → Abnormal |
| Cloud Service VPC ID | `vswitch.vpc_id` | Always Normal |
| VPC IPv4 Gateway Mode | `ipv4_gateway.support_ipv4_gateway` | `true` → Abnormal |
| VPC Route Table 0.0.0.0/0 → NAT Gateway | `route_table.next_hop_type` | `!= "NatGateway"` → Abnormal |
| VPC Has NAT Gateway | `nat_gateway.has_nat` | `false` → Abnormal |
| NAT Gateway Has SNAT | `snat.has_snat` | `false` → Abnormal |
| SNAT Associated EIP Address | `eip.has_eip` | `false` → Abnormal (degraded skip when no SNAT IP) |
| EIP DDoS Status | `ddos.ip_status` | `!= "normal"` → Abnormal (degraded skip when no SNAT IP) |
| EIP CFW Security Diversion | `cfw.has_cfw` | `true` → Abnormal |

## Failure Handling

The script handles all API call error capture internally:
- VSwitch query failure causes the script to exit with error JSON
- Other sub-query failures are recorded in the `errors` array but do not crash the script
- DDoS/CFW query failures return `status: "Normal"` with an `error` field attached, avoiding blocking the overall detection
