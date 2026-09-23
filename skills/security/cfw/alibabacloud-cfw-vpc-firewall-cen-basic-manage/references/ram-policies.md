# RAM Permission List

The RAM code (`RamCode`) for Cloud Firewall is **`yundun-cloudfirewall`**, not
`cloudfw`. Confirmed against the official permission list for Cloudfw
2017-12-07, which is also the source of the access levels and resource ARNs
below.

Every action listed here is reachable from this Skill's documented workflow, so this
file is the minimum grant set and nothing more. Diagnostic actions an operator might
run by hand are deliberately absent: keeping them out is what lets this list double as
the coverage baseline for the test cases without the two disagreeing.

## Read Permissions

| Action | Access level | Resource |
|---|---|---|
| `yundun-cloudfirewall:DescribeVpcFirewallCenList` | get | `acs:cloudfirewall::{accountId}:vpcfirewallcen/{VpcFirewallId}` |
| `yundun-cloudfirewall:DescribeVpcFirewallCenDetail` | get | `acs:cloudfirewall::{accountId}:vpcfirewallcen/{VpcFirewallId}` |
| `yundun-cloudfirewall:DescribeVpcFirewallCenSummaryList` | get | `*` |
| `yundun-cloudfirewall:DescribeVpcFirewallPrecheckDetail` | get | `*` |
| `yundun-cloudfirewall:DescribeFirewallTask` | get | `*` |
| `yundun-cloudfirewall:DescribeVpcFirewallZone` | none | `*` |
| `yundun-cloudfirewall:DescribeVpcFirewallAssetRegionList` | none | `*` |
| `yundun-cloudfirewall:DescribeVpcFirewallDefaultIPSConfig` | get | `acs:cloudfirewall::{accountId}:vpcfirewallipsconfig/{VpcFirewallId}` |
| `yundun-cloudfirewall:DescribeRegionInfo` | list | `*` |
| `yundun-cloudfirewall:DescribeVpcZone` | list | `*` |
| `yundun-cloudfirewall:DescribeUserBuyVersion` | get | `*` |

`DescribeVpcZone` backs the `zones` subcommand and takes `--environment`, whose two
values `VPC` and `TransitRouter` return different zone lists. `DescribeUserBuyVersion`
reports the purchased edition as a pre-flight signal, surfacing a missing entitlement
before any configuration is attempted rather than deep inside a failed attach. It is
not a gate: the numeric `Version` it returns has no documented mapping to an edition
name, so it is reported for the operator to judge rather than blocked on.

## Write Permissions

| Action | Access level | Resource |
|---|---|---|
| `yundun-cloudfirewall:CreateVpcFirewallPrecheck` | create | `*` |
| `yundun-cloudfirewall:CreateVpcFirewallCenConfigure` | create | `acs:yundun-cloudfirewall::{accountId}:vpcfirewallcen/*` |
| `yundun-cloudfirewall:ModifyVpcFirewallCenConfigure` | update | `acs:cloudfirewall::{accountId}:vpcfirewallcen/{VpcFirewallId}` |
| `yundun-cloudfirewall:ModifyVpcFirewallCenSwitchStatus` | update | `acs:cloudfirewall::{accountId}:vpcfirewallcen/{VpcFirewallId}` |
| `yundun-cloudfirewall:DeleteVpcFirewallCenConfigure` | delete | `acs:cloudfirewall::{accountId}:vpcfirewallcen/{VpcFirewallId}` |

`CreateVpcFirewallPrecheck` is a write action in RAM terms but it does not change
firewall state; it only records a check result. Granting it does not grant the
ability to attach a VPC.

## Permissions on Other Products

Attaching a VPC requires choosing a vSwitch inside the business VPC, and
`DescribeVpcFirewallManualVSwitchList` cannot be used for it: that action fails
with `400 MissingOwnerId` and the CLI exposes no `--owner-id` flag. The VPC
actions below are therefore not optional.

| Action | Access level | Resource | Needed for |
|---|---|---|---|
| `vpc:DescribeVSwitches` | list | `acs:vpc:{regionId}:{accountId}:vswitch/*` | listing candidate vSwitches in the business VPC |
| `vpc:DescribeRouteTableList` | list | `acs:vpc:{regionId}:{accountId}:routetable/*` | naming the custom route table a failed precheck complains about |
| `vpc:DescribeVpcs` | list | `acs:vpc:{regionId}:{accountId}:vpc/*` | verifying the regional firewall VPC was created or destroyed |
| `ecs:DescribeNetworkInterfaces` | get | `acs:ecs:{regionId}:{accountId}:eni/{eniId}` | verifying the diversion ENI was created or destroyed |

These four actions were verified against each product's own API metadata, the same
source as the `yundun-cloudfirewall` entries.

**Transit router edition lookup is not in this list, on purpose.** Reading a transit
router's edition directly is a useful diagnostic, but the Skill never needs it: it
asserts the edition on every row it reads instead, which also covers the case where
the CLI filter is silently dropped. Two things to know if an operator grants it by hand:
the RAM action is `cen:ListTransitRouters` with access level `get` and resource
`acs:cen:*:{accountId}:ceninstance/{ceninstanceId}`, and the prefix is `cen`, not the
`cbn` that the CLI product name suggests. A policy written as `cbn:ListTransitRouters`
never matches any request and surfaces as `NoPermission` rather than as a syntax error,
the same trap as `cloudfw` above.

## Notes

- Using the `cloudfw` prefix instead of `yundun-cloudfirewall` produces a policy
  that never matches, which surfaces as `NoPermission` or `ImplicitDeny` rather
  than as a policy syntax error.
- **The resource ARN service segment is documented inconsistently.** Every action
  above uses `acs:cloudfirewall::...` except `CreateVpcFirewallCenConfigure`,
  which the official metadata also writes as `acs:yundun-cloudfirewall::...`. The
  inconsistency is in the source data, not a transcription error here. When writing
  a resource-scoped policy, verify both forms in the RAM console, or set
  `Resource` to `*` and constrain by action instead.
- **Two actions take the CEN id where the ARN says `VpcFirewallId`.**
  `DescribeVpcFirewallDefaultIPSConfig` and
  `DescribeVpcFirewallAssetRegionList` are called with the CEN instance id, not
  the `vfw-` slot id. A resource-scoped policy written against slot ids will not
  behave as expected for these two.
- For a read-only reviewer, grant only the Read section. That is enough to list
  slots, read switch status, inspect detail and read a stored precheck verdict.
- `DeleteVpcFirewallCenConfigure` tears down the shared regional firewall VPC
  when it removes the last attached VPC in a region, so its blast radius is wider
  than one VPC. Restrict it to operations administrators.
- `BatchCloseVpcFirewallCen` and `DescribeVpcFirewallZoneSwitch` appear in the
  console traffic but have no entry in the RAM permission list and no CLI
  command, which is consistent with them being console-internal. They are out of
  scope.
