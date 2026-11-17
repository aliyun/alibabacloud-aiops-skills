---
name: alibabacloud-ecs-high-frequency-issues
area: stop-mode-billing-guide
description: |
  Read-only guide for ECS stop modes and for billing of stopped pay-as-you-go instances:
  which resources keep charging, who can use it, and why a restart can fail.
  Use when the customer says:
  stopped the instance but still charged
  no charge on stop not working
  economical mode or normal mode when stopping
  cannot find the economical stop mode option
  is the disk still billed after stopping
  public IP changed after stop and start
  restart failed with sold out in the specified zone
  will my data be lost if restart fails
  Do NOT use for stopping, starting or releasing instances, charge-type conversion, EIP or ICP filing, snapshots, spot interruption, refunds or coupons: those are customer-executed or belong to another skill.
---

# ECS stop mode and stopped-instance billing guide (read-only)

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

## What this skill answers

One symptom area: an Elastic Compute Service instance was stopped, or is about to be,
and the question is what that does to the bill and to the instance.

1. Why a stopped pay-as-you-go instance is still being charged, item by item.
2. Whether a given instance can use economical stop mode at all, from its billing method.
3. Where the mode is chosen, what to disclose before the customer clicks, and how to
   re-read the state afterwards.
4. Why a start failed after economical stop with a sold-out message, and whether the
   data is gone.
5. Why the public IP address changed after a stop and start, and what that means.
6. Where the request stops being this skill's: everything in Boundaries and handoff.

The customer names a symptom, never a root cause. Route on the symptom sentence or the
pasted error text, then read facts, then answer with the rule and its source.

## ABSOLUTE PROHIBITION (read-only boundary)

This skill is read-only and stays read-only.

- Never generate, run or hand over a command that changes a cloud resource: no
  `Stop*`, `Start*`, `Reboot*`, `Modify*`, `Create*`, `Delete*`, `Release*`, `Reset*`,
  `Replace*`, `Attach*`, `Detach*`, `Assign*`, `Convert*` or `Run*` action, in any form,
  including "run this yourself" snippets.
- Never run a command inside an instance, read-only or otherwise.
- Never submit, approve or perform commercial work: refunds, coupons, arrears, invoices,
  filing changes, address recovery.
- Never write an outcome as if the skill did it. No "stopped for you", no "fixed", no
  "confirmed in economical stop mode".
- The only cloud calls allowed are the three reads whitelisted in
  `scripts/areas/stop_mode_billing_guide/_constants.py`, plus the identity check in `scripts/areas/stop_mode_billing_guide/sts_token.py`. The
  transport layer refuses anything else before a process is spawned.

Change-making needs are answered as: prerequisites, the steps, the consequences of
those steps, and then a read-only re-check by this skill.

## Prerequisites and credentials

- A configured command-line client in the running environment, using its default
  credential chain. This package has no credential parameter, no credential file, no
  key prompt and no key in any output; ask for none.
- Read permissions listed in `references/ram-policies.md`: the three ECS read actions
  below, plus `sts:GetCallerIdentity` for the credential probe.
- `RegionId` is required for every call. Nothing is guessed in its place.
- A refused call reports the exact code and the missing action; the literals to expect
  are `NoPermission` and `ImplicitDeny`. Fix the policy and re-run the same read.

Product and action naming follows the client's two modes: RPC products keep PascalCase
action names (`ecs DescribeInstances`, `ecs DescribeInstanceStatus`,
`ecs DescribeAvailableResource`), plugin-mode products take the lowercase-hyphen form
(`aliyun sts get-caller-identity`).

## Observability

Every script run derives one session id with `uuid.uuid4().hex`, a 32-character hex
string, and attaches it as a User-Agent to every single cloud call through the shared
layer in `scripts/areas/stop_mode_billing_guide/_cli.py`:

```
--user-agent AlibabaCloud-Agent-Skills/alibabacloud-ecs-high-frequency-issues/<session-id> skill-version/<skill-version>
```

The template is `AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}`, defined once as
`UA_TEMPLATE` in `scripts/areas/stop_mode_billing_guide/_constants.py`. Each report prints the session id and the
resolved User-Agent in its header, so any line of the answer can be traced to one run
of one account. Requests time out per call (`CLI_TIMEOUT_SECONDS`, and a shorter
`STS_TIMEOUT_SECONDS` for the identity probe); transient service failures get a bounded
backoff retry, and nothing else is retried.

## Execution principle: one entry point

Run only `scripts/areas/stop_mode_billing_guide/ecs_stop_mode_billing_guide.py`. Never assemble a cloud API call by
hand, never call the client directly, never edit the whitelist to make something work.

