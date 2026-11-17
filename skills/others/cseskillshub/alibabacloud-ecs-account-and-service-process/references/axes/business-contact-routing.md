---
name: alibabacloud-ecs-business-contact-routing
description: |
  Read-only routing for Alibaba Cloud ECS cases where the customer wants a human or business
  contact instead of self-service. Classifies the ask, collects a read-only resource context
  pack, and returns the official hand-off path plus a material checklist. Changes no resource.
  Triggers: talk to my account manager, call me back, phone me, customer service number,
  human agent please, dedicated specialist, ask sales for a quote, refund question,
  invoice question.
  Do NOT use for disk usage or inode checks, expand-not-effective, transitional instance state,
  or slow disk IO: hand those to the matching read-only diagnosis skill.
---

# ECS business and human contact routing

## Scope

This skill covers exactly one symptom axis: an Alibaba Cloud ECS customer asks for a human or
business contact, or the substance of the ask is a commercial or account action. It performs
three things:

1. Classify the routing intent from the customer wording (deterministic, in-repo lexicon).
2. Optionally assemble a read-only material pack so a human owner never has to ask for the
   same facts twice.
3. Emit the hand-off guidance and state plainly what no agent can decide.

It does not diagnose technical faults, and it does not perform commercial actions.

## ABSOLUTE PROHIBITION

This skill is strictly **read-only**. It MUST NOT run, generate or recommend any call that
alters cloud state, including a change command handed to the customer to run by hand. Only the
four read actions in the allowlist below are permitted; anything outside that allowlist is
prohibited and is refused with a boundary statement plus the console entry.

* No guest command is executed inside an instance: no workbench session, no cloud-assistant
  command invocation. Command execution is a write-class capability and is out of scope here.
* No snapshot, backup or reversible write is performed. There is no cleanup branch in this skill,
  so the batch rule "take a snapshot before cleaning" has no trigger and is not implemented.
* Refund, unsubscribe, downgrade, invoice, billing and account-entity requests are never
  executed. The skill outputs the manual acceptance path and the read-only evidence list.
* No phone number, call-back window or business-owner assignment is asserted. See
  [references/business-contact-routing__routing-channels.md](references/business-contact-routing__routing-channels.md).

If a future requirement adds guest diagnostics or any state-changing step, the read-only
declaration here must be withdrawn at the same time.

## Execution principle

The agent runs only `scripts/axes/business_contact_routing/routing.py`. It MUST NOT compose CLI calls by hand or bypass the
entry point; the entry point is what carries the User-Agent, enforces the allowlist, applies
per-call timeouts and masks credential material.

```bash
python3 scripts/axes/business_contact_routing/routing.py run --text "<customer wording, Chinese or English>" \
  --region-id cn-hangzhou --instance-id i-xxxxxxxx
python3 scripts/axes/business_contact_routing/routing.py classify --text "<customer wording>"
python3 scripts/axes/business_contact_routing/routing.py context --region-id cn-hangzhou
python3 scripts/axes/business_contact_routing/routing.py channels --intent S2_human_phone
python3 scripts/axes/business_contact_routing/routing.py doctor
```

`run` without `--region-id` returns guidance only and performs no cloud query. `doctor` checks
offline, against the installed CLI metadata, that each allowlisted action resolves.

## Routing intents

| Intent | Customer wording | Handling |
|---|---|---|
| `S1_business_contact` | quotation, discount, contract, bulk purchase, named business contact | intent + account and resource pack + business hand-off guidance |
| `S2_human_phone` | asks for a human agent, a phone call or a call-back | self-service availability note, then official human channel guidance |
| `S3_commercial_action` | refund, unsubscribe, downgrade, invoice, account-entity change | read-only is refused for the action itself, manual acceptance path plus material pack |
| `unclassified` | no lexicon hit, or mixed wording below threshold | one clarifying question, guidance still emitted |

The matched lexicon lives in `scripts/axes/business_contact_routing/_constants.py` as embedded constants, in both customer
languages, because the customer wording is the only reliable signal. Confidence is the share of
matched terms owned by the winning intent; below `CONFIDENCE_THRESHOLD` the report asks one
clarifying question instead of guessing.

## Decision flow

1. Classify the text. A technical symptom mentioned in the same breath is recorded as a
   hand-off signal, never as an intent this skill owns.
2. Branch by intent:
   * Pure contact request, no technical question: identity and resource context, then guidance.
   * Technical question plus a demand for a human: state the self-service diagnosis that exists,
     name the owning skill, still emit the guidance.
   * Commercial or account action: state that it cannot be executed automatically, give the
     manual acceptance route, include the material pack.
3. Before the first cloud query, announce which read-only queries are about to run and why
   (printed as `[NOTICE]`). Read-only queries do not need a per-call confirmation gate.
