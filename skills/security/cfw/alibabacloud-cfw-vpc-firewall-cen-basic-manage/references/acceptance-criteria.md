# Acceptance Criteria

Correct and incorrect usage, side by side. Every ❌ below was either observed to fail
or observed to succeed while returning a wrong answer, which is the more dangerous
case.

## Contents

- [1. Command form](#1-command-form)
- [2. Edition scoping](#2-edition-scoping)
- [3. Identifier kinds](#3-identifier-kinds)
- [4. Region flags](#4-region-flags)
- [5. Attach parameters](#5-attach-parameters)
- [6. Polling and state](#6-polling-and-state)
- [7. Idempotency](#7-idempotency)
- [8. Observability](#8-observability)
- [9. Credentials](#9-credentials)
- [10. Interpretation of results](#10-interpretation-of-results)

## 1. Command form

```bash
# ✅ plugin mode, lowercase hyphenated action
aliyun cloudfw describe-vpc-firewall-cen-list --transit-router-type Basic

# ❌ PascalCase action name - rejected by the static checker and by the plugin
aliyun cloudfw DescribeVpcFirewallCenList --TransitRouterType Basic
```

## 2. Edition scoping

```bash
# ✅ exact capitalisation, then assert the edition on every returned row
aliyun cloudfw describe-vpc-firewall-cen-list --transit-router-type Basic --page-size 50
#    and check LocalVpc.TransitRouterType == "Basic" per row

# ❌ lowercase value: the filter is silently dropped and every slot in the
#    account is returned, HTTP 200, no warning
aliyun cloudfw describe-vpc-firewall-cen-list --transit-router-type basic

# ❌ relying on AllowConfiguration to tell editions apart - it answers whether the
#    regional firewall VPC is still undefined, which is a different question
```

## 3. Identifier kinds

```bash
# ✅ these two take the CEN instance id
aliyun cloudfw describe-vpc-firewall-default-ips-config --vpc-firewall-id cen-xxxxxxxx
aliyun cloudfw describe-vpc-firewall-asset-region-list --vpc-firewall-id cen-xxxxxxxx

# ❌ a slot id here gives 400 ErrorParametersFirewallId
aliyun cloudfw describe-vpc-firewall-default-ips-config --vpc-firewall-id vfw-xxxxxxxx

# ❌ a slot id here gives an empty list with HTTP 200, indistinguishable from a
#    genuine "no regions" answer
aliyun cloudfw describe-vpc-firewall-asset-region-list --vpc-firewall-id vfw-xxxxxxxx

# ✅ the task poll takes the business VPC id
aliyun cloudfw describe-firewall-task --child-instance-id vpc-xxxxxxxx

# ❌ the slot id returns nothing useful
aliyun cloudfw describe-firewall-task --child-instance-id vfw-xxxxxxxx

# ✅ detail accepts a slot id or a VPC id, but no region flag
aliyun cloudfw describe-vpc-firewall-cen-detail --vpc-firewall-id vfw-xxxxxxxx

# ❌ unknown flag
aliyun cloudfw describe-vpc-firewall-cen-detail --vpc-firewall-id vfw-xxxxxxxx --region-no cn-shanghai
```

## 4. Region flags

```bash
# ✅ cloudfw precheck uses --biz-region
aliyun cloudfw create-vpc-firewall-precheck --cen-id cen-xxxxxxxx --vpc-id vpc-xxxxxxxx \
  --network-instance-type cen_firewall --biz-region cn-shanghai

# ✅ vpc and ecs products use --biz-region-id for the API region parameter
aliyun vpc describe-vswitches --biz-region-id cn-shanghai --vpc-id vpc-xxxxxxxx
aliyun ecs describe-network-interfaces --biz-region-id cn-shanghai --vpc-id vpc-xxxxxxxx

# ❌ --region is the global endpoint override, not the business region
# ❌ --region-id is not a valid flag: returns a JSON error object with exit code 0,
#    so a parser reading TotalCount with a default reports "nothing found"
aliyun vpc describe-vswitches --region-id cn-shanghai --vpc-id vpc-xxxxxxxx

# ❌ camelCase flag
aliyun ecs describe-network-interfaces --biz-region-id cn-shanghai --VpcId vpc-xxxxxxxx

# ✅ --source-code is required here, not optional
aliyun cloudfw describe-region-info --source-code cfw
```

## 5. Attach parameters

```bash
# ✅ first access in a region (AllowConfiguration == 1): supply all four regional
#    parameters, with the vSwitch CIDR a subnet of the VPC CIDR, and the zone pair
#    taken from describe-vpc-firewall-zone
aliyun cloudfw create-vpc-firewall-cen-configure \
  --cen-id cen-xxxxxxxx --network-instance-id vpc-xxxxxxxx --vpc-region cn-shanghai \
  --vpc-firewall-name my-firewall --firewall-switch close --vswitch-id vsw-business \
  --firewall-vpc-cidr-block 10.0.0.0/24 --firewall-vswitch-cidr-block 10.0.0.0/26 \
  --firewall-vpc-zone-id cn-shanghai-b --firewall-vpc-standby-zone-id cn-shanghai-l \
  --firewall-vswitch-zone-id cn-shanghai-b

# ❌ vSwitch CIDR not a subnet of the firewall VPC CIDR
#    --firewall-vpc-cidr-block 10.0.0.0/24 --firewall-vswitch-cidr-block 10.9.9.0/26

# ❌ a range outside 10.0.0.0/8, 172.16.0.0/12 and 192.168.0.0/16
#    --firewall-vpc-cidr-block 8.8.8.0/24

# ❌ validating the mask-length limits the API help states. They contradict the
#    service defaults and contradict a /24 VPC with a /26 vSwitch that was accepted
#    twice, so enforcing them rejects known-good configurations

# ❌ composing a primary and a standby zone independently; pick a pair from
#    describe-vpc-firewall-zone, whose ZoneList entries are two-element arrays

# ❌ passing regional parameters when AllowConfiguration == 0 - they are ignored,
#    and the user is left believing a change was made

# ❌ sending part of the regional set. It is all-or-nothing on a first access, so a
#    lone zone or a lone CIDR must be rejected rather than half-applied

# ❌ using describe-vpc-firewall-manual-vswitch-list to find the business vSwitch:
#    it fails with 400 MissingOwnerId and exposes no --owner-id flag

# ✅ --firewall-switch open gated behind explicit confirmation, exactly like the
#    switch operation: it starts diversion immediately and flaps connections

# ❌ leaving --firewall-switch open ungated because "it is only an attach". That is a
#    bypass of the gate on the switch operation, with the same traffic consequence

# ❌ asking for confirmation before reading state. A no-op then demands it too, which
#    teaches the caller to pass the flag reflexively and disarms it where it matters
```

## 6. Polling and state

```bash
# ✅ treat opening / closing / deleting as progress and keep polling the list
# ✅ budget at least 30 minutes for a switch transition, per the official guide
# ✅ retry a failed status read inside the loop, counting consecutive failures: the
#    write is in flight and the read says nothing about it
# ✅ report a timeout, or six consecutive failed reads, as an unconfirmed outcome
#    carrying mutation_sent and a recheck command

# ❌ reporting a poll timeout or a lost status read as a failure. The write was
#    accepted, and the caller's natural response to a failure is to repeat it, which
#    returns ErrorFirewallStatus or -360142 and can never succeed

# ❌ aborting the poll on the first failed read. Throttling and transient transport
#    faults were both observed, and neither says anything about the transition

# ❌ counting read failures cumulatively across a 35 minute window: early jitter then
#    aborts a healthy long transition. Six in a row is the point to give up

# ❌ retrying a permission denial inside the poll loop. It will not clear on retry and
#    a minute of retries only buries the real cause

# ❌ treating a slot that left the list as a timeout during removal. Absence is the
#    same end state as notconfigured there - though not during a switch, where it
#    means the id or the filter is wrong

# ❌ treating ErrorPreCheckDoing as a failure. It arrives as HTTP 400 with a
#    non-zero exit, but it means the precheck is still running

# ❌ extracting the error code with an unanchored search for "Code:". The blob also
#    contains "StatusCode: 400", so that search yields 400 instead of the real code
#    and every code-specific branch silently stops matching

# ❌ reading describe-firewall-task or describe-vpc-firewall-precheck-detail once
#    and believing it: both return the last stored result even when nothing is
#    running. Snapshot TaskId and PrecheckTimestamp before the mutating call and
#    ignore anything older

# ❌ a timeout tuned to observed test timings. A lightly routed test CEN finished
#    open in 45 s; the guide allows 5 to 30 minutes

# ❌ filtering on --firewall-switch-status configured - that value has never been
#    observed, while the three transient states are not in the filter enum
```

## 7. Idempotency

```bash
# ✅ check-then-act: read FirewallSwitchStatus, then call only if the target
#    state is not already reached

# ❌ assuming a repeated call is a harmless no-op. None of them is:
#    attach an attached VPC      -> 400 ErrorFirewallStatus
#    open an opened slot         -> 400 -360142
#    close a notconfigured slot  -> 400 ErrorFirewallNotConfig
#    delete a notconfigured slot -> 400 -360134
#    rename a notconfigured slot -> 400 ErrorFirewallStatusCannotModify

# ❌ passing a --client-token for idempotency: none of these actions accepts one

# ❌ treating ErrorFirewallStatus as retryable. Its message says "please try again
#    later", but the real cause is that the VPC is already attached

# ❌ treating ErrorVpcFirewallExist as "already done". Its message says the firewall
#    has been configured and cannot be created repeatedly, but the real cause is
#    that the slot id does not exist

# ❌ using create-vpc-firewall-cen-configure to rename an existing firewall. It is
#    not an upsert; the name is unchanged and the call errors. Use
#    modify-vpc-firewall-cen-configure, which renames and does nothing else
```

## 8. Observability

```bash
# ✅ placeholder-form template, double quoted, carrying the skill-version segment
--user-agent "AlibabaCloud-Agent-Skills/alibabacloud-cfw-vpc-firewall-cen-basic-manage/{session-id} skill-version/{skill-version}"

# ✅ version read from the skill manifest, the only permitted source
# ✅ one 32-character lowercase hex session id reused for the whole session
# ✅ scripts receive it inline: SKILL_SESSION_ID={session-id} python3 scripts/...

# ❌ missing quotes, or missing the skill-version segment
# ❌ hardcoding or guessing the version instead of reading the manifest
# ❌ the CLI's persistent AI-mode configuration subcommand. It rewrites the user's
#    global settings and survives across processes, so any exit path that misses
#    turning it off leaks the AI user agent into later manual CLI use on that machine
# ❌ exporting a user-agent environment variable. Each tool call starts a fresh shell,
#    so the value does not survive and the attribution is silently lost
# ❌ adding --user-agent to local commands such as configure, plugin, version,
#    upgrade or help: they do not support it
```

## 9. Credentials

```bash
# ✅ the only permitted credential check; it calls no API and exposes no secret
aliyun configure list

# ❌ echoing, reading or printing an AccessKey id or secret from the environment
# ❌ asking the user to set an AccessKey id or secret environment variable
# ❌ aliyun configure set with plaintext credentials
# ❌ any hardcoded AccessKey or SecretKey in SKILL.md, references or scripts
```

## 10. Interpretation of results

```bash
# ✅ a removed slot still appears in the list as notconfigured - removal resets a
#    slot, it does not delete it, and TotalCount is unchanged
# ✅ an unprotected VPC appears as notconfigured, which is how candidates are found
# ✅ DefendCidrList holds values before attachment and after removal, because it
#    reflects the business VPC's own routing
# ✅ on a failed precheck, walk every group and entity: only the top-level
#    PrecheckStatus is an aggregate
# ✅ a precheck Suggestion names no resource, so resolve it locally with
#    describe-route-table-list before reporting it to the user

# ❌ reporting "firewall deleted" as a bug when the slot id is still listed
# ❌ reading DefendCidrList as evidence that protection is active
# ❌ relaying a precheck failure without saying which route table or vSwitch caused it
# ❌ reporting TotalCount 0 as "the CEN has no VPCs" without first confirming the
#    CEN id is valid - a nonexistent CEN id also returns 0
```
