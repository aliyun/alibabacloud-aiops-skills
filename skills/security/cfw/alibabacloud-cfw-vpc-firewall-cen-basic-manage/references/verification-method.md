# Success Verification Method

Step-by-step commands that confirm each operation actually took effect. Every call
below reaches a cloud API, so each one carries `--user-agent` with the session id
generated in the Observability section of SKILL.md.

Throughout, `{slot-id}` is a `vfw-` id, `{cen-id}` a CEN instance id, `{vpc-id}` the
business VPC, and `{region}` a region id such as `cn-shanghai`.

## Contents

- [1. General rules](#1-general-rules)
- [2. After attaching a VPC](#2-after-attaching-a-vpc)
- [3. After opening diversion](#3-after-opening-diversion)
- [4. After closing diversion](#4-after-closing-diversion)
- [5. After removing access](#5-after-removing-access)
- [6. After a rename](#6-after-a-rename)
- [7. Confirming a precheck verdict](#7-confirming-a-precheck-verdict)
- [8. When a change appears not to have taken effect](#8-when-a-change-appears-not-to-have-taken-effect)

## 1. General rules

Three habits prevent most false positives here.

**Read the row, then check its edition.** `--transit-router-type` is case sensitive
and is silently dropped when the value is wrong, so confirm
`LocalVpc.TransitRouterType` is `Basic` on the row being verified.

**Assert the response key exists.** A wrong flag returns a JSON object with no
`TotalCount` and exit code 0, which a tolerant parser reads as "nothing found".

**Compare timestamps in UTC+8.** Response timestamps carry no zone marker and are
UTC+8, so convert before judging freshness.

**An unconfirmed result is not a failed one.** When a script exits non-zero with
`outcome: "unknown"` and `mutation_sent: true`, the write was accepted and it is the
verification that did not complete. Run the checks below instead of re-issuing the
operation; the state is often already correct. `outcome: "confirmed_incomplete"` means
the opposite: the transition finished and a check below came back negative, so there is
nothing to wait for and the gap itself is what needs investigating.

## 2. After attaching a VPC

The task must have finished, the slot must be `closed`, and the diversion ENI must
exist in the vSwitch that was requested.

```bash
# 2.1 the provisioning task finished
aliyun cloudfw describe-firewall-task --child-instance-id {vpc-id} --lang zh \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-vpc-firewall-cen-basic-manage/{session-id} skill-version/{skill-version}"
# expect TaskStatus == "finished"; TaskSteps lists three steps, all finished
```

```bash
# 2.2 the slot reached the dormant state
aliyun cloudfw describe-vpc-firewall-cen-detail --vpc-firewall-id {slot-id} --lang zh \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-vpc-firewall-cen-basic-manage/{session-id} skill-version/{skill-version}"
```

From that response confirm:

| Field | Expected |
|---|---|
| `FirewallSwitchStatus` | `closed` |
| `LocalVpc.EniList[0].EniId` | non-empty |
| `LocalVpc.EniList[0].EniVSwitchId` | equal to the `--vswitch-id` that was passed |
| `LocalVpc.EniList[0].EniPrivateIpAddress` | non-empty |
| `LocalVpc.TransitRouterType` | `Basic` |
| `FirewallVpc.VpcId` | non-empty |
| `FirewallVpc.AllowConfiguration` | `0` after this call, whatever it was before |

`AllowConfiguration` flipping from `1` to `0` is the proof that this was the first
access in the region and the shared firewall VPC now exists.

```bash
# 2.3 cross-product: the ENI really exists in the business VPC
aliyun ecs describe-network-interfaces --biz-region-id {region} --vpc-id {vpc-id} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-vpc-firewall-cen-basic-manage/{session-id} skill-version/{skill-version}"
# expect TotalCount >= 1 and an interface id matching EniList[0].EniId
```

When this was the first access in the region, also confirm the shared resources:

```bash
# 2.4 the regional firewall VPC and its vSwitch
aliyun vpc describe-vpcs --biz-region-id {region} --page-size 50 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-vpc-firewall-cen-basic-manage/{session-id} skill-version/{skill-version}"
# expect one VPC named Cloud_Firewall_VPC whose CidrBlock equals the firewall VPC CIDR that was requested

aliyun vpc describe-vswitches --biz-region-id {region} --vpc-id {firewall-vpc-id} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-vpc-firewall-cen-basic-manage/{session-id} skill-version/{skill-version}"
# expect one vSwitch named Cloud_Firewall_VSWITCH
```

## 3. After opening diversion

```bash
aliyun cloudfw describe-vpc-firewall-cen-list --transit-router-type Basic \
  --cen-id {cen-id} --page-size 50 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-vpc-firewall-cen-basic-manage/{session-id} skill-version/{skill-version}"
```

Poll until the row for `{slot-id}` reports `FirewallSwitchStatus: opened`. Treat
`opening` as progress, not as an error. Budget at least 30 minutes: the official
guide allows 5 to 30 minutes depending on route entry count, and a lightly routed
CEN finishes in well under a minute, which is not representative.

Once `opened`, the IPS configuration becomes readable and confirms the firewall is
live at the CEN level. Note it takes the **CEN id**, not the slot id:

```bash
aliyun cloudfw describe-vpc-firewall-default-ips-config --vpc-firewall-id {cen-id} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-vpc-firewall-cen-basic-manage/{session-id} skill-version/{skill-version}"
```

Passing a `vfw-` slot id here returns `400 ErrorParametersFirewallId`, which is itself
a useful confirmation that the CEN-scoped lookup is the correct one.

After a route table change while protection is on, allow 15 to 30 minutes of route
relearning before judging the outcome.

## 4. After closing diversion

Same list call as section 3. Poll until the row reports `closed`, treating `closing`
as progress. Confirm the ENI still exists - closing diversion switches traffic off but
does not remove the access configuration, so `EniList` should still be populated.

## 5. After removing access

```bash
aliyun cloudfw describe-vpc-firewall-cen-detail --vpc-firewall-id {slot-id} --lang zh \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-vpc-firewall-cen-basic-manage/{session-id} skill-version/{skill-version}"
```

| Field | Expected |
|---|---|
| `FirewallSwitchStatus` | `notconfigured` |
| `VpcFirewallName` | empty string - the name does not survive removal |
| `FirewallVpc.VpcId` | empty |
| `LocalVpc.EniList[0].EniId` | empty |
| `FirewallVpc.AllowConfiguration` | `1` if this was the last access in the region |

The slot id still appears in the list afterwards. That is correct: removal resets a
slot, it does not delete it, and `TotalCount` is unchanged.

**If the slot has left the list instead, do not run the read above.** Disappearing is
also a removal end state, but asking for detail on an id that is no longer listed
answers `400 ErrorVpcFirewallExist`, whose message claims the firewall already exists.
Reading that as a failure turns a successful removal into a phantom error. Absence in
the list is the stronger evidence anyway; verify the ENI and the regional VPC below
instead.

**`FirewallSwitchStatus: notconfigured` alone does not prove the teardown finished.**
The four fields above are independent, and a slot can report the reset status while
still holding an ENI. Check all of them before calling a removal clean.

`LocalVpc.DefendCidrList` **still holds values** after removal, because it reflects
the business VPC's own routing rather than firewall state. Do not read it as evidence
that the firewall survived.

If this was the last access in the region, verify the shared resources were destroyed:

```bash
aliyun ecs describe-network-interfaces --biz-region-id {region} --vpc-id {vpc-id} \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-vpc-firewall-cen-basic-manage/{session-id} skill-version/{skill-version}"
# expect TotalCount 0

aliyun vpc describe-vpcs --biz-region-id {region} --page-size 50 \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-vpc-firewall-cen-basic-manage/{session-id} skill-version/{skill-version}"
# expect no VPC named Cloud_Firewall_VPC
```

Matching on the fixed name `Cloud_Firewall_VPC` is more reliable than matching on a
CIDR, because the name is assigned by the service rather than chosen by the operator.

## 6. After a rename

Re-read the detail call from section 5 and confirm `VpcFirewallName` equals the new
value. A rename against a `notconfigured` slot fails with
`ErrorFirewallStatusCannotModify`, so the slot must be attached first.

## 7. Confirming a precheck verdict

```bash
aliyun cloudfw describe-vpc-firewall-precheck-detail --cen-id {cen-id} --vpc-id {vpc-id} \
  --network-instance-type cen_firewall --biz-region {region} --lang zh \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-vpc-firewall-cen-basic-manage/{session-id} skill-version/{skill-version}"
```

Confirm three things, not just the status:

1. `IsFound` is `true`.
2. `PrecheckDetail.NetworkInstanceId` equals `{vpc-id}` and `PrecheckDetail.RegionNo`
   equals `{region}` - this proves the stored verdict belongs to the VPC being worked
   on rather than to an earlier one.
3. `PrecheckDetail.PrecheckTimestamp` is **later than the moment the precheck was
   issued**. The verdict persists server-side, so a timestamp older than the call
   means a stale read.

## 8. When a change appears not to have taken effect

Check these in order, because each is more likely than an actual product failure.

1. **Did the operation report `outcome: "unknown"`?** Then nothing is known to have
   failed. Re-read the slot with the `recheck` command carried in that payload rather
   than repeating the write, which would answer with an error instead of a no-op. Only
   a slot still transient past the guide's own budget is a real problem.
2. **Did it report `outcome: "confirmed_incomplete"`?** The transition did finish, so
   waiting longer and rechecking both cannot change the answer. Read the `reason` field
   for the check that failed, and follow `investigate`. A removal reporting
   `eni_cleared: false` here means traffic may still reach a residual interface.
3. **Is the slot still in a transient state?** `opening`, `closing` and `deleting`
   are normal intermediate values. Keep polling.
4. **Is the result stale?** Both `describe-firewall-task` and
   `describe-vpc-firewall-precheck-detail` return whatever the service last stored,
   even when nothing is running. Compare timestamps against the moment of the call.
5. **Is the row the right edition?** Re-check `LocalVpc.TransitRouterType`.
6. **Was the identifier the right kind?** `describe-vpc-firewall-default-ips-config`
   and `describe-vpc-firewall-asset-region-list` want the CEN id, not a slot id, and
   the latter answers an empty list rather than an error.
7. **Is the VPC absent from the list entirely?** There is no CLI equivalent of the
   console's asset-sync button, so a newly joined VPC may need syncing from the
   console before it appears.
