# CLB (Classic Load Balancer) Diagnosis Guide

## Query Flow

1. Call `DescribeLoadBalancerAttribute` to query instance attributes. Parse all listeners from `ListenerPortsAndProtocol` / `ListenerPortsAndProtocal`, generating listener identifiers (`Protocol_Port`, e.g. `TCP_443`). Also obtain the instance-level default backend server list (`BackendServers`).
   > Some STS roles lack `DescribeLoadBalancerListeners` permission, so the script prioritizes parsing the listener list from `DescribeLoadBalancerAttribute`.

2. Call the corresponding API by protocol to get listener detailed attributes (including health check config), and **identify the backend type associated with each listener**:
   - TCP listener: `DescribeLoadBalancerTCPListenerAttribute`
   - UDP listener: `DescribeLoadBalancerUDPListenerAttribute`
   - HTTP listener: `DescribeLoadBalancerHTTPListenerAttribute`
   - HTTPS listener: `DescribeLoadBalancerHTTPSListenerAttribute`

   **CLB Backend Three Association Modes** (determined by priority):
   - Returns `VServerGroupId` → **VServer Group**
   - Returns `MasterSlaveServerGroupId` → **Master/Slave Server Group**
   - Neither → **Default Server Group** (uses instance-level default backend servers)

3. For each listener, call `DescribeRules` to query all forwarding rules, collect:
   - `RuleId` / `RuleName` / `Domain` / `Url`
   - Rule-associated server group `VServerGroupId`
   - Rule's own health check config (when `ListenerSync=on`, usually inherits listener config)

4. Aggregate all server groups, **distinguishing VServer groups from Master/Slave groups**:
   - VServer Group: Call `DescribeVServerGroupAttribute` to query backend server list
   - Master/Slave Group: Call `DescribeMasterSlaveServerGroupAttribute` to query Master/Slave backend list

5. Attempt to call `DescribeHealthStatus` to get health status for **all** backends under the listener (including backends in server groups referenced by rules). If the STS role lacks permission for this API, catch the 403 and note "unable to retrieve probe results" in the report.

   **Key**: Backends returned by `DescribeHealthStatus` must be precisely attributed to their actual server groups based on ServerId + Port (by matching `servers_by_group`), not all lumped into the listener's direct server group.

## Health Check Config Display Rules

CLB health check config is attached to **listeners** or **forwarding rules**. The same server group may be reused by multiple listeners/rules. Therefore, the "Server Group Health Check Config" table displays multiple rows by **config source**:

- Each associated listener's config gets its own row (Source = Listener, Source ID = Protocol_Port).
- Only when a forwarding rule has its own independent health check config, add a new row (Source = Rule, Source ID = RuleId). Rules with `ListenerSync=on` inherit listener config and are marked as "Rule (inherited from listener)".
- Listeners using the default server group (instance default backends) are also merged into this table.

## Backend Health Status Translation Rules

CLB `DescribeHealthStatus` returns only two states, translated as:
- `normal` → Normal (health check passed)
- `abnormal` → Abnormal (health check failed)

## Table Aggregation Rules

- **Listener and Server Group Association Table**: Merged into one table. Each row shows the listener/rule, its associated server group, server group type (VServer Group / Master/Slave Group / Default Server Group), and backend server count. CLB server groups have no protocol attribute, so the protocol column is not displayed.
- **Health Check Config Table**: CLB also merges health check config for default server group listeners into this table. The first column "Target / Server Group ID" shows `Default Server Group` for the default server group scenario. Adds "Config Source" and "Source ID" columns.
- **Backend Server and Health Check Probe Table** (merged table): CLB merges the backend server list with `DescribeHealthStatus` probe results into one table. Primary key = Listener ID × Server Group ID × Server ID × Port. Grouped by listener; same Listener ID shown only in the first row; same Server Group ID within the same listener shown only in the first row, subsequent rows left blank. Backends must be precisely attributed to their actual server group based on ServerId + Port. The default server group is included in the same table with a "Default Server Group" label (port taken from listener `BackendServerPort`).
- **Default Server Group**: CLB listeners may not be associated with a VServerGroup/MasterSlaveServerGroup, using instance default backend servers instead. Health check config is merged into the "Health Check Config" table.

