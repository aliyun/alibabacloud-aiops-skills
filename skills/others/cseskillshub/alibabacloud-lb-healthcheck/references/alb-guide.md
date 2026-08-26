# ALB (Application Load Balancer) Diagnosis Guide

## Query Flow

1. Call `ListListeners` to query all listeners under the instance, collect:
   - `ListenerId` / `ListenerProtocol` / `ListenerPort`
   - Listener default action `DefaultActions` (containing default `ServerGroupId`)

2. Call `GetListenerHealthStatus` (**must include `IncludeRule=true` parameter**, otherwise probe results for server groups associated with forwarding rules will be lost) to query listener health status and abnormal servers (`NonNormalServers`).

3. For each listener, call `ListRules` to query all forwarding rules, **must** collect:
   - `RuleId` / `RuleName` / `Priority` / `Direction` (Request / Response)
   - **Complete match conditions** `RuleConditions`: Host / Path / Method / QueryString / Header / Cookie / SourceIp / ResponseStatusCode / ResponseHeader
   - **Complete action list** `RuleActions`, categorized by `Type`:
     - `ForwardGroup` → extract server group IDs and weights from `ForwardGroupConfig.ServerGroupTuples`
     - `Redirect` → extract `RedirectConfig` (Protocol/Host/Port/Path/Query/HttpCode)
     - `FixedResponse` → extract `FixedResponseConfig` (HttpCode/ContentType/Content)
     - `InsertHeader` / `RemoveHeader` → extract header config (Key/Value/ValueType/CoverEnabled)
     - `Rewrite` / `TrafficLimit` / `TrafficMirror` / `Cors` and other action types — extract key fields as needed

4. Aggregate all server groups that appear under the instance (listener default actions + all forwarding rule ForwardGroup actions), and build `ServerGroupOwnership` mapping: `{ServerGroupId: {ListenerId: [RuleId list]}}`.

5. Call `ListServerGroups` to query health check config (`HealthCheckConfig`), protocol, and server group name `ServerGroupName` for all server groups.

6. For each server group, call `ListServerGroupServers` to query backend servers in the group (including `ServerId` / `ServerIp` / `Port` / `ServerType` / `Weight` / `Status`).

## Backend Status Translation Rules

The `Status` returned by ALB `ListServerGroupServers` is the backend's **management status** (whether it has joined the server group and has valid configuration). **It does not represent health check probe results.** Actual health check probe results come from `GetListenerHealthStatus`. The two must be strictly distinguished — do not mix them:

**Backend Server Status Table (ListServerGroupServers → Status)**:
- `Available` → Available (joined server group)
- `Unavailable` → Unavailable (removed or misconfigured)
- `Initial` / `Configuring` → Initializing
- `Removing` → Removing

**Listener Health Check Probe Results Table (GetListenerHealthStatus → NonNormalServers)**:
- Not appearing in NonNormalServers list → Normal (health check passed)
- Appearing in NonNormalServers list → Abnormal (health check failed), must include ReasonCode

## Table Aggregation Rules

- **All Server Groups Summary Table**: Aggregate by server group. The "Owner Listener/Rule" column is grouped by listener, with rules indented under their parent listener. When the same server group is referenced by multiple listeners/rules, use `<br>` for multi-line display and indent rules with `&nbsp;&nbsp;`. **Each listener/rule entry must include the parent listener's protocol+port** (e.g. `Listener lsn-xxx (HTTP:80)`, `Rule rule-yyy (HTTP:80)`) for easy traffic entry identification. When referenced by a listener's default action, append ", default" marker.
- **Server Group Health Check Config Table**: Aggregate by server group, displaying health check config fields (Protocol/Path/Port/Interval/Timeout/Threshold/Method/Status Codes).
- **Backend Server Status Table**: Display grouped by server group, each row shows the parent server group ID.
- **Health Check Probe Results Table**: Aggregate by (Listener ID, Server Group ID), showing each backend's probe status and abnormal reason codes. When `NonNormalServers` is empty, mark the entire group as "Normal".

> ⛔ **Do NOT output a "Conclusions and Recommendations" section**: The md file must not include a "Conclusions and Recommendations / Listener Level / Server Group Level / Server Level / Forwarding Rule Level / Overall Recommendations" section. Tables already express abnormal facts (probe status / anomaly descriptions). Anomaly remediation guidance is handled by the "Customer-Facing Script". If the script stdout contains such a section, it must be proactively removed.

## Customer-Facing Script Template

The common skeleton (opening paragraph, five-step commands, all-normal scenario) is in the SKILL.md section [Customer-Facing Script Template](../SKILL.md#customer-facing-script-template). For ALB, each abnormal backend server self-check block's title and parameters are filled as follows:

**Block Title**: `**① \`{ECS Instance ID}\` ({ECS Private IP}, belongs to server group \`{Server Group ID}\`, matched listener {Protocol:Port}{ forwarding rule rule-xxx | default action})**`

**Block Config Line**: `Current config: health check protocol {HTTP|HTTPS|TCP|UDP}{(for HTTP/HTTPS append: , path \`{Path}\`, method {Method}, normal status codes \`{StatusCodes}\`))}, probe port = {Port or "backend port X" if health check port is 0}.`

### ALB-Specific Rules

- **Security Group Step Condition**: When backend ServerType=Ecs/Eni and in the same VPC as ALB, do not include the security group step (probes reach backend ENI directly). Only when ServerType=Ip (cross-VPC), append one step: confirm security group inbound rules allow `{associated vSwitch CIDR list}` to {TCP|UDP}:{Port}.
- **tcpdump Filter Expression**: `tcpdump -i eth0 '{tcp|udp} port {Port} and (host {HealthCheckSourceIPs joined with or})' -nn -c 20` — must use single quotes + parentheses to avoid and/or precedence errors.

## Diagnosis Script

```bash
# Default Markdown report output
python3 scripts/diagnose_alb.py --load-balancer-id <Instance ID> --region <RegionId>

# Structured JSON output
python3 scripts/diagnose_alb.py --load-balancer-id <Instance ID> --region <RegionId> --format json
```

### Script Output JSON Top-Level Fields

`diagnose_alb.py` output JSON top-level contains the following network info fields, which can be referenced directly without re-calling APIs:
- `VpcId` — VPC where the instance resides
- `VSwitchCIDRs` — List of CIDR blocks for ALB-associated vSwitches
- `HealthCheckSourceIPs` — Health check probe source IP list
- `ZoneMappings` — Zone mappings (including vSwitchId, VIP addresses; CIDR info is in the `VSwitchCIDRs` field)
