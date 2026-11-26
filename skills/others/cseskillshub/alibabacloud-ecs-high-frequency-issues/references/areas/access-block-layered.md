---
name: alibabacloud-ecs-high-frequency-issues
area: access-block-layered
description: |
  Layered attribution of blocked, dropped or reset access to an Alibaba Cloud ECS instance: walks the client, DNS and filing, Cloud Firewall and WAF, security group ingress and egress, guest firewall, listener and outside-platform layers, reporting per-layer evidence and manual-only fixes. Cloud queries run automatically; one whitelisted non-mutating guest command runs only after explicit user confirmation. Use when an ECS port or service is unreachable. Triggers: security group rule not taking effect; port blocked or not open; cannot connect SSH or remote desktop; iptables firewalld ufw blocking; WAF or cloud firewall interception; Connection timed out; Connection refused; Connection reset. Do NOT use for VPC route tables, EIP or cross-border link quality (use alibabacloud-ecs-vpc-publicnetwork-troubleshoot).
---

# ECS Access-Block Layered Diagnosis

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Attribute a blocked connection to the ONE layer where it dies - client,
DNS and domain compliance, platform protection, security group, guest firewall
or security software, kernel network parameters, service listener, or outside
the platform - and hand back evidence, not guesses. Every remedy is guidance;
this skill never changes a rule, a firewall, a kernel parameter or an instance.

## When to use it

A customer cannot reach a port or service on an ECS instance (or the instance
cannot reach an external endpoint) and an interception is plausible: a
security-group rule that does not take effect, a port that is "open but still
blocked", a remote session (SSH or Remote Desktop) that fails, an in-guest
`iptables` / `firewalld` / `ufw` or agent blocking traffic, a WAF or Cloud
Firewall suspected of dropping the flow, or the connection timing out, being
refused, or being reset.

## When NOT to use it

* VPC route tables, vswitch routes, network ACLs, third-party appliance
  diversion, EIP or public-path quality, cross-border link issues ->
  `alibabacloud-ecs-vpc-publicnetwork-troubleshoot` (this skill only reports
  that layer as out of scope; see [references/access-block-layered__handoff-boundaries.md](references/access-block-layered__handoff-boundaries.md)).
* Disk-IO saturation freezing the OS, or instance boot and state anomalies ->
  the disk-IO and instance-state skills.
* WAF or Cloud Firewall rule design, CC-protection tuning, filing procedures,
  billing disputes, suspected compromise -> the owning product or process.
* A bare "the server is unreachable" with no interception noun and no error
  string: ask first whether the connection times out, is refused or is reset,
  and whether a group, firewall or protection rule is suspected.

## Execution principles (mandatory)

1. **Run the bundled entry script; never hand-assemble cloud calls.** All cloud
   access goes through `scripts/areas/access_block_layered/diagnose_access_block.py`, which is the only
   place API calls are composed.
2. **Action whitelist.** Only these actions may be called:
   `sts:GetCallerIdentity`, `ecs:DescribeInstances`,
   `ecs:DescribeSecurityGroups`, `ecs:DescribeSecurityGroupAttribute`,
   `ecs:run-command` (gated, see rule 4), `ecs:DescribeInvocations`,
   Cloud Firewall `DescribeControlPolicy` and WAF `DescribeInstance`. Any
   action outside this list is refused, including every rule or resource change
   on an instance, group or firewall.
3. **ABSOLUTE PROHIBITION on mutation.** Never authorize, revoke, create,
   delete, modify or replace security-group rules; never enable, disable or
   reconfigure any firewall; never write a kernel parameter; never restart an
   instance or service; never mount rescue media, re-initialize a disk, capture
   packets, or unblock an address - neither by API nor by issuing such a
   command to the guest. These appear ONLY as manual steps with the console
   path, exact parameters, risk warning and snapshot reminder.
4. **Guest inspection is query-only and auto-approved.** Every guest command
   this skill can send comes from the read-only whitelist in
   `references/access-block-layered__guest-inspection-commands.md` (single non-mutating reads, enforced
   twice by the whitelist and the prohibited-token scan). When the Cloud
   Assistant agent responds, the entry tool runs the decisive reads
   (`iptables-rules`, `listeners`) by itself and quotes their output - no
   customer confirmation round is needed or allowed to skip them. Rule changes,
   toggles and captures remain outside this channel forever (manual guidance
   only, per rule 3).
5. **Whitelist-exceeding requests are refused, not improvised.** If the needed
   reading is not on the whitelist in
   [references/access-block-layered__guest-inspection-commands.md](references/access-block-layered__guest-inspection-commands.md),
   the skill hands the customer that single command as manual guidance and
   records the layer as UNKNOWN. The entry tool accepts a check NAME only, never
   raw command text, so nothing can be smuggled into the guest channel.
