---
name: alibabacloud-ecs-high-frequency-issues
area: bandwidth-modify-guide
description: |
  Reads an ECS instance's live public bandwidth, bandwidth billing mode and public IP, then guides bandwidth increase or decrease, conversion between fixed bandwidth and pay-by-traffic, temporary peak-hour upgrade, and public IP replacement through the EIP path. It sends only Describe and Get calls; changes, orders and refunds stay with the customer in the console.
  Use when the customer says: increase ECS public bandwidth; lower bandwidth to 2 Mbps; bandwidth capped at peak hours; switch fixed bandwidth to pay-by-traffic; order paid but bandwidth unchanged; need restart after bandwidth change; change the ECS public IP; NoPermission when changing bandwidth.
  Do NOT use: CPU or memory resize activation, disk capacity or partition growth, disk IO performance, boot or shutdown state, or packet loss while bandwidth is not saturated.
---

# ECS bandwidth change and billing-mode guide

> **Delivery override - outranks every relay instruction and template below.** `STATUS`,
> `NEXT_ACTION` and their `OK` / `DEGRADED` / `FAIL` / `BLOCKED` values are the entry script's
> internal run state, not a delivery format. Where this document says to relay, mirror or copy
> those lines "faithfully" or "verbatim", relay their MEANING in the customer's own words: never
> write the keys or the bare values into the reply or into anything saved under `outputs/` or
> `ran_scripts/` (SKILL.md rule 3h). A layer this run did not read is named in the customer's own words - which layer, and what would have settled it.

Helps a support engineer or a customer answer, in one pass, the questions that cluster around
ECS public bandwidth: can this value be changed, how does it take effect, what does the billing
mode mean, what happens to money already paid, and what has to be done by hand in the console.

The skill gathers facts from the cloud side with query APIs, prints them as evidence, and then
hands over a guided, documented path. It does not change anything.

## Permission model

This is a query-and-guide skill. Its mutation surface is empty by design, and it does not claim
any blanket exemption label either. The concrete rules below are what actually bound it.

1. **Automatic surface (no per-call approval needed).** Query APIs only, enumerated in
   [references/ram-policies.md](references/ram-policies.md) and
   [related_apis.yaml](related_apis.yaml). Every call is issued by the entry script.
2. **Guest-side command execution is off by default.** Bandwidth and traffic figures live on the
   cloud side, so this tier ships no in-instance command path at all. If a future revision ever
   adds one, the gate below applies unchanged.
3. **Confirmation gate (mandatory, forward looking).** Before executing any in-instance command or
   any mutating call, the agent MUST tell the user, in the same message, what will run, its
   blast radius on the running business, and whether it is reversible, and MUST obtain an explicit
   yes. No silent execution, no batching an unapproved call with an approved one.
4. **Out of scope permanently.** Refunds, unsubscriptions, downgrades that release resources,
   EIP release, price quotations, instance power actions. These are business or console actions;
   the skill only explains and routes.

## ABSOLUTE PROHIBITION

The agent MUST NOT construct, submit, or execute a mutating call, and MUST NOT hand the user a
command line that performs one. Prohibited action-name families for every product this skill
touches: Modify, Create, Delete, Release, Allocate, Associate, Unassociate, Convert, Renew,
Import, Revoke, Attach, Detach, Start, Stop, Reboot, Reset, Replace, Put, and `RunCommand`
in particular.

Concretely, the operations that appear in this tier's tickets are all **console actions the
customer performs**, and the skill only guides them there: changing the bandwidth value,
converting the bandwidth billing mode, temporary bandwidth upgrade, converting a fixed public IP
into an EIP, applying / binding / unbinding / releasing an EIP, snapshot creation, renewal with a
configuration change, unsubscription and refund.

Anything not in the enumerated query surface is refused, with the reason and the console entry
point stated. The agent MUST NOT invent an API name, a parameter name, or a response field to
make a case fit; it reports the gap instead.

## Execution principle

Run the single entry script. Do not assemble `aliyun` command lines by hand, do not call the
cloud APIs directly, and do not pipe the script's output through another tool.

```
python3 scripts/areas/bandwidth_modify_guide/bandwidth_modify_guide.py --region-id cn-hangzhou --instance-id i-xxxx
```

Useful switches:

| Switch | Effect |
| --- | --- |
| `--region-id` | required, the region that owns the instance |
| `--instance-id` | one instance; repeatable; omit to survey the whole region |
| `--intent` | narrows the guidance block that is printed (see below) |
| `--with-eip` | also queries EIP records for the matched instances |
| `--check-stock INSTANCE_TYPE` | adds a sellability lookup before a resize |
| `--expected-bandwidth N` | the value the customer ordered; drives the effectiveness comparison |
| `--page-size` | survey page size, default 50 |
| `--json` | machine readable evidence payload |
| `--timeout`, `--retries` | per-call CLI budget and backoff |