> ⛔ **Do NOT output a "Conclusions and Recommendations" section**: The md file must not include a "Conclusions and Recommendations / Listener Level / Server Group Level / Server Level / Forwarding Rule Level / Overall Recommendations" section. Tables already express abnormal facts (probe status / anomaly reason codes / anomaly descriptions). Anomaly remediation guidance is handled by the "Customer-Facing Script". If the script stdout contains such a section, it must be proactively removed.

- **CLB Listener Identifier**: CLB listeners have no independent ListenerId. Use `Protocol_Port` as the listener identifier.
- **CLB Server Group Types**: Three types — VServer Group (VServerGroupId), Master/Slave Group (MasterSlaveServerGroupId), Default Server Group (neither present).

> Note: CLB health check config is attached to listeners or forwarding rules. When a rule has its own health check config, the rule config takes precedence; when not configured, it inherits listener config, and the "Config Source" column shows "Rule (inherited from listener)". The "Default Server Group" column identifies whether the server group is the default for its parent listener.

## Customer-Facing Script Template

The common skeleton (opening paragraph, five-step commands, all-normal scenario) is in the SKILL.md section [Customer-Facing Script Template](../SKILL.md#customer-facing-script-template). The key difference between CLB and ALB/NLB is that CLB groups by **listener/forwarding rule** as the primary entity, not by backend server.

### CLB Grouping Structure

```markdown
## Customer-Facing Script

Hello, instance `{Instance ID}` currently has {M} entry points (listeners/forwarding rules) where backend server health checks are failing and have been isolated by CLB from receiving traffic. Please log into the corresponding ECS for each entry point below to troubleshoot:

---

### ① Listener {Protocol:Port}{(default action, VServer Group `{VServerGroupID}` | Default Server Group)}

Health check config: protocol {HTTP|HTTPS|TCP|UDP}{(for HTTP/HTTPS append: path `{Path}`, method {Method}, normal status codes `{StatusCodes}`)}, probe port = {Port or "backend port X" if health check port is 0}.

**Server `{ECS Instance ID}` ({ECS Private IP}:{Port})**

(Follow the five-step commands of [Customer-Facing Script Template](../SKILL.md#customer-facing-script-template); replace capture command per CLB-specific rules below)

---

### ② Listener {Protocol:Port} Forwarding Rule `{RuleID}` (VServer Group `{VServerGroupID}`)

(Same structure as above; health check config based on rule or inherited from listener)

---

### ③ Listener {Protocol:Port} Forwarding Rule `{RuleID2}` (VServer Group `{VServerGroupID2}`)

> Backends in this group are identical to ① (`{ECS Instance ID}:{Port}`), and health check config and probe port are the same. Troubleshooting results from ① apply directly to this entry point — no need to repeat.
```

### CLB-Specific Rules

- **Entry Point Deduplication**: When the same ECS+Port+health check config is referenced by multiple entry points, subsequent entries only write `> Backends in this group are identical to ①. Troubleshooting results from ① apply directly to this entry point — no need to repeat.` without repeating commands.
- **Never Include Security Group Step**: CLB health checks use an internal dedicated line and are not controlled by ECS security groups. The script must never include the step "allow 100.64.0.0/10 in security group to TCP:xx". The security-group step condition of [Customer-Facing Script Template](../SKILL.md#customer-facing-script-template) is skipped entirely for CLB scenarios.
- **tcpdump Filter Expression**: `tcpdump -i eth0 {tcp|udp} port {Port} and src net 100.64.0.0/10 -nn -c 20` — use `src net 100.64.0.0/10` to precisely filter CLB probe packets, replacing the host filter from the [Customer-Facing Script Template](../SKILL.md#customer-facing-script-template) common skeleton.
- **Probe Status Only Has abnormal**: CLB has no unavailable status.

## Diagnosis Script

```bash
# Default Markdown report output
python3 scripts/diagnose_clb.py --load-balancer-id <Instance ID> --region <RegionId>

# Structured JSON output
python3 scripts/diagnose_clb.py --load-balancer-id <Instance ID> --region <RegionId> --format json
```