```bash
# eligibility, billing matrix, disclosures for named instances or a whole region page
python3 scripts/areas/stop_mode_billing_guide/ecs_stop_mode_billing_guide.py assess --region-id cn-hangzhou \
  --instance-ids i-example1,i-example2

# read the power state back after the customer acted in the console
python3 scripts/areas/stop_mode_billing_guide/ecs_stop_mode_billing_guide.py verify-status --region-id cn-hangzhou \
  --instance-ids i-example1

# side-evidence for a restart that failed, plus the customer's own error sentence
python3 scripts/areas/stop_mode_billing_guide/ecs_stop_mode_billing_guide.py check-stock --region-id cn-hangzhou \
  --instance-ids i-example --error-text "The requested resource is sold out in the specified zone"

# the combined report, optionally including the availability read
python3 scripts/areas/stop_mode_billing_guide/ecs_stop_mode_billing_guide.py report --region-id cn-hangzhou \
  --instance-ids i-example1 --with-stock --json

# confirm the credential chain and get the account tag used in report lines
python3 scripts/areas/stop_mode_billing_guide/sts_token.py
```

`report` is the command to quote from when the intent is not obvious. `--json` gives the
same facts in machine form; use it when another step consumes the output. The scripts
write `[WARN]` lines to stderr when a read degrades and keep going, so a partial answer
is never presented as a complete one.

## Workflow: route the intent, then read facts

1. **Get the region and an instance identifier.** Without both, nothing is verifiable.
   Ask for them; do not assume a region.
2. **Read facts** with `assess` or `report`, and add `verify-status` whenever the ticket turns
   on what the instance is doing right now - still charged after a stop, a stop that did not
   take, or a restart that failed. Those three symptoms cannot be answered from the billing
   shape alone: the power state is the read that settles them, and `assess` does not return it.
   If the instance is not returned, say so and ask for the region and account. An empty list
   is not evidence the instance is gone.
3. **Route on intent:**
   - "Can I enable it, how?" -> use the billing method that was read, not the customer's
     memory. Subscription means the option is not offered; pay-as-you-go means the
     console steps in `references/stop-mode-billing-guide__enable-steps-and-prerequisites.md`, with disclosures.
   - "Why still charged?" -> the billing matrix and the continuing items in
     `references/stop-mode-billing-guide__stop-mode-billing-rules.md`; amounts come from the customer's own bill
     page, never from an estimate here.
   - "Restart failed" -> match the pasted sentence against the verified sold-out wording
     in `references/stop-mode-billing-guide__restart-sold-out.md`, add the availability read, answer the data
     question first.
   - "IP changed, I need a fixed one, filing affected" -> state the release rule, then
     hand off; address recovery is not possible from here.
   - "Stop charging completely" -> the three-state table; only release ends instance
     charging, and release destroys data, so back up first.
   - Anything in the handoff table -> boundary sentence plus the owning topic.
4. **Re-check only what a read can show**: the power state, again after the customer acted.
   The stop-mode marker is not one of them.
5. **Answer** with facts, rule, source, check date, limitations, then the script's
   `STATUS` and `NEXT_ACTION` tail.

## Known blind spots and degradation

Declare these; do not paper over them.

- **Stop-mode marker**: not readable through any verified read-only field claimed by
  this package. The customer reads it on the instance page or sends a screenshot. A
  changed power state proves the click landed, never which mode was chosen.
- **Billed amounts**: no billing action exists here, so amounts come from the customer's
  bill detail page only.
- **Public bandwidth under economical stop**: the source material conflicts, so the
  matrix row is marked unresolved. Say what is settled (the address is released), name
  the open point, and check the cited document online before quoting a value.
- **Visibility**: current credential, one region per call. Cross-account instances and
  unqueried regions are invisible, not absent.
- **Stock**: dynamic and partial; never a promise about a future start.
- **Document currency**: rules move. Verify the cited page at answer time and put the
  date in the answer.

When any needed fact is missing, the report ends `STATUS: DEGRADED` and the answer
carries the matching limitation and self-check path instead of a conclusion.

## Answer contract

- Quote only values that were actually read, and label rule statements as rules.
- Declare every auto-filled input the report names, such as a zone taken from the
  queried instance or the `DestinationResource` default.
- Keep the standing clarifications for recurring misreadings: stopped is not released;
  economical stop is not free; the mode is pay-as-you-go only; being able to read a
  value is not being able to change it.
- Attach sources with a check date, and the bill self-check entry for money questions.
- End with the script's `STATUS: OK|DEGRADED|FAIL` and `NEXT_ACTION` lines, unedited.
- Never claim an action was performed, and never ask for credentials.

## Boundaries and handoff

`references/stop-mode-billing-guide__handoff-boundaries.md` carries the recognition table and the wording for a
fixed public address or filing case, snapshot and image work, network unreachability (a
diagnosis topic such as `alibabacloud-ecs-vpc-publicnetwork-troubleshoot` owns it), spot
interruption, scheduled start and stop, refunds and arrears, and in-guest questions.

## References

- `references/ram-policies.md` - the exact read actions, the minimal policy, refusal handling.
- `references/stop-mode-billing-guide__stop-mode-billing-rules.md` - three states, continuing items, blind spots, sources.
- `references/stop-mode-billing-guide__enable-steps-and-prerequisites.md` - prerequisites, where the option is, disclosures.
- `references/stop-mode-billing-guide__restart-sold-out.md` - verified sold-out wording, side-evidence, ways out.
- `references/stop-mode-billing-guide__handoff-boundaries.md` - hard boundaries, handoff table, missing-data wording.
