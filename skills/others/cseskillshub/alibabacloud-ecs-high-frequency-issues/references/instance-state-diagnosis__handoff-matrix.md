# Handoff matrix

This tier owns one area: **where the state machine or the boot flow broke**. Everything else
is identified, then handed over with the evidence already collected, in one sentence the
customer can act on. The dedup risk against the OS-troubleshooting skill is real, so the
boundary is not a matter of taste.

## Ownership boundary

| Layer | Decides on | Owner |
|---|---|---|
| Cloud control plane | instance state machine, dwell time versus baseline, force-operation task conflict, expiry stop, system events and planned maintenance, capacity-driven start refusal | **this skill** |
| Boot flow stages | bootloader, kernel, filesystem check, auto-mount, boot-time initialization blocked by disk usage | this skill **locates the stage only**; every repair action is manual |
| Guest services and business code | nginx, MySQL, Apache, IIS, panel software, nacos: their configuration, certificates, ports, plugins | `alibabacloud-ecs-linux-os-troubleshooting` |

The thin service-layer slice of this tier is deliberate: "instance is `Running`, guest is
reachable, therefore the symptom is a service fault" is a *judgement*, and producing it is
in scope; diagnosing the service itself is not.

## When to hand off, and the sentence to use

| Target | Trigger evidence | Customer-facing sentence |
|---|---|---|
| `alibabacloud-ecs-linux-os-troubleshooting` | `Running` + Cloud Assistant reachable + the complaint is a unit/service/middleware that did not come up | "The instance itself is Running and Cloud Assistant is reachable, so the failure is at the guest service layer (unit status, logs, ports, DNS inside the OS). Handing over to the OS and service troubleshooting skill." |
| `area:disk-expand-diagnosis` | boot or login blocked by `df -h` / `df -i` readings | "Boot is blocked by filesystem usage on the guest disk. Space and inode cleanup belongs to the disk-capacity skill; it always takes a snapshot before any cleanup." |
| `area:resource-bottleneck` | BPS/IOPS at the ceiling of the instance type or disk performance level, console diagnosis note about throttled disk read/write | "Disk throughput reached the ceiling of the current instance type or disk performance level. The disk-IO skill covers spec limits and performance tuning." |
| `area:disk-expand-diagnosis` | the disk is attached but the partition or filesystem was never extended | "The disk is attached but the partition and filesystem are not expanded -- that is the disk-expand skill, not a boot fault." |
| Security incident response (human) | tampered system files, miner or ransomware behaviour, destroyed Cloud Assistant agent, security lock in the operation locks | "Signs of intrusion were found. Security incident response is outside this skill: snapshot the disks first, keep the scene, then engage the security team." |
| Commercial / account (human) | `Stopped` with a financial lock, expiry, renewal, refund, instance-type purchase | "This instance is stopped because the subscription expired. Renewal -- or building a custom image meanwhile to preserve the environment -- is a console action the customer performs; this skill never transacts." |
| Manual operator (class D execution) | force stop, rollback, re-initialization, repair-disk attach, file edits, service restart, swap configuration | "The next step changes the instance or its disks, so it is performed by the customer in the console after a snapshot: <steps>, with these risks: business interruption, unwritten memory lost on a forced stop, applications down afterwards unless autostart was set." |

## Counter-signals that must NOT be chased here

| Quoted signal | Why it is not this tier |
|---|---|
| `404 Not Found` page from the service | the web server answered, so it is running; "404" is not "did not start" |
| port 80 fine, port 443 timing out | certificate or HTTPS listener question, handed to the OS skill |
| `ErrCode:-401, ErrMsg:Client not connected, current status:STARTING` | an application client state string, unrelated to the ECS instance state machine |
| `host not found in upstream "..."`, `Name or service not known` | resolver configuration inside the guest; give the DNS reading, then hand over |
| "the data disk is gone" after a reboot, while `DescribeDisks` shows it attached | the disk exists and was simply never auto-mounted; say the disk is still there first, then hand over the mount fix |
| "snapshot cannot be deleted, so billing keeps running" | a snapshot lifecycle rule, not a start/stop fault; explain the custom-image dependency and hand over |

## The trust question

"Did Alibaba Cloud stop my service or edit my files?" appears across all four scenarios and
escalates fast. Answer with checkable items, never a bare denial:

- the platform does not stop services or edit files inside the instance;
- the authorization/operation timestamps from the customer's own console records;
- whether a scheduled system event exists (`DescribeInstancesFullStatus`,
  `DescribeInstanceHistoryEvents`);
- the monitoring curves around the incident minute, read by the customer in the CloudMonitor
  console at `https://cloudmonitor.console.aliyun.com/hostMonitor/`;
- whether a security alert exists.

If something genuinely cannot be shown from this side, say that plainly instead of
over-claiming, and offer the snapshot plus backup path.

## Handoff hygiene

Carry the evidence table with the handoff: statuses with timestamps, dwell minutes, event
findings, the guest readings already collected, and which commands still need running. The
customer should never be asked twice for the same reading -- the single most common failure
mode in this family of tickets is a run out of time while waiting for a screenshot.
