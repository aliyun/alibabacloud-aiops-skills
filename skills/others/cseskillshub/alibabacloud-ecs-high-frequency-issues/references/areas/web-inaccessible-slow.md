---
name: alibabacloud-ecs-high-frequency-issues
area: web-inaccessible-slow
description: |
  Layered troubleshooting for websites, domains and API endpoints on Alibaba Cloud ECS that
  will not open or load slowly. It walks the path in order - asset, DNS, security groups,
  in-guest listeners and firewalls, application status codes, TLS and filing, capacity and
  attack - then names the failed layer, its evidence and the fix.
  Use when an externally reachable site or interface is down, refused, closed, times out, or
  returns 4xx or 5xx.
  Triggers: website won't open | cannot access my site or domain | page loads very slow | connection refused | err_connection_timed_out | timed out | err_connection_reset | err_connection_closed | err_cert_date_invalid | http 502 504 404
  Do NOT use for: instance health or login failures (alibabacloud-ecs-diagnose), outbound
  connectivity from an instance, the hosting panel page itself, WordPress or Discuz program
  errors, certificate issuance, Java PHP .NET runtime.
---

# Website unreachable or slow on ECS: layered troubleshooting

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

## What this skill does

It answers one question: **which layer of the access path is failing, and what proves it.**

The method is a layer sweep along the path a browser takes to reach the customer's site, keyed
by the **error string the customer sees** - not by which symptom label the ticket was filed
under. Tickets in this scenario routinely carry three or four overlapping labels at once, so
labels are used for recall only; the decision tree below is the only thing that decides where
the search goes next.

Outputs are always: the failed layer (or an explicit "undecided, because X"), the evidence
chain, the action at the correct permission level, the retest instruction, and the layers that
were **not** excluded.

## When not to use it

| Customer says | Where it goes |
| --- | --- |
| "I cannot SSH / RDP / VNC into the instance", instance hung | Instance health, not an access path: `alibabacloud-ecs-diagnose` |
| "The instance cannot reach the internet" (outbound) | Outbound-connectivity scenario; here outbound rules are only one observation |
| "The BaoTa / hosting panel page will not open" | Panel scenario; panel modules are named here only as a suspect inside L5 |
| "WordPress / Discuz throws an error in the page" | Application-code scenario; this skill attributes the layer, then hands off |
| "The certificate expires, please deploy a new one" | Certificate service scenario |
| "Java / PHP / Python / .NET will not start" | Runtime environment scenario |
| "Instance A cannot reach instance B on the intranet" | Intranet connectivity scenario |
| "The Alibaba Cloud console page will not open", "an OS upgrade cannot reach its mirror", "my office VPN/VDI blocks everything" | Not this scenario; these were mis-recalled into it in real tickets and must be excluded on the trigger words |

## Permission model: four levels

This skill is **not** a purely descriptive tool, and it is not a change tool either. Every
action belongs to exactly one level below.

| Level | What it covers | How it runs |
| --- | --- | --- |
| **A - automatic** | Cloud metadata and monitoring reads: `ecs:DescribeInstances`, `ecs:DescribeSecurityGroups`, `ecs:DescribeSecurityGroupAttribute`, `ecs:DescribeInvocations`, `vpc:DescribeEipAddresses`, `alidns:DescribeDomainRecords`, `alidns:DescribeDomainNs`, `cms:DescribeMetricLast`, `sts:GetCallerIdentity` | Runs on its own after telling the customer which facts are being looked up |
| **B - confirmed in-guest reads** | Non-mutating commands inside the instance, dispatched through Cloud Assistant (`aliyun ecs run-command`) and read back with `ecs:DescribeInvocations` | Only after disclosing what runs, its blast radius and its revertibility, and only after the customer agrees. **One agreement authorises exactly one command.** |
| **C - low-risk, reversible change** | Adding one inbound security group rule, taking a snapshot, writing a temporary diagnostic file | Snapshot first (see below), disclose the billing effect, get explicit agreement, remind about cleaning up afterwards |
| **D - never automated** | Anything destructive or irreversible | Only written steps for the customer to perform; no executable path is offered |

### Before any level B or C action (mandatory)

State all three, in this order, then wait for agreement:

1. **what** exactly runs - the literal command, the literal API, or the literal rule content;
2. **blast radius** - one instance or all of them, whether live traffic is interrupted,
   whether existing connections drop;
