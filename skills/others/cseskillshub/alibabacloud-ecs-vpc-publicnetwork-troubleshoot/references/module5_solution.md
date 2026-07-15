# Module 5: Solution Module

## Output Rules

1. **The solution module is output only after the information table**, triggered only when there are **abnormal** items in the information table.
2. If there are no abnormal items in the information table (all normal), the solution module is **not output**.
3. Each abnormality corresponds to an independent solution section, arranged in the order they appear in the information table.
4. At the end of each abnormality's resolution steps, an adaptive step must be appended:
   > Step N: After completing the above steps, re-test connectivity;
   where N is the actual step number of that abnormality + 1.
5. When `nat_gateway.has_nat = false` (no NAT gateway in VPC), even if the route table lacks a 0.0.0.0/0 route pointing to the NAT gateway, **skip the solution output for Abnormality 7**, and only output Abnormality 8 and Abnormality 9 (or only Abnormality 8). Because configuring the route table is meaningless until a NAT gateway is created first.

## Output Format Template

```
Hello, after analysis the following issues exist, and the solutions are as follows:

[Abnormality 1] xxx
Root Cause: xxxx
Step 1: Configure xxxxxxxxxxxxx
Step 2: Configure xxxxxxxxxxxxx
Step N: After completing the above steps, re-test connectivity;

[Abnormality 2] xxx
Root Cause: xxxx
Step 1: Configure xxxxxxxxxxxxx
Step 2: Configure xxxxxxxxxxxxx
Step N: After completing the above steps, re-test connectivity;

...

Reference Documents: xxxxxxxx
```

> **Variable Substitution Note**: All `${region_id}`, `${vpc_id}`, `${route_table_id}`, `${nat_gateway_id}`, `${public_ip}`, `${snat_ip}`, `${instance_id}`, `${vswitch_id}`, `${security_group_id}` in the template must be adaptively replaced based on actual script query results.

---

## Abnormality Solution Template Index

| No. | Abnormality Name | Applicable Scenario |
|-----|-----------------|---------------------|
| 1 | Account Overdue | Branch A / Branch B / Scenario 2 |
| 2 | ECS Security Group (Missing ICMP Inbound Allow) | Branch A |
| 3 | ECS Security Group (Egress Drop Rule Exists) | Branch B |
| 4 | VSwitch Network ACL | Branch A / Branch B / Scenario 2 |
| 5 | VPC IPv4 Gateway Mode Enabled | Branch A / Branch B / Scenario 2 |
| 6 | VPC Main Route Table 0.0.0.0/0 Not Pointing to IPv4 Gateway | Branch A (Conditional Output) |
| 7 | VPC Route Table 0.0.0.0/0 Not Pointing to NAT Gateway | Branch B / Scenario 2 |
| 8 | No NAT Gateway in VPC | Branch B / Scenario 2 |
| 9 | NAT Gateway Has No SNAT Configuration | Branch B / Scenario 2 |
| 10 | IP Address Under DDoS Blackhole | Branch A / Branch B / Scenario 2 |
| 11 | IP Address Has Cloud Firewall (CFW) Traffic Diversion | Branch A / Branch B / Scenario 2 |

---

## Detailed Solution Templates

### Abnormality 1: Account Overdue

**Applicable Scenario**: Branch A / Branch B / Scenario 2

**Trigger Condition**: `account.is_owed = true` (`AvailableAmount < 0`)

**Reply Template**:
```
[Account Overdue]
Root Cause: Account overdue abnormality
Step 1: Visit the link https://billing-cost.console.aliyun.com/home
Step 2: Complete the payment top-up
Step 3: After completing the above steps, re-test connectivity;
```

---

### Abnormality 2: ECS Security Group — Missing ICMP Inbound Allow (Branch A)

**Applicable Scenario**: Branch A

**Trigger Condition**: `security_group.has_icmp_0_0_0_0 = false`

**Reply Template**:
```
[ECS Security Group Missing ICMP Inbound Allow]
Root Cause: The ECS security group does not allow public ICMP inbound traffic, preventing external ping access to the instance
Step 1: Find the security group ${security_group_id} associated with instance ${instance_id}
Step 2: Click "Configure Rules", then click "Add Rule" in the "Inbound" tab
Step 3: Add a rule: Authorization Policy select "Allow", Protocol Type select "ICMP(IPv4)", Port Range "-1/-1", Source set to "0.0.0.0/0"
Step 4: Click "Save"
Step 5: After completing the above steps, re-test connectivity;
Reference Document: https://help.aliyun.com/zh/ecs/user-guide/security-group-overview
```

