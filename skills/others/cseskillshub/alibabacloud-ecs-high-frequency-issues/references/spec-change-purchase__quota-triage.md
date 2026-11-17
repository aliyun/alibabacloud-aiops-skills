# Quota triage

Quota VALUES, usage counters and application states are NOT queryable from
this tier's API contract (requirements section 8-3 gap): the skill works
from the customer's verbatim error string / console screenshot, never
invents numbers, and routes each wording to the right owner.

## Triage order for quota-flavored wording

1. **Attribute the source first.** "Quota exceeded / insufficient" text can
   come from (a) the Alibaba Cloud console/API, (b) the customer's OWN
   program (reviewed case `T-ADB1836D`: an IIS-hosted site returned
   quota-like errors; the fix was on the customer's server software, not in
   any quota), or (c) another product (OSS resource packages, web hosting,
   shared bandwidth - out of this tier; see `references/spec-change-purchase__handoff-map.md`).
2. **Then the account check BEFORE any quota action.** `Your available
   quota is insufficient.` on a fresh purchase attempt was, in the reviewed
   case `T-F23EA8D8`, an OVERDUE BALANCE in disguise: ask the customer to
   check and settle the bill in the Billing Management console first.
   Raising a quota would have changed nothing.
3. **Then split by wording.**
   - `The maximum number of refund vcpu is exceeded: refund ecs vcpu quota
     limited by user quota: [<quota>] used: [<used>] need: [<need>]` -
     the REFUND vCPU quota (returned-vCPU allowance for downgrades), from
     `T-BCD8AD09`.
   - Console prompt that the account has reached the regional quota cap for
     ECS - the instance-creation quota, from `T-E48C384D`.

## Refund-vCPU error: what to echo and collect

- Echo the three bracketed numbers verbatim from the customer's text (never
  recalculate them): quota / used / need.
- Enumerate the scope like the human did in `T-BCD8AD09`: ask whether
  OTHER instances are also being downgraded; the same refund budget covers
  all of them, and one application should cover the full need. The entry
  script prints the instance facts to support the count.
- Explain the mechanism plainly: a downgrade "returns" vCPU to the
  provider, and the account's returned-vCPU budget is exhausted
  (used >= quota while the operation needs more).

## Application material the customer should prepare

The quota application itself is a SELF-SERVICE console action (this skill
never submits anything), and the reviewed cases show what decides approval
speed (`T-26C336BF`, `T-6D9AB6B5`, `T-E48C384D`):

- region and quota item;
- requested number (reasonable, not inflated);
- detailed business reason: scenario, instance families, total vCPU,
  expected usage duration;
- contact channel; results arrive by SMS and email.

State honestly: this skill cannot read the current quota value or the
application state; where a number matters, ask the customer for the console
quota-center screenshot.

## Approval-state facts (from `T-26C336BF`, `T-8CD3F2E5`, `T-6D9AB6B5`)

- An application in the "under approval" state LOCKS that quota item: the
  customer cannot re-submit while it is pending (reviewed case: an 89999
  vCPU request pending for a long time; large requests take longer).
- Urging, cancelling, adjusting refund-credit limits, and manual
  increases are HUMAN processes; escalation goes to support without
  promising timing.
- Refund-credit limits block unsubscription in the reviewed case
  `T-8CD3F2E5`:
  unsubscription / refund itself is a commercial, human-handled action;
  this tier only identifies the wording and hands off (the reviewed agent
  noted the limit adjustment takes ~5 minutes to become effective).
- Never promise an approval time or outcome; never claim the skill
  submitted anything.
