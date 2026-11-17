# Refund, Downgrade & Conversion - Mandatory Risk Notices

Output this block (assembled automatically by the `explain` mode for
risk-heavy branches) BEFORE any manual console guidance about downgrade,
unsubscription, refund or billing-mode/IP conversion. Every line is
evidenced by a real ticket where the customer lost money, time or trust
because the warning came after the action. The customer decides; the skill
never executes.

## The notice list (relate near-verbatim)

1. **Downgrading stops the instance** - business interruption; schedule off-
   peak; the operation is irreversible in its commercial effect (activity
   entitlements may not return).
2. **A refund can be 0 CNY.** When the original purchase carried a discount,
   the consumed period is re-priced at ORIGINAL prices (downgrade formula:
   remaining cost of old spec minus purchase cost of new spec; consumed
   amount re-priced; usage under 30 days may multiply it by 1.5; non-full
   unsubscription converts used time at original price). "It should be
   proportional to the remaining days" is the most common wrong expectation.
3. **Changing configuration of a long-term low-price activity instance (e.g.
   the 99 program) may forfeit the discounted renewal price.**
   <!-- anchor: activity-forfeit -->
4. **On refund the instance data is cleared immediately and is not kept**;
   vouchers/coupons used on the order are not returned; promotional gifts
   are voided; if the disks had auto-snapshot-on-release enabled, those
   snapshots disappear with the disks.
5. **A refund confirmation link is short-lived** (about 3 days in the source
   ticket) and the refundable amount DECREASES the later it is exercised.
6. **Converting the fixed public IP to an EIP is one-way**; the EIP carries
   extra configuration fees (a US-region example quoted 0.72 CNY/day -
   verify current regional price). Old EIP must be released deliberately,
   and releasing is irreversible.
7. **Fixed-bandwidth-to-traffic conversion auto-refunds the bandwidth
   balance, possibly 0** when discounts applied, and switching back later
   can require extra payment.

## What the skill must NOT do while guiding these flows

- compute or promise a refund figure (the system computes it; the console
  shows the expected figure before any confirmation - tell the customer to
  read it there, e.g. stop at the downgrade confirmation step);
- submit unsubscription applications; when the page itself errors with
  "unsubscription request submission failed, contact customer service",
  that marks a HUMAN special-application path - guide, don't retry;
- guarantee that an activity can be rejoined after refunding (the recorded
  rule: rejoining the 99 program depends on same-person/account history and
  instance release state - nobody can promise it 100 percent);
- advise refund-rebuy to chase a cheaper new-purchase price without first
  stating the data-migration, IP-change and eligibility risks.

## Historical configuration / order look-ups

For "what did I buy before / what did a past downgrade refund", the order
management pages are the source of truth: current configs while the instance
exists are visible in the ECS console; released instances and past orders
(incl. downgrade history and refund amounts) are visible in the order
management list page details. This skill has no order-query API and must
say so plainly, then hand the page path to the customer.
