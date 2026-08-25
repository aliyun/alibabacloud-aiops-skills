# Acceptance Criteria: alibabacloud-cfw-nat-firewall-protect

Correct and incorrect usage patterns. Every WRONG example below is a mistake that was actually made
(by a user, a service order, or an earlier version of this Skill).

## 1. Always go through the scripts, never raw CLI

```bash
# CORRECT
bash scripts/nat-fw-lifecycle.sh assess --region cn-hangzhou --nat-gateway-id ngw-xxx
bash scripts/nat-fw-switch.sh enable --proxy-ids "proxy-xxx"

# WRONG: calling the API directly skips the client-side pre-checks, the impact
# preview and the mandatory result verification
aliyun Cloudfw CreateSecurityProxy --NatGatewayId ngw-xxx --VswitchAuto true ...
aliyun Cloudfw SwitchSecurityProxy --ProxyId proxy-xxx --Switch open
```

Read-only VPC/ECS queries for ad-hoc investigation are fine, but any **state change** to a NAT
firewall must go through the scripts.

## 2. Never pass `--version` to Cloudfw commands

```bash
# CORRECT - the plugin manages the API version (2017-12-07) internally
aliyun Cloudfw DescribeSecurityProxy --PageNo 1 --PageSize 50 --Lang zh

# WRONG - the plugin rejects an external override with "unchecked version"
aliyun Cloudfw DescribeSecurityProxy --version 2017-12-07 ...
```

## 3. Diversion mode parameters are mutually exclusive

```bash
# CORRECT - auto mode: a FREE CIDR inside the VPC
bash scripts/nat-fw-lifecycle.sh create ... --vswitch-cidr 10.0.3.0/28 --yes

# CORRECT - manual mode: an EXISTING dedicated vswitch
bash scripts/nat-fw-lifecycle.sh create ... --vswitch-id vsw-xxx --yes

# WRONG - both at once (rejected by the script)
bash scripts/nat-fw-lifecycle.sh create ... --vswitch-cidr 10.0.3.0/28 --vswitch-id vsw-xxx

# WRONG - neither (auto mode without a CIDR fails server-side with ErrorParameters / MissingVswitchCidr)
bash scripts/nat-fw-lifecycle.sh create --nat-gateway-id ngw-xxx --region cn-hangzhou --vpc-id vpc-xxx --proxy-name x --yes
```

## 4. Manual mode requires a dedicated, empty vswitch on a FRESH custom route table

```bash
# CORRECT - let prepare build/reuse qualifying assets, then create
bash scripts/nat-fw-lifecycle.sh prepare --region cn-hangzhou --vpc-id vpc-xxx --nat-gateway-id ngw-xxx --yes
bash scripts/nat-fw-lifecycle.sh create ... --vswitch-id <vsw from prepare> --yes
```

WRONG choices for `--vswitch-id`, all refused by the pre-check:

| Wrong choice | Why |
|---|---|
| A vswitch bound to the **system** route table | Manual mode needs a custom table |
| A route table that already has `0.0.0.0/0` | Server rejects with `ErrorDefaultRouteConflicts` |
| A route table carrying **business routes** (next hop `Instance` / `HaVip` / `NetworkInterface` / another `NatGateway`) | The diversion table becomes the effective forwarding table for all diverted traffic - inheriting business routes reroutes production traffic |
| A vswitch with ENIs attached | The diversion vswitch must be dedicated and empty |
| A vswitch in a different zone or VPC than the NAT gateway | Hard constraint |
| A `/29` or smaller vswitch, or free IPs <= bound EIP count | Each EIP needs one egress ENI |

Pre-existing **cross-VPC return routes** (`VpcPeer` / `VpnGateway` / `RouterInterface` / `VBR` /
`Attachment` / `TunnelInterface`) are the ONE tolerated exception - the plan marks them
`route_table_clean: no` and requires human confirmation that they are intended.

## 5. The switch workflow has three phases; none may be skipped

```bash
# CORRECT
# Phase 1: preview who is affected  ->  Phase 2: execute  ->  Phase 3: poll and verify
bash scripts/nat-fw-switch.sh query --region cn-hangzhou --status closed
bash scripts/nat-fw-switch.sh enable --proxy-ids "proxy-xxx"
sleep 5 && bash scripts/nat-fw-switch.sh query --region cn-hangzhou --proxy-id proxy-xxx

# WRONG - treating the API's success response as proof. SwitchSecurityProxy returns
# success even for a ProxyId that does not exist
bash scripts/nat-fw-switch.sh enable --proxy-ids "proxy-typo" && echo "done"
```

WRONG reasoning patterns:

- "Phase 1 found 0 affected firewalls, so nothing to do" -> still execute Phase 2 and Phase 3; the
  API is idempotent
- "All targets are already `normal`, skipping" -> still execute; skipping hides drift
- Enabling/disabling without warning about the **1~2 second interruption of long-lived connections**
  (short connections unaffected)

## 6. Ask the gateway first, then present ONE plan

```bash
# CORRECT - Stage 1 inventory, then Stage 2 deep evaluation for the chosen gateway
bash scripts/nat-fw-lifecycle.sh assess --region cn-hangzhou
bash scripts/nat-fw-lifecycle.sh assess --region cn-hangzhou --nat-gateway-id ngw-xxx
```

WRONG interaction patterns:

- Asking "auto or manual diversion?" **before** running the single-gateway evaluation - the mode is
  a conclusion of the evaluation, not an opening question
