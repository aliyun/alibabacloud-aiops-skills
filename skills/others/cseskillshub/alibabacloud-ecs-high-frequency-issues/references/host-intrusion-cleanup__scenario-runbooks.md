# Scenario runbooks

Three branches, one shared triage front-end. Each branch lists what the cloud can
prove, the decision points, the verdict wording, and the manual steps that always
belong to the account holder.

Everything here is guidance. Nothing in this file is an instruction for the skill to
change a resource: cleanup, quarantine, process termination, rollback, re-imaging,
security-group edits and unblock appeals are class D in
[ram-policies.md](ram-policies.md) and stay human.

Grounding: the decision points and the misconception list come from this tier's
ticket evidence (1,029 tickets across the three member scenarios), the API surface
comes from [ram-policies.md](ram-policies.md), and the official links come from
[help-docs.md](host-intrusion-cleanup__help-docs.md). Where a statement is guidance rather than a returned
value, it is labelled as guidance.

## 0. Shared triage front-end

Run these four checks before any branch logic. They are cheap and they prevent the
most common wasted round trips.

### 0.1 Product form

Confirm the target really is an ECS instance. A cloud web hosting (virtual host) or
lightweight product has **no ECS API surface and no remote logon**: malicious files
there are handled through the hosting control panel's file manager or over FTP. A
customer who is told to "log in to the server" on a web hosting product will search
for an entry point that does not exist. Ask for the instance id (`i-...`); if the
customer only has a domain or an IP and the exposure surface carries no matching
record, treat "this is not ECS" as a live possibility and route per
[handoff-boundaries.md](host-intrusion-cleanup__handoff-boundaries.md).

### 0.2 Penalty recognition

The combination *mining or malware alert* **plus** *sudden loss of public
connectivity* (the instance is up, VNC works, but nothing reaches it from the
internet and nothing can leave it) is a platform security penalty, not a network
fault and not a platform defect. Say that plainly and keep gathering evidence.

Release is self-service, not ticket-only: once the infection is fully cleaned and the
host hardened, the customer submits the release application on the Security Center
penalty records page (`https://yundun.console.aliyun.com/?p=scnew#/sc/event/resources`).
This skill cannot lift a penalty, cannot submit that application and does NOT predict
the review outcome or how long it takes - the status shown on that page is
authoritative. The human support/appeal channel is the escalation path only after the
self-service application is rejected. Never quote a lift window or a number of days as
a promise (see the quoting rules in
[help-docs.md](host-intrusion-cleanup__help-docs.md)).

### 0.3 Commercial and legal demands

Refunds, unsubscription, withdrawal, contracts, invoices, liability claims, lawyer
letters and requests for an official "ransomware certificate" are not technical
questions. Preserve the evidence, then route to the human channel. Two facts to
state once, calmly: the platform does not issue forensic certificates for
ransomware incidents, and it can only produce historical contracts or invoices
through the order and contract pages.

### 0.4 This tier has no customer-facing error codes