6. **Remote-channel-locked cases come first with the out-of-band logon path**
   (console VNC-family session) before any in-guest work is proposed.
7. **Evidence-based output only.** Quote real field values and real readings;
   state which inputs were assumed or defaulted; never present a missing
   reading as an exclusion.

## Authentication

Credentials are resolved exclusively by the aliyun CLI default credential chain
(the CLI default credential chain). This skill never reads, prints, stores, transmits or asks
for an AccessKey pair, a token or an instance password, and no credential is
ever passed on a command line. If the identity check fails, direct the user to
reconfigure the CLI profile. Authorization errors are reported with the exact
missing action and the smallest policy fragment, using the literals
`NoPermission` and `ImplicitDeny` (see [references/ram-policies.md](references/ram-policies.md)).

## Observability

Every run generates one 32-character hex session id (`uuid.uuid4().hex`) and
attaches it to EVERY cloud call through the CLI `--user-agent` flag, so a whole
diagnosis is traceable to one run:

```
AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}
```

where `{skill}` is this skill's name (area:access-block-layered) and
`{session-id}` is replaced at runtime by the 32-character hex session id.

Each call also runs with a per-call timeout and a bounded retry for transient
throttling or server errors, and all error text is masked before it can reach a
report line.

## How to run

```
python3 scripts/areas/access_block_layered/sts_token.py                 # confirm the account under diagnosis
python3 scripts/areas/access_block_layered/diagnose_access_block.py --help
python3 scripts/areas/access_block_layered/diagnose_access_block.py --list-guest-checks
```

Typical layered run:

```
python3 scripts/areas/access_block_layered/diagnose_access_block.py \
  --region-id cn-hangzhou --instance-id i-example \
  --direction ingress --protocol tcp --port 443 \
  --source-ip 203.0.113.9 --symptom "Connection timed out"
```

Variants: `--ip` resolves a public or private address to its instance;
`--direction egress --target-ip` examines outbound failures;
`--direction internal` examines instance-to-instance flows; `--domain` enables
the DNS and filing branch; `--skip-platform-policy` omits the Cloud Firewall
and WAF reads when those products are not in scope; `--json` emits the machine
readable verdict set.

Gated guest inspection, after the confirmation dialogue in rule 4:

```
python3 scripts/areas/access_block_layered/diagnose_access_block.py \
  --region-id cn-hangzhou --instance-id i-example \
  --direction ingress --protocol tcp --port 15432 --source-ip 203.0.113.9 \
  --guest-check firewalld-rules
```

CLI command style differs per product: the `ecs` product is invoked as
`aliyun ecs describe-instances --biz-region-id ...` with PascalCase action and
parameters, while plugin-served products use lowercase-hyphenated commands such
as `aliyun sts get-caller-identity`, `aliyun cloudfw describe-control-policy`
and `aliyun waf-openapi describe-instance`. Never mix the two.

## Required inputs

| Input | If missing |
|---|---|
| `RegionId` | defaults to `cn-hangzhou`, and the report declares the default |
| instance id, or the IP under test | `STATUS: BLOCKED`; ask, never guess |
| direction (in / out / internal) | defaults to ingress and says so; a wrong direction invalidates the walk |
| protocol and port | required for coverage matching; well-known substitutions (22 for SSH, 3389 for Remote Desktop) are declared |
| exact symptom string | drives the layer priors; ask for the literal message or screenshot |
| client public egress IP | strongly advised; without it the authorization-object verdict stays UNKNOWN and the report gives the lookup pages |
| peer address for outbound, domain for reset symptoms | required for those branches |

## Report contract

**Answer surface (MANDATORY, ABSOLUTE PROHIBITION).** The customer-facing reply
opens with the verdict line (SKILL.md rules 3d/3h); that first line IS the
customer-facing conclusion, and everything after it is customer content only.
ABSOLUTE PROHIBITION on emitting any scheduler, queue, handoff-switch or
run-log reasoning - "let me check the scheduler options", "the scheduler has
queued a handoff", "checking the run log for the handoff switch", "the handoff
area needs a pinned target" - in any language, anywhere in the reply, not even
as a preamble: scheduling and handoff machinery are internal, never customer
content. A handoff reaches the customer only as the dispatcher's
customer-worded continuation meaning, never as internal switch or log talk.

Output is the per-layer verdict table (each layer EXCLUDED, HIT, UNKNOWN or
NOT_APPLICABLE with the evidence quoted), the most likely root cause with its
confidence and its counter-evidence, the exact manual steps for the hit layer,
the evidence still to collect, and any handoff. Close by relaying the script's
own status verbatim:

