---
name: alibabacloud-ecs-web-service-runtime-config

description: |
  Diagnose ECS web service and runtime environment faults: Nginx, Apache, IIS or FTP
  sites that will not start or serve; Java, PHP, Python, Node.js or .NET runtime
  mismatch; Docker and Kubernetes deployment; WordPress site environment.
  Use when the site will not open although the service looks installed.
  Triggers: website not accessible, web service not starting, application pool stopped, container loses data after restart, image pull timed out, Connection refused, Connection reset, err_cert_date_invalid.
  Do NOT use for disk capacity, inode exhaustion, instance state, disk IO, network path, billing, ICP filing, security cleanup or extension installs (see alibabacloud-ecs-install-extension).
---

# ECS Web Service and Runtime Environment Configuration

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Routed by symptom, answered with evidence. The customer reports what they see -
"the site will not open", "the application pool keeps stopping", "the container
loses the database after each restart" - and this skill turns that sentence into a
checked or rejected list of causes, each line tagged with where its fact came from.

Two situations in this problem domain cannot be settled from cloud APIs at all:
whether something is actually listening, and on which address; and what the
runtime, the configuration or the service log says. Those need a reading from
inside the instance, which is why this skill is not limited to cloud-side queries.

## What this skill does

1. Collects the instance baseline: state, OS name and type, image id, instance
   type with vCPU and memory, region, addresses, security groups.
2. Checks the inbound port rules, which is the cheapest thing to falsify and the
   most frequent finding in this problem domain - the rule is often absent even
   when the customer is certain it was added.
3. Records the documented platform behaviours that are mistaken for faults, before
   anything is dug into.
4. Interprets the quoted error string, including what it does **not** license the
   report to conclude.
5. Reads monitoring values and disk attachment metadata when, and only when, a
   resource shortage is a plausible cause of the service failure.
6. Collects in-instance observations, either gated through Cloud Assistant or as a
   command for the customer to run and paste back, depending on the approval state
   of that observation.
7. Emits manual steps, in cost order, with the official page for each one.

## What this skill never does

It repairs nothing and configures nothing on the customer's behalf. It does not
enter an instance to apply a setting, and it does not answer sales, pricing or
discount questions - those go to the commercial channel with no diagnosis attempted.

**ABSOLUTE PROHIBITION.** This skill must never call, generate, or hand the
customer a command that:

* starts, stops or reboots an instance, or detaches a disk;
* creates or changes a security group rule, in any direction, on any port;
* deletes or empties a file, truncates a log, redirects into a file, or formats,
  repartitions, repairs or resizes a filesystem;
* kills a process, or starts, stops, restarts, reloads, enables or disables a
  service (`systemctl`, `service`, `iisreset`, `taskkill`, `sc`);
* removes an IIS module, role or feature, or edits `applicationHost.config`;
* changes a container restart policy, recreates or removes a container, or moves a
  data directory;
* deletes a snapshot, resizes a disk, or requests a refund or downgrade.

Each of those belongs in the report as a numbered manual step, with its risk stated
and with "this is not guaranteed to resolve the issue" where that is true. A change
that the customer applies themselves is still not this skill's call to make.

## Permission model and execution gates

This skill declares two writing cloud API operations. It is deliberately not
presented as query-only, because a reading taken inside the instance and a
rollback point taken before a manual repair are both part of how this problem
domain is actually solved.

| Gate | What runs | Condition |
|---|---|---|
| T1 | `sts:GetCallerIdentity`, `ecs:DescribeInstances`, `ecs:DescribeSecurityGroupAttribute`, `ecs:DescribeDisks`, `ecs:DescribeInvocations`, `cms:QueryMetricLast` | automatic; no customer-facing effect |
| T2 | `ecs:run-command` | announce, then confirm; one approved non-mutating command per call |
| T3 | `ecs:create-snapshot` | announce, then confirm, including the billing note |

**T2 and T3 are mandatory stop points.** Before either call, state in plain
language: which single command or resource is involved, its scope, whether it
changes anything, what happens if it fails, and that the confirmation covers this
one call only. Then wait for the customer's agreement and pass it to the script
with `--confirmed "<what they agreed to>"`. Without it the script issues nothing
and returns `STATUS: DEGRADED`; that is the designed outcome of a declined
confirmation, not an error to retry around.

