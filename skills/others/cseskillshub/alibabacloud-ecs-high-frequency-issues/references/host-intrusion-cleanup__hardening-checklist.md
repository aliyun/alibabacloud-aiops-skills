# Hardening checklist

Relay all six items at the end of every run, in this order, regardless of branch.
This is the wording that closed tickets in this tier: short, actionable, and it always
ends with the snapshot-before-change rule. It is guidance for the account holder -
nothing here is applied by the skill.

## The six items

1. **Restrict the security group so management ports accept connections only from
   named addresses.** SSH (22) and remote desktop (3389) must never be open to
   `0.0.0.0/0`; open only the business ports the service truly serves. In this tier
   the exposed-management-port finding is the most common entry vector, and a single
   permissive rule among several bound security groups is enough to expose the port.
2. **Close or firewall-protect every management and database port.** 3306, 6379, 8069,
   11211, 9200 and similar should not face the internet. If a service does not need
   public access, remove the rule rather than relying on the application's own
   authentication.
3. **Set strong, unique passwords for every account on the host, and rotate all of
   them after an intrusion.** Weak or reused credentials on an exposed management
   port are the other dominant entry vector; assume every credential on a compromised
   host is known to the attacker.
4. **Upgrade the affected application and framework to a fixed version.** The
   recurring-infection root cause in this tier is usually an exploited application
   vulnerability (an upload or injection flaw, an unauthorized-access endpoint).
   Killing the process without patching the hole re-delivers the payload.
5. **Take disk snapshots regularly, with a sane retention and an automatic snapshot
   policy.** Retention of one day or 24 hours is how recoverable incidents become
   unrecoverable ones; a paused policy or a deleted snapshot has the same effect.
6. **Patch high-risk system and application vulnerabilities promptly - and always
   create a snapshot BEFORE patching or cleaning**, so a bad update or a failed
   cleanup is reversible.

## Snapshot-first, stated separately because it is the rule that gets skipped

No cleanup, patching, rollback, re-imaging or containment change should start before
a current-state evidence snapshot exists. This skill can create that snapshot through
its gated write (one disk, one approval, billing disclosed), or the account holder
creates it in the console. Deleting the evidence snapshot afterwards is a manual
console step, and it is also how the customer stops paying for it: snapshots are
billed pay-as-you-go for their stored size, so an incident that leaves a dozen
evidence snapshots behind leaves a surprise bill.

## Branch-specific additions

**Ransomware branch.** Verify the backup chain end to end after the incident:
automatic snapshot policy enabled, retention longer than the incident window, and -
where file-level recovery matters - a file backup that actually covers the
directories the customer cares about. Anti-ransomware capability and automatic
handling depend on the purchased Security Center edition; if the edition does not
include them, say so instead of implying protection that is not there.

**Mining / virus / trojan branch.** After cleanup, confirm all four persistence
categories are clear (process, socket, scheduled task, startup item) - a miner that
survives through a scheduled task is back within minutes. Then re-check the alert
list after a day of normal operation, because recurrence is the signal that the entry
vulnerability is still open. If public connectivity was cut by a penalty, the unblock
request goes to the human channel with the cleanup evidence attached; this skill
cannot lift it.

**Defacement / webshell branch.** Add the code-integrity items: restore from
known-clean source rather than editing the live files, review upload paths and
template directories, rotate site admin and FTP credentials, and keep a deployable
copy of the current site so the next incident is a restore instead of an
investigation. A search-engine snapshot complaint is filed with the search engine's
own channel, not with the cloud platform.

## What the skill will not do, even when asked

Delete, quarantine, move or restore a file; terminate a process; stop, start or
reboot an instance; roll a disk back; replace or re-image a system disk; change a
password or key pair; add, edit or remove a security-group rule; delete a snapshot;
file an unblock appeal; take any commercial or legal action. For each of these the
report gives the console entry, the risk, the irreversibility warning where one
applies, and who must approve it.

## Documentation to hand the customer

Links live in [help-docs.md](host-intrusion-cleanup__help-docs.md): security overview and best practices
(the responsibility-sharing boundary), the mining-virus protection and handling
guide, data backup and the snapshot-versus-file-backup comparison, snapshot creation
and rollback, snapshot billing and deletion, and the anti-ransomware protection plan.
Quote a link only when it matches what the report actually concluded.