* `STATUS: OK` - a layer was hit with direct evidence, or every layer was
  excluded with evidence and the responsibility is outside the platform.
* `STATUS: DEGRADED` - a needed reading was unavailable (access declined,
  agent offline, no egress from the instance, or a declared capability gap);
  conclusions become hypotheses and the missing reading is named.
* `STATUS: BLOCKED` - a required input is missing or the target cannot be
  resolved; `NEXT_ACTION` states what to ask.

## Capability limits (state them, do not paper over them)

No platform-side dial test from another network, no WAF or Cloud Firewall
interception **hit** records (policy configuration only), no domain filing
status query, and no instance diagnostic report reader. Where a verdict depends
on one of these, degrade to `STATUS: DEGRADED` and give the customer-side
comparison that would settle it.

## Documentation index

* Security groups: [Overview](https://help.aliyun.com/zh/ecs/user-guide/overview-44.md),
  [Precise access control quick guide](https://help.aliyun.com/zh/ecs/user-guide/5-minute-guide-to-security-groups-secure-and-precise-network-access-control.md),
  [Manage rules](https://help.aliyun.com/zh/ecs/user-guide/manage-security-group-rules),
  [Get started](https://help.aliyun.com/zh/ecs/user-guide/start-using-security-groups)
* Guest firewall and remote access: [Enable or disable the system firewall on a Linux instance](https://help.aliyun.com/zh/ecs/use-cases/enable-or-disable-the-system-firewall-in-a-linux-instance),
  [Connect by using VNC](https://help.aliyun.com/zh/ecs/user-guide/log-on-to-an-instance-by-using-vnc),
  [Workbench overview](https://help.aliyun.com/zh/ecs/user-guide/workbench-overview.md),
  [Workbench for a Windows instance](https://help.aliyun.com/zh/ecs/user-guide/connect-to-a-windows-instance-through-workbench.md)
* Platform protection: [Cloud Firewall against public-network attacks](https://help.aliyun.com/zh/ecs/user-guide/use-cloud-firewall-to-defend-against-public-network-attacks.md),
  [DDoS cleaning against public-network attacks](https://help.aliyun.com/zh/ecs/user-guide/use-ddos-cleaning-service-to-resist-public-network-attacks.md),
  [ECS security overview](https://help.aliyun.com/zh/ecs/user-guide/security-overview.md),
  [ECS best security practices](https://help.aliyun.com/zh/ecs/user-guide/best-security-practices.md),
  [ECS Insight capabilities](https://help.aliyun.com/zh/ecs/user-guide/ecs-insight-capabilities.md)
* Related products and processes: [WAF CNAME access](https://help.aliyun.com/zh/waf/web-application-firewall-3-0/user-guide/add-a-domain-name-to-waf-in-cname-record-mode),
  [WAF custom rules against specific requests](https://help.aliyun.com/zh/waf/web-application-firewall-3-0/user-guide/configure-custom-rules-to-defend-against-specific-requests),
  [ICP filing application](https://help.aliyun.com/zh/icp-filing/basic-icp-service/user-guide/icp-filing-application-overview),
  [Create a disk snapshot](https://help.aliyun.com/zh/ecs/user-guide/create-a-snapshot-of-a-disk),
  [VPC network isolation](https://help.aliyun.com/zh/ecs/user-guide/use-vpc-to-implement-network-isolation.md),
  [Enable telnet on a Windows instance](https://help.aliyun.com/zh/ecs/user-guide/enable-telnet-on-a-windows-instance)

## References

* [references/access-block-layered__layer-model.md](references/access-block-layered__layer-model.md) - layer definitions,
  three-state verdicts, termination rules, symptom-to-layer priors.
* [references/access-block-layered__symptom-error-strings.md](references/access-block-layered__symptom-error-strings.md) -
  quotable error strings and what each one proves.
* [references/access-block-layered__security-group-pitfalls.md](references/access-block-layered__security-group-pitfalls.md) -
  the L4 trap catalog: egress, group type, authorization object, priorities,
  stacked groups.
* [references/access-block-layered__guest-inspection-commands.md](references/access-block-layered__guest-inspection-commands.md) -
  the guest command whitelist, gate wording, fallbacks.
* [references/access-block-layered__evidence-collection.md](references/access-block-layered__evidence-collection.md) - what
  to ask the customer, from whom, in what format.
* [references/access-block-layered__handoff-boundaries.md](references/access-block-layered__handoff-boundaries.md) -
  boundary recognition and handoff wording.
* [references/ram-policies.md](references/ram-policies.md) - exact actions,
  policy strings, denied-error handling.
* [references/access-block-layered__ticket-patterns.md](references/access-block-layered__ticket-patterns.md) - maintainer
  pattern library: which reading settled which case, and what stayed unproven.
