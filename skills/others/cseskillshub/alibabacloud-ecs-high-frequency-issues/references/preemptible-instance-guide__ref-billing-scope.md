# Billing scope for spot instances — rules explained, amounts never read

**Hard boundary first:** this skill explains the **composition** of spot charges and where
the customer reads their own bill. It has **no billing API** in its whitelist, so it never
reads, computes, compares or confirms an amount, a daily figure, a discount application or
a refund. If the customer's question cannot be answered without a number, the answer is a
handoff, not an estimate.

This is a place where the skill is deliberately **weaker than a human agent**, who can
open the internal bill and read figures out. Say so in the answer rather than covering it
up: the rules and the self-check path are given, the figures are not.

Sources: no dedicated "spot billing rules" document was part of the injected evidence for
this tier — see `ref-handoff.md` §4. The composition and the console paths below come from
real ticket dialogs in this tier and must be re-verified against the live official
billing documents before being quoted; record the check date.
Bill-detail entry recorded from ticket dialogs:
`https://help.aliyun.com/zh/ecs/view-billing-details#title-jx3-hqs-6hn`.

## 1. A spot bill is not just the spot price

The discounted price covers the **compute** of the instance only. A bill for a spot
instance commonly also carries:

| Charge item | Present when | Note for the customer |
|---|---|---|
| Instance compute (spot) | Always, while running | The market price moves; a per-hour average over the month can look nothing like the advertised spot price |
| System disk | Almost always | Charged on its own, typically per GiB-hour, not part of the compute discount |
| Additional data disks | When attached | Same; and a disk that was kept alive after the instance went away keeps being charged |
| Public bandwidth or traffic | When the instance has a public address with traffic | Independent of the spot price |
| Disk performance burst | When that feature is enabled on the disk | Small unit price, can add up unnoticed; this exact item was the bulk of one ticket's surprise |
| Snapshots and images | When they exist | Billed by the snapshot tier's rules, and they keep billing after the instance is gone |

So the standard reply to "the spot price was 0.13 per hour, why did I pay more" is: the
compute is only one line; identify the disk, bandwidth and burst lines by opening the
bill per instance and per day. That is a **scope** answer, and the moment the customer
wants the figure itself, it is a handoff.

## 2. Timing rules that look like errors

- **The day of the release is billed** for the period the instance actually ran. A
  customer who sees a charge on a day they believe the instance "should have been free"
  is often looking at the running hours before the reclamation.
- **A stopped instance is not necessarily a zero-cost instance.** While an instance is in
  the stopped state, the compute charge depends on the stop mode, but **disk charges
  continue**. This is the one stop-mode rule this tier answers, because it is the rule
  customers hit right after a reclamation; the wider stop-mode behaviour belongs to the
  saving-stop-mode tier (`ref-handoff.md` §2).
- **Notice time, release time and charge time differ.** The interruption notice can
  arrive after the release it warned about, so an SMS timestamp is not evidence about a
  bill. Several tickets in this tier are exactly this confusion.
- **Spot price is not a fixed contract.** Any figure quoted from the advisor pages is a
  historical or instantaneous sample, not a promise about the next hour.

## 3. Where the customer reads it themselves

Give the path, the filters and the period; do not read the result for them.

1. Billing details in the cost console, filtered by **instance** and by **day** — that is
   the combination that separates the compute line from the disk and bandwidth lines.
2. Per-resource view for the disk and snapshot items.
3. The spot advisor console pages (`ref-inventory-advisor.md`) for the price side of the
   question, which is market data and not the customer's bill.

If the customer declines to look and asks the skill to fetch the numbers, the answer is:
"the rules and the exact console path are here; the figures are outside what this read-only
skill can see, and a bill-reconciliation request needs a support ticket."

## 4. Questions that must be handed off, not answered

| Customer ask | Correct behaviour |
|---|---|
| "How much did I spend on instance X between these dates" | Handoff: no billing API. Give the path, then the billing tier |
| "The charge looks wrong, check it" | Handoff to amount reconciliation; the composition table in §1 explains what *could* account for it |
| "Refund me for the reclaimed hours" | Commercial decision; support ticket. Never promise or estimate |
| "Do student vouchers or campaign coupons cover spot" | No public per-instance-type coverage list is available to this skill. The documented answer is that coverage follows what the voucher zone in the console displays; anything more is a ticket question |
| "Is the undiscounted price charged first and the difference refunded later" | **Not answered.** The ticket in this tier that asked it was escalated and has no settled conclusion in the evidence; do not construct a mechanism for it. Handoff wording in §5 |
| "Can I move this spot instance to a subscription" | No evidence in this bundle; see `ref-handoff.md` §4. Do not answer yes or no |
| "Why is my outbound traffic cost high" | Traffic tier; not this skill |

## 5. Handoff wording (adapt, keep the boundary)

> I can explain what a spot bill is made of and exactly where to read it, and I can check
> the instance facts that decide which rules apply. I cannot read your bill, confirm a
> figure, or handle a refund — those need the cost console on your side or a billing
> support ticket, and a ticket is also the right route for the pre-charge-and-refund
> question, because there is no documented rule for me to quote.
