---
name: alibabacloud-ecs-high-frequency-issues
area: attack-blackhole-diagnosis
description: |
  Read-only triage for an Alibaba Cloud ECS instance that looks attacked, blackholed or blocked: DDoS or CC suspicion, blackhole and scrubbing status, an IP, domain or port blocked plus unblocking requests, and connection-reset failures. It reads instance state, security-group rules with priority resolution, EIP state and Cloud Assistant history, then returns an evidence-based verdict plus guidance-only recovery steps; it changes nothing.
  Triggers: my ecs is under a ddos or cc attack, site is down; server entered blackhole, public traffic dropped; public ip or domain blocked, how to unblock; site unreachable, Connection reset / err_connection_reset; need attack evidence or a traffic proof package; how long does a blackhole last
  Do NOT use: miner, worm or webshell cleanup; instance lifecycle or boot failures; disk expansion; slow disk IO; disk-full cleanup; WAF, Anti-DDoS or CDN setup; fee or refund disputes.
---

# ECS Attack, Blackhole and Blockout Diagnosis

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

## What this skill does

A customer reports one symptom - the service is unreachable, the CPU spiked, a
port answers nothing, a notice says "attack detected" - and blames an attack.
This skill settles **which area** the evidence points at, using read-only cloud
queries only, and then hands over the matching manual guidance:

1. Is it a real DDoS event with a blackhole or scrubbing in progress?
2. Is it a platform penalty, because this instance was attacking others or
   serving a reported URL?
3. Is it somebody else's block: a peer site, a messaging platform, a registrar,
   an anti-spam listing, a carrier or a regulator?
4. Or is it not an attack at all - a security-group rule, a wedged instance, a
   full log volume, an unpaid bandwidth bill, a panel that blacklisted its own
   owner, or an application that never bound the port?

The decision logic lives in `scripts/areas/attack_blackhole_diagnosis/attack_blackhole_diagnosis.py`; the domain
knowledge lives in `references/`. Nothing in this skill can change a resource,
and nothing in it promises a timing, a price or an outcome.

## Permission model: read-only (RO + guidance)

**ABSOLUTE PROHIBITION.** Never generate, suggest-for-execution, or run any
changing call in this skill: no `Modify*`, `Create*`, `Delete*`, `Release*`,
`Reset*`, `Replace*`, `Attach*`, `Detach*`, `Reboot*`, `Start*`, `Stop*`,
`Revoke*`, `Bind*` or `Unbind*` action, no SDK equivalent, and no "please run
this to fix it" command that mutates cloud or guest state. That includes changes
the customer asks for politely. The read-only transport in `scripts/areas/attack_blackhole_diagnosis/_cli.py`
enforces this a second time: it refuses any action that is not whitelisted, so a
write action cannot be reached even by mistake.

Concretely out of bounds, even when requested: restarting or stopping an
instance, reinstalling the system disk, rolling a disk back, deleting files or
snapshots, killing processes, editing security-group rules, swapping a public IP
or EIP, and any command executed inside the
guest operating system. Each of these is **printed as a manual step with its
risk**, never performed. Buying and onboarding a mitigation product is out of
bounds for the *skill* only: it is a self-service console action the customer
runs, not work reserved for a specialist.

### Verified read-only actions (the complete whitelist)

| Product | Action | Version | Purpose in the flow |
|---|---|---|---|
| ecs | `DescribeInstanceStatus` | 2014-05-26 | Fastest Running or not split for the region |
| ecs | `DescribeInstances` | 2014-05-26 | Resolve the target, read addresses, attached groups, bandwidth, charge mode |
| ecs | `DescribeSecurityGroups` | 2014-05-26 | Locate and name the groups in the region |
| ecs | `DescribeSecurityGroupAttribute` | 2014-05-26 | Full ingress and egress rules with policy, priority, protocol, port range, authorisation object |
| ecs | `DescribeInvocations` | 2014-05-26 | Cloud Assistant run **history** in the window: did anyone operate on the instance |
| vpc | `DescribeEipAddresses` | 2016-04-28 | EIP address, status, bandwidth, charge mode; EIP versus fixed public IP |
| sts | `GetCallerIdentity` | 2015-04-01 | Which account these readings belong to |

`related_apis.yaml`, `references/ram-policies.md` and the scripts must stay
three-way aligned with this table. Adding a row requires verifying the action
first; an unverified action is never added.

## How to run

