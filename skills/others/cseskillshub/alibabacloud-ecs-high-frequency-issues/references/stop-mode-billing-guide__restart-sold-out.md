# Restart fails after economical stop: out of stock

This is the anxious path. The instance still exists, the customer cannot start it,
and the first question is always about the data. Answer the data question first,
then the cause, then the way out.

## 1. The wording to match

Verified sentence seen in the console of a customer who could not restart:

> The requested resource is sold out in the specified zone; try other types of
> resources or other regions and zones.

Read it as: the zone has no stock for that compute shape. Economical stop released
the vCPU, memory and GPU allocation, so the start has to win a fresh allocation, and
this time it lost.

It is **not**:

- a billing fault, and not a reason to expect a refund;
- a lost or corrupted instance;
- a lost disk: the system disk and data disks still exist and their content is intact.

Any other failure wording must be quoted exactly before it is interpreted. If the
text matches nothing verified here, do not invent a mapping: hand the exact sentence
to human support and say so plainly.

## 2. Read-only side-evidence

```bash
python3 scripts/areas/stop_mode_billing_guide/ecs_stop_mode_billing_guide.py check-stock --region-id cn-hangzhou \
  --instance-ids i-example --zone-id cn-hangzhou-b \
  --instance-type ecs.g6.large \
  --error-text "The requested resource is sold out in the specified zone"
```

- `--zone-id` and `--instance-type` are taken from the queried instance when they are
  omitted; the report declares that auto-fill explicitly.
- `--destination-resource` defaults to `InstanceType`. That default is an assumption;
  state it in the answer instead of presenting the result as a complete stock picture.
- The query sees only what the current account can see, and stock moves minute to
  minute. A zone that shows availability now can be sold out when the customer clicks.

Never turn this read into a promise. "Available in the query" is not "your start will
succeed".

## 3. Ways out, in the order to offer them

1. Retry the start later in the same zone: cheap, and enough when the shortage is brief.
2. Start with a different instance type in the same zone, in the same family where the
   workload allows it. The customer performs the change; this skill only reads state.
3. Move to another zone or region in the same account. Cross-zone moves can change
   addresses and latencies; say so before recommending it.
4. Back up first, then rebuild: snapshot the disks, build a custom image, and launch a
   new instance from it in a zone that has stock. Hand the snapshot and image work to
   the snapshot and image topic; this skill keeps only the rule that the data is safe
   where it is.
5. If the instance must be started for a business deadline and none of the above
   works, open a human support case with the exact error sentence, the instance id,
   the zone and the requested type.

## 4. What to say about the data

- Disk content is preserved while the instance exists, including when the start fails.
- The failure is an allocation problem, so it does not touch the disks.
- Data becomes unrecoverable only when the instance or the disk is released, which is a
  separate customer action with an explicit confirmation.
- For a business-critical instance, taking a snapshot before any stop is the cheap
  insurance, and it is the reason this package points at the snapshot topic rather
  than performing anything itself.

## 5. Related states that are not out of stock

| What the customer reports | What it actually is | Where to look |
|---|---|---|
| Stopped for a long time and the start spins | Normal provisioning time, or a guest that is slow to boot | Power state via `verify-status`; a running state with an unreachable service is a different topic |
| Start refused because of arrears | Account balance problem, not stock | Hand off to billing and human support |
| Started but a different public address | Expected after economical stop | `references/stop-mode-billing-guide__enable-steps-and-prerequisites.md` section 3, then the fixed-address handoff |
| Instance gone from the list | Wrong region, wrong account, or released | Re-run `assess` per region; never conclude "released" from an empty list |
