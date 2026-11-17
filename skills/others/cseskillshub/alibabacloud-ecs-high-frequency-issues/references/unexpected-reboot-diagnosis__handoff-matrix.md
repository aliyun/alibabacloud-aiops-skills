# Handoff Matrix

What leaves this skill, where it goes, and the wording that keeps the
customer from feeling bounced. Handoff is only legitimate after this skill's
own identification step has run (the report line that shows WHY the fault
lives on another area); the skill never refuses work by label alone.

## Cross-skill handoffs (named sibling diagnosis skills)

| Symptom that surfaces here | Recognition signal in the report | Handoff target | Keep-working note |
| --- | --- | --- | --- |
| instance stuck in `Stopping` / `Starting`, force-reboot loops, OS not coming up at all | power state in `INTERMEDIATE_STATES` or `Stopped` with a "will not start" narrative, no crash event | `area:instance-state-diagnosis` | if the trigger before the stuck state was memory exhaustion, family B stays here; both areas may run in parallel |
| disk expanded in console but guest still shows the old size, partition resize work | capacity mismatch narrative, no reboot event | `area:disk-expand-diagnosis` | nothing to keep |
| disk IO slow / performance below spec as the primary question (not "did IO saturation cause my reboot") | spec-ceiling metrics sustained high while the reboot question is absent | `area:resource-bottleneck` | the "did it explain the reboot" clarification stays here (family C) |
| disk or inode full and the customer wants it cleaned | `df -h` / `df -i` (gated) shows >=95% | `area:disk-expand-diagnosis` plus the snapshot-first guard from this skill | cleanup execution is never performed here |
| general Linux OS faults that are not on the reboot area (drivers, kernel parameters, non-crash misbehaviour) | report shows no reboot event and the narrative is not hang/OOM | `alibabacloud-ecs-linux-os-troubleshooting` | anything with a dated crash event stays here first |

## Human / vendor handoffs (no skill executes these)

| Request | Why it stops | Scripted response |
| --- | --- | --- |
| reboot or stop the instance for me | instance power actions are never automated here | "I will not restart the instance from this session. The console path is ECS console -> Instances -> the instance -> Restart/Stop. If rebooting is to recover a hang, first let me capture the event and monitoring evidence, since a reboot destroys the fault scene." |
| clean up files / kill the process eating memory | destructive, manual-only | "Deleting files or killing processes is outside what I execute. The gated `du` evidence can show where the space sits; the cleanup itself belongs to the capacity skill or to your operations runbook, with a snapshot taken first." |
| redeploy / migrate the instance away from the hardware risk | the platform's scheduled action, customer-authorized, not skill-executed | deliver family F's risk wording (local disks wiped, 15-20 min, ids/IPs unchanged), the backup context, then the console notification-authorization path |
| change maintenance attributes / scheduled reboot time / autostart / group policy / swap / container limits | guest or instance configuration writes are off this skill's allowlist | give the verified console or API documentation path from the playbook, and state that this skill changes nothing |
| expired-snapshot retrieval, mounted-disk rescue, deep data recovery | backend/human scope; expired snapshots are irreversibly gone | "Past their retention, snapshots are deleted and cannot be restored - that is the platform answer as well as the support answer. What remains is a rescue procedure through human support; I can prepare the disk and timeline facts for it." |
| third-party panel internals (BaoTa and similar) | not an Alibaba Cloud product | "The panel is third-party software; its own failures are for its vendor support (https://www.bt.cn/new/index.html). I keep the instance-side evidence - events, capacity, heartbeat - ready to hand over." |
| refunds, cost of the downtime, commercial migration help | commercial channel | acknowledge, then the console ticket channel; do not price anything |

## Tone rules (mirroring the tickets that lost customer trust)

* Never lead with "this is not a crash" when the customer lived it as one;
  lead with the evidence line ("Running since 09:14, no crash event,
  heartbeat fresh"), then the consequence.
* When a queue or a human is genuinely needed (backend deep-dive, sizeable
  migration), say what will be handed over: the event ids, the metrics
  window, the disk list - this skill's report is the ticket attachment.
* Emotional escalations get the factual recap plus one concrete next step;
  do not relitigate the platform narrative beyond the evidence.
