# Remediation Checklist (customer-executed; this skill guides only)

This skill never logs into the guest, never deletes anything, and never
changes any resource. It hands the customer the checklist below; every
customer-side action is taken by the customer, in their own console / remote
session, with the backup-first rule observed.

## Hard rules for every case

1. **Backup before touching anything.** Before any cleanup, page deletion,
   file replacement or password rotation, create a manual snapshot (or a
   full backup) of the affected disks from the ECS console yourself. This
   skill does not perform snapshots for you and does not enter the instance.
2. **Keep removal evidence.** Screenshot the violating page/entry before
   fixing it and after removing it; appeals for content violations require
   proof of deletion.
3. **Appeal after remediation, not before.** A review that finds the
   content still live ends badly; fix first, then submit the material set.
4. **Rectification windows are real.** Mining-communication and
   attack-behavior alerts carry deadlines; missing them escalates to a
   shutdown. If cleanup exceeds your ability, the deep in-guest cleanup
   belongs to the host-intrusion cleanup area (see handoff-map), with your
   own authorization.

## Self-inspection entry points (documentation-backed)

- Remote login for inspection/fixing: Workbench system management —
  https://help.aliyun.com/zh/ecs/user-guide/workbench-system-management.md
- Workbench CLI path (customer configures their own credentials):
  https://help.aliyun.com/zh/ecs/user-guide/install-and-configure-workbench-cli-credentials.md
- Stopping an instance from the console (e.g. to cut cost while an account
  action stands): https://help.aliyun.com/zh/ecs/user-guide/stop-an-instance.md
- General instance FAQ:
  https://help.aliyun.com/zh/ecs/instance-management-and-operations-faqs.md

## A. Defaced / injected or linked-out content (fraud, gambling, adult pages)

The most common trigger of instance and URL actions: the site was hacked,
tampered with, and hit by a fraud/gambling content sample pushed down by
superior authorities — even when "we only store game data and have no
website" (the associated site is what got sampled).

1. Compare the web root against your original code package; diff file
   lists and modification times since the last known-good point.
2. Check page titles and meta of public entry files, injected iframes,
   hidden link blocks (display:none SEO links), and dynamic include files.
3. Inspect upload directories, editor/editor-helper endpoints, weak CMS or
   panel passwords, and unpatched application entries.
4. Remove or fix every violating page and link; record before/after
   screenshots as deletion evidence.
5. Rotate all credentials touching the web root (panel, CMS, database,
   SSH) and patch the entry point, otherwise the block recurs.
6. If the intrusion depth exceeds page cleanup, hand off to the
   host-intrusion cleanup area (with snapshot done first).

## B. Outbound mining-pool / malware communication alerts

1. Snapshot the disks.
2. With the customer, review scheduled tasks / cron, startup items, unusual
   processes and unexpected outbound connections (customer-side commands in
   the customer's own session; this skill executes nothing).
3. Remove the malicious component and close the entry vector.
4. Keep screenshots of the removed items as remediation evidence; finish
   inside the deadline named in the notice.

## C. Instance observed attacking outward (source of freeze / automatic block)

1. Identify the abusing process or compromised site (snapshot first).
2. Stop the traffic source at the application level; a security-group
   tightening on egress is the customer's own console action, guided here
   only by pointing at the console path.
3. Expect an automatic release at a fixed timestamp in most such cases —
   and that timestamp cannot be advanced manually (see the timeliness
   wording in appeal-materials-and-channels).

## D. Disputed judgment (hijack, false positive, authorized security exercise)

1. Collect your proof set: original-code comparison, access logs, host
   forensic notes; for an authorized penetration exercise, the official
   authorizer letter.
2. Snapshot before any change so the disputed state remains reviewable.
3. Submit a written dispute statement together with the appeal materials —
   reviewers only see what you attach.
4. For recurring false positives on legitimate traffic, ask about the
   security-management platform's allow-listing option through the manual
   channel (its current official path requires confirmation; never paste an
   unverified console link).

## E. Notice received but violating content unknown

1. Re-read the notice: it is the only reliable carrier of the asset
   identifier and the URL/type fields; content detail is not disclosed to
   customers for privacy reasons, so work off what the notice names.
2. Self-inspect per checklist A on every site hosted on the asset.
3. Also check the basics that masquerade as bans: domain expiry (expired
   domains produce the same "site unreachable" symptom), DNS changes, and
   the browser/CDN cache of the removed page.
4. After cleanup, submit the appeal with deletion evidence; do not assume
   silence means compliance was reached.

## Closing loop

After the platform confirms the unblock, re-run the read-only verification
(entry script with the same instance identifiers) and confirm the status is
back to Running before declaring the case closed.