Host-intrusion tickets carry symptom wording ("files are encrypted", "the alert came
back"), not error strings. Do not invent an error code to sound precise, and do not
attribute a code to a customer who never produced one. The only codes this skill
quotes are the ones an API or the CLI actually returned, plus the two permission
literals `NoPermission` and `ImplicitDeny`.

## 1. Branch `ransom` - ransomware and encrypted data recovery

Trigger wording: files renamed or unreadable, a ransom note such as `readme.txt`, a
bitcoin or payment demand, "encrypted my files", a lock screen, or a server that no
longer boots because system files were encrypted. A black screen or an unreachable
instance can be the *result* of encryption, so triage before assuming a boot fault.

### 1.1 What the cloud can prove

| Evidence | Source | What it settles |
| --- | --- | --- |
| Ransomware, malicious-process or suspicious-logon alerts with their handling status | Security Center suspicious events | Whether the platform already saw the intrusion, and when |
| Purchased Security Center edition | Security Center version config | Whether anti-ransomware or auto-handling capability even exists on this account |
| Exposed ports and assets | Security Center exposure surface | The likely entry vector (3389 and 22 to the whole internet dominate this tier) |
| Snapshot inventory: existence, status, creation time, retention | ECS snapshot query | The recoverability verdict - the single most valuable output of this branch |
| File-backup restore jobs | Cloud Backup restore-job query | Whether a *file* backup (as opposed to a disk snapshot) exists, and what it can restore |

What the cloud cannot prove: whether a specific file on the disk is encrypted, what
the ransom note says, or who connected to a customer service. The platform keeps no
application-level access logs for customer services, so source attribution is not
available - say that instead of speculating.

### 1.2 Decision points

1. **Is there any accomplished snapshot or file backup created BEFORE the incident
   window?** This is a mechanical comparison, not an opinion. If the customer cannot
   name the incident time, ask for the ransom note's file timestamp or the newest
   encrypted file's modification time, and re-run with `--incident-time`. Without a
   window the verdict stays `undecided`, and the report says so.
2. **Is the incident time inside a local time zone?** The script reads a naive
   `--incident-time` as UTC and prints that assumption. A timezone slip can move the
   chosen recovery point by hours; confirm with the customer when the margin is
   small.
3. **Which disk holds the data that matters?** System disk first, then data disks.
   A snapshot of the system disk does not restore a data disk, and file backup does
   not replace a system-disk rollback.
4. **Was the retention policy the reason there is nothing to restore?** A retention
   of one day (or 24 hours), a paused automatic snapshot policy, or a manually
   deleted snapshot are the recurring causes in this tier. The script flags short
   retention explicitly. A deleted snapshot is gone; the platform keeps no hidden
   copy.
5. **Is the customer asking for a snapshot of the current, already-encrypted state
   in the hope of recovery?** Correct that immediately (see 1.4).

### 1.3 Verdicts and their wording

* **Restorable.** Name the recovery point (snapshot id and creation time), require a
  current-state evidence snapshot first, then give the console rollback steps: the
  rollback is executed by the account holder in the console, it is irreversible, it
  overwrites current disk content, and the order is system disk first, then data
  disks. Support cannot perform a rollback on the customer's behalf - state that as
  a boundary, not as an apology.
* **Undecided (no incident window).** Accomplished snapshots exist but cannot be
  matched to a time. Ask for the window and re-run; do not pick a snapshot by
  guessing.
* **Not restorable.** No accomplished snapshot or file backup predates the incident.
  Say plainly that platform-side recovery is impossible, that the platform does not
  decrypt ransomware-encrypted data, and that decryption or data-recovery attempts
  belong to specialized third parties reachable through the Alibaba Cloud
  Marketplace - with the caution that no paid service can guarantee decryption. Then
  fix the forward-looking part: retention policy, automatic snapshot policy, and
  entry-point hardening.

### 1.4 Misconceptions to correct every time

* **"Take a new snapshot and restore from it."** A snapshot of an already-encrypted
  disk preserves the crime scene; it cannot bring back the original data. Recovery
  only ever comes from a backup made *before* the encryption.
* **"The platform should restore my data / prove I was attacked."** Responsibility is
  shared: the platform secures the cloud, the customer owns the guest OS,
  applications, data and access control. No forensic certificate is issued.
* **"File backup and snapshots are the same thing."** They differ in scope (a file
  backup restores directories and files of a running instance; a snapshot rolls a
  whole disk back), in what they can recover, and in how they are billed. When the
  customer confuses them, the Cloud Backup restore-job evidence settles it with data.
* **"My snapshots were there last month."** Check retention and automatic-release
  settings before accepting the premise; an auto-released snapshot no longer exists.

### 1.5 Manual steps for this branch (never executed here)

Rolling a disk back from a snapshot; creating or deleting snapshots in bulk;
configuring an automatic snapshot policy; stopping an instance to contain spread;
re-installing the operating system; engaging a third-party recovery service; any
refund or unsubscription. Each is reported with its console entry, its risk and the
approval it needs.

## 2. Branch `miner` - mining, virus and trojan intrusion

Trigger wording: mining or virus alerts that keep returning, `xmrig`,
`kdevtmpfsi`, a mining pool connection, CPU pinned at 100%, an unknown process, a
backdoor or trojan finding, "my server was poisoned", a zombie or botnet alert,
bandwidth consumed by an unknown remote peer.

### 2.1 What the cloud can prove

| Evidence | Source | What it settles |
| --- | --- | --- |
| Alert list with names, levels, handling status and timestamps | Security Center suspicious events | What was detected, whether it was handled, and whether the same name recurs |
| Edition and capability | Security Center version config | Why some alerts cannot be auto-handled: auto-handling and some scan features are edition-dependent, so an unhandled alert is a capability or console question, not a detection failure |
| Affected-asset statistics | Security Center field statistics | Whether one host or many are involved |
| Exposed management and business ports | Security Center exposure surface | Entry-vector candidates (22, 3389, database and framework ports) |
| Recent CPU utilization | CloudMonitor metric reading | Corroboration only: sustained high CPU is consistent with a miner, and proves nothing on its own |
| Live processes, sockets, scheduled tasks, startup items | One gated in-guest probe per approved run | The persistence mechanism - the thing that has to be found before cleanup can succeed |

### 2.2 Decision points

1. **Are alerts recurring after handling?** Recurrence means the entry vulnerability
   was never fixed - an unpatched application, a weak password, an exposed admin or
   database port. Cleaning without patching re-delivers the payload. This is the
   single most common reason a customer says "I already killed it and it came back".
2. **Which alert names repeat, and how often?** The script lists recurring names;
   use them to separate one persistent implant from many unrelated findings.
3. **Is public connectivity gone as well?** Then apply 0.2 (penalty recognition)
   before anything else: an in-guest probe needs Cloud Assistant, and a penalized
   host may not be reachable.
4. **Is there persistence, and where?** Processes alone are not enough. Check all
   four categories: a miner that is killed but survives through a scheduled task or a
   startup entry will be back within minutes.
5. **Is the guest channel even available?** If Cloud Assistant does not answer, the
   report degrades and hands the customer the exact command to run in Workbench or
   VNC and paste back. Never present a probe that did not return as if it had.

### 2.3 Handling guidance for this branch

Order matters, and the order is always: **evidence snapshot, then contain, then
clean, then patch, then verify.**

1. Evidence snapshot (gate C) before any cleanup guidance.
2. Contain by narrowing access - a manual security-group change performed by the
   account holder: management ports to named office addresses only, business ports
   only where the service truly serves them, and a deny rule for a confirmed
   attacker address when one is known. This skill never edits a rule.
3. Clean: terminate the malicious process, delete or quarantine the files, remove
   the scheduled task and the startup entry - all manual, all in the console or in
   the guest by the account holder, and all after the snapshot exists.
4. Patch the entry vulnerability and rotate every credential on the host. Without
   this step the incident repeats.
5. Verify with a second evidence pass: a fresh alert list and, if the customer
   approves, a second gated probe (a new approval is required for each one).

### 2.4 Misconceptions to correct every time

* **"Anti-virus finished, so the problem is solved."** Handling an alert is not
  patching the hole; and some alerts can only be handled manually at the customer's
  edition.
* **"The block is a platform fault."** A penalty is a protective action triggered by
  the infection, and lifting it is an appeal, not a repair.
* **"High CPU proves mining."** It corroborates. Name the process and its remote
  peer from the guest evidence before using the word miner as a conclusion.

## 3. Branch `webshell` - defacement, webshell and content tampering

Trigger wording: the site redirects to gambling or other illegal pages, injected
scripts, black links or hidden SEO links, a changed home page, a webshell found or
quarantined by Security Center, file permissions changed by someone else, search
results showing another site's title, or "my website was hacked".

### 3.1 Three-layer localization

Work from the outside in and say which layer each fact belongs to:

1. **Name resolution.** Does the domain still point at this origin? A record that
   points elsewhere makes this a DNS or registrar question, not a host question.
   Resolution checks are a customer step here: this skill holds no DNS action in its
   verified surface, so it asks the customer to read the record and paste it.
2. **Origin content.** If resolution is correct, the origin is serving the malicious
   content: injected script files, a modified template, or a webshell that renders
   on request.
3. **Application code and upload paths.** The implant got in through something: an
   upload or injection vulnerability in a framework or an open-source application, an
   unpatched component, or a stolen admin credential.

A defaced site with a *clean* scan result is the important case: when the scan engine
finds no trojan but the content is still wrong, the attacker edited the page content
directly. That is a code-integrity problem, and the answer is restoring known-clean
code plus a developer review - not another scan.

### 3.2 What the cloud can prove

| Evidence | Source | What it settles |
| --- | --- | --- |
| Webshell, tampering and malicious-file alerts with their isolation status | Security Center suspicious events | Whether the platform already isolated or blocked the file, which often answers "what do I do next" on its own |
| Edition and protection modules | Security Center version config | Whether web-tamper protection or advanced protection is even purchased |
| Exposed web and management ports | Security Center exposure surface | Which surface the implant most likely arrived through |
| Snapshot inventory and file-backup restore jobs | ECS snapshot query, Cloud Backup restore-job query | Whether a clean pre-defacement restore point exists - asked before the customer is asked to describe their backups |

What the cloud cannot prove here: which file differs from the deployed source, what
the injected script contains, or whether the admin account was used by the attacker.
Those are content-level readings outside the frozen four-category guest whitelist, so
they are handed to the customer as a paste-back list in
[guest-forensics-commands.md](host-intrusion-cleanup__guest-forensics-commands.md).

### 3.3 Decision points

1. **Is the product ECS?** See 0.1; a web hosting product changes the entire channel.
2. **Is resolution correct?** Wrong record - route to the DNS/registrar path.
3. **Did Security Center already isolate the file?** If the status says isolated or
   blocked, tell the customer that first: the immediate leak may already be closed,
   and what remains is code integrity and the vulnerability.
4. **Is there a clean restore point?** If yes: evidence snapshot, then restore from
   known-clean code or the pre-defacement backup, then patch. If no: manual code
   review with the developer, because there is nothing clean to go back to.
5. **Is the customer asking this skill to delete the malicious files?** It will not.
   Deletion and quarantine are class D; the skill provides the candidate list, the
   console entry and the risk.

### 3.4 Misconceptions to correct every time

* **"The platform was hacked, so the platform must clean my site."** The guest OS,
  the application and its content are the customer's side of the shared
  responsibility model. The skill says this once, with the boundary documented, and
  then helps with what it can actually do.
* **"SEO hijack, DNS hijack and defacement are the same problem."** They are three
  different layers with three different fixes: site admin-panel settings, name
  resolution, and origin files. Search-engine snapshot complaints belong to the
  search engine's own channel.
* **"No trojan found means nothing was changed."** See 3.1: direct content edits are
  invisible to a signature scan.

## 4. Evidence report skeleton

Keep the customer-facing summary in this order; it mirrors what the script prints.

1. Scope: account, region, instance, session id, and which values were supplied
   versus auto-filled.
2. Alerts: what was detected, handling status, recurring names.
3. Entry vector: exposure findings, with the note that per-rule security-group
   verification is a console check.
4. Corroboration: the CPU reading, labelled as corroboration.
5. Recoverability: the snapshot and file-backup inventory, and the verdict.
6. Guest evidence: the approved probe, its command, its output, and the suspicious
   candidates - or the paste-back request when the channel was unavailable.
7. Handling guidance: manual steps, gated behind the snapshot-first rule.
8. Hardening: the six items in [hardening-checklist.md](host-intrusion-cleanup__hardening-checklist.md).
9. Boundaries: what was refused and why, what was handed off and to whom, plus the
   snapshot billing reminder.
10. `STATUS` and `NEXT_ACTION`.
