# Enabling economical stop mode: prerequisites, steps, warnings

The customer performs every step below in the console. This skill never performs
them; it checks the prerequisites read-only, hands over the steps, and afterwards
re-reads the power state.

## 1. Prerequisite check first

| Prerequisite | How it is established here | If it fails |
|---|---|---|
| Billing method is pay-as-you-go | `ecs:DescribeInstances` returns the charge type | A subscription instance offers no stop-mode choice; converting is the customer's change, and after converting the instance may start to appear differently in the bill |
| Instance is in the queried region and account | Same call | Nothing was found: ask for the region and the account, do not infer |
| Instance is running or in a state that accepts a stop | `ecs:DescribeInstanceStatus` | A pending or already stopped instance needs no mode choice now |
| The customer accepts losing the system-assigned public address | Not queryable; it is a disclosure | State the warning before the customer acts, and offer the fixed-address handoff |

Command that produces the first two rows:

```bash
python3 scripts/areas/stop_mode_billing_guide/ecs_stop_mode_billing_guide.py assess --region-id cn-hangzhou \
  --instance-ids i-example1,i-example2
```

## 2. Where the option actually is

The highest-frequency dead end in reported cases: the choice is not a switch on
the instance list page and not in a settings tab. It appears **inside the confirmation
dialog that opens after the customer clicks Stop**.

1. Open the ECS console instance list for the target region.
2. Select the instance or instances.
3. Choose the stop action.
4. In the dialog that opens, select the economical option instead of the normal one,
   and read the two consequences the dialog lists.
5. Confirm. The state moves to stopped; the compute allocation is given back.

If the customer reports that no such choice appears in the dialog, do not conclude the
feature is missing. Check the billing method again: a subscription instance is the
usual reason, and the dialog simply offers the plain stop.

## 3. What to disclose before the customer clicks confirm

Say all four, in this order, every time:

1. Compute billing stops; disk billing does not. The bill drops, it does not vanish.
2. The system-assigned public IP address is released. On the next start a different
   address may be assigned, and the released address cannot be reserved or claimed back.
3. The next start needs fresh stock in that zone. It can fail with a sold-out message
   even though the instance still exists, and disks and data are then untouched.
4. This skill changed nothing. It only reads state; the dialog action is the customer's.

Anything that depends on a fixed address - a filing record, an allowlist at a partner,
a hard-coded client firewall rule - is a reason to stop before step 5 and hand off to
the fixed-address topic in `references/stop-mode-billing-guide__handoff-boundaries.md`.

## 4. Read-only verification after the customer acted

```bash
python3 scripts/areas/stop_mode_billing_guide/ecs_stop_mode_billing_guide.py verify-status --region-id cn-hangzhou \
  --instance-ids i-example1
```

What this proves, and what it does not:

- Proves: the power state moved, so the customer's click landed.
- Does not prove: which stop mode was chosen. Never write "confirmed in economical
  stop mode" from this output. The mode marker is a blind spot; the customer reads it
  on the instance details page, or sends a screenshot.

## 5. Batch and cost-reduction cases

When the customer wants to save money across several idle instances:

1. `assess` over the id list to see which ones are pay-as-you-go at all.
2. Separate the answer into three groups: eligible now, needs a billing-method
   conversion first, and out of scope because it is a fixed-address or filing case.
3. Give the steps once, not per instance, and repeat the four disclosures.
4. Re-read the states afterwards and report only states.

The window for a savings effect on the current bill is decided by the billing system,
not by this skill. Do not promise that today's charge disappears.

## 6. Neighbouring choices that are not this one

- Forcing the stop is a different checkbox in the same dialog; it cuts power abruptly
  and can leave the guest filesystem dirty. It does not change which mode was picked.
- Performance mode on a burstable instance is unrelated to stop modes.
- Starting, restarting and releasing are separate console actions with their own
  consequences; releasing destroys data irreversibly and always needs a backup first.