**Only whitelisted commands may be dispatched.** `ecs:run-command` is issued only
for an observation whose approval state is `approved` in
`references/web-service-runtime-config__guest-observation-commands.md`, and only after the resolved command
passes both a whitelist and a side-effect blacklist in
`scripts/axes/web_service_runtime_config/_constants.py`. Chaining with `|`, `;` or `&` is rejected. A command that
is rejected is reported as rejected; it is never reworded until it slips past the
guardrail, and it is never replaced by an invented equivalent.

**Observations that are not yet signed off are handed to the customer.** Several
observation points this tier needs - listen address, service state, configuration
syntax, log tail, runtime version, container restart policy and mounts - are not in
this batch's approved command set. Those are printed as the exact command line for
the customer to run and paste, and the item is recorded as unread with
`STATUS: DEGRADED`. Do not paraphrase them, and do not present the gap as a
finding.

**Snapshot first, before any manual repair step.** A step that touches files,
system libraries, roles or a data directory requires a snapshot that already
exists. Quote the capacity-and-duration cost, and say that removing the snapshot
afterwards is itself a manual step. Pure evidence collection does not require one.

## Prerequisites

* The Alibaba Cloud CLI on `PATH`, signed in through its own default credential
  chain. This skill never asks for, reads, prints, writes or stores credentials,
  and has no credential arguments of any kind. If the identity pre-flight fails,
  the guidance is to reconfigure the CLI (the CLI default credential chain) and nothing else.
* Python 3, standard library only. See `scripts/requirements.txt`.
* `ecs:run-command` requires the Cloud Assistant agent present and online in the
  instance. When it is not, fall back to the customer-run reading; do not retry a
  dispatch that the agent cannot receive.
* Region and instance locator (instance id, or the public address to look it up
  by). Every branch needs them; asking for them first is the shortest path in this
  problem domain.

**Locator rule (MANDATORY).** When the customer supplies neither an instance id nor
a public address, do not list or enumerate the account's instances to find a
candidate, and never substitute a different instance. Do one of two things instead:
ask for the locator, or answer with the platform fact that settles the symptom
without a cloud read (for example, a container's writable layer is destroyed when
the container is recreated, so data must live in a named volume or a bind mount)
plus the exact in-guest read checklist. Name the missing locator as the confirmed
blocker. Enumerating a fleet costs the whole turn budget and still cannot identify
the customer's machine.

## Observability

Each run of an entry script generates one 32-character hexadecimal session id
(one run, one id, shared by every cloud call of that run) and attaches it to
every cloud call, so a whole investigation can be traced as one unit. The UA
template is:

```
AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}
```

issued on every call as the `--user-agent` flag, where `{skill}` is the skill
name `alibabacloud-ecs-high-frequency-issues: web-service-runtime-config` and `{session-id}` is the
run's 32-character lowercase-hex session id.

The template and the flag are defined once, in `scripts/axes/web_service_runtime_config/_cli.py` and
`scripts/axes/web_service_runtime_config/_constants.py`, and applied at every call site rather than per command.
The session id is echoed in the report header and may be pinned across the calls
of one investigation with `--session-id`.

## Running it

`scripts/axes/web_service_runtime_config/web_service_runtime_config.py` is the only entry point. Run it as
presented; do not assemble CLI calls by hand, because the guardrails, the gates,
the per-call timeouts, the retry policy and the credential masking all live in the
scripts.

```
python3 scripts/axes/web_service_runtime_config/web_service_runtime_config.py report \
  --region-id cn-hangzhou --instance-id i-xxxxxxxx \
  --symptom "nginx is running but the site will not open" \
  --error-string "Connection refused" --port 443

python3 scripts/axes/web_service_runtime_config/web_service_runtime_config.py guest-plan --scenario B
python3 scripts/axes/web_service_runtime_config/web_service_runtime_config.py guest-run --region-id cn-hangzhou \
  --instance-id i-xxxxxxxx --check disk-space-facts \
  --confirmed "customer agreed to one disk usage query on this instance"
python3 scripts/axes/web_service_runtime_config/web_service_runtime_config.py snapshot --region-id cn-hangzhou \
  --disk-id d-xxxxxxxx --confirmed "customer agreed to one snapshot before the repair"
python3 scripts/axes/web_service_runtime_config/web_service_runtime_config.py knowledge
python3 scripts/axes/web_service_runtime_config/sts_token.py check
```

* `report` - the normal entry point: baseline, routing, inbound rules, expected
  behaviours, error-string reading, resource area, observation plan, manual steps.
* `guest-plan` - which observations a route needs, each with its approval state.
  Makes no cloud call.
