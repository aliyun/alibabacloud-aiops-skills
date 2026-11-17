---
name: alibabacloud-ecs-high-frequency-issues
area: network-quality-bandwidth
description: |
  Read-only diagnosis of ECS public network quality and bandwidth saturation: purchased peak and
  billing mode, EIP and shared bandwidth settings, outbound traffic measured against that peak over
  a stated window, and throttling or packet-loss attribution.
  Use when an ECS instance is slow, times out, or looks throttled. Triggers (customer wording):
  high latency or packet loss
  bandwidth used up and speed drops
  transfer rate far below the purchased Mbps
  limited after traffic reached the cap
  ping normal but website slow
  overseas access fails with TCP connection reset by peer or Request timeout for icmp_seq
  Do NOT use for hop-by-hop MTR analysis (use alibabacloud-mtr-network-diagnosis-customer), disk IOPS
  or disk bandwidth alarms (use area:resource-bottleneck), instance startup or logon
  failures, attack blocking, WAF rules, bandwidth changes, or pricing and coupon questions.
---

# ECS Network Quality and Bandwidth Saturation Diagnosis

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

## What this skill does

It answers two questions with cloud-side evidence instead of guesses:

1. **Is the public bandwidth actually at the purchased limit?** The script reads the instance and
   EIP bandwidth peak plus billing mode, converts them to a theoretical transfer rate, then compares
   measured traffic against that peak over an explicit time window. Every verdict carries the
   reading, the threshold, and the window.
2. **If the customer reports latency, packet loss, or throttling, which side owns it?** It separates
   cloud-side capacity causes (spec limit, billing-mode peak ceiling, overdue account, temporary
   upgrade not effective, instance specification baseline) from customer-local network and
   cross-border carrier links, and hands the latter off instead of pretending to fix them.

Evidence comes from the entry script and the reference files shipped in this package. Do not spend
turns browsing the web for metric names, namespaces, thresholds or policy pages: when an identifier
is not stated in this package, record it as an evidence gap and use the console path instead of
guessing or researching. The scene's job is a verdict from measurable facts, not a documentation
tour.

## Permission model: read-only

This skill is read-only. Every cloud call it makes is a query: `DescribeInstances`,
`DescribeInstanceAttribute`, `DescribeEipAddresses`, `DescribeCommonBandwidthPackages`,
`DescribeMetricList`, and `GetCallerIdentity`. The full list, with the purpose of each, is in
[references/ram-policies.md](references/ram-policies.md).

It also runs nothing inside the customer's instance. When a reading can only come from the operating
system, `guide` prints the exact measurement command and the agent sends it to the customer, who
runs it and pastes the output back. That output is evidence the customer supplied, not evidence this
skill collected, and the report labels it that way.

Nothing here changes a resource: no bandwidth peak change, no billing-mode conversion, no upgrade,
no security group edit, no reboot, no snapshot, no installation, no command execution.

## ABSOLUTE PROHIBITION

Never generate, run, or hand the customer a command to run, for any mutating action. This includes
every action whose name begins with `Create*`, `Modify*`, `Delete*`, `Release*`, `Reset*`,
`Replace*`, `Attach*`, `Detach*`, `Start*`, `Stop*`, `Reboot*`, `Set*`, `Authorize*`, `Revoke*`,
`Convert*`, `Upgrade*`, `Downgrade*`, `Import*`, `Export*`, or `Put*`, even when the customer
explicitly asks for it. For those requests: state the boundary, give the console path as human
guidance, and stop there. In particular:

- Bandwidth peak, billing mode, temporary upgrade, renewal, refund, coupon: human action only.
- Security group blocking of attacking IPs, WAF rules, platform security unblocking: human only.
- Changing the guest MTU (`ip link set`), killing processes, rebooting, log rotation: human only.
- Installing any tool (`wget`, `yum`, `apt`, `make install`, `netatop`): never automated, only
  documented as a manual step with its risk.
- Executing anything in the guest on the customer's behalf: never, in this version.

## Execution principle

The agent runs the single entry point and never assembles cloud calls by hand:

```
python3 scripts/areas/network_quality_bandwidth/network_quality_bandwidth.py <subcommand> [options]
```

`preflight`, `collect`, `judge`, `guide`, and `report` are the only supported ways to reach the
cloud for this skill. If a needed fact cannot be produced by these commands, say so as a limitation;
do not invent it. Never guess a region, an instance id, a metric name, a threshold, or a customer
answer.

