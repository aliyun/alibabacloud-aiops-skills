---
name: alibabacloud-ecs-swas-boundary-guide
description: |
  Read-only boundary guide for Alibaba Cloud Simple Application Server (SWAS):
  attributes an instance id or IP to SWAS vs ECS via whitelisted Describe APIs,
  then answers the matching product-boundary rule (product form, plan wording,
  migration and region limits, SSH vs RDP, promo and refund rules) and routes
  out-of-scope in-guest faults to another skill.
  Triggers (use when the customer says any of):
  - simple application server / SWAS / lightweight server
  - is my lightweight server physical; what does 2 core 2G mean
  - can I convert my simple application server to ECS; can I move region
  - remote desktop cannot connect; file-transfer function unavailable
  - promo price gone after refund; overseas site slow from mainland China
  Do NOT use for disk IO slowness, resize not applied, instance state or
  in-guest usage (alibabacloud-ecs-disk-io-diagnosis, alibabacloud-ecs-diagnose).
---

# Simple Application Server (SWAS) Product-Boundary Guide

## 1. What this skill is for

Customers of Simple Application Server (SWAS) almost never have a broken
product -- they have a **wrong expectation about the product's boundary**. They
take a SWAS instance for an ECS instance or a physical machine, expect a
seamless conversion between the two product lines, expect to move an instance
to another region, expect Remote Desktop on a Linux image, or expect a
new-customer price to survive a refund. A small remainder are genuine in-guest
faults (memory pressure, disk IO saturation, intrusion, keyboard/input
failures) that this skill must **recognise and hand off**, never diagnose.

This skill therefore provides seven read-only capabilities:

1. **Attribution** -- is this instance id / IP a SWAS instance, an ECS
   instance, or not found under the current credential and region.
2. **Boundary-rule wording** -- a fixed, evidence-backed answer for each
   product-boundary question, with its official documentation link.
3. **Migration path planning** -- preconditions first (target system disk vs
   source system disk), then the correct image path or the manual fallback.
4. **Connection-method matching** -- which tool actually fits the installed OS,
   with the data-loss warnings that must precede any OS change.
5. **Reachability self-evidence guidance** -- how the customer collects
   multi-node probe evidence themselves, and what the boundary of an online
   check is.
6. **Commercial-rule explanation and escalation** -- quote the rule, never
   transact.
7. **Out-of-scope detection and handoff** -- route to the adjacent skill or the
   human support channel with the context attached.

The evidence base is 499 SWAS support tickets plus the read-only APIs verified
for this tier. Rules derived only from a ticket *summary* (the full dialogue was
not re-verified) are marked as such by the script and must be presented as
ticket wording, never as an official policy quote.

## 2. Operating model: read-only

This skill is **read-only**. It answers questions and guides a human through
the console. Every output is evidence-based or knowledge-based; nothing is
inferred from model memory about prices, quotas or eligibility.

### ABSOLUTE PROHIBITION

- NEVER call, write, generate, or hand a human a mutating OpenAPI action. Only
  the four read actions in the whitelist table below may ever be invoked; every
  other action is out of bounds by construction. The mutating verb families
  (modify, create, delete, release, reset, replace, attach, detach, reboot,
  start, stop, run, invoke, put, import, export, revoke, bind, unbind) are
  refused, not merely discouraged.
- NEVER run diagnostics inside a customer instance: no command execution, no
  remote shell, no workbench or agent session, no in-guest read of any kind.
- NEVER perform or simulate a commercial action: no refund, no price quote, no
  eligibility restore, no order, no resource removal on the customer's behalf.
- NEVER execute a migration, an image operation, an OS change or a plan change.
  The steps this skill prints are performed by the customer in the console.
- NEVER hand-write an `aliyun` CLI command. All cloud access goes through the
  single entry script below, which enforces the read-only whitelist at the code
  layer. A request outside the whitelist is refused, not worked around.
- NEVER state an API reading, a price, a disk size, a document URL or a root
  cause that is not present in the script output or in `references/`. When a
  check could not run, say so.

The only cloud actions this skill may invoke are these four read APIs, and no
others:

