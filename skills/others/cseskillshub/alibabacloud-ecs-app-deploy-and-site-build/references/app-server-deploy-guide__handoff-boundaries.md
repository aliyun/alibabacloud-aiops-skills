# Handoff boundaries: recognise, evidence, transfer

This tier is the deployment-guide axis and nothing else. The moment the
conversation is actually about another axis, the correct output is a clean
handoff -- the symptom as confirmed, the evidence already collected, the
target tier, and one sentence on why this skill stops. Guessing across a
boundary is how a deployment session turns into a broken instance.

## Symptom-to-target table

| What the customer describes | Belongs to | Do here |
|---|---|---|
| Disk full, inode exhausted, "cannot create new file", "No space left on device", file-count limit | `alibabacloud-ecs-disk-capacity-cleanup` | Take the confirmed `space` / `inodes` / `deleted-open` readings if not yet available, then hand off. Never guide the cleanup itself without snapshot-first, and never perform one |
| "Resized the disk but the OS still shows the old size", partition not extended | `alibabacloud-ecs-disk-expand-diagnosis` | Hand off with the instance and disk ids from the evidence section |
| Instance will not start, stuck starting/stopping, boot failure | `alibabacloud-ecs-instance-state-diagnosis` | The readiness gate already names it; hand off, deployment pauses |
| Disk IO slow, IOPS at the ceiling, lag since a specific change | `alibabacloud-ecs-disk-io-diagnosis` | Hand off; do not re-run deployment steps hoping it improves |
| Panel operations (BaoTa / aaPanel and similar web panels) | `alibabacloud-ecs-bt-panel-diagnosis` | Deployment guidance for the panel itself stops at the official install path being the customer's action |
| Site unreachable, DNS, "website not opening" | `alibabacloud-ecs-web-inaccessible-slow` | Hand off; this skill never diagnoses web accessibility |
| Nginx / Java / PHP runtime configuration errors | `alibabacloud-ecs-web-service-runtime-config` | Hand off; runtime version checks stay customer-side here |
| Database install/migration/ops on ECS | `alibabacloud-ecs-db-on-ecs-diagnosis` | Hand off |
| Whole-site deep migration diagnosis between servers | `alibabacloud-ecs-site-migration-guide` | This tier keeps only the pre-migration readiness facts it collected |
| Port 25 / mail sending blocked | `alibabacloud-ecs-smtp-block-diagnosis` | Hand off |
| "Server is installed but nobody can join / connect" | stays here as guidance, then firewall tier | Listener check is a human step (not on the command whitelist); then security group console path from [deploy-paths.md](deploy-paths.md) |
| Simple Application Server instead of ECS | other product | Identify it, say so, stop; reference the client-management document |

## The handoff script (fixed template)

Output all four parts, in this order, when handing off:

```text
1. SYMPTOM AS CONFIRMED   The customer's own wording, quoted, plus which
                          signature it matched.
2. EVIDENCE ALREADY TAKEN Region, instance id, status, and every reading
                          with its source (cloud query / confirmed probe /
                          customer-pasted output).
3. TARGET                "This continues under <target skill name>, the tier
                          for <axis>."
4. WHY THIS STOPS        "Deployment guidance on this instance is paused
                          here; <target axis> is outside this skill's scope,
                          and acting across that boundary risks turning a
                          one-tier problem into a two-tier problem."
```

Rules that hold inside every handoff:

* Evidence travels; conclusions do not. Do not claim the target tier's root
  cause -- say what the readings show and name the tier.
* Never bundle a destructive action with the handoff ("run this rm first").
  Cleanup advice is capacity-tier territory and always snapshot-first.
* A refused or failed probe is still handoff material: list what could not be
  taken and why (`DEGRADED` line verbatim), so the next session does not
  repeat the same dead end.

## Anti-overlap note for the retrieval layer

Words like "server", "deploy" and "build up" are shared across the whole
family; this skill's own trigger phrases stay game/app-server specific (see
the description block) so a capacity, boot or IO conversation lands on its
own tier first. If the conversation's first message is really one of those
axes, hand off immediately rather than running the deployment checklist.