Intents: `survey`, `resize`, `not-effective`, `billing-convert`, `ip-swap`, `temp-upgrade`,
`cost-rule`, `triage`. Each maps to one row of the decision tree.

## Observability

Every CLI invocation carries a per-run user agent so that a session can be traced end to end:

```
--user-agent AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}
```

`{skill}` resolves to this skill's name (`area:bandwidth-modify-guide`);
`{session-id}` is a 32-character hex string generated once per script run from
`uuid.uuid4().hex` and reused for all calls of that run, including retries. The account id from
`sts:GetCallerIdentity` is appended as a `uid=<digits>` tag on the report header. Credentials are
resolved exclusively through the default credential chain; the code never reads, prints, stores or
forwards an access key pair, and all error text passes through a redaction filter first.

## Authentication and pre-flight

1. The script starts with `aliyun sts get-caller-identity` (plugin-mode, lower-case hyphenated
   form) to confirm the credential chain resolves.
2. If it fails, tell the user to verify the default credential chain with `aliyun sts get-caller-identity` and stop. Do not ask for an access key id
   or secret, do not accept them in chat, do not export them into the environment.
3. If an individual query is denied, name the missing action and paste the minimal policy snippet
   from [references/ram-policies.md](references/ram-policies.md). The literals to quote are
   `NoPermission` and `ImplicitDeny`.
4. `RegionId` is mandatory for `ecs` and `vpc` calls and is never guessed. If the user did not
   state it, ask once; if the survey is empty, say so and list the regions already checked.

## Decision tree

The first two columns are facts the script prints; the guidance is what the agent says afterwards.

### 1. Triage: is this a bandwidth question at all

Facts: `DescribeInstances` (status, instance charge type, bandwidth billing mode, outbound and
inbound bandwidth, public IP or EIP) plus `DescribeInstanceStatus` when the state matters.

* Customer reports slow access and the configured bandwidth is small or the peak window is named
  → go to 4.
* Customer reports paid order but the old value is still displayed → go to 2.
* Customer wants a different public IP address → go to 3.
* Customer asks what it will cost → go to 5.
* Bandwidth is nowhere near the cap and the symptom is packet loss or ping timeout → this is not
  a bandwidth question; use [references/bandwidth-modify-guide__handoff-matrix.md](references/bandwidth-modify-guide__handoff-matrix.md) and hand
  off with the verified facts attached.

### 2. Does the change take effect, and is a restart needed

This is the single most common misunderstanding, and the two areas have different answers:

* **Public bandwidth value**: takes effect without an instance restart. Do not tell the customer
  to reboot for a bandwidth-only change.
* **CPU and memory specification**: takes effect only after the instance restarts. Before that
  restart, advise off-peak timing, stopping the application so buffers are flushed to disk, and
  taking a snapshot first; snapshots are billed.
* **Paid order is not the same as an effective configuration.** Read the live values and compare
  them with what the customer expected. If they still differ, the order path is a backend
  synchronisation question, not a bandwidth-configuration question: escalate a ticket carrying
  order id, instance id, region, expected value and the live value the script printed.

### 3. Changing the public IP

A fixed public IP assigned to an ECS instance cannot be edited in place. The only self-service
route is the five-step EIP path, with three pre-flight caveats and one closing check, all in
[references/bandwidth-modify-guide__eip-swap-runbook.md](references/bandwidth-modify-guide__eip-swap-runbook.md). The script reads
`DescribeEipAddresses` so the agent can state whether the instance already has an EIP, and can
re-check after each customer step.

### 4. Peak-hour saturation: temporary upgrade or permanent upgrade

* Periodic, short peaks (a couple of windows per day) → temporary bandwidth upgrade from the
  console, plus the periodic maintenance task in OOS for a repeating schedule.
* Sustained growth → a normal bandwidth upgrade.
* **Cancelling a temporary upgrade that has not taken effect**: there is no separate order-cancel
  entry. The same **Change Bandwidth** page is the cancel route — set the value back to
  the original bandwidth there and do not set it to 0. Ticket `T-EBA03F4B` (2026-09) confirms this
  and shows the cost of the opposite claim: saying "no cancel entry exists" leaves the customer
  stuck. If the upgrade is already in effect, treat the cancel as a normal bandwidth change with
  billing consequences and use the console preview before quoting any amount.