The agent runs the single entry point and reads its report. Do not assemble
`aliyun` commands by hand, and do not call an API outside this skill to
"double-check" it.

```
python3 scripts/areas/attack_blackhole_diagnosis/attack_blackhole_diagnosis.py \
  --region-id cn-hangzhou \
  --instance-id i-exampleid0000000000 \
  --symptom "site down since 10:00, cpu 100 percent, ssh refused" \
  --error-string "Connection reset" \
  --source-ip 203.0.113.7 \
  --time-window 2026-09-17T10:00Z,2026-09-17T14:00Z \
  --alarm-text "<verbatim platform notice, if any>" \
  --forbidden-actions "do not change the public ip, do not stop the instance"
```

* `--region-id` is required and is echoed back in the report; if it was
  inferred rather than stated by the customer, say so.
* Give exactly one target selector: `--instance-id`, `--public-ip`,
  `--eip-address` or `--private-ip`. With none, the first page of the region is
  scanned and the report is explicit that the target was not pinned down.
* `--source-ip` is the client whose flow should be resolved against the rules;
  without it, narrow authorisation objects are reported as
  `UNDETERMINED-NEEDS-PEER` instead of guessed.
* `--output json` produces the machine-readable report for a hand-off;
  `--no-invocations` skips the Cloud Assistant history lookup.
* Preflight only: `python3 scripts/areas/attack_blackhole_diagnosis/sts_token.py`.

Dependencies are standard library only (`scripts/requirements.txt`); the
transport is the locally configured Alibaba Cloud CLI using its default
credential chain.

## Diagnosis flow

```
Intake: instance or IP, region, symptom words, verbatim error, verbatim
        platform notice, incident window, what the customer forbids
  Step 0  Identity: which account are we reading? Resolves "not your asset"
          and "is this IP mine?" before anything else.
  Step 1  Instance state (DescribeInstanceStatus + DescribeInstances)
          not Running  -> instance-lifecycle area: hand off, stop here
          Running      -> continue; a wedged guest OS still reads Running, so
                          Running proves nothing about health
  Step 2  Inbound reachability (DescribeSecurityGroupAttribute)
          deny overriding accept by priority, missing accept for the business
          port, 100.104.0.0/16 absent from port 22, peer not authorised
          -> "not an attack": configuration, printed with the exact rule trace
  Step 3  Address and path (DescribeEipAddresses + DescribeInstances)
          EIP status not InUse, zero effective bandwidth, fixed public IP
          rather than an EIP (so a proxied defence may be bypassed)
          -> billing or topology, not an attack
  Step 4  Operation history in the window (DescribeInvocations)
          someone ran commands during the incident -> record it as context,
          history only, never presented as live load
  Step 5  Attack and penalty state: NOT queryable with a verified read-only
          action here. Degrade: name the console page, ask for the event
          detail and the thresholds, then classify from the customer's text.
          Verbatim notice mentioning an outbound cut or a shielded URL routes
          to the penalty area, not the blackhole area.
  Step 6  External-party block: peer system, messaging platform, registrar,
          carrier or regulator. Nothing to lift here; produce the appeal
          evidence list instead.
  Step 7  Output: four-way verdict, confidence, evidence already gathered,
          missing evidence, manual-only recovery paths with their
          preconditions and cost warnings, hardening list, hand-off, and
          STATUS plus NEXT_ACTION.
```

The two error strings this skill may quote verbatim are `Connection reset` and
`err_connection_reset`. Both are **neutral**: a blackhole drop, a security-group
deny, a platform outbound cut, a wedged service and an application that is not
listening can all produce them. Never conclude "DDoS" from either one. Text such
as "empty reply", "connection closed ... end of file" or "connection timed out"
may be quoted as the customer's words and is labelled as such, not as an
official error code.

## Output contract

Report the script's own `Summary`, `STATUS` and `NEXT_ACTION`; do not upgrade a
conclusion the script did not reach.

* `STATUS: OK` - the read-only evidence was complete for the question asked.
* `STATUS: DEGRADED` - at least one read failed or one capability is outside the
  verified surface. State **which** item is missing and **where** to read it.
  A degraded report is still useful: publish what was proven and what was not.
* `STATUS: FAIL` - no usable identity or permission; authentication comes first.
* `NEXT_ACTION` - the single most valuable manual step, never a change this
  skill performs.

## Hard rules against invented facts

1. Every number, state and rule in the answer must come from a returned field or
   from `references/`. Never from memory of a product's defaults.
