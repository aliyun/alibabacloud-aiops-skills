# Visibility triage: region / account / product views, and status semantics

The dominant root cause family behind "I cannot find it" and "the status is
wrong" tickets (union 852 tickets, scenarios A+B of this tier) is that the
ECS console is a **scoped view**, and the customer is looking through the
wrong scope. This manual sequences the checks; the evidence side is
`scripts/areas/console_resource_lookup/lookup_console_resource.py`, and the navigation side is
`scripts/areas/console_resource_lookup/console_navigation.py`.

## Step 0 -- ask once, ask completely

Before any query, collect: resource type; the exact id (i-.../d-.../s-...) or
name or IP; the region currently shown in the console's top-left switcher;
how many accounts the customer operates (different login phone numbers,
member accounts); whether the item might be a Simple Application Server or an
order rather than an ECS resource; for a missing button, its exact label, the
device used (PC browser vs phone app) and any error text. Ticket T-19C9B029
closed unanswered precisely because "cannot find the entry" named no
function: an unscoped request cannot be triaged at all.

## The three views, in order

### 1. Region view (most frequent single cause)

Every ECS console list (instances, disks/block storage, snapshots, images,
security groups) renders ONE region at a time. T-88FFF9CD was solved by
nothing but switching to the right region. The skill replaces guess-and-check
with an exhaustive per-region `DescribeInstances` sweep and reports every
region where the id exists. Snapshots deserve the same suspicion: in
T-C8FA71CA the customer twice asked "is it the wrong region?" and the agent
never closed that hypothesis -- the sweep exists to close it mechanically.

### 2. Account view

Resources created under another account never appear. T-CA25DD32: the
instance lived under a second account registered to another phone, and that
account was overdue. The sweep prints the account id of the current
credential; if the resource is found with OTHER credentials, or the sweep is
empty everywhere, put the account question next. Campaign "same person
already used the benefit" disputes (T-557197AF, T-B1F0887B) are also
account-view problems, but their data is marketing-side: explain, then route
to the human commercial channel.

### 3. Product view

Wrong console entirely: Simple Application Server is not ECS (T-E847A8C0
bought SAS, searched the ECS list); saved-plan and similar purchases are
orders in the billing center, not ECS objects (T-DF87AF28); RAM users live in
the RAM console (T-8AA82DFC took six customer turns because the agent never
said "different console" first); DNS records, EIPs, DAS charges and
Wanxiaozhi site settings each belong to their own product's console
(T-F66F330B, T-AB34E2B9, T-D91ACD63, T-AFD53C57). The entry map in
[console-entry-map.md](console-resource-lookup__console-entry-map.md) carries the verified links; the
skill stops at the boundary of another product's console.

Residual scope filters: a stuck resource-group filter hides everything
outside the group -- tell the customer to reset the view to account scope.
The mobile app renders a reduced feature set (T-8BBBBAF4, T-75C85AC2): all
navigation guidance here assumes the PC web console and says so.

## Status semantics once the resource is found

Two orthogonal areas answer "the status is wrong":

| Area | Where it lives | What it can prove |
|---|---|---|
| Control-plane state (`Status`: Pending/Starting/Running/Stopping/Stopped) | this skill's queries | what the platform intends and tracks; lock reasons (Financial/Security) ride on it |
| In-guest reality | only inside the OS | whether the OS booted, a service listens, a disk is partitioned/mounted |

Hard rules, all ticket-verified:

- Console "In Use" for a disk proves the ATTACHMENT finished. It does not
  prove the disk is usable in the OS: partition + file system + mount are a
  second step (T-37463A4B: the greyed "configure mount point" button was grey
  because the console-side step was already complete).
- A resized (expanded) cloud disk keeps showing the old capacity inside the
  guest until the partition and file system are extended -- a second-layer
  job, never a "console bug" (T-E268C6BA).
- One cloud disk can contain several logical partitions; partition count is
  not disk count (T-67C8E3F5, DiskGenius confusion).
- Security/violation banners can show disposed-of records after the disposal
  is lifted (T-0ADBA324): the queried `Status`/lock fields are the objective
  anchor, the banner belongs to the security module and is verified there.
- `Stopped` on a subscription instance still bills; expired-plus-overdue
  freezes, auto-snapshot policy pauses and short auto-snapshot retention
  explain "charged for what I cannot see" (T-C8FA71CA, T-D52AE555,
  T-804A0640). The lifecycle question itself routes out (see
  [handoff-matrix.md](console-resource-lookup__handoff-matrix.md)).

## Why buttons exist or not (the "missing entry" that is actually a gate)

| Gate | Effect a customer reads as "entry missing" | Verified ticket |
|---|---|---|
| Billing mode | a subscription data disk exposes no detach action until its billing method is converted to pay-as-you-go | T-5E9C11A3 |
| Image type | non-public-image subscription instances refuse self-unsubscription ("switch to a public image") | T-C3D40EB0 (summary) |
| Terminal form | phone-app console lacks desktop entries | T-8BBBBAF4, T-75C85AC2 |
| Instance capability / agent state | password reset unavailable when the Cloud Assistant agent is absent | T-04713EBF |
| Account eligibility | regions/specs invisible on the buy page under real-name/overdue constraints; custom supply (e.g. domestic CPU lines) is sales-gated | T-8D8F2AD9, T-9D1410F9 |
| Information policy | physical machine-room address is never displayed; reviewed human disclosure only | T-3F5A3E75 |

## Concept corrections that end tickets faster than any query

| Customer wording | Product reality | Real entry point |
|---|---|---|
| "there is no shutdown/permanent-stop button" | the action is called RELEASE, and it destroys data irreversibly | instance list More menu (manual, customer-side only) |
| "unbind my domain from the server" | domains resolve via DNS records, nothing binds them to ECS | Alibaba Cloud DNS console |
| "console has no FTP management" | FTP is software inside the guest; the console offers instance-detail file upload/download instead | instance detail page, official doc |
| "the snapshot is gone" | snapshots are per-region AND auto-snapshots expire; two different searches | snapshot page per region + billing/overdue state |

Quote `scripts/areas/console_resource_lookup/console_navigation.py --question "<customer wording>"` output
verbatim for these rows; do not paraphrase entry paths from memory.
