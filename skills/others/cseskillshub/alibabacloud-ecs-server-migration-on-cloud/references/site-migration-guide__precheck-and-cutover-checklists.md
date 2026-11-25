# Pre-check and cutover checklists

Two gates around the move. The cloud rows are produced by `scripts/axes/site_migration_guide/site_migration.py`; the manual
rows are answered by the customer in the console or inside the instance.

## Pre-check (before anything is copied)

| # | Check | How it is answered | Stop condition |
|---|---|---|---|
| 1 | Source and destination inventory | `precheck` evidence: instance ids, status, region and zone, type, image id, billing type | The destination is not the region, zone, or account the customer meant |
| 2 | Destination sells the needed specification | `precheck` available-resource evidence for the destination region and zone | No sellable entry: change zone, change family, or accept a redeploy instead of a clone |
| 3 | System disk capacity | Manual: read both system disk sizes in the console | Destination smaller than source: the image or snapshot cannot be applied; this must be settled before the maintenance window |
| 4 | Data disks that must travel | Manual: list data disks and their sizes; confirm the image covers them | Data disk excluded: the site will boot without its uploads or database |
| 5 | Image and instance-type compatibility | `precheck` reports type and image; then validate on one pay-as-you-go instance of the target type | Test instance will not boot or log in: stop and change plan; do not touch production |
| 6 | Security groups bound to the destination | `precheck` evidence lists the group ids | Login and site ports are not open in that group: expect a failed cutover that looks like data loss |
| 7 | Cross-account carry-over list | Manual against [migration-paths.md](migration-paths.md) Path 3 | Promotions, prefix lists, port range lists, and security-group rules have to be rebuilt, not migrated |
| 8 | Volume to move | One allow-listed in-guest command per round, announced, confirmed, output pasted back: see [guest-inspection-and-errors.md](guest-inspection-and-errors.md) | Estimate unavailable: widen the transfer window rather than guess |
| 9 | Billing type, status, expiry | `precheck` evidence plus the console expiry date | Expired or retained instance: switch to the rescue path and treat the retention window as the clock |
| 10 | Snapshot baseline | Manual: snapshot the source system disk and every data disk, wait until completed | No snapshot: no destructive or capacity-related step may be proposed |
| 11 | Side services still billing | Manual bill item review: post-paid disks, outbound traffic, file storage | Leftovers will keep charging after the old server is gone |

## Cutover (after the copy, before the announcement)

| # | Check | Cloud or manual | What good looks like |
|---|---|---|---|
| 1 | Destination running | `cutover` status evidence | Running; anything else is an instance-state question and is handed off |
| 2 | Login ports allowed | `cutover` lists the bound group ids; the rules are edited by the customer | 22 or 3389 for login, 80 and 443 for the site, plus the application or control-panel port such as 8888 |
| 3 | DNS re-pointed | `cutover` prints the destination public address as the expected record value; the customer edits the record | Each authoritative record value equals the new address. Test from outside the local network and clear the local resolver cache before concluding a failure |
| 4 | Site answers by address, not only by name | Manual browser or curl check by the customer | Application pages render, not just the welcome page or a blank page |
| 5 | Service actually started | Manual; the customer starts it with their own service manager | A start attempt that reports a missing PID file usually means the service was never started, or a reload or check command was used instead of a start command |
| 6 | Database reachable and configured | Manual; compare the application configuration against the new database endpoint | No connection error; a connection error means configuration still points at the old database |
| 7 | File completeness | Manual with one allow-listed listing or size command per round, plus the customer's own check of theme, template, and upload directories | Directory counts and sizes match the pre-check baseline |
| 8 | Disk count and size versus baseline | `cutover` plus the console disk listing | Same number of disks. A size that reads smaller than purchased is an expansion question, not a migration failure |
| 9 | Private address not stale from the image | Manual inside the instance | The interface uses the address assigned in the new network; a copied static address breaks logins in a way that resembles a security-group fault |
| 10 | Old server stopped billing | Manual: released or unattached disks, traffic, side services reviewed | Post-paid disks detached and handled deliberately, not silently left mounted |
| 11 | Compensation, refund, extension requests | Human or commercial owner only | The skill states the rule and the entry point and never quotes an amount or promises an approval |

## Reporting rules

- Quote only values that appear in the evidence, and name the source of each: cloud query, console
  page the customer read, or pasted in-instance output.
- A missing fact is written as an open question with the exact command or console page that would
  answer it, never as an assumed number.
- If any evidence source failed, the run ends `STATUS: DEGRADED` and names the source; if none of it
  worked, `STATUS: FAIL` with the failing action and its minimum policy statement.
