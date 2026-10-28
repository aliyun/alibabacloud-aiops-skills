# Automatic Snapshot Policy Design and Effectiveness

Knowledge module for capabilities "policy element design" and "effectiveness
re-check". The evidence-batch document set is described in
[references/backup-mechanisms-and-limits.md](backup-mechanisms-and-limits.md).

## 1. Policy design parameters

An automatic snapshot policy is fully specified by four elements; design
them against the customer's RPO/RTR, not defaults:

| Element | Design question | Guidance |
|---|---|---|
| Recurrence (which days of week) | how often must recovery points exist | daily for transactional systems; weekly only for cold data |
| Time points (hour of day) | when to capture | pick the low-write window; snapshots at peak IO worsen IO-saturation symptoms seen in the evidence batch |
| Retention (days) | how far back recovery goes | balance against the growth model in [billing-models.md](billing-models.md); retention expiry auto-deletes old snapshots |
| Target disks | what is protected | EVERY business disk; a disk left unbound has zero protection |

Docs: [create an automatic snapshot policy](https://help.aliyun.com/zh/ecs/user-guide/automatic-snapshot-policy),
[enable or disable an automatic snapshot policy](https://help.aliyun.com/zh/ecs/user-guide/enable-or-disable-an-automatic-snapshot-policy),
[delete an automatic snapshot policy](https://help.aliyun.com/zh/ecs/user-guide/delete-an-automatic-snapshot-policy)
(deletion/teardown paths are guidance for the customer only).

## 2. Effectiveness = policy EXISTS + APPLIED to disks + snapshots appear

The dominant "it does not work" root cause in the evidence batch: the policy
was created but never applied (bound) to a disk, so it never runs.

Judgment ladder (run in this order):

1. **Does the policy exist in the right region?** Policies are regional --
   a policy created in region A never touches a disk in region B.
2. **Is it applied to the disk(s)?** In the console, open the policy and
   inspect the applied-disk binding. Empty binding = not effective. This
   single check resolves the majority of "policy not working" tickets.
3. **Has a scheduled time point passed and produced a snapshot?** Check the
   snapshot list for automatic-origin snapshots named after the policy.
4. **For single-system-disk instances:** applying the policy to that disk
   covers the whole system state on it (evidence: support confirmed "this
   disk contains the entire system"). Multiple disks each need binding.
5. **Copy expectations:** copies follow snapshots one-to-one; see
   [billing-models.md](billing-models.md) section 3.

## 3. Why effectiveness is customer-confirmed in this release

This skill's verified read-only API surface covers instance facts only. The
query actions for policies/snapshots/files-backup have unverified permission
points, so this skill does NOT call them (see
[ram-policies.md](ram-policies.md), "Deferred"). Consequences:

- The report marks policy/snapshot facts as `NOT FETCHED -- customer
  confirmation required`.
- The customer performs the two-minute console self-check above and reports
  back; the Agent re-runs the entry script with `--check-effectiveness
  --customer-report "<what the console shows>"` to rule-check the answer.
- The skill NEVER states "backup confirmed usable/confirmed effective" from
  its own data when the fact was customer-reported: it says "per your
  console report, effective" and still requires a real snapshot at point 3.

## 4. Re-check triggers (when to re-verify a working design)

Re-run the effectiveness ladder after any of: disk replacement/re-init or
re-swap, instance migration, region move, policy edited or disabled/enabled,
disk added, retention changed, or a billing suspension that released
resources. These are the events that silently break bindings.

## 5. Design output contract

The plan section for each object MUST list, in this order:

1. chosen mechanism(s) and the core binding rule;
2. the four policy parameters with recommended values and WHY;
3. the customer-performed console steps (the skill only advises; the
   customer clicks -- mirror of the support line "I cannot operate on your
   behalf");
4. the coverage-gap probes the customer must answer (data size, change rate,
   DB directory location, retention demand, off-site requirement);
5. the effectiveness ladder as the verification step after the customer
   finishes.
