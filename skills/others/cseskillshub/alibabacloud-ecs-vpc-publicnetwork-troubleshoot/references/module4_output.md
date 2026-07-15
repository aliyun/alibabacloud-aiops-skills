# Module 4: Output Results and Determination Specification

## Output Specification

- **Final output consists of two parts**: (1) Information table; (2) Solution module (output only when abnormal items exist in the table).
- Each row in the table MUST include a "Status" column, which only allows **Normal** or **Abnormal**.
- **Style Requirement**: When **Abnormal** appears in the "Status" column, it MUST be rendered in bold red, i.e., `**<span style="color:red">Abnormal</span>**` (or equivalent rendering). Normal status needs no special coloring.
- **Solution Module**: Per [module5_solution.md](module5_solution.md), output corresponding remediation for each abnormal item in the table. If all items are "Normal", skip the solution module.
- **Execution Notes (Errors Array)**: The script JSON output includes an `errors` field recording degradation or skip information during execution (e.g., "no SNAT IP"). If `errors` is non-empty, append a gray footnote below the table: "Execution Notes: xxx", helping confirm which checks were degraded due to missing prerequisites.
- **Degraded Status**: DDoS/CFW checks depend on SNAT IP or public IP. When no IP is available, the script returns `status="Normal"` with an `error` explanation (e.g., "no SNAT IP") — this is a **degraded skip**, not a true pass. When rendering the table, fill the status column per script output, but annotate the result column with the degradation reason (e.g., "Normal (no SNAT IP, check skipped)").
- Status determination logic as follows, MUST be strictly followed:
  | Field | Normal | Abnormal |
  |-------|--------|----------|
  | Account UID | Always Normal | — |
  | Account Overdue | Not overdue (AvailableAmount >= 0) | Overdue (AvailableAmount < 0) |
  | ECS Instance ID | Always Normal | — |
  | ECS Private IP | Always Normal | — |
  | ECS Public IP | Always Normal | — |
  | ECS Public IP Billing Mode | Not overdue, or billing mode is not pay-by-traffic | Overdue (AvailableAmount < 0) AND billing mode is pay-by-traffic (PayByTraffic) |
  | ECS IP DDoS Status | IpStatus = normal | IpStatus != normal |
  | ECS Security Group | Has `0.0.0.0/0` ingress `icmp` or `all` Accept rule (Branch A); No egress `Drop` rule (Branch B) | Missing above rule (Branch A: no ICMP ingress allow; Branch B: egress Drop rule exists) |
  | ECS VSwitch | Always Normal | — |
  | ECS VSwitch Network ACL | No ACL bound | ACL bound |
  | ECS VPC | Always Normal | — |
  | ECS VPC IPv4 Gateway Mode | Not enabled, or enabled with route table correctly pointing to IPv4 Gateway | Enabled but route table does not point to IPv4 Gateway |
  | VPC Main Route Table 0.0.0.0/0 → IPv4 Gateway | Exists 0.0.0.0/0 with next hop Ipv4Gateway | Route does not exist |
  | ECS Public IP CFW Security Diversion | Not enabled (Assets empty) | Enabled (Assets non-empty) |

## Billing Mode Output Logic

1. **Value Mapping**: `PayByBandwidth` → **Pay-by-Bandwidth**, `PayByTraffic` → **Pay-by-Traffic**; empty or unrecognized → **—**.
2. **EIP Scenario Supplementary Query**: When instance `PublicIpAddress` is empty but EIP is bound, the script queries `DescribeEipAddresses` via CLI to get EIP's `InternetChargeType` as the billing mode reference.
3. **Status Determination**:
   - If `AvailableAmount < 0` (overdue) AND `InternetChargeType == "PayByTraffic"` → **Abnormal**, result column: **Pay-by-Traffic (account overdue, throttled)**
   - Otherwise → **Normal**, result column per value mapping

---

## Branch A: Direct Public Info Table (ECS has Public IP/EIP)

When ECS instance has a public IP or directly bound EIP, output the following 14-field information table:

