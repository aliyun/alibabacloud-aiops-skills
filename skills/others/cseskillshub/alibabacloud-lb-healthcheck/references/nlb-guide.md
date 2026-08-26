# NLB (Network Load Balancer) Diagnosis Guide

## Query Flow

1. Call `ListListeners` to query all listeners under the instance, collect:
   - `ListenerId` / `ListenerProtocol` / `ListenerPort`
   - Associated server group `ServerGroupId`

2. Call `GetListenerHealthStatus` (recommended to include `IncludeRule=true` parameter, consistent with ALB) to query listener health check status and abnormal backend server info (`NonNormalServers`).

3. Call `ListServerGroups` to query server group detailed health check config (`HealthCheck`), protocol, and server group name `ServerGroupName`.

4. Call `ListServerGroupServers` to query backend server list within each server group (including `ServerId` / `ServerIp` / `Port` / `ServerType` / `Weight` / `Status`).

> Note: NLB listeners are directly associated with server groups — there are no forwarding rules. Therefore, the report does not need a "Forwarding Rule Match Conditions" section.

## Backend Status Translation Rules

The `Status` returned by NLB `ListServerGroupServers` is the backend's **management status**. **It does not represent health check probe results.** The two must be strictly distinguished:

**Backend Server Status Table (ListServerGroupServers → Status)**:
- `Available` → Available (joined server group)
- `Unavailable` → Unavailable (removed or misconfigured)
- `Initial` / `Configuring` → Initializing
- `Removing` → Removing

**Listener Health Check Probe Results Table (GetListenerHealthStatus → NonNormalServers)**:
- Not appearing in NonNormalServers list → Normal (health check passed)
- Appearing in NonNormalServers list → Abnormal (health check failed), must include ReasonCode

## Table Aggregation Rules

- **Listener Info Table**: One row per listener, showing Listener ID, Protocol, Port, Default Server Group ID. NLB has no forwarding rules, so the Forwarding Rule Count column is `-`.
- **All Server Groups Summary Table**: Aggregate by server group. The "Owner Listener/Rule" column is grouped by listener. When the same server group is referenced by multiple listeners in NLB, use `<br>` for multi-line display.
- **Server Group Health Check Config Table**: Aggregate by server group, displaying health check config fields (Protocol/Path/Port/Interval/Timeout/Threshold/Method/Status Codes). For TCP protocol, Path/HTTP Method/Normal Status Codes show as `-`.
- **Backend Server Status Table**: Display grouped by server group, each row shows the parent server group ID.
- **Listener Health Check Probe Results Table**: Aggregate by (Listener ID, Server Group ID). When `NonNormalServers` is empty, display the entire group in one row with note "Enabled, no abnormal backends".

> ⛔ **Do NOT output a "Conclusions and Recommendations" section**: The md file must not include a "Conclusions and Recommendations / Listener Level / Server Group Level / Server Level / Overall Recommendations" section. Tables already express abnormal facts (probe status / anomaly descriptions). Anomaly remediation guidance is handled by the "Customer-Facing Script". If the script stdout contains such a section, it must be proactively removed.

## Customer-Facing Script Template

The common skeleton (opening paragraph, five-step commands, all-normal scenario) is in the SKILL.md section [Customer-Facing Script Template](../SKILL.md#customer-facing-script-template). For NLB, each abnormal backend server self-check block's title and parameters are filled as follows:

**Block Title**: `**① \`{ECS Instance ID}\` ({ECS Private IP}, belongs to server group \`{Server Group ID}\`, matched listener {Protocol:Port})**` — note NLB has no forwarding rules, so the title only shows "matched listener".

**Block Config Line**: `Current config: health check protocol {HTTP|HTTPS|TCP|UDP}{(for HTTP/HTTPS append: , path \`{Path}\`, method {Method}, normal status codes \`{StatusCodes}\`)}, probe port = {Port or "backend port X" if health check port is 0}.`

### NLB-Specific Rules

- **Security Group Step Condition**: When backend ServerType=Ecs/Eni and in the same VPC as NLB, do not include the security group step (probes reach backend ENI directly). Only when ServerType=Ip (cross-VPC), append one step: confirm security group inbound rules allow `{associated vSwitch CIDR list}` to {TCP|UDP}:{Port}.
- **tcpdump Filter Expression**: `tcpdump -i eth0 '{tcp|udp} port {Port} and (host {HealthCheckSourceIPs joined with or})' -nn -c 20` — must use single quotes + parentheses to avoid and/or precedence errors. The host set must **only use Ipv4LocalAddresses** (probe sources); PrivateIPv4Address (frontend VIP) is forbidden.
- **Host Firewall Allow Recommendation**: Allow the entire NLB vSwitch CIDR block (e.g. `172.22.0.0/24`), do not enumerate current probe IPs to prevent rules from becoming stale after NLB scale-out.

## Diagnosis Script

```bash
# Default Markdown report output
python3 scripts/diagnose_nlb.py --load-balancer-id <Instance ID> --region <RegionId>

# Structured JSON output
python3 scripts/diagnose_nlb.py --load-balancer-id <Instance ID> --region <RegionId> --format json
```

### Script Output JSON Top-Level Fields

`diagnose_nlb.py` output JSON top-level contains the following network info fields, which can be referenced directly without re-calling APIs:
- `VpcId` — VPC where the instance resides
- `VSwitchCIDRs` — List of CIDR blocks for NLB-associated vSwitches
- `HealthCheckSourceIPs` — Health check probe source IP list (only contains `Ipv4LocalAddresses`, i.e. ENI secondary IPs)
- `ZoneMappings` — Zone mappings (including vSwitchId, `Ipv4LocalAddresses` and `PrivateIPv4Address` raw fields; CIDR info is in the `VSwitchCIDRs` field)

### NLB Probe Source IP Extraction Rules (Important)

- `ZoneMappings[].LoadBalancerAddresses[].Ipv4LocalAddresses[]` → **Health check probe source IPs** (secondary IPs on the ENI, typically 2 per ENI).
- `ZoneMappings[].LoadBalancerAddresses[].PrivateIPv4Address` → **Frontend business VIP** (client access entry). **Not** a probe source. Must not be written to the "Health Check Probe Source IP" line, and must not appear in the customer-facing script's tcpdump host filter parameter.
- When generating the customer-facing script's packet capture command, the `host` filter must only use the `Ipv4LocalAddresses` set.
- Backend host firewall allow recommendation: allow the entire NLB vSwitch CIDR block (e.g. `172.22.0.0/24`), do not enumerate current probe IPs to prevent rules from becoming stale after NLB scale-out.
