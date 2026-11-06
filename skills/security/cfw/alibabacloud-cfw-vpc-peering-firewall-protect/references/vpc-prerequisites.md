# VPC Boundary Firewall Prerequisites & Business Impact (Express Connect / Peering)

Source: the official Cloud Firewall user guide "Protect access traffic between network instances
connected through VPC peering" (original title: `防护通过VPC对等连接连接的网络实例之间的访问流量`).

## What this firewall protects

The VPC boundary firewall for a peering pair protects the **east-west traffic between two VPCs
connected by Express Connect (`高速通道`, `ConnectSubType=vpc2vpc`) or a VPC peering connection
(`对等连接`, `ConnectSubType=vpcpeer`)**. It does NOT protect:

- IPv6 traffic
- Traffic to the cloud-service CIDR `100.64.0.0/10` (not diverted)
- Cross-region or cross-account traffic, and VPC-to-VBR traffic (out of scope for the peering family)
- CEN-based interconnect traffic (a different API family, out of scope for this skill)

## Prerequisites for creating a VPC boundary firewall

Before creating, the peering pair must satisfy ALL of the following:

1. **Cloud Firewall Enterprise / Ultimate / pay-as-you-go edition is active.** The Advanced edition does
   not support the transit-router VPC firewall; peering-based VPC firewalls require one of the supported
   editions.
2. **Cloud Firewall is authorized to access the cloud resources** of BOTH VPCs (`AuthorizationStatus =
   authorized`). If not, the list entry carries `ResultCode = Unauthorized`.
3. **A peering instance is purchased and the two VPCs are already interconnected** (Express Connect or a
   VPC peering connection with working routes between them).
4. **Both VPC regions support the VPC boundary firewall** (`RegionStatus = enable`). An unsupported region
   yields `ResultCode = RegionDisable`.
5. **Each VPC has at least one route entry pointing at the peering / Express Connect next hop**
   (`NextHopType = VpcPeer` or `RouterInterface`). These are the routes the firewall diverts; they are
   auto-discovered into `LocalVpcCidrTableList` / `PeerVpcCidrTableList`.
6. **No protected route uses a `/32` mask.** A `/32` route is not diverted and, once the firewall is
   enabled, access to that CIDR is interrupted. Change the mask to `<= /30` first.

New peering assets may take a few minutes to appear; if the pair is missing from the list, click
`同步资产` in the console (`开关 -> VPC边界防火墙 -> 对等连接`) and retry.

## Business impact

| Operation | Impact |
|---|---|
| Create the firewall (switch stays closed) | No business impact. Duration ~ 5 minutes. No topology change is required |
| Create + immediately open (`--firewall-switch open`) | Opening re-learns routes: 5~30 minutes, with a second-level flap of long-lived connections |
| Enable / Disable the switch | 5~30 minutes of route re-learning (depends on the route entry count); long-lived connections flap for a few seconds, short connections are unaffected. Do it during off-peak hours |
| Delete a closed firewall (console only - this skill never deletes) | May flap traffic during deletion; releases the quota |
| Delete an enabled firewall (console only) | Close + delete happen together -> traffic flap. Close first, then delete |

> **Recommendation:** check that your applications support TCP auto-retransmission before enabling, and
> watch connection state during the switch, to avoid drops for apps without retransmission.

## Route learning after creation

- After the firewall is enabled, if you add or remove VPC route table entries, Cloud Firewall needs
  **15~30 minutes** to finish route learning. Wait for it to complete before judging whether routes took
  effect.
- The enable process does **not** support rollback or pause; if an exception occurs the system rolls back
  automatically.
- After creation, Cloud Firewall auto-creates inside your VPCs:
  - custom route table entries, remarked `Created by cloud firewall. Do not modify or delete it.`
  - a security group named `Cloud_Firewall_Security_Group` with an allow policy that lets traffic reach
    the firewall. **Do not delete this security group or its allow policy** - doing so stops traffic from
    flowing into the firewall.
- Do NOT change the vswitch or route tables Cloud Firewall created for the firewall; doing so may
  interrupt traffic.

