# Conversion Playbook (Billing-Method Change, Both Directions)

Customer-performed console guidance with pre-checks, risk gates, and
read-only re-verification. The skill itself NEVER executes a change: this
tier is a read-only advisory, so every remediation step below is something
the customer clicks in their own console while the skill is watching the
outcome through Describe*-class queries only.

## Step 0 - always: pin the exact target instance

Tickets show even support staff quoting the wrong instance id first and
correcting later (T-C3E9D9B3: two ids were exchanged in one conversation).
Before any direction is discussed, run the advisory with `--region-id`
(and `--instance-ids` when given) and echo back `instance_id + name +
public IP + current billing type` for the customer to confirm. The read-only
inventory is the single source for this step; never confirm from memory.

## Direction A: pay-as-you-go -> subscription

Pre-checks (all must be addressed before console steps):

1. Account not in arrears. Arrears hide the console conversion entry
   [ticket-summary T-AABC1FF1]; a `financial` value under `OperationLocks`
   in the read-only output is the programmatic signal. Fix = customer tops
   up in the Billing Center; the skill never touches money.
2. Instance in normal status (not locked / not expired) - visible via
   `Status` + `OperationLocks`.
3. Expectation set: the conversion itself does not interrupt the running
   service or touch data [ticket-summary T-AABC1FF1 support statement].
4. No price promises: the order page shows the only authoritative price;
   campaign packages (activity offers) go to a sales manager [ticket-summary
   T-E089159A].

Console steps (customer performs):

1. ECS console instance list for the region: https://ecs.console.aliyun.com/home
   (entry observed in ticket T-C3E9D9B3 dialogue).
2. Locate the confirmed instance; open its billing-method change entry
   (wording along the lines of "Change Billing Method" / "Convert to
   Subscription" - follow the on-screen form).
3. Choose the term, review the displayed amount, submit.
4. Expected: billing field becomes subscription (PrePaid) shortly; an
   `ExpiredTime` appears.

Re-verification (read-only): re-run the advisory and check
`InstanceChargeType` / `ExpiredTime`.

## Direction B: subscription -> pay-as-you-go

Risk gate FIRST - the customer must acknowledge all four points before
steps are presented:

1. After the switch the instance is hourly-billed; arrears can lead to
   automatic release with data NOT recoverable - this exact loss happened
   in ticket T-381ADD6C (instance auto-released after the switch, no
   snapshot, unrecoverable; customer never replied).
2. Backup first: snapshots / custom image are created by the customer in
   the console before the switch.
3. Promotional/activity-price purchases do not receive a price-difference
   refund on this change (downgrade-equivalent rule) [ticket-summary
   T-F740449A].
4. Refund destination rules (verified dialogue T-3CA25349): default is the
   original payment channel; if the refund exceeds the account's current
   invoiceable amount it lands in the account balance instead. The exact
   amount is only ever shown on the console page at submission time
   [verified-dialog T-263837C7 notice 5].

Console steps (customer performs): mirror Direction A with the conversion
entry aimed at pay-as-you-go, then immediately walk
`residual-billing-checklist.md` (data disks especially - see T-49041DCA
below).

Re-verification (read-only): `InstanceChargeType` is `PostPaid`; bills for
the pre-switch window may still arrive due to billing lag (see residual
checklist).

## Known link-direction trap

Ticket T-C3E9D9B3: the customer wanted pay-as-you-go -> subscription, but
the support agent pasted the subscription -> pay-as-you-go document. The
help page quoted in that dialogue is kept in the advisory output with an
explicit re-check-the-direction warning:
https://help.aliyun.com/zh/ecs/user-guide/change-the-billing-method-of-an-instance-from-subscription-to-pay-as-you-go
(reachability and bidirectional coverage of that page are pending human
verification this phase). The reverse-direction ("pay-as-you-go to
subscription") help document had NO hit in the injected help search and is
a known documentation gap for this phase: guide by console wording, not by
a remembered URL.

## The "converted the instance, missed the disk" case

T-49041DCA: after converting an instance, costs kept accruing because the
attached DATA DISK was still pay-as-you-go; the fix was a separate
disk-billing conversion entry (document quoted in that ticket, URL not
captured - guide the customer to the disk billing entry in the console and
the Disks list). This is why Direction B ends with the residual checklist
as a mandatory follow-up, and why the residual intent exists in its own
right.

## Error-string handling (this tier)

| Customer-visible signal | Interpretation | Action |
|---|---|---|
| `DiskExpiredOrInArrears` (400, `ModifyInstanceChargeType`) -- message: "Your account has an overdue payment for the specified instance." (the console shows the same message in Chinese) | Arrears on the account/instance during the conversion | Customer tops up in Billing Center first; re-run the advisory to confirm the financial lock cleared |
| `InvalidAccountStatus.NotEnoughBalance` (403, `ModifyInstanceChargeType`) -- message: "Your account does not have enough balance." | Balance below the pay-as-you-go opening threshold | Guide the customer to fund the account; the 100 CNY combined balance+voucher floor applies [verified-dialog T-3CA25349] |
| `InstanceExpiredOrInArrears` (403, `StopInstance`) -- message: "The specified operation is denied as your prepay instance is expired (prepay mode) or in arrears (afterpay mode)." | NOT a conversion error: the stop request was rejected because the prepaid instance is expired or the account is in arrears. `ModifyInstanceChargeType` does not publish this code | Keep it in the stop/start-expiry branch (route to `area:instance-start-stop-anomaly` / the expiry area); never present it as the failure of a billing-mode conversion |
| Conversion entry missing | Arrears lock, abnormal status, or promo constraint | Walk pre-checks 1-2, then the promotional rule (Direction B gate 3) |
| `NoPermission` / `ImplicitDeny` from the advisory's own queries | Credential lacks a Describe action | Degrade to guidance-only mode per SKILL.md; see `ram-policies.md` |

The three literals above are quoted verbatim from the official OpenAPI error
tables of `ModifyInstanceChargeType` (`DiskExpiredOrInArrears`,
`InvalidAccountStatus.NotEnoughBalance`) and `StopInstance`
(`InstanceExpiredOrInArrears`); the console shows the same conditions, and
only the `DiskExpiredOrInArrears` message ("Your account has an overdue payment
for the specified instance.") is published in the same table. Keep each code attached to its own operation -
quoting a stop-instance code as the conversion failure sends the customer to
the wrong fix.

## Provenance discipline

Lines tagged [verified-dialog] were confirmed in full dialogue text;
[ticket-summary] lines were taken from ticket summaries whose conversations
could not be re-fetched this round (17 of 20 sampled tickets) and must be
treated as directional until the dialogue re-check completes.
