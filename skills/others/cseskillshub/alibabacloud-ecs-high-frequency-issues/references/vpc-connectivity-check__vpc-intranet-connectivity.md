# Module: VPC / Intranet Connectivity Decision Tree

> Scope: read-only cloud-configuration review for "ECS instances cannot
> reach each other over the private network" and adjacent VPC / vSwitch /
> security-group configuration questions. The Agent routes the customer
> symptom to one sub-area below, runs the entry script mode, and interprets
> the deterministic findings. Facts come only from the script's API evidence
> or from this module's embedded knowledge -- never from model memory.

## 0. Routing: customer wording -> sub-area

| Customer wording (examples) | Sub-area | Entry mode |
|---|---|---|
| "two ECS cannot ping each other by private IP", "intranet connectivity not working", "cannot access port ... on the other server" | S1 security-group intranet allowlist (then S2 if rules are fine) | `pair` |
| "the two switches have overlapping CIDR", "connection shows success but internal ping fails", "lightweight server and ECS cannot reach each other" | S2 vSwitch / CIDR overlap | `pair --cidr-a --cidr-b` or `cidr-only` |
| "cannot select vSwitch / security group when transferring the instance to another account", "InvalidDependence.GrantAccess" | S3 cross-account transfer pre-check | `transfer` |
| "how do I list every 10.19.x.x private IP", "does the private IP change / can I add a second one" | S4 private-IP inventory / mechanism | `ip-inventory` |
| "reachable from inside, not from outside", "browser says not secure / 503", "alert claims attack from a 192.168.x.x internal address" | S5 application-layer look-alikes (identify + hand off) | `public-path` then hand off |
| "the AccessKey stopped working after I set a VPC access policy", "a NoPermission or ImplicitDeny denial although the resource group was granted" | S6 access-control policies (identify + hand off to RAM guidance) | no cloud mode applies; knowledge answer |

## S1. Security-group intranet allowlist (same / different security group)

Deterministic cloud evidence (`pair` mode): both instances' `VpcId`,
`VSwitchId`, `ZoneId`, private-IP list, bound security-group list, live
status, **and the inbound RULE CONTENT of the target instance's security
groups**, read with `DescribeSecurityGroupAttribute` (read-only). Every
returned rule is compared on direction, IP protocol, port range,
authorization object, policy and priority against the flow "source private IP
-> target port/protocol":

| Verdict | Meaning | Result code |
|---|---|---|
| an allow rule matches and no better-priority deny shadows it | the cloud-side rule is not the block; continue on the guest/application side | `PASS` |
| a matching deny has priority <= the matching allow | the security group drops this flow | `FAIL` |
| no rule matches source + protocol + port | the allow is missing: a cloud-side root cause | `FAIL` |
| no `--port` supplied | rules are listed, but a port-level verdict needs the port | `INFO` |
| the group could not be read (permission / API error) | degraded with a `[WARN]`; the printed dimensions become the console fallback | `SKIPPED` |

A rule that authorizes a **source security group** instead of a CIDR is
reported in its own finding: membership of the source instance in that group
is not an address match, so it is never silently counted as allowed. Fixing a
missing or shadowed rule is still a manual console edit.

Root-cause pattern frequency (from the ticket corpus):

1. **Direction misconception** -- customers think BOTH sides need a rule.
   Correct: an inbound rule on the **target** instance's security group that
   allows the **source private IP + the target port/protocol** is sufficient;
   the source side needs no inbound rule for this traffic.
2. **Over-broad authorization misconception** -- customers believe they must
   allow the whole `172.16.0.0/12`. Correct: authorize the source IP written
   as `<source-ip>/32` plus the concrete port; precise and safer.
3. **Protocol misconception** -- `ping` uses ICMP. A failed ping does NOT
   prove the TCP port is blocked, and a working port does NOT mean ICMP is
   allowed; ICMP needs its own inbound rule. Always retest the service port
   with `telnet <private-ip> <port>` or `curl`.
4. **Different VPCs** -- private IPs are not reachable across VPCs without
   an explicit interconnection (peering / CEN + routes). `pair` mode flags
   this as `same-vpc = FAIL`.
5. **Stopped instance** -- a stopped instance answers nothing on any port;
   `instance-live-status` provides the context.

Out of cloud visibility (declare, do not guess): guest `iptables` /
`firewalld` / Windows firewall, the service listening on `127.0.0.1`
instead of `0.0.0.0`, and third-party host security software. The customer
self-checks those or escalates to manual support.

## S2. vSwitch / VPC CIDR overlap

`cidr-only` (pure local, deterministic) or `pair` with `--cidr-a/--cidr-b`
read by the customer from the VPC console. Verdicts: identical / a-within-b /
b-within-a / partial-overlap / disjoint. An overlapping pair of vSwitch
ranges (for example `172.26.0.0/18` vs `172.26.32.0/20`) makes return routing
ambiguous -- the top cloud-visible root cause for "connection shows
successful but the internal ping fails".

Manual fix: create a NON-conflicting vSwitch inside the same VPC and move the
instance's private IP onto it; the vSwitch change requires the SAME
availability zone. When the two ends belong to different accounts, the change
must be performed by the owning account (see S3 boundary).

**Container-bridge sub-case**: Docker bridges default to `172.17.0.0/16` and
neighbors and can collide with the ECS private range even when every CLOUD
vSwitch is clean. Cloud read-only APIs cannot see `br-*` interfaces inside
the guest; after the CIDR check says "disjoint", tell the customer to run
`docker network ls` / `ip addr` in-guest (self-help) or escalate -- do not
claim a verdict the APIs cannot support.