---

### Abnormality 3: ECS Security Group — Egress Drop Rule Exists (Branch B)

**Applicable Scenario**: Branch B

**Trigger Condition**: `security_group.has_egress_drop = true`

**Reply Template**:
```
[ECS Security Group Has Egress Drop Rule]
Root Cause: The ECS security group has an egress Drop rule that blocks outbound traffic from ECS through the NAT gateway to the internet
Step 1: Find the security group ${security_group_id} associated with instance ${instance_id}
Step 2: Click "Configure Rules", switch to the "Outbound" tab
Step 3: Check if there are rules with "Deny" (Drop) policy, remove or adjust them if found
Step 4: Ensure at least one allow rule exists for outbound 0.0.0.0/0 (e.g., "All TCP" or "All ICMP" with "Allow" policy)
Step 5: Click "Save"
Step 6: After completing the above steps, re-test connectivity;
Reference Document: https://help.aliyun.com/zh/ecs/user-guide/security-group-overview
```

---

### Abnormality 4: VSwitch Network ACL

**Applicable Scenario**: Branch A / Branch B / Scenario 2

**Trigger Condition**: `vswitch.has_acl = true`

**Reply Template**:
```
[VSwitch Has Network ACL Bound]
Root Cause: VSwitch ${vswitch_id} has a network ACL bound, and deny rules in the ACL may block public network traffic
Step 1: Find the network ACL instance bound to VSwitch ${vswitch_id}
Step 2: Check the inbound and outbound rule lists
Step 3: Allow the required protocols and ports for business needs, or temporarily set the relevant rules to "Allow" for testing
Step 4: Save the rule changes
Step 5: After completing the above steps, re-test connectivity;
Reference Document: https://help.aliyun.com/zh/vpc/network-acl-overview
```

---

### Abnormality 5: VPC IPv4 Gateway Mode Enabled

**Applicable Scenario**: Branch A / Branch B / Scenario 2

**Trigger Condition**:
- Branch A: `vpc.support_ipv4_gateway = true` and route table does not correctly point to IPv4 gateway (`route_table.next_hop_type != "Ipv4Gateway"`)
- Branch B / Scenario 2: `vpc.support_ipv4_gateway = true`

**Reply Template**:
```
[VPC Has IPv4 Gateway Enabled]
Root Cause: This VPC has IPv4 gateway enabled. Please confirm the reason for enabling the IPv4 gateway and whether it is necessary.
If the IPv4 gateway is not needed, the deletion steps are as follows:
Step 1: Visit the link https://vpc.console.aliyun.com/ipv4/${region_id}/ipv4s
Step 2: Find the corresponding ${vpc_id} and click the delete button
Step 3: In the deletion dialog, select public network mode (make sure to select correctly)
Step 4: After completing the above steps, re-test connectivity;
Reference Document: https://help.aliyun.com/zh/vpc/ipv4-gateway-overview#37b32469c9n6j
```

---

### Abnormality 6: VPC Main Route Table 0.0.0.0/0 Not Pointing to IPv4 Gateway (Branch A)

**Applicable Scenario**: Branch A (output only when `SupportIpv4Gateway = true`)

**Trigger Condition**: `route_table.next_hop_type != "Ipv4Gateway"`

**Reply Template**:
```
[VPC Main Route Table Missing 0.0.0.0/0 Route to IPv4 Gateway]
Root Cause: The IPv4 gateway under this VPC is not fully configured
Step 1: Visit the link https://vpc.console.aliyun.com/vpc/${region_id}/route-tables/${route_table_id}
Step 2: Click "Add Route Entry"
Step 3: Set destination CIDR to 0.0.0.0/0, next hop type select "IPv4 Gateway", next hop select the corresponding IPv4 gateway instance
Step 4: Click "OK" to save
Step 5: After completing the above steps, re-test connectivity;
Reference Document: https://help.aliyun.com/zh/vpc/vpc-route-table/#e2a77086dae4t
```

---

### Abnormality 7: VPC Route Table 0.0.0.0/0 Not Pointing to NAT Gateway (Branch B / Scenario 2)

**Applicable Scenario**: Branch B / Scenario 2

**Trigger Condition**: `route_table.next_hop_type != "NatGateway"`

