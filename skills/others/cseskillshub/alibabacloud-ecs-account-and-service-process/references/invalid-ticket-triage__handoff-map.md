# Handoff map: real requests found inside this tier

Three of the reviewed tickets carry a concrete, repeatable request even though they sit
in the test / invalid union, and a fourth category (a genuine fault) has no sample in the
reviewed batch but must still be routed. The rule is absolute: a request that can be
restated in one sentence is never judged invalid, whatever the title says.

Destination names are not fixed for this batch - the tier specification supplied no
neighbour list, so each target below is the direction, marked as pending alignment with
the batch's skill inventory.

| Symptom group | Recognition in customer text | Evidence | Destination direction | Facts this skill can attach |
|---|---|---|---|---|
| `purchase-and-promotion` | asks about buying another instance, a discounted price, a monthly term, a coupon, or which type to pick | 0002HRUTWX | Sales / promotion consultation, or a business manager through a human | nothing cloud-side; the one-discounted-instance limit is a rule statement, not an API fact |
| `unsubscribe-and-refund` | asks about refund, unsubscription, the 5-day no-reason return, or whether an action breaks eligibility | 000F4RUDD8 | Unsubscribe and refund rules | `DescribeInstances` presence and charge type of the instance named |
| `disk-and-order-change` | asks to expand, shrink or correct a disk or an order, often quoting an order number | 000GJRW460 | Disk and order change handling | disk or instance ids found in the text; a masked order number is reported as unresolvable here |
| `instance-fault` | describes something reproducible: cannot connect, an error message, a hang, a timeout | none in the reviewed 20 | ECS instance fault diagnosis | instance visibility and running state |

## What is handed over and what is not

The skill hands over: the one-sentence request summary, the matched symptom group, the
quoted evidence, and any read-only facts already collected. It does not answer the
request: price matching, refund approval, order correction, unsubscription, and a
business-manager arrangement are all outside a read-only triage, and every ticket-system
action (closing, replying, marking pending confirmation, transferring) belongs to the
duty operator, because no ticket operation interface exists in this package.

## Routing reply

`REPLIES["D"]` in `scripts/axes/invalid_ticket_triage/_constants.py` fills one template:

> This ticket contains a real request (summary), which is outside the scope of test or
> invalid ticket handling, so it has been routed to the destination above; the read-only
> facts confirmed are listed; this record keeps the judgement basis only.

It is a draft for a human to send. Until the destination list is aligned, the report
appends "destination tier name pending alignment with this batch" so nobody reads the
routing as settled.

## Open items this file inherits from the reviewed batch

- Whether the three pseudo-request tickets stay in this tier as routing samples or move
  to their own tier.
- The fixed notification route for a confirmed security or interface probe: archival is
  suggested, but the reviewed evidence shows no owner.
- Re-pull of two first messages that arrived concatenated or truncated (000ACRGR12,
  000FLRREFR) before their payload wording is treated as exact.