3. **revertibility** - how to undo it, and for level C that a snapshot exists and what it costs.

### Level D: absolute prohibition

Never execute, and never offer a copy-paste one-liner that the skill itself could run:

- deleting or emptying files, including any "truncate the log" form such as
  `echo "" > some.log`; `rm -rf` in any shape;
- filesystem operations: formatting, `fsck`, partition or filesystem rebuilds, `tune2fs`;
- killing processes, restarting services, rebooting or stopping instances;
- deleting snapshots, refunds, downgrades, releasing resources;
- writing security group rules or DNS records on the customer's behalf.

For each, output the manual steps instead, plus the sentence: *this is irreversible or
service-interrupting, so by policy it is not executed here.*

### Snapshot first (level C)

Before any cleanup or change, create a snapshot of the affected disk; **pure non-mutating
diagnosis is exempt**. Snapshot billing reference: a 100 GB disk is roughly **0.016 CNY per
hour, about 0.4 CNY per day** - quote the live pricing page as authoritative, and at the end
remind the customer to delete the snapshot to stop the charge.

## Credentials policy

- Never ask for, accept, repeat back, store or transmit a plaintext password, private key or
  panel credential.
- In-guest work goes through Cloud Assistant (no password needed), through an authorised
  console session, or through the customer executing a listed check.
- If the customer pastes a credential anyway, do not echo it and reply with:
  **"If you have shared an account password or any other credential in this conversation,
  change it immediately."**
- Scripts use the ambient credential chain only; nothing reads, prints or stores an access key.
- Console links must be parameterised with **the current customer's own** region and resource
  identifiers. Never hard-code a resource id copied from another ticket.

## Evidence intake (L0) - gate before any judgement

| Element | Why it is required |
| --- | --- |
| Domain / URL, public IP, port, protocol | 80 versus 443 and domain versus IP are the sharpest cuts available |
| **Customer-visible error string or HTTP status** | Primary key of the tree; "it does not open" is not enough to route |
| **Most recent change** - when, what, by whom, revertible | Engineers opened the locating question this way in 8 of the reviewed tickets; it always comes second, right after the error string |
| Impact breadth: all / some users / some regions / some resources / some ports | The impact surface is itself the strongest signal |
| Client location, ISP, and whether the network was switched (enterprise, campus, VDI, mobile data) | Without it, L3 can never be closed out |
| Instance ID and region | Needed for the level A reads |
| Incident time window | Scopes metric reads and log searches |

If anything above is missing, ask for it in **one** message and stop. An incomplete sweep that
silently guesses is worse than a short round trip.

## How to run

**MANDATORY SINGLE ENTRY POINT — ABSOLUTE PROHIBITION on raw cloud calls.**
Every read this skill performs (DescribeInstances, security-group attribute,
EIP, DNS, CMS and anything else whitelisted in `related_apis.yaml`) MUST be
issued through `scripts/areas/web_inaccessible_slow/ecs_web_access_check.py`. Calling `aliyun ecs ...`,
`aliyun vpc ...`, `aliyun cms ...` or any equivalent raw CLI from the shell to
gather the same evidence is forbidden **even after the script has already run**:
hand-assembled calls bypass the read-only whitelist, the session user-agent and
the redaction path, and their output is not admissible evidence in the report.
If the entry script cannot produce a reading, that layer stays UNKNOWN in the
report - never substitute a raw CLI call for it.

Run the single entry point; never assemble service calls by hand:

```bash
python3 scripts/areas/web_inaccessible_slow/ecs_web_access_check.py \
  --url "https://www.example.com" --port 443 \
  --error-string "err_connection_timed_out" \
  --change "security group edited on 2 Sep" --scope all \
  --region-id cn-hangzhou --instance-id i-xxxxxxxxxxxxxxxxxx
```

- Preflight the identity separately with `python3 scripts/areas/web_inaccessible_slow/sts_token.py`.
- List the in-guest check keys and their approval state with
  `python3 scripts/areas/web_inaccessible_slow/ecs_web_access_check.py --list-guest-checks`.
- Ask for one in-guest check with `--guest-command <key> --confirm`; without `--confirm` the
  script discloses and refuses, exactly as the policy requires.
- When the customer runs the command themselves, feed the output back with
  `--guest-output "<text>"` or `--guest-output-file <path>`. Nothing is dispatched and no
  permission is widened; the same interpreter decides L5 from it (stopped service, no listener,
  loopback-only bind, guest firewall block, or excluded). Unrecognisable output stays undecided.