**Reply Template**:
```
[VPC Main Route Table Missing 0.0.0.0/0 Route to NAT Gateway]
Root Cause: The route table under this VPC does not direct public network traffic to the NAT gateway
Step 1: Visit the link https://vpc.console.aliyun.com/vpc/${region_id}/route-tables/${route_table_id}
Step 2: Click "Add Route Entry"
Step 3: Set destination CIDR to 0.0.0.0/0, next hop type select "NAT Gateway", next hop select the corresponding NAT gateway instance
Step 4: Click "OK" to save
Step 5: After completing the above steps, re-test connectivity;
Reference Document: https://help.aliyun.com/zh/vpc/vpc-route-table/#e2a77086dae4t
```

---

### Abnormality 8: No NAT Gateway in VPC (Branch B / Scenario 2)

**Applicable Scenario**: Branch B / Scenario 2

**Trigger Condition**: `nat_gateway.has_nat = false`

**Reply Template**:
```
[No NAT Gateway in VPC]
Root Cause: There is no NAT gateway as public network egress under this VPC
Step 1: Visit the link https://vpc.console.aliyun.com/nat/${region_id}/nats
Step 2: Click the blue button "Create NAT Gateway" to create a NAT gateway instance for ${vpc_id}
Step 3: After creation, continue to configure the SNAT entry (see Abnormality 9)
Step 4: After completing the above steps, re-test connectivity;
Reference Document: https://help.aliyun.com/zh/nat-gateway/user-guide/use-internet-nat-gateway-for-public-network-access
```

---

### Abnormality 9: NAT Gateway Has No SNAT Configuration (Branch B / Scenario 2)

**Applicable Scenario**: Branch B / Scenario 2

**Trigger Condition**: `snat.has_snat = false`

**Reply Template**:
```
[NAT Gateway Has No SNAT Configured]
Root Cause: The NAT gateway under this VPC does not have an SNAT entry covering the VSwitch CIDR range
Step 1: Visit the link https://vpc.console.aliyun.com/nat/${region_id}/nats/${nat_gateway_id}/snats
Step 2: Configure a VPC-level SNAT entry
Step 3: After completing the above steps, re-test connectivity;
Reference Document: https://help.aliyun.com/zh/nat-gateway/user-guide/use-internet-nat-gateway-for-public-network-access#03d28dc30blc0
```

---

### Abnormality 10: IP Address Under DDoS Blackhole

**Applicable Scenario**: Branch A / Branch B / Scenario 2

**Trigger Condition**: `ddos.ip_status != "normal"`

**Reply Template (Branch A, Public IP / EIP)**:
```
[Public IP Under DDoS Blackhole]
Root Cause: The IP address ${public_ip} is under DDoS blackhole
Step 1: Please wait patiently for the blackhole to end.
Step 2: After completing the above steps, re-test connectivity;
```

**Reply Template (Branch B / Scenario 2, NAT Gateway SNAT EIP)**:
```
[NAT Gateway SNAT EIP Under DDoS Blackhole]
Root Cause: The EIP ${snat_ip} bound to SNAT is under DDoS blackhole
Step 1: Please wait patiently for the blackhole to end.
Step 2: After completing the above steps, re-test connectivity;
```

---

### Abnormality 11: IP Address Has Cloud Firewall (CFW) Traffic Diversion

**Applicable Scenario**: Branch A / Branch B / Scenario 2

**Trigger Condition**: `cfw.has_cfw = true`

**Reply Template (Branch A, Public IP / EIP)**:
```
[Public IP Has Cloud Firewall Traffic Diversion Enabled]
Root Cause: The public IP ${public_ip} has Cloud Firewall enabled. Please try disabling Cloud Firewall protection to see if connectivity recovers.
Step 1: Visit the link https://yundun.console.aliyun.com/cfw#/firewall/switch/internet/ipv4
Step 2: Find your IP address ${public_ip}, select "Disable Protection"
Step 3: Re-test connectivity
Step 4: After completing the above steps, re-test connectivity;
```

**Reply Template (Branch B / Scenario 2, NAT Gateway SNAT EIP)**:
```
[SNAT EIP Has Cloud Firewall Traffic Diversion Enabled]
Root Cause: The EIP ${snat_ip} bound to SNAT has Cloud Firewall enabled. Please try disabling Cloud Firewall protection to see if connectivity recovers.
Step 1: Visit the link https://yundun.console.aliyun.com/cfw#/firewall/switch/internet/ipv4
Step 2: Find your IP address ${snat_ip}, select "Disable Protection"
Step 3: Re-test connectivity
Step 4: After completing the above steps, re-test connectivity;
```

---

## Reference Document Output Rules

After all abnormality solution outputs are complete, if there are reference documents, they are listed at the end uniformly (deduplicated and arranged in order of appearance). No additional "Step N" statement is appended (that statement is already built into the last step of each abnormality template).
