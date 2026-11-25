---
name: alibabacloud-ecs-marketplace-image-guide
description: |
  Read-only facts plus guided resolution for an ECS instance running an Alibaba Cloud
  Marketplace or other paid third-party image: license billing and renewal, conversion
  blocks, refund preconditions, system-disk change payment failures, cross-account
  transfer, image export scope, resource-group authorization.
  Prints evidence plus console steps for the customer; this skill changes nothing.
  Use when an ECS instance runs a Marketplace or other paid third-party image.
  Triggers: marketplace image, cloud marketplace image, paid third-party image, image license fee on renewal, marketplace image conversion not supported, image not compatible with the instance type, no refund amount for a paid image order, payment failed when changing the system disk
  Do NOT use: Docker container image pulls, software shipped inside an image, ISO
  installation, or boot faults unrelated to the image source.
---

# ECS Marketplace and paid third-party image guide

Answer one question with evidence: is this customer's problem caused by the **image
source** being an Alibaba Cloud Marketplace or otherwise paid third-party image, and if
so, which documented rule applies and what exact console steps should the customer
perform next.

The skill gathers facts through read-only queries, states the rule, hands the customer a
numbered console procedure with the risk notice attached, and then re-checks the same
facts to confirm the state changed as expected.

## Scope

In scope, all limited to the Marketplace or paid-image axis:

- Selection and compatibility: image versus instance family support, public image versus
  Marketplace image, display-language availability, the fact that an ISO cannot be mounted.
- Billing rules: image license charged separately, renewed together with the instance, not
  covered by renewal promotions, and which operating systems are license-charging.
- Billing-method conversion refused because the instance image is a Marketplace image,
  including the same message appearing while the customer works on the public IP address.
- Cancellation and refund preconditions driven by a paid image, and the fixed order in
  which not-yet-effective renewal orders are handled.
- System-disk change that fails payment because the instance is not in the stopped state.
- Cross-account transfer and image export limits caused by the image source, with the
  documented alternative paths.
- Resource-group authorization that fails when a Marketplace image is selected, because
  such an image belongs to no resource group.

Out of scope, recognised and then handed over (see `references/marketplace-image-guide__handoff.md`): Docker
container image pulls, software shipped inside an image misbehaving in the guest, ISO or
bring-your-own-image operations, instance boot faults unrelated to the image source,
bandwidth and public IP operations themselves, RAM and resource-group model design, and
every order-level or amount-level judgement.

## Permission model: read-only, guidance only

`ABSOLUTE PROHIBITION.` This skill only queries. It MUST NOT call, generate, or hand over
a command line for any OpenAPI action other than the read-only actions listed in
`references/ram-policies.md`. In particular, any action whose name begins with a change
verb is blocked here, including the `Modify*`, `Create*`, `Delete*`, `Release*`,
`Reset*`, `Replace*`, `Attach*`, `Detach*`, `Reboot*`, `Start*`, `Stop*`, `Import*` and
`Run*` families, and that ban also covers any change command written out for the customer
to paste.

Three consequences that MUST be respected in every answer:

1. **The customer performs every change.** Stop the instance, change the operating system,
   convert the billing method, cancel an order, share an image, edit a RAM policy: the
   skill outputs entry point, clicks, expected result, risk notice and rollback path. It
   never performs them and never says it did.
2. **Nothing runs inside a customer instance.** This skill has no guest-side capability.
   When a fact lives only inside the guest, ask the customer to run the vendor's read-only
   check over a remote connection and paste the output back, or hand over to the
   remote-connection channel. Never imply that such a reading was taken automatically.
3. **No business judgement.** Amounts, order eligibility, approval, refund arrival and
   duplicate-order diagnosis go to the billing or Marketplace support channel with the
   evidence block attached. Never state a price, never promise a refund, never claim an
   order was cancelled.

## Prerequisites

- The Alibaba Cloud CLI installed and configured through its own credential profile.
  Never pass an access key pair to this skill, in an argument, a file or an environment
  variable; the default credential chain is the only supported route.
- The RAM identity needs only the three read actions in `references/ram-policies.md`.
- `RegionId` is mandatory: it is the required parameter of every query used here.

## How to run

One entry point, one command. The agent MUST call this script rather than composing
queries by hand.

```bash
python3 scripts/axes/marketplace_image_guide/ecs_marketplace_image_guide.py --region-id <region> \
    --instance-id <instance-id> --symptom <symptom>
```

Common forms:

```bash
# Which image is attached, and is it paid
python3 scripts/axes/marketplace_image_guide/ecs_marketplace_image_guide.py --region-id cn-hangzhou --instance-id i-x
# The same message appears in two console entries: pass the quoted message
python3 scripts/axes/marketplace_image_guide/ecs_marketplace_image_guide.py --region-id cn-hangzhou --instance-id i-x \
    --error-text "marketplace image does not support conversion"
# Compatibility of a candidate image against the running instance family
python3 scripts/axes/marketplace_image_guide/ecs_marketplace_image_guide.py --region-id cn-hangzhou --instance-id i-x \
    --target-image-id m-y
# Region-wide inventory of paid and Marketplace images
python3 scripts/axes/marketplace_image_guide/ecs_marketplace_image_guide.py --region-id cn-hangzhou --inventory
# Credential provenance only
python3 scripts/axes/marketplace_image_guide/sts_token.py
```

`--list-symptoms` prints the routing vocabulary. Flags: `--image-id`, `--intent`,
`--facts-only`.

## Decision tree

1. Collect `RegionId`, an instance or image identifier, the customer's goal, and the
   verbatim console message when there is one.
2. Run the script: it reads the attached image, the image metadata, the instance type and
   the lifecycle state.
3. Read the verdict. Paid or Marketplace image confirmed → continue in this tier. Public
   image with no license signal, or an image the customer *believes* is paid → state the
   evidence and re-frame the problem; if the symptom belongs to another axis, hand over.
4. Route the symptom. The conversion message MUST be split by the operation actually being
   performed first: instance billing-method conversion, or bandwidth and public IP billing.
   Those two branches have different answers.
5. Output the five-part answer (below), then re-run the same read-only query after the
   customer acts.
6. Order-level or amount-level facts, or an attribution the customer rejects → hand over
   with the evidence block; do not restate the rule a second time as if it were new
   evidence.

## Answer format

Every customer-facing answer carries the same five blocks:

| Block | Content |
|---|---|
| Fact | Values returned by the script: instance id, type, state, image id and name, the field that drove the verdict |
| Rule | The documented rule for that symptom, quoted from `references/` |
| Steps | Numbered console path the customer performs: entry point, object, expected result, what to do if it fails |
| Risk | What is destroyed or interrupted, whether it is reversible, what backup must exist first |
| Recheck | The read-only command to run afterwards, plus the state that proves success |

Close with the script's `STATUS: OK|DEGRADED|FAIL` and `NEXT_ACTION:` values, verbatim.

## Confirmation gate before any change step

Before printing a step that can destroy data, interrupt a service, or alter a billing or
order state, the skill MUST output, in this order:

1. the notice that the operation is performed by the customer in the console and is not
   reversible where the reference says so;
2. the backup or snapshot precondition, with the reminder that snapshots are billed
   separately;
3. an explicit request for the customer to confirm that notice, and only then the steps.

Silently listing the steps, or listing them before the notice, is a violation.

## Observability

Every query issued by `scripts/axes/marketplace_image_guide/_cli.py` carries a User-Agent built from the template

```
AlibabaCloud-Agent-Skills/{skill-name}/{session-id} skill-version/{skill-version}
```

where `{skill-name}` is `alibabacloud-ecs-marketplace-image-guide` and `{session-id}` is a
fresh 32-character hexadecimal value generated once per run with `uuid.uuid4().hex` and
reused for all calls of that run. The CLI flag is `--user-agent`. The run header prints
both `session_id:` and `user_agent:` so a report can be traced back to one invocation.

## When a query is refused

If a call returns `NoPermission` or `ImplicitDeny`, stop guessing at the resource state.
Report which action was refused, which resource it was aimed at, and emit the smallest
policy that fixes it:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": ["ecs:DescribeInstances"],
      "Resource": "*"
    }
  ]
}
```

Add `ecs:DescribeImages` when image metadata was the missing piece and
`ecs:DescribeInstanceStatus` when the lifecycle state was. Ask the customer to switch to a
principal that already holds those read actions; never request broader coverage and never
ask for credentials inside the conversation.

## Data boundaries: say so instead of concluding

Read-only queries see only the current credential account and the requested region, and
they see no billing data at all. These facts are outside this skill and MUST be either
self-checked by the customer or handed over: whether the purchase page warned about
incompatibility, what a conversion or cancellation page actually renders, amounts,
renewal order counts, refund arrival, in-guest state, and the RAM or resource-group view
held by another identity. A degraded or empty result is reported as "not visible here",
never as "does not exist". Where the queried image fields carry no supported-family hint,
the Marketplace product detail page is named as the authority.

## References

| File | Use it for |
|---|---|
| `references/ram-policies.md` | The exact read-only actions this skill requires |
| `references/marketplace-image-guide__decision-tree.md` | Symptom routing, root-cause patterns, quoted console messages |
| `references/marketplace-image-guide__billing-rules.md` | Licence billing, renewal, promotion scope, charge attribution disputes |
| `references/marketplace-image-guide__restriction-matrix.md` | Which operations a Marketplace or paid image blocks, and why |
| `references/marketplace-image-guide__console-guides.md` | Customer-performed step cards, each with entry, action, expected result, rollback, risk |
| `references/marketplace-image-guide__handoff.md` | Recognition signals and handover wording for neighbouring topics |