- Read `references/ram-policies.md` before the first run in a new account: it names the exact
  actions, with no wildcards.

## Layered decision tree

```
L0 elements collected (gate)
 -> L1 asset and account ownership   : exists? Running? this account? ECS or Simple Application
                                       Server or another platform? origin off-cloud at all?
    -> stop and hand off if the asset is not a live ECS instance of this account
 -> L2 DNS                           : records listed and compared with the real public address
 -> L3 public path                    : carriers, interception, blackhole, client-side network
 -> L4 cloud access control           : inbound AND outbound, authorisation object, several
                                        security groups merged, cloud firewall, EIP bound
 -> L5 in-guest                      : port listening AND bound to 0.0.0.0 not 127.0.0.1,
                                        service alive and enabled at boot, host firewall, panel
                                        hardening modules, docker bridge and routes, hosts.deny
 -> L6 application                   : status code attributed to origin or edge, then logs
 -> L7 TLS and filing                 : certificate, SNI, protocol version, filing-missing reset
 -> L8 capacity and attack            : CPU, bandwidth, connection count, source ranges
```

Three hard rules:

1. Every layer ends in a verdict - **confirmed**, **excluded**, or **undecided with a reason**.
   Never hand over a list of possible causes for the customer to try at random.
2. After any change, ask the customer to retest and **report the new error string**. The change
   of the error string is the state transition: `timeout` becoming `connection refused` after
   opening a port proves L4 is passed and the fault moved to L5. That is progress, not a new bug.
3. "Slow" is always three lines at once - L8 capacity, L6 application time, L3 link quality -
   and each gets its own verdict.

### Error string to first layer

| What the customer sees | Family | Look here first |
| --- | --- | --- |
| `err_connection_timed_out`, spinning forever, "timed out" | DROP - discarded silently | L4 inbound rules, cloud firewall, merged groups -> L5 host firewall -> L3 blackhole, interception |
| `Connection refused` | RST - answered | L5 no listener or bound to 127.0.0.1 or service down -> L7 filing reset -> L4 reject-shaped rule |
| `err_connection_reset`, "reset by peer" | RST | L5, then **L7 missing ICP / access filing**, then L4 |
| `err_connection_closed` | handshake | L7 TLS version, cipher suite, SNI, origin certificate trust |
| `err_cert_date_invalid` | certificate | L7 validity window |
| `404` `405` `500` `502` `504` `521`, blank page | application | L6 - **but first prove whether the code came from the origin or from an edge node** |
| slow, "takes several seconds", intermittently slow | performance | L8 + L6 + L3 in parallel |

### Corrections that must be said out loud

- **A reply to ping proves nothing about TCP 80/443.** ICMP passing while the web port times out
  is normal and is the single most common misunderstanding.
- **`connection refused` means the packet arrived.** The path is fine; search downward. This
  points the opposite way from a timeout.
- **An HTTP status code means the path reached an application layer**, so it is not evidence
  that "the cloud side is fine, fix it" - it locates the work in L6 or in an edge product.
- A CNAME into CDN/WAF/GA/Cloudflare **hides the real origin address** by design.

### Differential tests (each one halves the search)

domain versus direct IP - port 80 versus 443 - `127.0.0.1` versus intranet IP versus public IP -
static page versus dynamic page - one file type versus a specific directory - another network
(mobile data), another city, another device - this cloud versus the customer's own machine.

### Proving whether an edge layer is involved

Run both and compare. Same answer on both sides means the origin is the problem; different
answers mean the edge is, and the case goes to that product's owner.

```bash
curl -v --resolve www.example.com:443:ORIGIN_PUBLIC_IP https://www.example.com/
curl -kv -H "Host: www.example.com" https://ORIGIN_PUBLIC_IP:443/
```

## Capability limits (state them, never paper over them)

