# Lifecycle: Expiry, Renewal, Early Unsubscription, Manual Release

Rules for subscription instances reaching (or leaving early from) their
term end. The three branches - renew, wait for expiry, unsubscribe early -
have different money and data outcomes; present them as branches, never as
one blur. All rules below are anchored to a support dialogue that was
verified verbatim this round (T-263837C7); date math uses the `ExpiredTime`
returned by the read-only query when present, otherwise the expiry shown in
the customer's console list.

## Branch 1: renew and continue

- Renewal keeps everything; done by the customer in the console renewal
  entry. Not covered further by this skill (renewal pricing pages are the
  authority).

## Branch 2: do nothing -> expiry timeline

- Manual release becomes available from 00:00 of the day AFTER the expiry
  timestamp. Verified example from the dialogue: expiry
  `2026-09-03 23:59:59` -> customer may release from `2026-09-04 00:00`.
- If nobody acts, the instance is auto-deleted and released 15 days after
  expiry and the data is NOT recoverable. [verified-dialog T-263837C7]
- Advisory behavior: when `ExpiredTime` is in the past, say explicitly
  which of the two windows the instance is in (manual-release window vs
  approaching auto-delete) using the days computed from the real field.

## Branch 3: early unsubscription (refund path)

Console path observed verbatim in the dialogue: Billing Center ->
unsubscribe resources -> ordinary cloud resources -> five-day no-reason
refund or non-full refund -> select the instance -> submit.
Entry: https://billing-cost.console.aliyun.com/refund/refund
(customer console page quoted in ticket T-263837C7; verify reachability
before quoting cold).

The five mandatory notices (deliver ALL of them, verbatim in substance,
before the customer submits - a weak-model-safe checklist, not prose):

1. After refunding, the resource is cleared and its data is NOT retained -
   back up first (snapshot/custom image, customer action).
2. A successful refund usually returns within about 2 working days.
3. The invoiceable quota of the account is reduced automatically after the
   refund.
4. Gifts attached to the order (vouchers, extended service periods) are
   voided.
5. The refundable amount is exactly what the refund page displays - the
   customer confirms it on-screen before submitting; this skill never
   predicts it.

Supporting rules (verified dialogues): refund defaults to the original
payment channel; amounts above the invoiceable quota go to the account
balance [T-3CA25349]. Rules background docs (dialogue-quoted, reachability
pending re-verification):
https://help.aliyun.com/zh/user-center/user-guide/refund-destinations and
https://help.aliyun.com/zh/user-center/user-guide/unsubscription-rules

## Pay-as-you-go side of the lifecycle (contrast)

- Pay-as-you-go instances are released by the customer any time; the money
  risk moves to arrears: overdue -> stop -> auto-release, data gone
  [ticket-summary T-381ADD6C].
- Opening pay-as-you-go needs combined balance+vouchers >= 100 CNY
  [verified-dialog T-3CA25349].

## Release-time expectations (both modes)

- Charges seen shortly after a release were typically accrued before it
  (billing lag): cross-check with `residual-billing-checklist.md` row 5
  before escalating. [ticket-summary T-82BD6370]
- After a release, walk the residual checklist rows 1-4 - the instance
  being gone does not stop disks, snapshots, traffic items, or side
  products. [ticket-summary T-1F45414E]
