# M4 — Resource Package / Savings Plan / Coupon Deduction Rules

This skill has **no read-only inventory API for packages, savings plans or
coupons** within its whitelist. Therefore deduction analysis runs in
DEGRADED mode: it proves WHERE deduction is zero from the bill triple
(`PretaxAmount` / `DeductedByResourcePackage` / `DeductedByCoupons`) and
classifies the WHY against the deterministic rule list below plus the
package facts the customer states. Confidence is stated explicitly; a
"correctly associated but still not deducted" case goes to a backend
ticket with the evidence pack, never to a guess.

## Deduction-failure reasons (deterministic rule list)

| # | Reason | Rule as proven by tickets |
|---|---|---|
| R1 | Item type mismatch | An OSS storage package never offsets egress traffic or data-retrieval items; a CDN package never offsets ECS public traffic (separate billing systems); the ECS file-backup basic free quota covers Cloud Backup only, NOT snapshots |
| R2 | Redundancy mismatch | Storage packages strictly distinguish redundancy type and never cross-deduct: Standard-LRS package vs zone-redundant (ZRS) billed usage — and the reverse — both fail; ECS snapshot storage IS deductible by a Standard-LRS storage package |
| R3 | Region mismatch | Region-scoped packages never deduct other regions' usage; snapshot deduction is same-region; a "mainland common" package does not cover Hong Kong / Macau / overseas |
| R4 | Allowance exhausted | A fully-consumed downlink traffic package leaves every later GB to bill pay-as-you-go until renewal/reset |
| R5 | Activation gap | Old package exhausted at one hour, renewal activates at a later hour: usage inside the gap bills with zero deduction — and the ~2h metering delivery delay hides the warning |
| R6 | Association conditions | Student/compute-plan packages only deduct instances created THROUGH the plan's own entry; any later configuration change (upgrade/downgrade) re-orders the instance and stops plan deduction |
| R7 | Free-quota preconditions | The limited-time-free snapshot quota needs the disk BOUND to the free auto-snapshot policy; manual snapshots and unbound disks bill normally |
| R8 | Coupon rules | See below |

## Coupon / voucher rules (state verbatim)

- A coupon **cannot offset an already-issued bill**: it applies only to
  bills or orders created AFTER issuance. "Waive this existing charge" is
  a commercial decision for the duty manager, never a coupon outcome.
- Pay-as-you-go bills consume eligible coupons automatically at
  settlement time; prepaid orders auto-filter usable coupons at the
  payment page (nothing to "find" there).
- Campaign coupons (e.g. student credits) may exclude pay-as-you-go
  specifications entirely — check the applicability page.
- A usable coupon can be consumed in parts across multiple orders/bills
  until its value is exhausted.

## Package coverage quick matrix (what CAN offset what)

| Charge | Offset by | Not offset by |
|---|---|---|
| ECS public outbound traffic (pay-by-traffic) | Shared traffic plan (fixed-public-IP IPv4, pay-by-traffic instances only), CDT allowance (post-upgrade: monthly 20 GB Chinese-mainland free quota, tiered pricing) | CDN packages, OSS downlink traffic packages, storage packages |
| Snapshot storage | OSS Standard-LRS storage package (same region), per deduction rules above | Cloud Backup free quota, IA/archive-oriented packages other than LRS standard |
| Instance spec (pay-as-you-go) | Savings plan / reserved-style plans meeting family+region conditions; compute plan if associated per R6 | Storage/traffic packages |
| Disk capacity | Storage capacity unit plans covering the disk category | OSS packages |

The longest purchasable term for shared-traffic / CDT style plans observed
in tickets is 1 year — for instances with a longer remaining life, cover
the residual by balance instead of promising an unbought discount.

## How to run the check (skill workflow)

1. `--deduction-report --billing-cycle YYYY-MM` lists every row in fee with
   zero deduction and every row partially deducted.
2. Match each un-deducted row against R1..R8 using the customer-stated
   package type / region / redundancy / validity window.
3. Output the verdict with the reason id and the DEGRADED caveat; when the
   customer insists the association is correct (R6 edge), stop and hand off
   with the evidence pack — that is a system-side check, not a rules
   question.