## Credentials

Use the default credential chain configured on the machine. Never ask for, accept, echo, store, or
forward an AccessKey pair, a password, a token, or a panel (for example BaoTa) login. If the
customer already pasted a credential into the conversation, advise once that they change it outside
the ticket, then stop referencing its content. The measurements this skill suggests never need a
credential from the customer, because the customer runs them in a session they already hold; that is
why there is no password option anywhere in this package.

## Required inputs (ask, never infer)

| Input | Necessity | Why it matters |
| --- | --- | --- |
| `InstanceId` **or** public IP | one of the two | Customers often send a private address (`192.168.x.x`) or a hostname shaped like `iZ...Z`; neither is an instance id, and a private address cannot be used for a public bandwidth verdict. Ask again. |
| `RegionId` | required | Never derive it from the IP address. |
| Problem time window, to the minute | required | A monitoring reading without a window cannot be reviewed by anyone. |
| Peer target IP or domain | for quality and cross-border cases | Needed for the suggested measurements and per-node comparison. |
| Customer local public IP | for bidirectional MTR | The reverse measurement printed by `guide` targets that address; a human runs it and pastes the table back. |
| Port and protocol (80/443/22/UDP) | when the symptom is protocol specific | Reset on 443 while 80 works changes the conclusion. |
| Whether the customer can run a measurement and paste it back | decides how far the run gets | Otherwise the run stops at cloud-side facts and reports what is missing. |

## Workflow

Run the steps in order. Each one prints JSON to stdout and writes no file itself: redirect the
output (`> collect.json`) to hand it to the next step. The trailing `STATUS:` and `NEXT_ACTION:`
lines are tolerated when such a file is read back.

1. Identity preflight (also proves the credential chain works):

   `python3 scripts/areas/network_quality_bandwidth/network_quality_bandwidth.py preflight`
2. Cloud facts, by instance or by public IP:

   `python3 scripts/areas/network_quality_bandwidth/network_quality_bandwidth.py collect --region-id <RegionId> --instance-id <InstanceId>`
   or `python3 scripts/areas/network_quality_bandwidth/network_quality_bandwidth.py collect --region-id <RegionId> --public-ip <ip>`
   Add `--eip-allocation-id <id>` or `--bandwidth-package-id <id>` when that resource is the one whose
   peak should be treated as the ceiling.
   Add `--with-metrics --namespace <ns> --metric-name <name> --start <ms> --end <ms>` only when the
   metric identifiers were confirmed from the console monitoring page or the CloudMonitor metric
   reference. The script refuses to guess them, and a returned series is converted with the same
   `--unit` as the supplied readings, which `judge` records as a limitation to confirm.
3. Saturation verdict:

   `python3 scripts/areas/network_quality_bandwidth/network_quality_bandwidth.py judge --facts-file collect.json --window-start <ms> --window-end <ms>`
   Add `--observed "epochMs=Mbps,epochMs=Mbps"` or `--observed-file observed.txt` when the reading
   came from the console chart instead of the API. `--unit bps|kbps|mbps` must match the source unit.
4. Customer-side measurement, when a reading only exists inside the instance:

   `python3 scripts/areas/network_quality_bandwidth/network_quality_bandwidth.py guide --tool mtr --target <ip-or-domain> --count 30`
   (`--tool ping` with `--packet-size 80,200,1400` prints the packet-size sweep.) This prints the
   command text for the customer; it executes nothing.
5. Final report:

   `python3 scripts/areas/network_quality_bandwidth/network_quality_bandwidth.py report --facts-file collect.json --judge-file judge.json --symptom "<customer wording>" --window "<start> to <end>"`
   plus `--pasted-output-file pasted.txt` once the customer has sent the measurement back.

## Sending a measurement to the customer

`guide` only suggests `ping` and `mtr`, assembled from validated numeric options and a filtered
target string, so the printed command cannot be steered into anything else. When sending it:

- state plainly that the customer runs it, and that this skill cannot run it for them;
- ask for the complete output plus the wall clock time it was taken, to the minute;
- one packet size per command, kept separate, so the size at which transfers start failing stays
  visible;