- Chaining separate questions for mode -> risk handling -> name -> switch -> engine mode
- Offering to create while `plan.blockers` is non-empty
- Truncating resource IDs in options (`ngw-bp19ue5...`) instead of the full `<ID> (<name>)`, or
  putting contextual fields ahead of the identity
- Leading option labels such as "verification-failed scenario" / "direct success" instead of factual descriptions

## 6b. Never release a NAT firewall - close it instead

```bash
# CORRECT - stop protection without destroying anything (reversible)
bash scripts/nat-fw-switch.sh disable --proxy-ids "proxy-xxx"

# CORRECT - user genuinely wants the resource gone: give the read-only report, hand over the console path
bash scripts/nat-fw-lifecycle.sh delete --proxy-id proxy-xxx   # refuses by design, prints guidance

# WRONG - bypassing the restriction with a raw CLI call
aliyun Cloudfw DeleteSecurityProxy --ProxyId proxy-xxx --Lang zh
```

WRONG reasoning patterns:

- Treating "delete the firewall" / "take it offline" / "don't want it anymore" as a delete request without clarifying - in most cases the user
  means **close** (`disable`), which is reversible; deletion frees the authorization and reclaims the
  auto-mode diversion vswitch irreversibly
- Passing `--yes` and expecting the delete to proceed (it does not, by design)
- Requesting `yundun-cloudfirewall:DeleteSecurityProxy` in the RAM policy "just in case" - leaving it
  ungranted is the strongest safeguard
- Describing `disable` as "deleting the firewall", or `delete` as "turning it off" - the two differ in
  reversibility, quota occupancy and diversion assets

## 7. Never modify routes on the user's behalf

```bash
# CORRECT - diagnose and hand the plan over
bash scripts/nat-fw-lifecycle.sh route-diff --region cn-hangzhou --vpc-id vpc-xxx

# WRONG - applying the alignment plan yourself
aliyun Vpc CreateRouteEntry --RouteTableId vtb-xxx --DestinationCidrBlock 10.0.0.0/8 ...
aliyun Vpc DeleteRouteEntry --RouteEntryId ...
```

`route-diff` only generates `alignment_plan`. Aligning entries changes forwarding for every vswitch
bound to those tables; when `classification` is `business_topology` or `mixed`, explicitly advise
against it and prefer manual-mode diversion.

## 8. Region and identifier formats

```bash
# CORRECT
--region cn-hangzhou            # region ID
--nat-gateway-id ngw-xxxxxxxx   # NAT gateway
--vpc-id vpc-xxxxxxxx           # VPC
--proxy-id proxy-natxxxxxxxx    # NAT firewall (NOT the NAT gateway ID)
--proxy-ids "proxy-a,proxy-b"   # comma-separated, no spaces

# WRONG
--region hangzhou                       # not a region ID
--proxy-id ngw-bp1exampleid00000001      # gateway ID where a proxy ID is required
--proxy-ids "proxy-a, proxy-b"          # spaces break the split
```

The RAM action prefix is `yundun-cloudfirewall`, **not** `cloudfw`:

```json
// CORRECT
{"Action": ["yundun-cloudfirewall:DescribeSecurityProxy"], "Effect": "Allow", "Resource": "*"}
// WRONG - the policy silently has no effect
{"Action": ["cloudfw:DescribeSecurityProxy"], "Effect": "Allow", "Resource": "*"}
```

## 9. Credentials and User-Agent

```bash
# CORRECT - inspect only
aliyun configure list

# CORRECT - UA injection is handled by the scripts: common.sh exports
# ALIBABA_CLOUD_USER_AGENT (AlibabaCloud-Agent-Skills/<skill-name>/<session-id>)
# and every API wrapper passes --user-agent per call.
# Ad-hoc CLI calls outside the scripts must pass the same UA explicitly:
aliyun Cloudfw DescribeSecurityProxy --user-agent "$ALIBABA_CLOUD_USER_AGENT"

# WRONG - never read, echo, or set literal credentials
echo $ALIBABA_CLOUD_ACCESS_KEY_ID
aliyun configure set --access-key-id LTAI... --access-key-secret ...

# WRONG - deprecated global agent-mode toggles (aliyun configure ai-mode ...):
# UA injection is per-call via --user-agent only; no global mode to enable/disable
```

## 10. Treat the assessment as a snapshot

```bash
# CORRECT - re-run right before acting when anything may have changed
bash scripts/nat-fw-lifecycle.sh assess --region cn-hangzhou --nat-gateway-id ngw-xxx
```

- WRONG: reusing an `assess` report from an earlier turn after the user touched the console. A real
  session saw a candidate vswitch gain an ECS instance between two runs, which correctly disqualified
  it - a stale report would have proposed it
- WRONG: presenting `quota_projection` items whose `status` is `unknown` as safe
- WRONG: presenting a green server pre-check as a guarantee - it does not check cross-table route
  consistency

> All identifiers in this document are placeholders (`ngw-bp1exampleid00000001`, `vsw-xxx`,
> `proxy-xxx`). Never paste a real account's resource IDs into the Skill's documentation.

## Acceptance Checklist

A change to this Skill is acceptable when:

1. `bash tests/run_unit_tests.sh` is fully green (39 assertions, offline)
2. `bash -n` passes for every script and all 11 subcommand `--help` invocations work
3. Any new subcommand appears in BOTH the Operation Routing and Script Reference tables
4. Any newly called cloud API is declared in the RAM policy reference listed in SKILL.md
5. Any newly diagnosed error code is documented in the API error reference listed in SKILL.md
6. New capability keywords are added to the frontmatter `description` (English and Chinese)
7. A live run of the affected workflow was verified per the verification reference listed in SKILL.md