| Product | Action | Purpose |
|---|---|---|
| `ecs` | `DescribeInstances` | attribute an id/IP, read region, instance type and family, CPU/memory, image OS name and type, charge type, expiry, security groups |
| `ecs` | `DescribeInstanceStatus` | cross-check the running state of the identified instance |
| `ecs` | `DescribeAvailableResource` | check whether a migration target region / instance type is purchasable |
| `sts` | `GetCallerIdentity` | verify which account the credential belongs to; derive the UID label |

`scripts/axes/swas_boundary_guide/_cli.py` refuses every other product and action before a process is
spawned, so a mistake upstream cannot turn this skill into a mutating one.

## 3. Prerequisites

1. Alibaba Cloud CLI 3.x installed and configured with the default credential
   chain (`aliyun configure`). The scripts never accept, read, print or store a
   key pair; see `references/ram-policies.md` for what the identity needs.
2. The minimal read-only policy in [references/ram-policies.md](references/ram-policies.md)
   attached to that identity. If a call is refused, report the missing action
   with the `NoPermission` / `ImplicitDeny` wording and the policy snippet;
   never widen the policy and never retry around the refusal.
3. The customer's identifier: an instance id (ECS ids start with `i-`, SWAS ids
   are 32-character hex strings) or an IPv4 address, plus the region if known.

## 4. Execution principle

Run the entry script; do not assemble CLI calls yourself.

```bash
python3 scripts/axes/swas_boundary_guide/swas_boundary_guide.py --identify --instance-id i-bp12abcd34efgh67ab --region cn-hangzhou
```

Read the printed `STATUS:` and `NEXT_ACTION:` lines and relay them faithfully.
Use `--json` when you need to consume the result programmatically.
`python3 scripts/axes/swas_boundary_guide/sts_token.py` answers the narrower question "which account am
I looking at?" on its own.

### Mode selection (decision tree)

```
customer wording / identifier
+-- "which product is this", id or IP given        -> --identify
+-- product form, spec wording, plan meaning       -> --rules --topic product-identity | spec-terminology
+-- convert to ECS, move region, migrate, price
|   gap after migration                            -> --migration-check
+-- cannot connect, remote desktop, switch OS      -> --connect-check  (or --identify first to read OSType)
+-- slow or unreachable from another country       -> --rules --topic network-access  (+ probe link)
+-- promo price, refund, expiry, removal ask       -> --rules --topic commerce | lifecycle
+-- in-guest symptom (memory, IO, boot, intrusion) -> --refer  (classify and hand off; do not diagnose)
```

### Modes

| Mode | What it does | Cloud calls |
|---|---|---|
| `--identify` | Product attribution plus read-only ECS attributes and status; SWAS ids are attributed by id form and degrade to console self-service | `DescribeInstances`, `DescribeInstanceStatus`, `GetCallerIdentity` |
| `--rules` | Prints the embedded boundary-rule cards for one topic, each with source ticket ids and verified documentation links | none |
| `--migration-check` | Capacity precondition (target system disk >= source), path selection (cross-region image copy vs share/export to ECS vs manual fallback), standing cost and filing warnings, optional target-region availability lookup | `DescribeAvailableResource` (only with `--target-region`) |
| `--connect-check` | OS-to-connection-method matrix, mismatch verdict, and the three mandatory warnings before any OS change | none |
| `--refer` | Out-of-scope symptom classification and the handoff target, with the context checklist the handoff must carry | none |

## 5. Output contract

