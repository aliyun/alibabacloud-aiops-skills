# Lifecycle Rules: Expiry -> Stop -> Data-Retention Window -> Release

Scope: the single symptom area of this skill -- what happens to an ECS
instance and its data from expiry to release, per billing form. Every rule
carries its evidence source and confidence. Numbers without a source are
never stated.

Source tag legend:

- `[ticket:<id>]` -- verbatim front-line support dialog in a real ticket.
- `[doc:<url>]` -- official help document (title verified in the tier
  evidence; body text was NOT crawled, so treat quoted rules as
  ticket-sourced until confirmed).
- `[TO VERIFY]` -- front-line consensus without a crawled official text;
  the skill MUST render this tag whenever it quotes the value.
- Confidence: high = multiple reviewed dialogs agree; medium = single
  dialog or a conflicting pair; low = phone-only ticket (no reviewable
  dialog) -- low-confidence rules must never be presented as certain.

## 1. Subscription (prepaid) instances

| Stage | Rule | Source | Confidence |
|---|---|---|---|
| Before expiry | Billing runs to `ExpiredTime`. Authoritative expiry comes from the API, never from customer arithmetic on orders (a bandwidth-upgrade order was once mistaken for an extension order). | [ticket:T-CB867A71] | high |
| At expiry | The instance stops; business becomes unavailable. | [ticket:T-63376A9B] | high |
| Retention window | Data is retained for **15 days** after expiry, then the instance is released automatically and data cannot be recovered. | [ticket:T-5E3EDF72] [ticket:T-263837C7] [ticket:T-63376A9B] [ticket:T-CD20304A]; doc anchor [doc:https://help.aliyun.com/zh/ecs/product-overview/subscription#9bfa29b0407gc] (body not crawled) | medium -- always output as "15 days [TO VERIFY: official confirmation pending]" |
| Renew inside retention | Renewal restores the instance ONLY inside the 15-day retention window; after release, renewal is impossible. | [ticket:T-C12BF6F7] | high |
| Manual release timing | A subscription instance can be released manually starting **00:00 of the calendar day after** the expiry timestamp (e.g. expiry 2026-09-03 23:59:59 -> operable from Sept 4, 00:00). There is no need to wait for the automatic release. | [ticket:T-263837C7] | high |
| Early release before expiry | Releasing a not-yet-expired subscription instance is done through UNSUBSCRIPTION, not the release button. See `renewal-refund-extension.md`. | [ticket:T-263837C7] | high |
| Backup while expired-stopped | An expired, stopped instance usually CANNOT create snapshots in place ("once expired, it cannot be backed up"); a real attempt failed. Correct order: renew (or get an extension) -> instance back up -> create snapshots -> only then consider unsubscribing. | [ticket:T-5E3EDF72] [ticket:T-084C4147] | high |

## 2. Pay-as-you-go (postpaid) instances and overdue accounts

| Stage | Rule | Source | Confidence |
|---|---|---|---|
| Billing while running | A pay-as-you-go instance bills while Running. | [ticket:T-1834B8F1] | high |
| Stop vs billing | A normal stop does not necessarily stop all charges; the economical (savings) stop mode stops vCPU/memory billing but the system disk and data disks KEEP BILLING. Only releasing the instance stops billing entirely. | [ticket:T-1834B8F1]; [doc:https://help.aliyun.com/zh/ecs/user-guide/economical-mode] | high |
| Overdue -> snapshot loss | If the ACCOUNT is overdue for more than **15 days**, existing SNAPSHOTS are released. This is a DIFFERENT 15-day rule from the post-expiry retention window; never mix the two. | [ticket:T-0E502AF0] | medium |
| Retention window for overdue pay-as-you-go | Whether the overdue stop -> release window is also 15 days has NO evidence in this tier. | none | low -- output UNKNOWN, never guess |

## 3. Economical (savings) stop mode

- Stops compute billing, keeps disks (and their billing) -- see the matrix in
  `billing-stop-matrix.md`. Source: [ticket:T-1834B8F1],
  [doc:https://help.aliyun.com/zh/ecs/user-guide/stop-an-instance#1dbe594a8082k],
  [doc:https://help.aliyun.com/zh/ecs/user-guide/economical-mode]. Confidence: high.
- Applicability limits per instance type are documented on the economical-mode
  page but its body was not crawled: [TO VERIFY]. Do not assert which instance
  families support it.

## 4. Spot (preemptible) instances

| Rule | Source | Confidence |
|---|---|---|
| A spot instance can be reclaimed automatically when inventory or price changes; this is not a user deletion and not an account fault. | [ticket:T-7D84AD37] | high |
| The specific reclamation reason (price vs inventory vs protection-period end) is NOT asserted: no verified API field carries it. State only the fact and time of reclamation when evidenced. | tier evidence gap | rule |
| Spot instances are unsuitable for long-running workloads; they may be released at any time. | [ticket:T-B12C03B4] | medium |
| When creating a spot instance, set the interruption mode to the economical (savings) stop mode so a reclamation stops the instance instead of releasing it immediately, preserving the data environment. | [ticket:T-7D84AD37]; [doc:https://help.aliyun.com/zh/ecs/user-guide/create-a-spot-instance] | high |
| Data retention / recovery after reclamation follows the spot data-retention doc. | [doc:https://help.aliyun.com/zh/ecs/user-guide/preemptible-instance-data-retention-and-data-recovery-after-interrupt-reclamation.md] | doc title verified, body not crawled |

## 5. Free trial ("ECS free trial" SMS notifications)

| Rule | Source | Confidence |
|---|---|---|
| The free trial is NOT a separate free server product: it is a pay-as-you-go instance whose bill is offset by a granted savings-plan-style resource package. | [ticket:T-C3E9D9B3] | high |
| When the trial package ends, it does NOT auto-renew; if no instance remains under the account, no further charges accrue -- there is nothing to "manually release". | [ticket:T-EDCE8535] | high |
| After the trial ends, the pay-as-you-go instance keeps billing against the account balance unless it is released or converted. | [ticket:T-C3E9D9B3] | medium |
| Trial-to-paid conversion paths: pay-as-you-go -> subscription billing conversion. | [doc:https://help.aliyun.com/zh/ecs/user-guide/what-should-i-do-if-my-ecs-free-trial-is-about-to-expire.md] [doc:https://help.aliyun.com/zh/ecs/user-guide/common-operations-for-the-ecs-free-trial.md] | titles verified |
| Non-ECS product trials (e.g. security products) follow their own product rules -- hand off, see `handoff-boundaries.md`. | [ticket:T-56201A2E] | high |

## 6. Expiry extension ("grace period") -- CONFLICTING front-line statements, shown side by side

| Statement | Source | Confidence |
|---|---|---|
| Extension limits: one account / one calendar year / one time / one day / one instance. | [ticket:T-63376A9B] | high |
| An unpaid renewal order must be VOIDED before an extension can be applied; voiding is irreversible (the order cannot be paid afterwards; renewal must be re-ordered). | [ticket:T-63376A9B] [ticket:T-88CA26A9] | high |
| Extensions ARE granted case-by-case (1-day and 24-hour approvals observed; one approval stressed "this time only, not supported afterwards"). | [ticket:T-084C4147] [ticket:T-CD20304A] [ticket:T-240B40F6] | high |
| Conflicting statement: "expiry stop cannot be delayed". | [ticket:T-B92D8D06] | medium -- contradicts the row above |
| Resolution rule for the skill: present BOTH statements, mark the decision as "manual case-by-case approval; rules may vary per case; outcome never promised". Do not pick a side. | design decision | rule |
| An EIP does NOT extend together with the instance (renew or convert separately). | [ticket:T-C8B6DAEA] | low -- phone-only ticket, no reviewable dialog; present with the low-confidence caveat |
| Unpaid renewal orders ARE verifiable read-only: `bssopenapi QueryOrders` (RAM action `bss:DescribeOrderList`) with `PaymentStatus=Unpaid` plus a `CreateTimeStart`/`CreateTimeEnd` window, and `GetOrderDetail` by order id. This area does not call it yet, so the skill must say it did NOT verify the precondition and point the customer at Billing console > Orders. Prior-extension history: no read-only query for extension records is documented or verified in this tier; the customer must self-check it in the Billing console. | official BSS API reference (QueryOrders / GetOrderDetail) + local CLI check 2026-10-28 | high (API existence); unverified per run |

## 7. Public IP behavior across the lifecycle

| Rule | Source | Confidence |
|---|---|---|
| Recovering from a snapshot / custom image yields a NEW public IP; the old one is not kept. | [ticket:T-5E3EDF72] | high |
| A classic public IP is lost permanently once the instance expires and is released; to keep the address, convert it to an EIP BEFORE expiry/release (manual action; conversion mechanics and EIP billing are out of scope -- hand off). | [ticket:T-8D31E368]; [doc:https://help.aliyun.com/zh/ecs/user-guide/convert-the-public-ip-address-of-an-instance-in-a-vpc-to-an-eip] | high |

## 8. What the skill must never do with these rules

- Never present the 15-day retention window without its `[TO VERIFY]` tag.
- Never mix the retention window (expiry + 15 days) with the overdue-snapshot
  rule (overdue > 15 days -> snapshots released).
- Never infer "released" from "not found by the API" -- see the three-branch
  rule in SKILL.md Error Handling.
- Never promise an extension, a refund, or a recovery outcome.
- Never state a pay-as-you-go retention window: no evidence, output UNKNOWN.
