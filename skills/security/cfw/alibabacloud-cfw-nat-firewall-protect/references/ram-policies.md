# RAM Permission List

## Read Permissions

- `yundun-cloudfirewall:DescribeSecurityProxy` - Query NAT firewall list and protection status
- `yundun-cloudfirewall:DescribeNatFirewallList` - Query NAT firewall details incl. StrictMode (required by `update` built-in verification)
- `yundun-cloudfirewall:DescribeNatFirewallQuota` - Query NAT firewall authorization quota
- `yundun-cloudfirewall:DescribeNatFirewallPrecheckDetail` - Query NAT firewall pre-check results

## Write Permissions

- `yundun-cloudfirewall:SwitchSecurityProxy` - Enable/disable a NAT firewall protection switch
- `yundun-cloudfirewall:CreateNatFirewallPreCheck` - Trigger a NAT firewall creation pre-check
- `yundun-cloudfirewall:CreateSecurityProxy` - Create a NAT firewall
- `yundun-cloudfirewall:UpdateSecurityProxy` - Rename a NAT firewall / change engine strict mode

> **Deliberately NOT required: `yundun-cloudfirewall:DeleteSecurityProxy`.** This Skill never
> releases a NAT firewall (see SKILL.md section Stopping Protection). Leaving the permission ungranted is
> the strongest guarantee: even a hand-written CLI call would be rejected by RAM. Protection can
> still be switched off with `SwitchSecurityProxy`, which does not release anything. Grant the delete
> permission only to the human operators who release firewalls in the console.

## VPC Read Permissions (required by the `create` command's route auto-discovery)

- `vpc:DescribeRouteTableList` - List route tables of the VPC
- `vpc:DescribeRouteEntryList` - Find route entries whose next hop is the NAT gateway
- `vpc:DescribeVpcAttribute` - Read VPC CIDR (optional; powers the `create` CIDR pre-check, degrades gracefully if missing)
- `vpc:DescribeVpcs` - **Fallback for reading the VPC CIDR** when `DescribeVpcAttribute` is denied (the scripts retry with this API automatically). Grant BOTH: sub-accounts frequently hold only one of the two, and without either one the CIDR / free-/28 checks degrade to notes
- `vpc:DescribeVSwitches` - List/read vswitches (optional; powers the `create` CIDR overlap pre-check and the manual-mode vswitch pre-check, degrades gracefully if missing)
- `vpc:DescribeNatGateways` - Read NAT gateway zone and bound EIP count (optional; powers the manual-mode vswitch pre-check, `assess` and `prepare`, degrades gracefully if missing)
- `vpc:DescribeForwardTableEntries` - Count DNAT entries (optional; powers `assess` blocker detection, degrades to a note if missing)
- `vpc:DescribeSnatTableEntries` - Count SNAT entries (optional; powers the `assess` empty-SNAT-table blocker, degrades to a note if missing)

## ECS Read Permission (manual-mode vswitch occupancy check)

- `ecs:DescribeNetworkInterfaces` - Enumerate ENIs of a candidate diversion vswitch to enforce manual-mode constraint 6 ("no other cloud resources attached") in `assess` and `create` (optional; degrades to a human-checklist warning if missing)

## Quotas Center Read Permission (assess post-creation quota projection, REQUIRED)

- `quotas:GetProductQuota` - Resolve the account's REAL resource quotas used by the `assess` post-creation quota projection. NOTE: the real `QuotaActionCode` values are opaque `q_*` codes (verified 2026-08-14); the `*_quota_*` names below are the quota NAMES shown in the docs/console:
  - `vpc` / `q_e1mq5l` (`vpc_quota_route_tables_num`) - custom route tables per VPC (auto mode creates one)
  - `vpc` / `q_b7klmn` (`vpc_quota_vswitches_num`) - vswitches per VPC (auto mode creates one)
  - `vpc` / `q_62f05n` (`vpc_quota_vpn_custom_route_entry`) - VPN-pointing custom routes per VPC (the firewall diversion route table inherits them)
  - `nat` / `q_fwiygs` (`natgw_quota_snat_entry_num`) - SNAT entries per NAT gateway (creation adds one). Product code is `nat` (NOT `natgw`)
- `quotas:ListProductQuotas` - (recommended, troubleshooting) enumerate a product's quota items to re-discover the `q_*` action codes if Alibaba Cloud ever changes them

This permission is REQUIRED for a trustworthy `assess`: documentation default values are deliberately NOT assumed (customers may have raised their quotas, and guessing defaults produces false blockers). Without it the projection reports `status: unknown` and the report tells the user to grant this permission and re-run.

## Manual Mode Preparation Permissions (VPC Write)

Required only when preparing manual-mode diversion assets yourself or via `nat-fw-lifecycle.sh prepare` (create/diversion vswitch + NEW custom route table + binding). NOT needed for auto mode.

Required (prepare/create):

- `vpc:CreateVSwitch` - Create the dedicated diversion vswitch
- `vpc:CreateRouteTable` - Create the NEW custom route table (only when no reusable orphan custom route table exists)
- `vpc:AssociateRouteTable` - Bind the custom route table to the diversion vswitch

Recommended (cleanup of diversion assets after firewall deletion):

- `vpc:DeleteVSwitch` - Remove the diversion vswitch
- `vpc:DeleteRouteTable` - Remove the orphaned custom route table
- `vpc:UnassociateRouteTable` - Unbind the route table before deleting it

Probe before preparing (detects missing permissions in one shot, uses fake resource IDs, nothing is created):

```bash
bash scripts/validate-cli.sh --check-permission --mode manual [--region cn-hangzhou]
```

The probe classifies each action as `granted` / `missing` / `unknown` and reports `manual_mode_ready`. A `missing` result means the corresponding action in the lists above must be granted via RAM before running `prepare`.

## Notes

- The RAM Action prefix for Cloud Firewall is `yundun-cloudfirewall`, NOT `cloudfw`. Using the wrong prefix will cause the policy to not take effect, resulting in NoPermission / ImplicitDeny errors.
- For read-only access, grant only the `Describe*` permissions above. `assess` is fully read-only and works with read-only permissions (missing VPC reads degrade individual checks to notes).
- `CreateSecurityProxy` modifies VPC route tables and SNAT entries - restrict to operations administrators.
- If the identity lacks the two VPC read permissions, `create` can still work by passing `--route-entry-json` manually.
- In manual mode (`--vswitch-id`), if the identity lacks `vpc:DescribeVSwitches`/`vpc:DescribeNatGateways`, the vswitch pre-check degrades to a warning and the create API enforces the constraints server-side.
- Manual-mode constraint 5 (diversion route table must be freshly created - no default route, no business routes) and constraint 6 (no attached ENI) are enforced client-side only: without `vpc:DescribeRouteEntryList` / `ecs:DescribeNetworkInterfaces` they degrade to warnings, and the server does NOT re-check them.
- If the identity lacks `DescribeNatFirewallList`, `update` still executes but its built-in verification fails with `verify_api_failed` - use `--skip-verify` and confirm manually in that case.
- VPC write permissions are granted per-action: granting `vpc:CreateVSwitch` does NOT imply `vpc:CreateRouteTable`. When manual-mode creation fails with `Forbidden.RAM`, run the `--mode manual` probe above to list ALL missing actions at once instead of discovering them one by one.