* Inbound bandwidth follows the outbound value: below 10 Mbit/s purchased outbound the inbound
  ceiling is 10 Mbit/s; above 10 Mbit/s the inbound value equals the purchased outbound value.
* The exact minimum and maximum duration of a temporary upgrade is **not asserted here**; it is a
  published parameter that must be read from the official page and the console selector at the
  time of the case. See [references/bandwidth-modify-guide__evidence-gaps.md](references/bandwidth-modify-guide__evidence-gaps.md).

### 5. Money, discounts and price difference

Two orthogonal dimensions confuse almost every ticket: the **instance charge type**
(subscription versus pay-as-you-go) and the **bandwidth billing mode** (fixed bandwidth versus
pay-by-traffic). A subscription covers the instance, system disk and image licence;
pay-by-traffic bandwidth is billed afterwards. [references/bandwidth-modify-guide__bandwidth-billing-matrix.md](references/bandwidth-modify-guide__bandwidth-billing-matrix.md)
is the lookup table.

Hard rule: **the skill never states a number for a refund, a price difference, a configuration
fee or a renewal total.** Not even an illustrative one outside the documented examples, and any
quoted example must carry "subject to the live billing page". The three sanctioned answers are:

1. Console preview: click the conversion or change entry, fill the target value, read the
   estimated fee or refund on the confirmation page, and do not submit.
2. Price configurator for a new purchase estimate.
3. Commercial follow-up for bundled renewal, campaign pricing or discount restoration, with the
   normal one-business-day callback expectation.

Related published rules to explain: a downgrade is irreversible, so restoring the old value is a
new upgrade with its own price difference; discounts are not inherited across configuration
changes; leaving a campaign price is permanent once the configuration changes; each resource item
is billed independently; a five-day unconditional refund does not return a used coupon.

## Handoff and escalation

Boundary rows, detection features and ready-to-send wording are in
[references/bandwidth-modify-guide__handoff-matrix.md](references/bandwidth-modify-guide__handoff-matrix.md). A handoff MUST carry the facts
already verified (live bandwidth, billing mode, public IP, saturation reading), so the customer
does not restate them. Console entry points are collected in
[references/bandwidth-modify-guide__console-entrypoints.md](references/bandwidth-modify-guide__console-entrypoints.md).

## Output contract

Every run ends with the script's own status block, faithfully relayed, never upgraded:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <one concrete step>
```

* `OK`: every requested fact was read; restate values verbatim, then give the guidance.
* `DEGRADED`: one or more reads failed or returned nothing. List each missing item with the reason
  (`NoPermission` plus the action, unsupported region, empty result, CLI timeout), fall back to the
  human phrasing that a ticket would use ("please attach the bandwidth monitoring chart for the
  peak window"), and never fill a gap from memory.
* `FAIL`: the credential chain or the CLI itself is unusable. Say what is broken and give the fix.

Only numbers and identifiers that appear in the script output may be quoted. Declared defaults,
auto-filled parameters and unchecked assumptions are stated in the answer.

## Known limitations

* Whether the peak actually saturated the link is a monitoring reading. This tier's verified API
  surface contains no bandwidth-utilisation metric, so the script does not fabricate one; it asks
  for the console chart. See [references/bandwidth-modify-guide__evidence-gaps.md](references/bandwidth-modify-guide__evidence-gaps.md).
* Account-level pricing, discount entitlement and refund arithmetic are not exposed to the skill.
* No order, invoice or ticket-system lookup is available in this package.

## References

| File | Contents |
| --- | --- |
| [references/bandwidth-modify-guide__bandwidth-billing-matrix.md](references/bandwidth-modify-guide__bandwidth-billing-matrix.md) | change and activation matrix, billing-mode orthogonality, temporary versus permanent upgrade, discount and refund rules |
| [references/bandwidth-modify-guide__eip-swap-runbook.md](references/bandwidth-modify-guide__eip-swap-runbook.md) | five-step public IP replacement path, three caveats, closing self-check |
| [references/bandwidth-modify-guide__handoff-matrix.md](references/bandwidth-modify-guide__handoff-matrix.md) | boundary detection, handoff wording, escalation contents |
| [references/bandwidth-modify-guide__console-entrypoints.md](references/bandwidth-modify-guide__console-entrypoints.md) | console paths and official documentation links |
| [references/ram-policies.md](references/ram-policies.md) | explicit actions used, minimal policies |
| [references/bandwidth-modify-guide__evidence-gaps.md](references/bandwidth-modify-guide__evidence-gaps.md) | facts deliberately not asserted |