| Field | Status | Result |
|-------|--------|--------|
| Account UID | Normal | 1178674910674516 |
| Account Overdue | Normal | No |
| ECS Instance ID | Normal | i-bp17hhpkwwc8en8jrha5 |
| ECS Private IP | Normal | 172.16.2.239 |
| ECS Public IP | Normal | 47.100.xxx.xxx (5Mbps) |
| ECS Public IP Billing Mode | Normal | Pay-by-Traffic |
| ECS IP DDoS Status | Normal | No (IpStatus=normal) |
| ECS Security Group | Normal/Abnormal | sg-bp123456 (1 security group total) |
| ECS VSwitch | Normal | vsw-bp123456 |
| ECS VSwitch Network ACL | Normal/Abnormal | None / Yes (ACL ID: xxx) |
| ECS VPC | Normal | vpc-bp12oglg7akaq80m40p3z |
| ECS VPC IPv4 Gateway Mode | Normal/Abnormal | Not enabled / Enabled |
| VPC Main Route Table 0.0.0.0/0 → IPv4 Gateway | Normal/Abnormal | Yes / No |
| ECS Public IP CFW Security Diversion | Normal/Abnormal | No / Yes |

> **Conditional Output**: The "VPC Main Route Table 0.0.0.0/0 → IPv4 Gateway" row is only output when `SupportIpv4Gateway = true`; if IPv4 Gateway is not enabled, this row does not appear in the final table.

> **Field Order**: Billing mode follows immediately after public IP and before DDoS status, for quick identification of bandwidth billing and public access cost correlation.

---

## Branch B: NAT Gateway Info Table (ECS without Public IP)

When ECS instance has no public IP and no directly bound EIP, output the following 15-field information table:

> **Branch B Security Group Note**: Since ECS has no public IP, external access is not possible. Security group check focuses on **whether egress Drop rules exist** (which would block ECS access to public via NAT Gateway), rather than ingress ICMP allow.

| Field | Status | Result |
|-------|--------|--------|
| Account UID | Normal | 1234567890123456 |
| Account Overdue | Normal | No |
| ECS Instance ID | Normal | i-bp17hhpkwwc8en8jrha5 |
| ECS Private IP | Normal | 172.16.2.239 |
| ECS Security Group | Normal/Abnormal | sg-bp123456 (no explicit egress Drop rule) |
| ECS VSwitch | Normal | vsw-bp123456 |
| ECS VSwitch Network ACL | Normal/Abnormal | None / Yes (ACL ID: xxx) |
| ECS VPC | Normal | vpc-bp12oglg7akaq80m40p3z |
| ECS VPC IPv4 Gateway Mode | Normal/Abnormal | Not enabled / Enabled |
| VPC Route Table 0.0.0.0/0 → NAT Gateway | Normal/Abnormal | Yes / No |
| VPC Has NAT Gateway | Normal/Abnormal | Yes / No |
| NAT Gateway Has SNAT | Normal/Abnormal | Yes / No |
| NAT Gateway SNAT EIP Details | Normal | 47.100.xxx.xxx (Pay-by-Traffic) |
| EIP DDoS Status | Normal | Normal (NAT Gateway EIP); degraded skip if no SNAT IP |
| EIP CFW Security Diversion | Normal/Abnormal | No / Yes; degraded skip if no SNAT IP |

---

## Scenario 2: VPC Cloud Service Info Table

When a cloud service in VPC cannot access the public network, output the following 12-field information table:

| Field | Status | Result |
|-------|--------|--------|
| Account UID | Normal | 1234567890123456 |
| Account Overdue | Normal | No |
| Cloud Service VSwitch | Normal | vsw-bp123456 (cloud service instance) |
| Cloud Service VSwitch Network ACL | Normal/Abnormal | None / Yes (ACL ID: xxx) |
| Cloud Service VSwitch VPC | Normal | vpc-bp12oglg7akaq80m40p3z (cloud service) |
| VPC IPv4 Gateway Mode | Normal/Abnormal | Not enabled / Enabled |
| VPC Route Table 0.0.0.0/0 → NAT Gateway | Normal/Abnormal | Yes / No; if abnormal check IPv4 Gateway or configure complete route |
| VPC Has NAT Gateway | Normal/Abnormal | Yes / No |
| NAT Gateway Has SNAT | Normal/Abnormal | Yes / No |
| NAT Gateway SNAT EIP Details | Normal | 47.100.xxx.xxx (Pay-by-Traffic) |
| EIP DDoS Status | Normal | Normal (NAT Gateway EIP) |
| EIP CFW Security Diversion | Normal/Abnormal | No / Yes |
