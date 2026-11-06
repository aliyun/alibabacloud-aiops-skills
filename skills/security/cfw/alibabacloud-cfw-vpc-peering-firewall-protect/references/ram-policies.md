# RAM Permission List

The RAM Action prefix for Cloud Firewall is `yundun-cloudfirewall`, NOT `cloudfw`.
Using the wrong prefix makes the policy silently ineffective (NoPermission / ImplicitDeny).

## Read Permissions (query / detail / assess / engine)

- `yundun-cloudfirewall:DescribeVpcFirewallList` - Query the VPC boundary firewall list, switch status, and the protectable peering pairs. Also the ONLY API that returns `AclConfig.StrictMode`, so the engine commands read the ACL engine mode here
- `yundun-cloudfirewall:DescribeVpcFirewallDetail` - Query one firewall's detail (local/peer VPC, ENI, router interface, protected route/CIDR tables); the authoritative source read back by `update`
- `yundun-cloudfirewall:DescribeVpcFirewallDefaultIpsConfig` - Read one firewall's IPS defense configuration (defense mode, rule group, basic rules, virtual patching). Optional: without it the engine command falls back to the `IpsConfig` block of `DescribeVpcFirewallList` and says so in `source_api`

## Write Permissions (switch / create / update)

- `yundun-cloudfirewall:ModifyVpcFirewallSwitchStatus` - Enable/disable a VPC boundary firewall switch (resource-level: `vpcfirewall/{#VpcFirewallId}`)
- `yundun-cloudfirewall:CreateVpcFirewallConfigure` - Create a VPC boundary firewall for a peering pair
- `yundun-cloudfirewall:ModifyVpcFirewallConfigure` - Rename a firewall / adjust the protected route (CIDR) tables

## Engine Write Permissions (IPS defense config / ACL engine mode)

- `yundun-cloudfirewall:ModifyVpcFirewallDefaultIpsConfig` - Change the IPS defense mode, rule group and the two capability switches of ONE VPC boundary firewall
- `yundun-cloudfirewall:ModifyVpcFirewallAclEngineMode` - Switch the ACL engine mode between strict and loose for ONE VPC boundary firewall

Both directly change protection strength, so grant them only to operations administrators. A caller
that holds only the read permissions still gets every read answer plus the impact preview and the
`--dry-run` command; the write itself then fails with `NoPermission`, which is the intended behaviour.

> **Deliberately NOT required: `yundun-cloudfirewall:DeleteVpcFirewallConfigure`.** This Skill never
> releases a VPC boundary firewall (see SKILL.md section Stopping Protection). Leaving the permission
> ungranted is the strongest guarantee: even a hand-written CLI call would be rejected by RAM.
> Protection can still be switched off with `ModifyVpcFirewallSwitchStatus`, which releases nothing.
> Grant the delete permission only to the human operators who release firewalls in the console.

## VPC Read Permissions (required by `create` / `assess` route auto-discovery)

- `vpc:DescribeRouteTableList` - List the route tables of a VPC
- `vpc:DescribeRouteEntryList` - Read route entries and keep the ones whose next hop is a peering / Express Connect interface (`VpcPeer` / `RouterInterface`)

These two power the automatic assembly of `LocalVpcCidrTableList` / `PeerVpcCidrTableList`. They are
READ-only - Cloud Firewall creates the diversion route entries and the `Cloud_Firewall_Security_Group`
itself, so no VPC write permission is needed by this Skill.

If either read permission is missing, `assess` degrades route discovery to a note and `create` requires
the explicit `--local-cidr-json` / `--peer-cidr-json` parameters instead of auto-discovering.

## Probe before create (detects missing read permissions in one shot)

```bash
bash scripts/validate-cli.sh --check-permission --mode create [--region cn-hangzhou]
```

The probe calls the VPC read APIs with fake but format-valid resource IDs (nothing is created) and
classifies each action as `granted` / `missing` / `unknown`, reporting `create_mode_ready`. A `missing`
result means the corresponding `vpc:Describe*` action above must be granted before route auto-discovery
will work.

## Notes

- For read-only access, grant only the three `yundun-cloudfirewall:Describe*` permissions plus the two
  `vpc:Describe*` permissions. `assess`, `query`, and both `vpc-fw-engine.sh` subcommands without a
  write flag are fully read-only.
- `CreateVpcFirewallConfigure` makes Cloud Firewall create route entries and a security group inside
  both VPCs - restrict to operations administrators.
- VPC firewall APIs are capped at 10 QPS per user; a `Throttling` error means wait and retry.
- When operating a member account's firewalls from a management account, every command accepts
  `--member-uid`; the same RAM actions apply on the management identity.