Every run ends with exactly two contract lines:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <the single next step the agent must take>
```

- `OK` -- the requested judgement was produced from API readings and/or the
  embedded knowledge base.
- `DEGRADED` -- at least one check could not be completed. Present the
  `Graceful degradation log` verbatim as the limitation of the answer; never
  fill a gap with an assumption.
- `FAIL` -- a blocking prerequisite is missing (no identifier, unusable input,
  or the credential cannot query at all). Ask the customer for the missing item
  or point at the read-only policy; do not guess.

In the final answer:

1. Report only values the script printed, and name the region and account UID
   it used (both are declared in `Auto-filled parameters` when defaulted).
2. Give the boundary rule and the documentation links the script printed. Do
   not add any other URL. Links marked "no verified link" in `references/` stay
   unpublished: describe the console path instead of citing a guess.
3. Keep every recommendation manual-guidance only, with the console entry named.
4. Where online support itself could not settle the matter (cross-border
   disputes, eligibility restoration, price negotiation), say so plainly and
   escalate with the evidence list. Matching human support is the honest
   result; promising more is fabrication.

## Observability

Each script run generates one 32-character hexadecimal session id
(`uuid.uuid4().hex`) at start-up and attaches it to **every** API call of that
run as a User-Agent, so all calls belonging to one boundary check correlate:

```
--user-agent AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}
```

where `{skill-name}` is `alibabacloud-ecs-swas-boundary-guide` and
`{session-id}` is the 32-character hex value above. The session id is printed
to stderr as `[_cli] session-id: <value>`. It carries
no customer data. Every invocation additionally runs with an argument list
(never a shell), a per-call timeout, `stdin` detached, bounded retries with
backoff on transient throttling or server-side failures, and credential-value
masking applied to all error text before it can reach a log line or report.

## 7. Known limits (state these when they bind)

- **No SWAS-side read API is verified for this skill.** The ECS read surface
  cannot see SWAS resources, which is exactly what real tickets show. SWAS
  attribution is by id form; SWAS attributes (plan, disk size, image, expiry)
  are read by the customer in the SWAS console. Never claim API-verified
  numbers for a SWAS instance id.
- **No billing-side read API is verified.** Expiry, renewal and unsubscribe
  states degrade to console self-service guidance.
- **No monitoring metrics are read.** Bandwidth-throttling and resource-
  contention claims stay as product-positioning wording plus a support ticket,
  not as a measurement.
- **The customer's side is invisible**: local network, local security policy,
  and what they click in their Remote Desktop client. Give the self-check steps
  and stop there.
- **Prices and eligibility are never decided here** -- only the published rule
  is quoted and the commercial channel is offered.

## 8. Handoff map

| Symptom family | Handoff target |
|---|---|
| Disk resized but the capacity or partition did not take effect | `alibabacloud-ecs-disk-expand-diagnosis` |
| Instance stuck in a lifecycle transition or will not boot | `alibabacloud-ecs-instance-state-diagnosis` |
| Disk IO at the ceiling, performance below the quoted spec | `alibabacloud-ecs-disk-io-diagnosis` |
| In-guest memory, disk or inode consumption | `alibabacloud-ecs-diagnose` (resource-usage diagnosis) |
| Suspected intrusion or cryptomining | security handling channel, with the detection source cited |
| Refund, eligibility restoration, negotiation, removal on the customer's behalf | human sales / support ticket channel |
| Cross-border reachability dispute after both sides checked | support ticket with the probe evidence attached |

Always attach the handoff context the `--refer` output lists: attribution,
instance id, region, OS type, status, and what was already checked here.

## 9. Customer-facing wording rules

- Answer the boundary question first, then the technical one. A customer who
  believes the product is at fault needs the rule stated before any troubleshooting.
- Warn **before** an irreversible step, not after: an OS change erases the
  system disk, and a refund forfeits new-customer pricing permanently.
- Never assert a cause without evidence. If a customer demands proof of a
  detection or a throttling claim, cite where the reading came from or state
  that this skill does not collect it.
- Never promise an outcome owned by a commercial or offline engineering
  process; offer the channel and the evidence list instead.

## 10. References

- [references/swas-boundary-guide__boundary-rules.md](references/swas-boundary-guide__boundary-rules.md) -- the rule
  cards by topic, each with its source tickets and verified links.
- [references/swas-boundary-guide__migration-paths.md](references/swas-boundary-guide__migration-paths.md) -- first
  principles, path matrix, verdict logic, manual fallback.
- [references/swas-boundary-guide__connect-methods.md](references/swas-boundary-guide__connect-methods.md) -- OS-to-tool
  matrix, the two different OS-change console entries, mandatory warnings.
- [references/swas-boundary-guide__commerce-rules.md](references/swas-boundary-guide__commerce-rules.md) -- promotion and
  refund wording, lifecycle self-service, escalation wording.
- [references/ram-policies.md](references/ram-policies.md) -- the minimal
  read-only policy, action by action, and what is deliberately not granted.
