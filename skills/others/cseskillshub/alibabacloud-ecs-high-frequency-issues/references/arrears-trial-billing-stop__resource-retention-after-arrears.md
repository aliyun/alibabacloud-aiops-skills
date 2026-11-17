# M2 — Resource Retention and Auto-Release After Overdue (Area A rules, evidence-disciplined)

This module states WHAT happens after an account becomes overdue, and —
equally important — HOW MUCH of it this skill may assert as fact. Numeric
retention windows (day counts) appeared in ticket dialogue as verbal support
statements but were NOT re-confirmed against an authoritative public document
during preparation of this skill. Policy adopted from the tier's requirements
document: **describe the rule qualitatively, cite the official document, and
never hard-code day counts or prices that only exist in ticket memory.**

## 1. The rules that matter for customer decisions

1. Overdue accounts enter a restricted state for pay-as-you-go products:
   instances are stopped, and resources can be progressively reclaimed.
2. There IS a retention window between "stopped/restricted" and "automatic
   release/deletion". Inside it, topping up restores; past it, resources and
   data are reclaimed automatically.
3. Snapshots are NOT exempt because of a customer-side "keep forever" flag:
   support tickets record snapshots that the customer believed permanently
   retained being auto-deleted after the arrears retention window, and
   **deleted snapshots are unrecoverable — support cannot restore them
   either**. Never promise recovery of an arrears-deleted snapshot.
4. The retention window differs per resource type (instance vs snapshot vs
   other pay-as-you-go artifacts). Treat any single quoted number as
   per-resource and document-sourced, or quote none at all.
5. Automatic release does not wait for the customer's consent message: the
   notification SMS is a warning, not a consent gate.

## 2. What the skill may and may not say

| Claim type | Allowed? | Basis |
|---|---|---|
| "A retention window exists; inside it, settle + restore works; past it, resources are reclaimed and data is gone" | YES | official overdue document + repeated ticket pattern |
| "Snapshot deletion caused by overdue is unrecoverable" | YES | ticket-confirmed support behavior |
| "The snapshot retention window is exactly N days" | NO — until an authoritative document is cited by the running agent from the official link below | ticket dialogue only |
| "Your data survived / your snapshot will come back" | NEVER | contradicts rule 3 |

If the customer needs the exact countdown NOW, the honest answer is: open the
official overdue-payment document (below) for the per-resource table, or ask
the console's retention display; the skill's own machine-readable evidence is
limited to instance Status / lock reasons.

## 3. Machine-checkable part (authorized read set)

- `ecs:DescribeInstances` → `Status`, `OperationLocks.LockReason`
  (a `financial` lock reason marks arrears-driven restriction; `Recycling`
  marks the pre-release phase in real responses).
- Absence of the instance from every swept region after overdue is consistent
  with automatic release already having happened — state it as consistent
  with, and have the customer confirm from the console + bill.
- Snapshot presence/absence: NOT enumerable with the authorized action set —
  CONSOLE-CHECK per region:
  `https://ecs.console.aliyun.com/snapshot` (the region selector switches the
  view; overdue-deleted snapshots simply vanish from this list).

## 4. Customer-facing script (adapt wording, keep the discipline)

> "Your account has been overdue. While overdue, pay-as-you-go resources are
> stopped and, once the retention window in the official overdue-payment
> policy passes, they are released automatically and the data cannot be
> recovered by anyone, including support. Settle the balance as soon as
> possible. Whether THIS resource is still inside the window can be read from
> its state: it currently shows <evidence from the script>, and the exact
> per-resource periods are in the official document: <link>."

## 5. Official documents (verified links only)

- Overdue-payment rules (authoritative for the retention table):
  `https://help.aliyun.com/zh/ecs/overdue-payments`
- Snapshot overview (billing + retention behavior context):
  `https://help.aliyun.com/zh/ecs/user-guide/snapshot-overview`
- Snapshot billing: `https://help.aliyun.com/zh/ecs/snapshots-1`
