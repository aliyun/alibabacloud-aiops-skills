# Intent taxonomy and decision rules

## Evidence status of this taxonomy

The three intents below were derived from the tier name, not from ticket conversations. No
representative ticket identifier, conversation or tier error-code table was supplied, so this
taxonomy is a working hypothesis. It is recalibrated as soon as ticket evidence lands, and until
then nothing here is presented to a customer as an established pattern of how their case is
usually handled.

## Intents

| Intent | Typical customer wording | Substance |
|---|---|---|
| `S1_business_contact` | asks for a business or sales contact, quotation, discount, contract, framework pricing, bulk purchase | Commercial relationship, not a fault |
| `S2_human_phone` | asks for a human agent, customer service number, a call, a call-back, "a real person" | Wants a person to take over, whatever the underlying topic |
| `S3_commercial_action` | refund, unsubscribe, downgrade, invoice, billing adjustment, account-entity change | The actionable path lies on the commercial or billing side even if raised as a technical case |
| `unclassified` | no lexicon term matched, or terms split across intents below the threshold | Needs one clarifying question before anything else |

The literal matcher terms, in both customer languages, are embedded constants in
`scripts/axes/business_contact_routing/_constants.py`. Customer wording is matched case-insensitively; the terms are customer
phrases, not root-cause phrasing.

## Confidence and the clarify-once rule

Confidence is the share of all matched terms that belong to the winning intent:

```
confidence = matched_terms(winner) / matched_terms(all intents)
```

* One-sided wording scores 1.0 and is acted on directly.
* Mixed wording, for example a technical complaint plus a demand for a call, lands between 0.5
  and 0.9. The dominant intent is still reported, and the technical part is emitted as a
  hand-off signal rather than being absorbed.
* Below `CONFIDENCE_THRESHOLD` the report asks exactly one clarifying question and still prints
  the channel guidance. The agent must not ask a second round on its own.

## Decision tree

1. Match the text. Emit the winning intent, its confidence and every matched term.
2. Detect technical symptom terms; each becomes a hand-off signal naming the owning skill.
3. Branch:
   * Pure contact ask, no technical question: account tag, then instance and status context,
     then guidance.
   * Technical ask plus demand for a person: state the self-service capability that exists, name
     the owning skill, then guidance; context is still collected so the human does not re-ask.
   * Commercial or account action: state plainly that it cannot be executed here, give the manual
     acceptance route, and provide the material pack.
4. Print the report and end with `STATUS` and `NEXT_ACTION`.

## Degradation ladder

Guidance is the deliverable and never depends on a successful query.

| Condition | Effect on the pack | `STATUS` |
|---|---|---|
| Every attempted query returned | complete | `OK` |
| Confidence below threshold, all queries fine | complete but possibly about the wrong ask | `DEGRADED` |
| One or more queries failed or were denied | that item is listed as missing, with its code | `DEGRADED` |
| No region supplied | no queries attempted | `DEGRADED` |
| Entry point cannot service the arguments at all | nothing assembled | `FAIL` |

`FAIL` never suppresses the guidance block; the guidance prints first and `NEXT_ACTION` states
which argument has to be corrected.

## Error relay rules

* No tier-specific error-code table exists for this skill, so none is quoted. Console text is
  relayed masked and verbatim, described in customer terms: a permission problem, a parameter
  problem, or an empty result.
* Permission failures are named with the literals `NoPermission` or `ImplicitDeny`, together with
  the single denied action and the policy line in
  [references/ram-policies.md](references/ram-policies.md).
* A `Throttling` or server-side answer is retried with backoff by the transport layer; a
  non-transient answer fails fast and is reported as-is.
* An empty list is a finding, not a guess: report the parameters used and go no further.

## Facts that must never be inferred

* Whether the account already has a named business owner.
* Any response time, call-back or queue position.
* Refund, downgrade or invoice eligibility, and any amount.
* Any in-guest reading; no command is executed inside an instance by this skill.