- anything outside that pair is refused and answered with manual steps, including `iftop`,
  `traceroute`, `ss`, `netstat`, `ip`, `curl`, `tcpdump`, log parsing, and database introspection.
  See [references/network-quality-bandwidth__guest-command-whitelist.md](references/network-quality-bandwidth__guest-command-whitelist.md);
- request the whole evidence set in one message, and label every pasted number as customer-supplied
  rather than cloud-collected, per
  [references/network-quality-bandwidth__customer-side-probes.md](references/network-quality-bandwidth__customer-side-probes.md);
- if the customer cannot or will not run it, continue with what the cloud side can still prove and
  report `STATUS: DEGRADED` naming the missing reading.

## Decision tree

1. Locate the resource. Only a private IP, or only a hostname shaped like `iZ...Z`, or an unusable
   domain? Ask for the instance id or public IP and the region. Do not infer a region from an IP.
2. Route on measurements, not on the customer's wording. Before judging bandwidth:
   - A disk bandwidth or IOPS alarm: storage performance, hand off with the evidence already
     collected; do not continue the bandwidth flow.
   - CPU or memory at limit while the title says bandwidth: compute area, hand off. This skill
     suggests only ping and mtr, so a process listing is the customer's manual step.
   - Instance not reachable at all, both SSH and VNC fail: instance state area, hand off.
   - HTTP 499 or 502 with normal cloud resources: application operations, hand off with the numbers
     that exonerate the cloud side.
   - Quoting, coupons, refunds, selection advice: presales or billing, hand off.
   - Platform security blocking, confirmed attack traffic: evidence only, hand off. No unblocking, no
     exemption promise.
   - Monitoring trap: when resources were exhausted the CloudMonitor plugin quits to avoid competing
     with the workload, so readings taken after a hang are unreliable. Use readings from before the
     incident. Say this whenever declaring a metric "normal" for a hung instance.
3. Bandwidth area (the main path):
   - Peak and billing mode from `DescribeInstanceAttribute` (plus EIP and shared bandwidth package):
     convert to KB/s with 1 Mbps = 128 KB/s and state both numbers. The region-wide EIP listing is
     narrowed to the queried address or the resolved instance, and a shared bandwidth package peak is
     used only when `--bandwidth-package-id` named that package; anything left over is reported as
     region context, never as this instance's ceiling.
   - Verdict: saturated (any reading at or above the effective peak, or at least two readings at or
     above 95% of it), near-limit (highest reading at or above 80%), not saturated, or unknown. The
     effective peak is the minimum of the configured peaks and the specification baseline; see
     [references/network-quality-bandwidth__bandwidth-facts.md](references/network-quality-bandwidth__bandwidth-facts.md) for why the billing-mode cap is
     listed separately rather than folded in.
   - Spec limit reached with no abnormal source: answer "specification limit", show the conversion,
     and present the upgrade as a human action.
   - Billing mode is pay-by-traffic and the customer reports sudden slowdown with large packets
     failing: list both candidates, an overdue account throttling outbound bandwidth and a guest
     interface MTU, and ask the customer to check the account balance in the billing center. Do not
     collapse it to one cause without evidence.
   - Temporary upgrade reported as ineffective: compare readings before and after the upgrade
     timestamp; if the new peak is never reached, question whether the change took effect.
   - Saturated plus concentrated traffic source: automated attribution stops at the reading. The
     per-connection and per-process source is a customer-side step, so give the manual guidance and
     ask for the pasted output.
4. Quality area: cloud resources normal plus the symptom is latency or loss.
   - Ask for the customer's local public IP, print the server-side reverse measurement with `guide`
     for them to run, and in the same message give the symmetric instruction to run the local test
     and paste it.
   - Judge with the three rules in [references/network-quality-bandwidth__mtr-interpretation.md](references/network-quality-bandwidth__mtr-interpretation.md):
     attribute only the first hop that loses continuously and whose successors keep losing; a middle
     hop that drops sharply while its successor recovers is ICMP rate limiting; TCP-MTR loss does not
     prove application loss.
   - First sustained loss at the customer's own gateway: local network. Suggest a different uplink,
     for example a mobile hotspot, and confirm afterwards.
   - Loss starting at an international egress hop: cross-border link. Follow
     [references/network-quality-bandwidth__cross-border.md](references/network-quality-bandwidth__cross-border.md): evidence separation, Global Acceleration
     or premium BGP EIP options, and no promise of improvement.
   - Need hop-by-hop deep dive: hand off to `alibabacloud-mtr-network-diagnosis-customer`.