2. Blackhole duration is stated as "not fixed; repeated attacks extend it; the
   console event detail is the only authority" and **no** minutes or hours are
   promised. There is no early manual removal.
3. Protection thresholds, Gbps figures and bandwidth floors are never quoted
   from recollection; the customer's own asset page is the source.
4. Absence of a Security Center alarm is not proof of no attack, and presence of
   one is not proof that the platform must clean the host.
5. Whether a flood targeted the IP or a domain name cannot be determined; say so.
6. Only the URLs listed in `references/attack-blackhole-diagnosis__evidence-checklist.md` may be cited. If a
   page is not listed, say it could not be sourced.
7. Ticket ids, internal system names and internal process vocabulary do not
   appear in customer-facing output.
8. When the customer forbids an action, that constraint outranks every
   recommendation this skill could make; it is reprinted at the top of the report.

## Security, privacy and authentication failures

* Credentials come from the default chain only. Never ask for, accept, echo,
  store or transmit an AccessKey pair or an account password. If the customer
  volunteers a password in a chat, decline it and tell them to change it.
* A denied read is reported as `NoPermission` or `ImplicitDeny` with the exact
  action name and the minimal policy fragment from
  `references/ram-policies.md`. Never reinterpret a permission denial as "no
  attack found".
* If the identity preflight fails, stop and direct the customer to authenticate
  in their own terminal (the CLI default credential chain); this skill performs no
  credential setup.
* All error text is masked before display: key identifiers, tokens, signatures
  and password-looking pairs become `***`.

## Observability

Every OpenAPI call made by this skill carries a per-run User-Agent so a customer
incident can be traced to one execution:

```
--user-agent "AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}"
```

* `{skill}` is `area:attack-blackhole-diagnosis`, and `{session-id}`
  is `uuid.uuid4().hex`: one 32-character lowercase hex value generated per run
  in `scripts/areas/attack_blackhole_diagnosis/_cli.py` and reused for all calls of that run.
* The same value is printed in the report header next to the account provenance
  tag, so a screenshot, a ticket reply and a log line can be correlated.
* Each call has its own timeout, transient failures (throttling, 5xx, timeouts)
  are retried with capped backoff, and non-transient failures surface
  immediately instead of being retried into a delay.

## Hand-off boundaries

| Instead of this skill, use | When |
|---|---|
| `alibabacloud-mining-attack-diagnosis` | A miner, worm, webshell or backdoor must actually be found and removed |
| `area:instance-state-diagnosis` | The instance will not start, or is stuck between states |
| `area:disk-expand-diagnosis` | Capacity was added but is not visible in the guest |
| `area:resource-bottleneck` | Throughput or latency is below the purchased specification |
| The disk-capacity skill | A volume is full or inodes are exhausted; a full log volume can mimic an attack |
| The customer, self-service | Buying, activating, onboarding a domain onto, and turning on basic protection for Anti-DDoS / WAF / CDN. This is **not** specialist work and must never be described as waiting for a human; the entry point is the corresponding product page in the console |
| Pre-sales, and a ticket for rule work | An Enterprise-edition quote or a solution design is pre-sales; complex custom rule, rate-limit or bot-policy tuning can be raised as a ticket. Basic protection settings stay self-service |
| A human specialist | Appeals to third parties, account freeze, refunds, cross-border or carrier limits, private-tunnel policy, and any cloud-path repair that needs platform-side action |

**Penalty release, stated the same way everywhere in this area.** The release
application is **self-service**: the customer submits it on the penalty record
page after remediating the abuse or the shielded URL. The review conclusion is
decided by the platform, so this skill predicts no turnaround and promises no
fixed number of days. A ticket is only for a rejection that needs a human
re-check.

## References

* `references/ram-policies.md` - the exact read-only actions and the minimal policy.
* `references/attack-blackhole-diagnosis__blackhole-and-blockout.md` - blackhole and scrubbing mechanics, the
  four areas, recovery paths, port 25, account freeze, application-layer floods.
* `references/attack-blackhole-diagnosis__security-group-hardening.md` - rule evaluation order, the known
  false-attack patterns, blocking one address without collateral damage.
* `references/attack-blackhole-diagnosis__intrusion-handoff.md` - reading each alarm, evidence preservation,
  the guest-side read-only commands the customer runs, when to stop.
* `references/attack-blackhole-diagnosis__evidence-checklist.md` - the evidence pack fields and every URL
  this skill is allowed to cite.
