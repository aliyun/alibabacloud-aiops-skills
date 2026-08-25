# NAT Firewall Prerequisites & Business Impact

Source: official documentation "Managing traffic security for private-to-internet outbound access of NAT gateways" (Cloud Firewall user guide).

## Prerequisites for Creating a NAT Firewall

Before creating a NAT firewall, the target public NAT gateway must satisfy ALL of the following:

1. **Cloud Firewall service is activated** and enough NAT firewall authorizations are purchased (`nat-fw-lifecycle.sh quota`: `UsedCount` must be below `TotalCount`).
2. **Public NAT gateway only** - enhanced private NAT gateways are not supported.
3. **Region is supported** by NAT firewall.
4. **EIP count within the range Cloud Firewall supports** (at least 1). The CFW-side supported bound-EIP count defaults to **20**. A user hitting this pre-check failure has ALREADY raised the NAT gateway's own binding quota (`natgw_quota_eip_num_per_nat`, Quotas Center `nat/q_gh61qw`) - do NOT advise raising the NAT gateway quota again, and NEVER advise unbinding. Reply: submit a ticket to the **Cloud Firewall side**, or contact PDSA for whitelisting evaluation to lift the CFW-side supported EIP count.
5. **SNAT entries configured, and NO DNAT entries** - if DNAT entries exist, they must be deleted first. (The server pre-check item uses a negative-style state description; when presenting to users, rephrase it as the requirement: the NAT gateway must have NO DNAT entries - DNAT entries are mutually exclusive with a NAT firewall and must be deleted first.)
6. **The VPC has a route entry `0.0.0.0/0` pointing to this NAT gateway** (this is what the `create` command auto-discovers as `NatRouteEntryList`).
7. **Diversion vswitch available** - auto mode: the VPC can allocate at least a /28 subnet (VPC secondary CIDR is supported); manual mode: an existing vswitch satisfying the manual-mode constraints below.
8. New NAT gateways take **1~5 minutes** to sync into Cloud Firewall (EIPs/SNAT entries 1~2 minutes, routes up to 30 minutes). If pre-check reports the gateway is not found, trigger "Asset Sync" in the console and retry.

Run `nat-fw-lifecycle.sh precheck` to verify these automatically (console equivalent: the one-click enablement check).

## Traffic Diversion Mode

Run `nat-fw-lifecycle.sh assess --region <id>` first: it inventories all unprotected NAT gateways, analyzes each VPC (free /28 CIDRs, existing vswitches, custom route tables), and recommends the mode below per gateway - including a suggested `--vswitch-cidr` (auto) or `--vswitch-id` (manual).

### Auto mode (`--vswitch-cidr`, `VswitchAuto=true`, recommended)

Cloud Firewall automatically creates the diversion vswitch, the custom route table `Cloud_Firewall_ROUTE_TABLE`, SNAT entries, and switches the system route table. Suitable when the VPC has spare address space. The auto-created vswitch is reclaimed when the firewall is deleted.

### Manual mode (`--vswitch-id`, `VswitchAuto=false`)

Reuses an EXISTING vswitch. Suitable when the VPC has no spare address space. Officially flagged as expert-only (more steps, network knowledge required), so the skill enforces a pre-check + human checklist before calling the API.

**Hard constraints (the create pre-check enforces 1~6 automatically):**

1. The vswitch, the NAT gateway, and the NAT firewall must be in the **same VPC**.
2. The vswitch and the NAT gateway must be in the **same availability zone** (NAT gateway zone read from `DescribeNatGateways` -> `NatGatewayPrivateInfo.IzNo`).
3. The vswitch CIDR prefix must be **/28 or larger network** (e.g. /28, /24).
4. The vswitch **available IP count must exceed the number of EIPs** bound to the NAT gateway (each EIP maps to one egress ENI inside the vswitch).
5. The vswitch must be bound to a **custom** route table that is **newly created for this firewall**:
   - **no `0.0.0.0/0` entry** (the server injects its own default route; a pre-existing one is rejected), and
   - **no business routes**. The only pre-existing entries tolerated are the cross-VPC **return routes** of human step 2 below, i.e. next hops of type `VpcPeer` / `VpnGateway` / `RouterInterface` / `VBR` / `Attachment` / `TunnelInterface`. Any other next hop (`Instance`, `NetworkInterface`, `HaVip`, another `NatGateway` ...) means the table is a production table: `assess` drops the candidate and `create` refuses, because all diverted traffic is forwarded by this table and inheriting business routes would reroute live traffic.
   - A table carrying return routes only is accepted but reported as `route_table_clean: no` - confirm the entries are intended before creating.
6. The vswitch must have **no other cloud resources attached** - verified automatically by enumerating ENIs (`ecs:DescribeNetworkInterfaces`); degrades to a human-checklist warning when that permission is missing. Non-ENI occupants (e.g. SLB) still require human confirmation.

**Mandatory human steps BEFORE creation:**

1. Create a NEW custom route table and bind it to the chosen vswitch. (If the console option is greyed out: the vswitch already has resources attached, or it is already bound to a custom route table.)
2. (Optional) For cross-VPC protected traffic, add the VPC return routes into that new route table.

**Differences after creation:**

- The manual vswitch stays a user asset - deleting the NAT firewall does **NOT** delete the vswitch (unlike auto mode).
- Do NOT modify the diversion routes or the SNAT entries Cloud Firewall creates in that route table.

## Business Impact

| Operation | Impact |
|---|---|
| Create NAT firewall (switch stays closed) | No business impact. Duration about 2~5 minutes per bound EIP |
| Create + immediately enable | 1~2 second interruption of long-lived connections during route switching (short connections unaffected) |
| Enable / Disable switch | 1~2 second interruption of long-lived connections (NAT route switching). Do it during off-peak hours. **Disable keeps the firewall instance, its authorization quota and its diversion assets** - it can be re-enabled anytime |
| Delete a closed NAT firewall (console only - this Skill never deletes) | No business impact. Releases the authorization; auto-mode diversion vswitch is reclaimed |
| Delete an enabled NAT firewall (console only) | Close + delete happen together -> 1~2 second interruption of long-lived connections. Closing first is safer |
| CFW instance expires without renewal | NAT firewall is auto-released and routes switch back to the original path - may cause brief interruption |

## Usage Limits (after creation)

- Do NOT modify routes of the firewall diversion vswitch, or routes whose next hop is the NAT firewall - traffic may be interrupted.
- Do NOT delete or modify the SNAT entries created by Cloud Firewall (count equals the number of bound EIPs).
- To add cross-VPC protected CIDRs later, manually update the route table of the firewall diversion vswitch (and preferably the original route table too, to avoid missing routes after closing).
- NAT firewall does **not** protect IPv6 traffic and does **not** provide IPS capabilities.
- If the VPC contains ACK clusters using the Flannel network plugin, configure Cloud Controller Manager multi-route-table support after creation, or node scaling may be affected.
- Traffic exceeding the purchased CFW processing spec may trigger degradation rules (ACL/IPS/log becoming ineffective, top over-quota assets being closed, rate limiting).
- Firewalls created before 2023-09-01 have a 20 Mbps per-destination-tuple bandwidth cap; recreate to remove the limit.

## Engine (Strict) Mode

- **Loose mode (`StrictMode=0`, default)**: ACL policies for applications/domains let unrecognized traffic pass - availability first.
- **Strict mode (`StrictMode=1`)**: unrecognized traffic continues to subsequent policies; if a deny rule matches, it is blocked.

Change the mode any time with `nat-fw-lifecycle.sh update --proxy-id <id> --proxy-name <current-name> --strict-mode 0|1`.
