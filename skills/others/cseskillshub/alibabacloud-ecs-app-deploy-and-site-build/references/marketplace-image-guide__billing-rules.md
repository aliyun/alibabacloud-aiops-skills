# Marketplace and paid image billing rules

Use this file for the `billing` intent and for the `renewal-charge-question`,
`unexpected-image-charge` and `duplicate-renewal-order` symptom routes. Each rule
below was confirmed in the support evidence for this tier; amounts never were, and
this skill must not state any.

## Core rules

1. **The image is billed on its own axis.** The image charge is independent of the
   instance charge mode. A subscription instance can carry an image that is billed on
   its own periodic cycle, so "my server is yearly" does not imply "my image is
   included".
2. **Renewal renews the licence.** When a subscription instance is renewed while using
   a paid image, the operating-system licence for that image is renewed at the same
   time, on the same cycle as the instance. Paid images include Windows Server, Red Hat
   Enterprise Linux, SUSE Linux Enterprise Server and Alibaba Cloud Linux 3 Pro, in
   addition to any third-party Marketplace product.
3. **Renewal promotions do not cover the image order.** A discounted renewal can still
   produce a separate image line. This is the most common source of a "why is my
   renewal higher" ticket.
4. **The fee follows the image, not the customer's recollection.** An instance built
   from a Marketplace product that pre-installs a software stack is billed for that
   product even when the customer believes they installed the software by hand. Before
   discussing the charge, read the image name and identifier with `DescribeImages` so
   the attribution is stated from evidence.
5. **To stop image charges, move to a free image before the next renewal.**
   Preconditions: the instance is Stopped and a backup or snapshot is confirmed. The
   change releases the current system disk permanently, so it is irreversible, and
   `console-guides.md` carries the gate.
6. **A paid image fee is not refundable on its own.** Once a paid image has been
   associated with an instance it is treated as consumed. On cancellation, only the
   remaining value of the instance is refundable.
7. **A not-yet-effective renewal order needs the manual route when a paid image is
   attached.** The cancellation specialist settles the instance renewal order first;
   the image renewal order is then cancelled automatically as a follow-on. The customer
   has to grant authorization in the ticket, and an approval is required.

## Facts this skill cannot see

Order amounts, order counts, invoice quota, coupon effects, refund eligibility and
refund arrival are all outside the three read-only actions in `ram-policies.md`. When
the conversation reaches one of those, switch to the customer self-check plus the
billing route:

| Question | Where the answer lives |
|---|---|
| How much am I being charged for the image? | Billing console statement, filtered by Marketplace / image line |
| Where did my refund go, and when did it arrive? | Income-and-expense statement page in the billing console |
| Why are there two renewal orders for one image? | Ticket route, reviewed by the Marketplace team, quoting both order numbers |
| Is this charge attributable to the image or to something I installed? | Image identifier and image name from this skill; the amount from the billing console |

Phrase it as: the amount has to be read from the billing console, or escalated with
the order numbers attached. Never estimate, and never confirm a figure the customer
reads out.

## A refund page that shows no amount

Reported after an image change. Two candidate causes, in this order:

1. The instance is still on the paid image, so the cancellation flow refuses it. This
   is checkable: re-run the entry script and read the image verdict.
2. State propagation lag after a genuine change. The accepted customer sequence is
   refresh, re-enter the page, wait for the state to synchronize, retry later, and
   raise a ticket if nothing appears. Treat this as the documented customer-side
   sequence, not as a confirmed diagnosis; the evidence for it is thin, and submitting
   twice is worse than waiting.

## How to answer a billing question

1. Read the facts: instance identifier, instance type, charge mode, image identifier,
   image name, product code.
2. State the rule from this file that applies, quoting nothing that was not returned.
3. Separate the two halves of the answer out loud: what the image metadata proves, and
   what only the billing console can show.
4. Put the customer on the billing console, or on the ticket route, for the money half.
