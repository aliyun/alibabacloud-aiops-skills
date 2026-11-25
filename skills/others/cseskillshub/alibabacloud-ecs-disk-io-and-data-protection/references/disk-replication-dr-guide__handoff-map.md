# Hand-off Map (what this skill identifies but does not treat)

This skill covers ONE symptom axis: cloud disk disaster recovery (async replication pairs,
consistency replication groups, zone-redundant ESSD) and the read-only evidence that supports it.
Everything below is recognised here and then routed. The rule is **identify, one-sentence judgement,
hand off** -- never start a diagnosis of the neighbouring domain inside this skill.

Skill names marked *(name pending alignment)* come from the batch planning list and still need to be
matched against the final skill inventory; use the domain description if the name does not resolve.

## 1. Routing rules

| Symptom that arrives at this skill's door | One-sentence judgement rule | Where it goes | Evidence in this tier |
|---|---|---|---|
| High bill, traffic fees, refund demand, "backup/DR is eating my balance" | The core ask is charge attribution, not DR configuration | Cost attribution and billing reconciliation; overdue / trial-expiry and stop-billing flows *(name pending alignment)* | Two tickets where the customer blamed DR/backup for public outbound traffic; the human check was "no DR or cloud backup usage found in the bill" |
| Abnormal IP ranges hitting the site, requests to block addresses | The fix is a security-group / access-control change | Layered access-blocking diagnosis (security group, firewall, WAF) and brute-force IP blocking *(name pending alignment)* | One ticket where the resolution was blocking an attacking IP range in the security group |
| Site returns 404 or renders blank after data was copied or restored; panel-side protection switches | Root cause sits in the guest web application or control panel | Panel / web-server operations diagnosis and "website unreachable or slow" layered localization *(name pending alignment)* | Verified conversation: the customer found the cause themselves -- the panel's tamper-proof (file protection) feature |
| Copying between a cloud disk and a local disk is very slow | The ask is disk IO performance, not DR | Disk performance and IO diagnosis *(name pending alignment)* | One ticket where the agent speculated many small files and IO throttling while the account was overdue; never closed |
| Which physical machine room / data centre serves my instance (filing forms) | The ask is machine-room information | Instance physical machine-room address lookup *(name pending alignment)* | One ticket where support answered with the machine-room lookup link |
| End-to-end high availability: load balancing, auto scaling, standby server, cloning instances, images | Beyond the disk-DR product boundary; instance- and architecture-level | Load balancing / auto scaling are cross-product; instance clone and custom-image paths are their own domains *(name pending alignment)* | One ticket asking for automatic switch to a standby server within 10 minutes |
| Snapshot creation, policies, quotas, cross-region copy procedure, snapshot cost clean-up | Snapshot lifecycle, not the DR axis | `alibabacloud-ebs-disk-snapshot-management` *(name pending alignment)* | One ticket about automatic off-site snapshot backup |
| Image-based or snapshot-based DR architectures | Different DR medium (image / snapshot), different skill | `alibabacloud-ecs-disaster-recovery-snapshot`, `alibabacloud-ecs-disaster-recovery-image` *(name pending alignment)* | Existing online skills with overlapping "disaster recovery" naming -- keep this skill's triggers disk-specific |
| Anything needing a write call on the customer's account | Outside this skill's read-only contract | Console self-service (guide with section 5 protocol of `SKILL.md`) or the owning domain | Design constraint of the RO_GUIDE archetype |

## 2. Hand-off wording (fill the braces, keep the scope sentence)

### Charges blamed on DR or backup

> I checked account UID `{uid}` in the regions `{regions}` with read-only queries. Replication-pair
> and consistency-group objects are outside the read scope of this check, and billing data is not
> either, so this covers instances, disks and snapshots in those regions only. Result:
> `{evidence lines from the inventory report}`. Your charge is on the public-network traffic line,
> which is settled from the billing side, so I am handing the amount question to the cost
> attribution flow. Nothing here is a refund decision, and I have not changed anything.

### Replication or backup objects found and the customer wants them stopped

> The inventory shows `{what exists, in which region}`. Stopping disk protection is a change you
> make in your own console: the steps, the risk (in-flight replication data is discarded when a pair
> is removed during replication) and the verification are in
> `references/disk-replication-dr-guide__dr-operation-guidance.md`. After you finish, I can re-run the same read-only query in
> region `{region}` to confirm the disk and snapshot state, and you can confirm the pair is gone on
> the async replication page.

### In-guest / panel symptom after restoring data

> This behaves like a web-server or control-panel setting inside the instance, not a disk replication
> issue: `{one-line reason based on the inventory}`. I do not log into instances or panels and never
> need your panel address or account. Please run the read-only checks in
> `references/disk-replication-dr-guide__self-check-commands.md` and paste the output back, or continue in the panel / website
> operations flow, which owns that layer.

### Slow copy between a cloud disk and a local disk

> The disk-side facts are `{category, size, status, charge type}`, so nothing here points at
> replication. Copy speed between a cloud disk and a local disk is a disk performance question
> (small-file workload, local disk class, and the throttling that can follow an overdue account),
> which belongs to the disk performance diagnosis flow. Please include the read-only output listed in
> `references/disk-replication-dr-guide__self-check-commands.md` when you continue there.

### Machine-room / filing question

> ECS does not fail a single instance over to another server by itself, so the failover field of a
> filing form is answered with the machine room of the instance you actually run. Looking up that
> address is a separate flow; this skill can only confirm the region and zone of your instance from
> the read-only inventory: `{region / zone lines}`.

### Architecture-level high availability

> Disk async replication protects the disk layer with a manual switch; it does not automatically
> move your service to a standby server. Automatic request redistribution and capacity changes come
> from load balancing plus auto scaling, and a standby instance you build and maintain yourself --
> all outside this skill. Read-only facts about your current instances and disks are
> `{inventory lines}`; the architecture work goes to the load balancing / auto scaling domains.

### Authorization failure

> The read-only query failed with `NoPermission` / `ImplicitDeny` for action `{action}`. Ask the
> account owner to attach the minimal policy in `references/ram-policies.md` (that file names exactly
> the read actions this skill needs), then I will re-run the same query. No credential material is
> needed from you and none should be pasted into this conversation.

## 3. Things this skill must never claim

- "Your account has no backup anywhere" -- only "nothing found in account `{uid}`, regions `{regions}`,
  via `{the four whitelisted read calls}`".
- A reason for a bill amount, a refund decision, or a traffic source IP.
- Any in-guest state (files present, panel switches, service logs) it did not receive from the customer.
- Any replication-pair or group status: not reachable here; customer console self-check only.
- That a failover succeeded at the business level: application verification (mounts, connection
  strings, DNS) is the customer's check.