| Needed for | Status | What the skill does instead |
| --- | --- | --- |
| Blackhole / DDoS cleaning state | not verified | Point to the Anti-DDoS console; do not claim a state |
| ICP / access filing status | not verified | Infer from "domain reset while direct IP works and the origin passes its own loopback test", **labelled as an inference**, and send the customer to the filing console |
| CloudMonitor namespace and metric names | not verified | The read is implemented, but no metric name is hard-coded; the operator supplies them (`--cms-namespace`, `--cms-metric`) and a threshold (`--saturate-above`) |
| CDN / WAF / GA configuration | cross product, not verified | Prove it with the origin-direct comparison, then hand off |
| Arrears and expiry state | not verified | Instance existence and status are indirect signals; the billing centre is authoritative |
| Multi-region dial test, client egress IP | not verified | Hand out the public probe page and ask for the pasted result - this is what engineers already did in tickets |
| Simple Application Server firewall | cross product | Identify the asset type, say plainly that it is not an ECS security group, hand off |
| Windows in-guest command set | not approved | Windows is guidance-only: IIS bindings, application pool, Windows Firewall inbound rules |
| Anything inside the guest other than what L5 lists | not visible | No cloud-side describe call exposes listening sockets or service liveness; that is why level B exists |

Empty results are reported as "not found", never as "no problem".

## Failure and degradation handling

| Situation | Behaviour |
| --- | --- |
| A call is denied | Name the exact missing permission point (for example `cms:QueryMetricLast`, which is **not** derived from the API name `DescribeMetricLast`), give the minimal grant snippet, continue with the other layers. Report codes as `NoPermission` / `ImplicitDeny`. |
| Cloud Assistant agent missing or offline | Degrade to an authorised console/VNC session, then to the execute-and-paste-back sheet; print `STATUS: DEGRADED` with the reason |
| Requested in-guest command is not on the approved list | **Refuse, explain why**, then give the paste-back sheet. Never widen the list on your own authority; chained or piped commands are refused outright. |
| Customer asks for a level D action | Explain the boundary, give the manual steps and the console entry point |
| Credentials absent | Stop with guidance to configure the CLI outside this conversation |

## Report contract

Every answer reproduces the script's findings in the reader's own words. The
status line below is the machine channel of this entry script (parsed by the
dispatcher, forbidden inside a customer reply by `SKILL.md` 3h):

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <single concrete next step>
```

with, in order: 1) the verdict layer; 2) the evidence chain (actual returned values only);
3) actions split by level A/B/C/D; 4) the retest instruction; 5) the layers **not** excluded and
why. Declare every auto-filled parameter (region, protocol inferred from a port, zone derived
from a URL) instead of presenting it as fact.

## Hand-offs

Each hand-off must carry: **why** it is outside this scenario, **what has already been excluded
with evidence**, and **who picks it up next** - never a bare referral. The register of twelve
out-of-scope topics with their wording is in `references/web-inaccessible-slow__out-of-scope-handoffs.md`. When the
conclusion is "not the cloud" (customer LAN, VDI, carrier interception), attach the comparison
evidence in the same message, otherwise the customer will not accept it.

## References

- `references/web-inaccessible-slow__layered-decision-tree.md` - the full L1-L8 tree, per-layer root causes and the
  error-string routing detail.
- `references/ram-policies.md` - the exact actions this skill calls, with a minimal policy.
- `references/web-inaccessible-slow__guest-read-checks.md` - the in-guest non-mutating checks, their approval state and
  the paste-back sheet.
- `references/web-inaccessible-slow__out-of-scope-handoffs.md` - the twelve hand-offs and their wording.
- `references/web-inaccessible-slow__help-documents.md` - help topics and tools actually cited by engineers, plus the
  explicitly unresolved documentation gaps.
- `scripts/areas/web_inaccessible_slow/ecs_web_access_check.py` - the single entry point. `scripts/areas/web_inaccessible_slow/_cli.py` holds the
  transport discipline; `scripts/areas/web_inaccessible_slow/_constants.py` holds every data table.

## Observability

Each run generates one 32-character hex session id with `uuid.uuid4().hex` and attaches the
User-Agent below to **every** service call, so calls can be traced back to one diagnosis:

```
AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}
```

With this skill's name and a live session id the value sent on the wire is:

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/<32-hex-session-id>
```

`UA_TEMPLATE` in `scripts/areas/web_inaccessible_slow/_constants.py` is the same string expressed with Python format keys
(`{skill}` and `{session_id}`) and is expanded by `user_agent()` in `scripts/areas/web_inaccessible_slow/_cli.py`.

Every call is built by `scripts/areas/web_inaccessible_slow/_cli.py` in the CLI's plugin-mode form - product, then the
lowercase-hyphenated action, then PascalCase parameters - and is executed as an argument vector
without a shell, with its own timeout, while transient errors are retried a bounded number of
times with backoff.