## The two CIDR table lists (creation / update input)

`LocalVpcCidrTableList` and `PeerVpcCidrTableList` are JSON arrays describing which route tables and
target CIDRs to protect on each side. Shape:

```json
[{"RouteTableId":"vtb-example0001","RouteEntryList":[{"DestinationCidr":"192.168.0.0/24","NextHopInstanceId":"vrt-example0001"}]}]
```

- `RouteTableId` - a route table of that VPC.
- `RouteEntryList[].DestinationCidr` - the target network segment to protect.
- `RouteEntryList[].NextHopInstanceId` - the next hop of that route (the peering / router interface ID).

The `create` command builds both lists automatically from the VPC route entries whose next hop is a
peering / Express Connect interface. Pass `--local-cidr-json` / `--peer-cidr-json` to override, or when
the VPC read permissions for auto-discovery are missing.

## IPS / ACL engine mode

IPS defense mode, the IPS rule group, the two IPS capabilities (basic rules / virtual patching) and the
ACL engine mode of a VPC boundary firewall are NOT parameters of `CreateVpcFirewallConfigure` /
`ModifyVpcFirewallConfigure`. They live behind their own per-firewall APIs and are handled by
`scripts/vpc-fw-engine.sh` (console equivalent: `配置IPS` and `访问控制 -> 引擎模式`).

| Setting | Write API | Field | Values |
|---|---|---|---|
| IPS defense mode | `ModifyVpcFirewallDefaultIpsConfig` | `RunMode` | `0` observe, `1` block |
| IPS rule group | `ModifyVpcFirewallDefaultIpsConfig` | `RuleClass` | `1` loose, `2` medium, `3` strict; `0` means not applicable (observe mode) |
| Basic rules | `ModifyVpcFirewallDefaultIpsConfig` | `BasicRules` | `0` off, `1` on |
| Virtual patching | `ModifyVpcFirewallDefaultIpsConfig` | `EnableAllPatch` | `0` off, `1` on |
| ACL engine mode | `ModifyVpcFirewallAclEngineMode` | `StrictMode` | `0` loose, `1` strict |

Constraints verified against the live API:

1. **`RunMode`, `BasicRules` and `EnableAllPatch` are REQUIRED on the modify call**; `RuleClass` is
   optional. Omitting a required one is a CLI error rather than a preserved value, so a partial change
   must read the current values first and pass the untouched fields through. The script does this
   automatically from one read-only call.
2. **`RuleClass` is coupled to `RunMode` by the service, which does not simply store what you send.**
   Measured live with five probes: in observe mode (`RunMode=0`) the stored `RuleClass` is always `0`
   ("not applicable") whatever value was passed; in block mode (`RunMode=1`) an omitted `--rule-class`
   preserves the current group, while an explicit `0` is normalized to `3` (strict). Sending a
   `RuleClass` echoed from a stale read-back can therefore move the rule group silently. The script
   sends the flag only when the caller passed it, derives the expected stored value from this coupling
   for its read-back verification, and flags `rule_class_derived_by_service` when the two differ.
3. **The ACL engine mode has no dedicated read API.** `AclConfig.StrictMode` comes from
   `DescribeVpcFirewallList`; `DescribeVpcFirewallDetail` omits `AclConfig` entirely.
4. **A `notconfigured` firewall has no engine instance.** Both write APIs (and the dedicated IPS read)
   reject its ID with `ErrorParametersFirewallId`. Create and open the firewall first.
5. **Both modify APIs return only a `RequestId`**, so success is proven by reading the value back.
6. **Strict mode is the stronger setting.** In loose mode, traffic from unrecognized applications or
   domains is allowed without further policy matching, so deny policies aimed at unknown traffic stop
   applying. Moving from strict to loose is a protection downgrade and must be disclosed to the user.
7. **`configuring` is a real transitional `FirewallSwitchStatus`**, seen for a minute or two after
   `CreateVpcFirewallConfigure` returns and before the first `closed`. It is undocumented; a poll loop
   that only accepts `opened` / `closed` would treat it as invalid and give up.