4. Emit guidance regardless of query outcome. Guidance is the core deliverable and never
   depends on a successful API call.

## Verified read-only API surface

| Product | Action | Version | Read | Required | Used for |
|---|---|---|---|---|---|
| ecs | `DescribeInstances` | 2014-05-26 | yes | `RegionId` | which resources the ask concerns |
| ecs | `DescribeInstanceStatus` | 2014-05-26 | yes | `RegionId` | status snapshot recorded for the human owner |
| ecs | `DescribeAvailableResource` | 2014-05-26 | yes | `RegionId`, `DestinationResource` | sellability check when the ask involves purchase or scale |
| sts | `get-caller-identity` | 2015-04-01 | yes | none | account attribution of the material pack |

CLI form follows the platform convention: `aliyun ecs describe-instances --region-id <region>`
for RPC products, and lowercase-hyphen plugin form `aliyun sts get-caller-identity`. The script
builds both; the agent does not.

Parameter values are never guessed. `DestinationResource` is passed through only when the
operator supplies the exact console value, because the permitted value enumeration was not
confirmed for this tier. Pagination is auto-filled where an action supports it, and every
auto-filled parameter is declared in the report.

## Failure and degradation

* Credential or permission failure: relay `NoPermission` or `ImplicitDeny` plus the missing
  action name, and point to the smallest policy in
  [references/ram-policies.md](references/ram-policies.md). Ask the operator to refresh the
  default credential chain; never ask for key material.
* Empty result: reported as a limitation with the exact parameters used, never back-filled
  from memory.
* Wrong region or unknown instance id: relayed as-is, masked, as a parameter problem.
* Any failure above degrades the pack, not the answer: guidance still prints in full and
  `STATUS: DEGRADED` lists each missing item.

## Output contract

The report ends with:

```
STATUS: OK | DEGRADED | FAIL
NEXT_ACTION: <single line, ordered human steps>
```

`STATUS: OK` needs every attempted read query successful and classification at or above the
confidence threshold. `STATUS: DEGRADED` means guidance is complete but part of the pack is
missing or the intent was ambiguous. `STATUS: FAIL` is reserved for a request the entry point
cannot service at all, such as an unusable region argument. The agent relays `STATUS` and
`NEXT_ACTION` faithfully and quotes only returned values. Outward-facing fields are masked: the
account is shown as `acct-tail-<last4>`.

## Observability

Each process run generates one 32-character hex session id with `uuid.uuid4().hex`, and every
CLI call sends it through `--user-agent` using the template:

```
AlibabaCloud-Agent-Skills/{skill}/{session-id} skill-version/{skill-version}
```

where `{skill}` resolves to `alibabacloud-ecs-business-contact-routing` and `{session-id}` to
the 32-character hex session id generated above. The id groups all calls of one routing case in
platform logs; it carries no customer data. `doctor` prints the exact User-Agent the run would
use.

## Authentication

Credentials are resolved only by the default credential chain of the locally configured CLI.
This skill never reads, prints, stores, transmits or asks for an access key, secret or token,
and has no command-line credential parameter. All stderr and error text passes through
credential masking before it reaches a report or log, and transient failures such as
`Throttling` and server-side 5xx are retried with backoff while anything else fails fast.

## Boundaries and hand-off

Symptom ownership, transfer wording and the reason guest diagnostics stay out of this skill are
in [references/business-contact-routing__handoff-matrix.md](references/business-contact-routing__handoff-matrix.md). Classification rules and the
degradation ladder are in [references/business-contact-routing__intent-taxonomy.md](references/business-contact-routing__intent-taxonomy.md).

## Evidence limits

No representative ticket, conversation, official channel directory or tier error-code table was
supplied for this tier, so this package asserts none of them. Contact routing facts come only
from a confirmed source; where a fact is missing, the skill says so and degrades. See
[references/business-contact-routing__routing-channels.md](references/business-contact-routing__routing-channels.md) for the pending items.

## Package layout

```
SKILL.md
related_apis.yaml
scripts/axes/business_contact_routing/routing.py        single entry point, STATUS / NEXT_ACTION contract
scripts/axes/business_contact_routing/_cli.py           allowlist-enforced read-only transport, UA, timeout, retry, masking
scripts/axes/business_contact_routing/_constants.py     endpoints, limits, embedded intent and hand-off lexicon
scripts/axes/business_contact_routing/sts_token.py      account attribution through the default credential chain
scripts/requirements.txt  standard library only
references/ram-policies.md
references/business-contact-routing__routing-channels.md
references/business-contact-routing__handoff-matrix.md
references/business-contact-routing__intent-taxonomy.md
```