## S3. Cross-account transfer: vSwitch / security group not selectable

The target-account picker only offers resources that satisfy ALL three
conditions (two of them measured against the SOURCE instance, one inside the
target account):

1. **Same region** -- transfers are never cross-region; a vSwitch created in
   the wrong region is invisible (a recurring real failure: resources built
   in another region).
2. **Same VPC (within one account)** -- the target vSwitch AND the target
   security group must belong to one and the same VPC, and that VPC belongs
   to the TARGET account: VPC IDs are account-local, so the source account's
   VPC ID cannot be reused and a differing ID is NOT a mismatch. A security
   group created under any other VPC never appears. Resources must be created
   BY the target account itself. The same-account variant (moving an
   instance to another vSwitch rather than transferring it) is where the
   destination vSwitch must sit inside the instance's CURRENT VPC.
3. **Same availability zone** -- the target vSwitch must be in the source
   instance's zone (a vSwitch change also requires the same zone).

Extra deterministic inputs: economy-type families can be placed in a RANDOM
zone, so the target account covers every zone of the region with its own
vSwitch (one per zone, all inside the one target VPC it will select);
`instance-type-zone-availability` (via `DescribeAvailableResource`) lists
which zones currently serve the family under the queried account.

**Error string `InvalidDependence.GrantAccess`**: this maps to an
uncleared grant / reverse-authorization dependency of the transfer. Manual
disposition: the SOURCE account cancels the reverse authorization, then the
target account retries the selection. Quote the RequestId if the picker
still errors, and route to human support. Alternative when VPCs cannot be
aligned: share a custom image instead of transferring the instance (manual).

Hard boundary: the transfer execution, cross-account resource changes and
any "do it from the backend" request are NOT in this skill's scope -- the
owning accounts act in the console, or a human specialist handles the
cross-account case.

## S4. Private-IP mechanism and inventory

`ip-inventory` pages `DescribeInstances` across the region (optional
`--vpc-id`, `--cidr-filter`) and reports each instance's primary + secondary
private IP list -- faster and repeatable compared with exporting the console
instance list to a spreadsheet and filtering locally.

Mechanism answers (knowledge): the primary private IP changes only when the
instance is released or its vSwitch is changed; secondary private IPs can be
assigned per ENI; activation of a new IP inside the OS is a guest manual step
(for NetworkManager-based images the connection name shown by
`nmcli -t -f NAME connection show` is typically `System eth0`, not `eth0`).
OS-level command execution is outside this skill.

## S5. Application-layer look-alikes (identify + hand off)

The cloud-side read-only check first EXCLUDES configuration factors, then
hands off:

- "reachable inside, unreachable outside, browser fails on HTTPS" --
  commonly the site has NO HTTPS certificate deployed while the browser
  defaults to HTTPS; HTTP itself works. Application-layer fix (deploy the
  certificate), not a network fault.
- "503 although no CDN is configured, direct internal access is fine" --
  reverse-proxy configuration on the guest web server; inspect the server
  config manually.
- "resolver returns a private IP without configured DNS" -- OS / default
  resolver behavior question; hand off.
- "attack alert from a 192.168.x.x address" -- if the customer's VPC uses a
  172.x range, that source is not routable into it; likely probe noise or
  internal test traffic; verify web access logs with the security team.

## S6. Access-control policies (identify + hand off)

- AccessKey VPC access-control policy: a VPC-only policy intentionally
  rejects public calls; when both call styles are needed, BOTH a
  VPC-allowance and the required public-IP allowance must be configured.
  Explaining the policy logic is in scope; changing it belongs to the
  account's access-control console (manual).
- A denial reported as `NoPermission` / `ImplicitDeny` that persists after
  the security-group / VPC facts are verified correct, or that mentions
  policy conditions / resource groups, is a RAM
  authorization topic: report the security-group facts as NOT the cause and
  hand off to RAM / access-control guidance. Output the failing action as
  `NoPermission` / `ImplicitDeny` style, never guess a rule.

## Boundary matrix (dedup vs the existing network-diagnose skill)

This skill answers "**is the configuration consistent?**" with deterministic
field comparisons. It does NOT probe packets hop by hop, does NOT touch
public-internet egress paths, and does NOT execute anything in the guest:

| Need | Route to |
|---|---|
| hop-by-hop path probing between two endpoints | `alibabacloud-network-diagnose` |
| public-internet / NAT / SNAT / EIP egress chain | `alibabacloud-ecs-vpc-publicnetwork-troubleshoot` |
| disk expansion not taking effect | `area:disk-expand-diagnosis` |
| instance stuck in start / stop states | `area:instance-state-diagnosis` |
| disk IO / capacity / inode pressure | `area:resource-bottleneck` |
| RAM policy conditions, AccessKey access-control edits | manual RAM / access-control guidance |
| guest firewall, Docker bridge, NIC configuration, app faults | customer in-guest investigation |

## Evidence discipline

- Every finding quotes the concrete returned field values (VPC IDs, zone
  IDs, CIDRs, statuses). Missing fields print `N/A`; empty inventories are
  valid findings, not errors.
- Degraded sub-queries remain visible as `[WARN]` entries plus the
  "Graceful Degradation Log"; the conclusion still ships with the data at
  hand (`STATUS: DEGRADED`).
- If every evidence call fails, `STATUS: FAIL` with the reason is the
  correct output; never invent values to fill the report.
