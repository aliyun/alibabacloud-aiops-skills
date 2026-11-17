# M3 — Timing and Amount Caliber (the authoritative statements)

State the caliber BEFORE discussing any number. Most "the bill is wrong"
disputes end here; the remaining residue is a bill-system question, not a
diagnosis question.

## When bill numbers become authoritative

1. **The final bill detail of a month is issued at 12:00 on the 3rd day of
   the following month.** Before that moment, current-month figures are
   provisional reference only and are **not a basis for reconciliation**;
   reconciliation of the current month is officially unsupported.
2. **Bill detail lags actual consumption by ~24 hours.** Instance-dimension
   fields (instance config / spec / nickname / resource group / public IP /
   private IP / zone) lag by **~48 hours**.
3. **Post-paid metering delivery itself has a delay** (roughly around 2
   hours for hourly items): a period currently in progress may not have
   appeared in the bill yet.
4. **Pay-as-you-go settles monthly**: the deduction seen at the start of
   month N pays the cycle N-1. A "charge on Aug 1" is July's bill, not an
   August event. This mapping is deterministic and is applied automatically
   by `--charge-date`.

## Amount calibers that coexist in one period (they are NOT supposed to be equal)

| Caliber | Where it comes from | Meaning |
|---|---|---|
| Payable `[official-doc]` | bill rows; API field `PretaxAmount` is for internal diagnosis only, never the customer-facing label | the amount finally owed for the month's cloud resources, AFTER every discount, subscription deduction (such as a savings plan) and coupon deduction has been taken off |
| Repaid `[official-doc]` | settlement; API field `CashAmount` is for internal diagnosis only, never the customer-facing label | what has ACTUALLY been paid: the sum of cash, vouchers AND stored-value cards. Do NOT gloss it as "what the balance/cash already paid" and do NOT list vouchers as something separate from it — voucher payment is already inside this figure |
| Outstanding `[official-doc]` | month overview page | the unsettled remainder, and the official relation between the three terms is a formula, not a paraphrase: Outstanding = Payable − Repaid |
| Due / unpaid | month overview page | unsettled portion incl. previous cycles |
| Unsettled / arrears | account view | unpaid balance including non-bill items; drives overdue behavior |
| Deducted by package / coupon | bill rows | CNY-equivalent of allowance consumption — already excluded from Payable above, and the voucher-paid part is already counted inside Repaid, so quoting it beside either one double-counts. Never shown inside the payable figure's label |
| Order amount | order list | prepaid purchases incl. auto-renewal — lives OUTSIDE the bill detail |

Payable / Repaid / Outstanding are the working terms of this file. The customer's
bill page displays these three calibers under Chinese labels, and the official
relation between them is stated as a formula on the page, not as a paraphrase.
Both the literal labels and the formula are carried by anchor
`billing-attribution__repaid-caliber`, whose claim is hash-verified against the
official page — quote them from there. This file is English-only by platform rule
(MUST 4.1.2), so it deliberately holds no copy of the labels: a prose copy would
be a second, unverified source of truth that can drift away from the page the
anchor is verified against, and a drifted label is a customer-facing defect.

Consequences to state to the customer:

- "Bill total = what I owe" is FALSE while a cycle is provisional or older
  cycles are unsettled.
- A renewal payment and a post-paid settlement on the same day are two
  different objects (order vs bill).
- If the four layers (overview / bill / instance items / settlement) still
  disagree after this mapping, the residual is a bill-system question:
  output the evidence pack and route to a backend review ticket — never
  invent a cause.

## Bill usage vs monitoring usage

Both numbers may be legitimately different for the same period:

- Bill usage is metered on the billing side and lags ~24h (instance fields
  ~48h); monitor charts are nearer to real time but are sampled
  (hourly averages by default) and have their own retention window.
- The traffic cross-check compares them with a tolerance (the script uses
  15%) and shows BOTH values side by side; it never "corrects" one with the
  other.
- A persistent, unexplained gap after the final bill (3rd 12:00) goes to
  backend review with the evidence pack.

## Overdue mechanics (customer-impact statement)

- An overdue balance cuts pay-per-traffic service almost immediately
  (arrears of even a tiny amount stop delivery); long-overdue pay-as-you-go
  resources are eventually released and their data is unrecoverable.
- Settling arrears (top-up) is a manual customer action at the billing
  center; this skill only quantifies what is owed and why.
