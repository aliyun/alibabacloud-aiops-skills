# Contact channels: what this skill may say

## Status of the channel directory

`PENDING_HUMAN_CONFIRMATION`

No official channel directory was supplied for this tier: no business-contact request entry,
no support hotline number, no online human-agent link, no refund or invoice flow document, and
no ticket-escalation document. Therefore this skill quotes none of them, and MUST NOT invent
one from memory, from a similar product, or from a guessed document number.

## The one fallback this skill is allowed to give

The confirmed requirement for this tier authorises a single verifiable instruction: route the
customer to the ticket entry inside the Alibaba Cloud console and request human handling there,
then ask for escalation to a business contact if the ask is commercial.

That wording is what `scripts/axes/business_contact_routing/routing.py` prints. It names an area of the console rather than a
link, because an unverified URL is worse than no URL.

## Supplementary self-service channel

One help document was surfaced for this tier, and it is weakly related:

| Item | Value |
|---|---|
| Topic | ECS message notification overview |
| Document path | `help.aliyun.com/zh/ecs/user-guide/overview-35.md` |
| Relation | A subscription to service notifications is a self-service alternative to chasing a person |
| Evidence | Single hit of the injected help-document search for this tier |

It is offered as optional only. It never substitutes for a requested human contact.

## Hard rules

* No telephone number, extension, working-hours window or response-time promise is produced.
* No call-back is booked, and no claim is made that one will arrive.
* Whether the account already has a named business owner is not observable from the cloud API;
  the skill says it needs confirmation on the human side rather than guessing.
* Commercial eligibility, amounts and policy judgements stay with the human owner.
* Emotional escalation is not something an agent handles better than a person; the limitation is
  stated instead of being papered over.

## What a human owner must confirm before a channel is quoted

1. The official business-contact request entry and its document address.
2. The support hotline number and its service-hours wording.
3. The online human-agent entry and the ticket-to-human escalation path.
4. The self-service flow documents for refund, unsubscribe, invoice and account-entity change.
5. Whether the message notification subscription stays in this skill's output.

Until item 1 to 3 land here, `STATUS: OK` still means "guidance by console ticket entry", not
"customer received a phone number".
