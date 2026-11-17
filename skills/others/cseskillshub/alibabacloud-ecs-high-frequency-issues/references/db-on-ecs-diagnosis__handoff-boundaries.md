# Hand-off boundaries

This tier covers exactly one vertical symptom area: deployment, connection,
availability and performance triage of self-managed databases inside ECS
instances. Adjacent symptoms are recognised, evidenced as far as this tier's
data allows, and moved on - never diagnosed or fixed here. Each target below is
a sibling skill whose identifier this tier's evidence supplied, a named human
channel, or - where no identifier was supplied - a tier described by its scope
and marked for confirmation. An identifier is never guessed to fill a column.

## What stays here

* Layered remote-connection triage (the L0-L8 walk) for database ports (3306, 6379, 1433,
  5432, 27017 and custom/dynamic ports) with the `timed out` versus
  `Connection refused` error-semantics split.
* Authentication and grant layer *identification* for self-managed MySQL, SQL
  Server, Redis, PostgreSQL and MongoDB (mixed-mode auth, host grants,
  bind-address, dynamic-port drift) - check procedures and evidence, with all
  changes left to the customer.
* Install / migrate / backup / restore *environment pre-checks*: disk free
  space, inode headroom, memory pressure, port availability, login-path
  readiness. The restore or migration work itself is business-layer, not here.
* Database performance triage: sustained metric reading, spec-family
  interpretation (shared vs dedicated), separating "resource-chain" from
  "business SQL" causes before handing the halves off.
* Database-port security exposure checks and the hardening standard set.
* Capacity/inode/memory pressure *detection* through the whitelisted guest
  commands - only to answer "is the database failure actually a capacity
  failure?" - then immediate hand-off of the cleanup itself.

## Recognise and hand off

| Recognised in the session | Hand off to | Why it is not this tier |
| --- | --- | --- |
| Disk expanded in the console but the guest size unchanged; partition or filesystem not grown | `area:disk-expand-diagnosis` | Expansion chain, not a database symptom (ticket evidence: console shows new size, `df` still old) |
| Instance will not boot, stuck in a starting/stopping state, unbootable OS, service that never came up after boot | `area:instance-state-diagnosis` | Lifecycle/boot tier; the database is a bystander there |
| Disk IO latency / throughput below the purchased spec | `area:resource-bottleneck` | Storage performance tier; this skill only quotes instance-level specs |
| Disk full / inode exhausted cleanup, deleted-file space reclamation, file-count governance | The ECS disk-capacity and inode tier (skill id to confirm) | Capacity tier owns the cleanup; this tier only triages whether capacity caused the database symptom, snapshot-first |
| SSH/RDP/console cannot log into the instance at all (OS-level login, not a database port) | The ECS remote-login entry tier (skill id to confirm) | Login channel is separate from database connectivity |
| Managed product instances - RDS, product Redis/Tair, DTS, DBS - failing, migrating or mis-billed | The product's own console/support channel | ECS-side skill; product-internal faults are out of the API surface declared here |
| Orders, refunds, price-difference changes, renewal discounts, "does ECS come with a database" purchases | Commercial / billing human channel (billing console) | No order or bill API is declared or called here; the skill only checks expiry/release status through `DescribeInstancesFullStatus` |
| Ransomware encryption, deletion accidents, forensic timelines, intrusion cleanup | Third-party data-recovery specialists (cloud marketplace) and the security-incident tiers; rebuild via re-initialize-system-disk is a documented manual step | This skill preserves the scene (gated snapshot) and hardens; it never cleans, deletes or decrypts |
| Business-layer work: writing SQL, slow-query optimization, SSMS restore wizards, ERP / panel (e.g. third-party hosting panels) product internals | The customer's DBA / the software vendor | Platform support does not own in-database business work; ticket practice says so explicitly |
| A platform-arranged physical host migration or replacement, cross-zone relocation, a platform-side component upgrade | Offline human ticket | Needs a scheduled downtime window and the customer's acknowledgement of the data risk; never performed by a skill |

## Hand-off script (adapt the bracketed parts)

"Detected problem root cause is [X] (evidence: [API/command readings with
timestamps]), which belongs to the [Y] scope - please continue with
[the target the hand-off ladder named, or this skill itself]. This skill completed the database-side triage;
the conclusions and evidence list above can be carried into that session
directly."

For commercial cases: "Changes to packages, refunds and bill detail are
handled by the commercial channel in the billing console - this skill does not
act on orders."

For intrusion cases: "Please let a data-recovery specialist handle it. Do not
pay the ransom note and do not delete or reinstall anything before the
snapshot preserving the scene is in place."

## Evidence carried across the boundary

The hand-off report always includes, from the legs this skill ran: instance
id / region / zone, power status and any scheduled events, bound security
group ids, instance type and spec read, metric readings with their period and
timestamp, every guest reading collected (dispatched or pasted) labeled with
its source, snapshot status, and the layer where the trail stops. Nothing is
summarized away: the next tier should not repeat a query this tier already
answered.
