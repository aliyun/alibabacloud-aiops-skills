# Post-Clone Verification Checklist (capabilities K4 + K5)

Run this after the customer performs a clone (wizard or image chain). The
machine-readable version lives in `scripts/axes/instance_clone_guide/_constants.py`
(`POST_CLONE_CHECKLIST`, `GUEST_SELF_CHECK_COMMANDS`), served by
`scripts/axes/instance_clone_guide/clone_guidance.py --checklist`. Owners: read-only query = this
skill's script; customer console / customer in-guest = the customer acts and
reports back; sibling area = recognize and hand off (see handoff-map.md).

## Checklist

| # | Verify | Owner | How |
|---|---|---|---|
| 1 | The new instance exists with the intended status | read-only query | `python3 scripts/axes/instance_clone_guide/clone_readiness_check.py --region-id <region> --instance-ids <ids>` |
| 2 | No duplicate creation after a "clone failed" page (loss prevention) | read-only query + console | Compare the reported region instance count and the console instance / resource-stack lists against expectations BEFORE any retry |
| 3 | Data disks present on the clone | customer console | Image detail page lists associated disks; then the new instance's disk list |
| 4 | IP changed: DNS records, web-panel site bindings (for example the BT/BaoTa panel), partner whitelists, IP-bound licenses | customer | Point them at the new private/public IP; EIP-style IP retention is a sibling area, not a clone answer |
| 5 | Security group of the new instance re-confirmed | customer console | The clone may reference a copied group; check rule contents; behavioral diagnosis of rules belongs to the security-group sibling area |
| 6 | Guest identity duplication (image-derived fleets) | customer in-guest, read-only | Ask the customer to run the read-only commands below inside their own OS and paste the output back; remediation (file changes, probe restart) goes to the Cloud Monitor / remote-connection sibling areas |
| 7 | Snapshot and copy-traffic cleanup | customer console | Delete unneeded snapshots after verification; note the cross-region traffic already spent |
| 8 | Fee sanity check | customer + commercial handoff | Review the bill for snapshot storage and copy traffic; compensation, refunds and balance withdrawals are commercial processes outside this skill |

## Guest-side read-only self-check commands

The CUSTOMER runs these inside their own operating system and pastes the
output back. This skill never executes anything inside an instance; these
lines are pure listings that change nothing.

```bash
blkid
ls -l /dev/disk/by-uuid /dev/disk/by-partuuid
cat /etc/machine-id
df -h
```

Why: machines copied from one image can share filesystem UUIDs, partition
UUIDs, machine-id values and monitoring-agent identity files. A `root=UUID`
kernel parameter may then resolve to the clone's data disk instead of the
system disk and break boot (observed in a real ticket in this tier, where
recovery happened via rebuilding from the data-disk snapshot, performed by
the customer). Duplicate agent identity shows up as monitoring data jumping
between the source and the clone.

## Evidence discipline for this checklist

- Existence conclusions come from the read-only queries and console
  listings, never from the task banner: page status and the platform's real
  result can disagree in both directions.
- If the customer's pasted facts and the read-only facts cannot
  cross-verify (screenshot region/account mismatch, instance not found for
  the claimed account), DO NOT conclude "stuck/succeeded/failed". Output
  the verified facts, the missing self-check items, and the escalation
  wording (see progress-triage.md). That matches where human sessions
  actually end in these cases.

Related: clone-solution-matrix.md, clone-scope-and-billing.md,
progress-triage.md, handoff-map.md (relative to this directory).
