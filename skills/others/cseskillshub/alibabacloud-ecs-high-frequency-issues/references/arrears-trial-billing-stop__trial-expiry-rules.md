# M3 — Free Trial / Campaign Offer Expiry (Area B)

Scope: the customer holds an ECS instance they call "free trial" (or a
new-user campaign machine) and the trial or discount is ending, has ended, or
already started producing small deductions.

## 1. The mechanism the customer must understand first

- A "free trial" ECS server is NOT a separate free product. It is a normal
  **pay-as-you-go instance whose bill is offset by a trial entitlement** (a
  savings-plan / resource-package style deduction). Consequences that follow
  mechanically:
  - The instance has a real running-metered bill from day one; during the
    entitlement the deducted portion simply shows as covered.
  - **Entitlement expiry ≠ instance deletion.** Nothing about the trial
    ending removes the instance or its data.
  - After entitlement expiry, the same metered usage starts deducting from
    the account balance; a thin/zero balance then enters the arrears flow of
    [arrears-recovery-rules.md](arrears-trial-billing-stop__arrears-recovery-rules.md).
- Support tickets record customers panicking on exactly this seam ("trial
  expired, is my server going to be cleaned up silently?") and, on the other
  side, customers surprised that a trial instance that they "stopped using"
  still bills once the deduction ends.

## 2. Expiry-time evidence: what is machine-readable and what is not

| Fact | Source |
|---|---|
| Instance billing method (pay-as-you-go vs subscription) and instance-level `ExpiredTime` | `ecs:DescribeInstances` — machine-readable, always quote it |
| Trial entitlement / deduction expiry date | NOT in this skill's authorized action set — CONSOLE-CHECK in Expenses and Costs; SMS wording as secondary evidence (see attribution playbook) |
| The specific campaign/plan a machine belongs to | not queryable — never assert; ask for the activity page or hand off |

Never present a derived guess as "the entitlement expires on ...": state the
instance-level expiry from the API, then explicitly mark the entitlement
expiry as console-check (a real ticket had support read it from a back-office
view the public APIs here do not cover).

## 3. Branches after expiry (customer picks one; the skill only guides)

### Branch KEEP — continue using the instance
1. Settle any arrears and keep a buffer balance (rule chain in M1).
2. Decide billing form: staying pay-as-you-go is valid; a subscription may be
   cheaper for steady usage — cost comparison itself belongs to the cost
   inspection skill, this skill only explains the mechanics and the path.
3. Billing-method conversion runs in ONE DIRECTION per document:
   - pay-as-you-go -> subscription (customer "convert to monthly"): use the
     console billing-conversion entry on the instance; verify the doc you
     cite covers THAT direction.
   - subscription -> pay-as-you-go is the opposite operation
     (`https://help.aliyun.com/zh/ecs/user-guide/change-the-billing-method-of-an-instance-from-subscription-to-pay-as-you-go`).
   A real ticket showed support handing the customer the OPPOSITE-direction
   link — check the direction against the customer's request before quoting
   any conversion document.

### Branch CAMPAIGN PLAN — "can I renew the trial onto the cheap activity package?"
Recorded ticket answer pattern: fixed-price campaign packages are bound to
NEW purchases of specified specifications; a trial instance generally CANNOT
be renewed or converted onto such a plan. The compliant workflow is:

1. Back up: create a custom image of the current instance
   (`https://help.aliyun.com/document_detail/35109.html`).
2. New-purchase the campaign instance from the activity page (eligibility and
   regional stock are campaign rules — hand off / activity page, not here).
3. Move data: switch the new instance's system disk to the custom image.
4. Public IP does NOT migrate: the address changes; update DNS/whitelists.
5. Release the old instance only after verifying the new one — with the full
   risk-disclosure gate.

### Branch STOP — "I don't want it anymore"
Go to [stop-billing-checklist.md](arrears-trial-billing-stop__stop-billing-checklist.md). Two trial-specific
traps: (a) customers assume expiry releases everything — it does not; (b) the
trial machine's disk/snapshot/EIP residue keeps billing after the console
list looks empty.

## 4. Notification panic triage (very common)

An expiring-soon SMS arrives; the customer reads it as "my ECS server is
being deleted". First attribute the message subject — it may name a different
product (a security-center trial package) or a machine already released — per
[billing-attribution-playbook.md](arrears-trial-billing-stop__billing-attribution-playbook.md). Then:

- subject = this ECS instance: apply Branch KEEP/STOP above;
- subject = another product: hand off with the billing-side exclusion
  already proven (instance expiry time + balance state from the script);
- subject = a machine already released: explain the delayed/system-generated
  notification pattern; confirm no live instance exists in the sweep.

## 5. Entry-page eligibility questions (image / region / plan choices on the trial page)

The trial entry page only offers the OS versions, regions and
specifications IT lists; an option missing there is a campaign-entry
limitation, not a product-wide one, and trial instances generally cannot
switch region afterwards. Eligibility questions route to the activity page /
human commercial channel ([handoff-map.md](arrears-trial-billing-stop__handoff-map.md)); this skill adds
only the factual: what region and charge type the CURRENT instance has.

## 6. Documents (verified links only)

- Pay-as-you-go starter guide:
  `https://help.aliyun.com/zh/ecs/user-guide/ecs-pay-as-you-go-starter-guide.md`
- Billing-method best practice:
  `https://help.aliyun.com/zh/ecs/user-guide/best-practices-for-ecs-billing-methods.md`
- Subscription -> pay-as-you-go conversion (OPPOSITE direction example):
  `https://help.aliyun.com/zh/ecs/user-guide/change-the-billing-method-of-an-instance-from-subscription-to-pay-as-you-go`
- Custom image creation (migration backup):
  `https://help.aliyun.com/document_detail/35109.html`
- Release an instance:
  `https://help.aliyun.com/zh/ecs/user-guide/release-an-instance`.