5. Output per the contract below.

## Evidence and confidence contract

Every conclusion must be accompanied by its evidence: the API action that produced it, the value,
and the time it was sampled. Conclusions without a reading are labelled as possibilities, and
possibilities are never written as causes.

- **High**: cloud-side readings and a documented rule agree.
- **Medium**: a cloud-side metric series exists but no verdict could be reached against a confirmed
  peak, or the rule applied is flagged unverified.
- **Low**: the conclusion depends on output the customer pasted, or on cross-carrier comparison.

Finish every run with:

```
STATUS: OK|DEGRADED|FAIL
NEXT_ACTION: <what this skill does next | what the customer does manually | handoff target>
```

`STATUS: DEGRADED` when a query was refused or unsupported, required identifiers are missing, metric
identifiers are unconfirmed, or an in-instance reading has not been pasted back yet. State which
one. `STATUS: FAIL` only when no fact could be gathered at all; say what is missing.

## Authentication and permission failures

On `NoPermission` or `ImplicitDeny`, report the exact missing action, name the minimum policy
statement, and point the customer to their RAM administrator. Never retry with different
credentials, never substitute a broader policy, and never describe the error as a network problem.
The action list is in [references/ram-policies.md](references/ram-policies.md).

## What this skill cannot do

- It cannot see the customer's local network, device, or carrier path.
- It cannot read anything inside the guest: no traffic, no process, no interface state, no log. An
  in-instance reading only enters the report after the customer pastes it.
- It cannot attribute historical traffic to an application or a peer; only aggregate historical
  bandwidth is available. Ongoing per-connection attribution needs a customer-side real-time step at
  the moment bandwidth is high.
- It cannot fix cross-border or third-party link quality, and never promises that it can.
- It cannot state numeric latency or throughput guarantees for a region, a link, or a product.
- It does not change configuration, and does not touch security controls, billing, or refunds.

## Known unverified items

Ask for these instead of asserting them. Each is also marked at its point of use.

- Exact CloudMonitor namespace and metric identifiers for ECS public bandwidth, and their units.
- The numeric inbound bandwidth cap per billing mode (reported to customers only as "inbound peak is
  not freely adjustable", low confidence, until a citable source exists).
- The mechanism that would explain why throttling drops larger packets first.
- Authoritative CDN or ESA back-to-origin address ranges.
- The account balance or overdue state via API: this package has no billing action, so balance is a
  customer self-check in the billing center.
- Any OpenAPI error code for this tier: none is verified, so the report quotes request ids only.

## Observability

Every cloud call made by this skill is tagged so that a single diagnosis run can be traced end to
end:

- User-Agent header template: `AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}`, where `{skill}` is
  this skill's name `area:network-quality-bandwidth`.
- `{session-id}` is a 32-character lowercase hex value generated once per run with
  `uuid.uuid4().hex`, held in `scripts/areas/network_quality_bandwidth/_cli.py`, and attached to every call through the
  `--user-agent` CLI option.
- The same `session_id` is printed in the script preamble, so a report can be tied back to the calls
  that produced it.

## References

- [references/network-quality-bandwidth__bandwidth-facts.md](references/network-quality-bandwidth__bandwidth-facts.md): billing modes, peaks, caps,
  conversions, bill timing, specification baseline.
- [references/network-quality-bandwidth__mtr-interpretation.md](references/network-quality-bandwidth__mtr-interpretation.md): bidirectional test request
  wording and the three loss-attribution rules.
- [references/network-quality-bandwidth__cross-border.md](references/network-quality-bandwidth__cross-border.md): evidence template, options, expectation
  management wording.
- [references/network-quality-bandwidth__guest-command-whitelist.md](references/network-quality-bandwidth__guest-command-whitelist.md): what may be
  suggested to the customer, and what must be refused.
- [references/network-quality-bandwidth__customer-side-probes.md](references/network-quality-bandwidth__customer-side-probes.md): how to ask for the whole
  evidence set in one message, and how a pasted reading is labelled against a cloud-collected one.
- [references/network-quality-bandwidth__handoff-map.md](references/network-quality-bandwidth__handoff-map.md): out-of-scope symptoms and their targets.
- [references/ram-policies.md](references/ram-policies.md): actions used and the minimum policy.
