# Root Causes and Routing (disk async replication / DR tier)

This file maps what customers SAY to what is usually TRUE, and tells you
which evidence to collect and where to route. The three groups below are
distilled from real support tickets in this tier. Route first, then answer;
never diagnose a neighboring domain here.

## Group A -- DR capability misconception

**What the customer says**

- "Does ECS have a disaster recovery plan? Can it switch to a standby server
  within 10 minutes automatically?"
- "If my instance fails, which server / which data center does it fail over to?"
- "I want my Shanghai snapshots backed up to another city automatically."

**What is usually true**

- A single ECS instance has NO automatic failover; the customer assumes the
  platform switches business to a standby server by itself.
- Snapshots are region-local; there is no automatic cross-region snapshot
  backup.
- Disk-level DR exists as a product axis the customer must set up and operate:
  async replication (replication pair), consistency group, zone-redundant
  ESSD. See [dr-capability-boundary.md](dr-capability-boundary.md).

**Evidence to collect (read-only, via `scripts/axes/disk_replication_dr_guide/disk_dr_inventory.py`)**

- Which regions/zones the instances and disks live in.
- Whether any disk is in a zone-redundant category.
- Whether snapshots exist (and the automatic-snapshot flag on disks).

**How to answer**

1. State the boundary honestly: no automatic failover for a single instance;
   snapshots do not cross regions automatically.
2. Show the inventory as evidence of the CURRENT posture ("your disks in
   cn-hangzhou are single-zone ESSD with no snapshots -- today there is no
   disk-level DR redundancy for them").
3. Offer the product paths from the capability-boundary table with their
   official doc URLs; every create/failover/delete step is executed by the
   customer in the console, accompanied by the risk notice, expected result
   and verification method.
4. Business-level RTO/RPO targets, load-balancer/auto-scaling architectures
   and filing-form wording are out of scope: explain the difference and hand
   off per [handoff-map.md](handoff-map.md).

## Group B -- charges misattributed to "DR / backup"

**What the customer says**

- "Disaster recovery and backup keep running and eating my traffic budget --
  turn them off and refund me."
- "I never touched anything, but DR/backup charges keep growing."

**What is usually true**

- In the observed tickets, the account had NO DR/backup usage at all; the real
  driver was public outbound traffic (for example abnormal high-frequency
  access from external IP ranges). Customers see a big bill and attribute it
  to an imagined background DR service.
- Occasionally an automatic snapshot policy or another backup feature really
  is enabled -- which is exactly why the evidence list comes first.

**Evidence to collect (read-only)**

- Run the inventory for every region the customer names (and ask which
  regions matter; never extrapolate one region to the whole account).
- The inventory answers ONE question with evidence: do DR/backup-related
  resources (disks, snapshots, auto-snapshot flags, zone-redundant
  categories) exist in the queried account + regions?

**How to answer**

1. Relay the evidence list plus the visibility-scope declaration verbatim:
   account UID, regions queried, APIs used, and the NOT-covered list
   (billing details, cloud backup/HBR, security groups, guest state,
   replication-pair objects).
2. If DR/backup resources EXIST: list them, explain what each one is, and --
   when the customer wants them stopped -- guide the customer-executed
   teardown (delete replication pair doc / snapshot policy management handoff)
   with risk notice and post-step verification.
3. If NONE exist: state exactly that, bounded to the queried scope. Do NOT
   conclude why the bill is high -- bill amounts, traffic sources and refunds
   are the billing domain. Hand off with the template in
   [handoff-map.md](handoff-map.md).
4. **Disputed claims**: when the read-only evidence contradicts what the
   customer insists (repeated complaints, refund demands), output the
   evidence list with its scope declaration, do not adjudicate, do not
   promise refunds and do not argue -- hand off to billing support and, if
   the customer asks to escalate, to human support. Never invent a billing
   conclusion either way.
5. Abnormal traffic from attacking IP ranges (the frequent real cause) is a
   security/access-control matter: hand off; this skill never changes
   security-group rules and never advises specific rule edits itself.

## Group C -- in-guest problems after copying data from a cloud disk

**What the customer says**

- "After I reset the system disk and copied my website files back from the
  data disk, pages return 404 or render blank, but the files exist and
  permissions look normal."
- "Copying data from the cloud disk to a local disk is extremely slow."

**What is usually true**

- The fault lives INSIDE the guest: web-server or management-panel
  configuration (for example a panel's tamper-proof / file-protection feature
  blocking page access or renaming), site-root mapping, default-index
  settings -- or disk IO performance (many small files, or throttling while
  the account is overdue). None of these is a disk async replication / DR
  fault, and this skill has no guest visibility.

**Boundary (hard)**

- This skill NEVER runs commands inside customer instances, never logs into
  panels, and never asks for panel addresses, usernames, passwords or any
  credential (a real ticket leaked panel credentials into the conversation --
  do not repeat that mistake).
- What this skill CAN contribute: the disk-side facts from the inventory
  (disk type, status, size, charge type -- e.g. a pay-as-you-go disk under an
  overdue account can have degraded IO, which the disk charge type helps
  confirm or rule out as a hypothesis, never as a verdict).

**How to answer**

1. State that the symptom is not a disk-replication/DR fault, based on what
   the inventory shows (replication/DR objects are not even involved in a
   file-copy workflow inside the guest).
2. Give the customer the read-only self-check list from
   [self-check-commands.md](self-check-commands.md) and ask them to paste the
   OUTPUT back (never credentials).
3. Hand off: website/panel symptoms -> website and panel operations support;
   slow-copy/IO symptoms -> disk performance diagnosis. Use the templates in
   [handoff-map.md](handoff-map.md).

## Routing table

| Symptom signal | Group | First action |
|---|---|---|
| failover / standby server / automatic takeover / cross-region snapshot backup questions | A | Inventory + capability-boundary answer + product-path guidance |
| "DR/backup is charging me" / "turn off DR and refund" | B | Inventory as evidence list + scope declaration; then teardown guidance (if resources exist) or billing handoff (if not) |
| 404 / blank pages / slow copy after moving data between disks | C | Disk-side facts + self-check list + handoff (website/panel or disk performance) |
| replication pair create / failover / delete how-to | A (guidance) | Cite the matching official doc URL + risk notice + expected result + verification |
| bill amounts, invoices, refunds, traffic pricing | out of scope | Billing handoff template |
| security-group rule changes, blocking IP ranges | out of scope | Access-control handoff template |