* `guest-run` - one approved observation on one instance, behind the T2 gate.
* `snapshot` - one snapshot, behind the T3 gate. Never deletes anything.
* `knowledge` - the embedded tables, for offline reading and for review.
* `--plan-only` prints the calls a run intends to make and issues none of them.
  Use it whenever the customer wants to see the plan before agreeing to it.

## Workflow

The executable form is in `references/web-service-runtime-config__decision-tree.md`. The order is the order of
cost, and it is the order that produced the fewest wasted rounds in this tier's
evidence:

1. **S0 baseline.** Identity, then the instance. If the instance is not `Running`,
   the diagnosis stops there and moves to the lifecycle area: while the guest
   releases processes and flushes memory, nothing can be dispatched and no service
   can answer, so both symptoms are expected rather than faults.
2. **S1 routing.** Match the customer's own words against the five areas, and run
   two filters at the same time: handoff (this belongs to another owner, say so now
   rather than after a full investigation) and expected-behaviour (a documented
   mechanism that looks like a fault, ruled out before digging).
3. **S2 branches.** Runtime and OS compatibility; service startup and
   configuration; reachability; resource pressure; containers; the quoted error
   string. For reachability the fixed order is inbound rule, then listen address,
   then a self-test from the instance itself, and only then the service
   configuration.
4. **S3 gate.** Snapshot before any manual repair step.
5. **S4 output.** What was queried, what was observed and by whom, what remains
   unread with the command or question that would settle it, then the manual steps.

Two rules bind the whole flow. Do not name a root cause before the error text or
the configuration has actually been read: in one ticket an interpreter override was
blamed, and a Python 2 print statement in the customer's own script turned out to
be the entire problem. And where the evidence reached no conclusion, output
candidates with the split that would decide between them - never the ticket summary
that guessed. In particular, "the platform intercepted it" is not a conclusion this
skill offers; it self-tests from inside the instance, splits on the result, and
sends the platform-side question to a human queue.

## Output contract

The final answer restates the script's own `Summary`, `STATUS` and
`NEXT_ACTION` lines. It quotes only values a call returned, names every value the
run filled in itself, and never substitutes a plausible number for a missing one.

* `STATUS: OK` - the evidence list is complete enough to act on.
* `STATUS: DEGRADED` - at least one item is unread; the report names the command or
  the question that settles it. This covers a declined confirmation, an offline
  agent, a pending whitelist entry, an absent monitoring datapoint, and a Windows
  instance, where no in-instance query is approved in this batch.
* `STATUS: FAIL` - the report cannot be used yet, typically a wrong region or an
  instance that was not found.

A monitoring metric that returned nothing is not evidence that the resource is
normal. Memory metrics in particular may need a guest agent installed before they
report at all, so absence is stated as absence.

## When a call comes back denied

Name the exact RAM action that is missing and quote the least-privilege fragment
from `references/ram-policies.md`. The two wordings used for a denial in this skill
are `NoPermission` and `ImplicitDeny`. An identity that resolves to the wrong
account is a different failure from a missing action, and the report says which one
it saw. Never widen a policy to a product wildcard to make a denial go away.

## Handoffs

Out of scope, identified and passed on with one sentence and the right owner rather
than investigated here: disk capacity and inode, disk IO performance, disk
expansion, instance lifecycle and scheduled start/stop, network path and carrier
blocking, bandwidth arrears, ICP filing, security incident cleanup, RAM
authorization, cross-platform migration, backup scope, cluster node scaling, and
third-party control panels, which are not Alibaba Cloud products. The full table,
with the boundary wording for each, is in `references/web-service-runtime-config__handoff-matrix.md`.

## References

* `references/web-service-runtime-config__decision-tree.md` - the symptom-led branch order, node by node.
* `references/web-service-runtime-config__guest-observation-commands.md` - approval state of every in-instance
  observation, the confirmation gate, and the guardrail.
* `references/web-service-runtime-config__os-runtime-support.md` - which runtime on which release, including
  where there is no official statement.
* `references/web-service-runtime-config__non-fault-mechanisms.md` - documented platform behaviour that is
  reported as a fault.
* `references/web-service-runtime-config__handoff-matrix.md` - what belongs to another owner, and how to say so.
* `references/web-service-runtime-config__help-docs.md` - the verified official pages, and the topics still
  awaiting a URL.
* `references/ram-policies.md` - the actions this skill calls, their gates, and the
  least-privilege fragment.
