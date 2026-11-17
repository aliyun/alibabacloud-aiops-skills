# State machine, dwell time and the timeout baseline

This is the highest-value page of the tier: most tickets in this family are resolved by
giving the customer a factual status plus one honest time statement **before** anyone talks
about a fault.

## Control-plane states

| `Status` | What it means | What it does NOT mean |
|---|---|---|
| `Pending` | the transition was accepted, booting has not begun | the OS is booting |
| `Starting` | the platform is bringing the instance up | the guest reached user space |
| `Running` | the control plane sees the instance up | a service inside is listening, or the customer can log in |
| `Stopping` | the guest shutdown flow is in progress | the instance is stuck (check dwell first) |
| `Stopped` | down, by request, by expiry lock, or by crash handling | data loss |

Collect with `DescribeInstances` (primary), `DescribeInstanceStatus` (independent
cross-check, good for a batch). When the two disagree seconds apart, the state was
transitioning: say so and re-query instead of picking one.

## Dwell time is an input, not an API field

No query in this tier's surface returns "how long has it been in this state". The
authoritative source is the customer's own console **operation records** (the exact minute
the stop/reboot/change was issued) or the timestamp in the ticket. Pass it as
`--state-since`; the script computes the dwell against the baseline below. Without it the
script reports the status and explicitly declines to apply a baseline (`STATUS: DEGRADED`),
rather than guessing.

## Baseline (single value, converged from five inconsistent human wordings)

Real tickets said 5-10, 8-10, 8-15, 10-15, 10-20 minutes for the same phenomenon. This
skill uses one table:

| State | Typical | Expected ceiling | Borderline | Escalate |
|---|---|---|---|---|
| `Stopping` after a normal console stop/reboot | 5-15 min | 15 min | 15-20 min | > 20 min |
| `Starting` / `Pending` | under 5 min | 5 min | 5-15 min | > 15 min |

Why a normal stop takes that long: a console stop/reboot first runs the guest shutdown
flow, which releases processes and persists memory and cache data to the block storage. If
the host was under load or heavy IO just before the operation, that flush dominates the
elapsed time and the instance stays in `Stopping` for nearly the whole ceiling.

## "Nobody can intervene" -- say it plainly

While the shutdown flow runs, neither the customer, the console, support staff nor this
skill can accelerate, pause or cancel it. A force stop issued inside that window fails with
a **task conflict**, and that rejection is expected behaviour, not a second fault. Repeated
clicking does not help and produces the failing request ids customers then quote back.

Escalation only after the ceiling: snapshot every disk and wait for 100% (see
`snapshot-first-checklist.md`), record what VNC shows, and only then let the customer force
the operation from the console.

## Status-display lag (one-line fix, check it first)

`DescribeInstances` may already report the target state while the console page still shows
`Stopping` / `Starting`. Verified in tickets where the only effective action was "refresh
the instance list page". So when the API says the instance reached the target state, the
first instruction is to refresh, before any investigation.

## Multi-instance and cross-region runs

One ticket can carry several instances. `DescribeInstanceStatus` and
`DescribeInstancesFullStatus` accept repeated `InstanceId.N`, so a run covers up to
`MAX_BATCH_INSTANCES` (10) at once and gives a per-instance verdict. Instances in another
region need a separate run with that `--region-id`; never reuse a region from a previous
answer.

## Expiry and locks

`DescribeInstances` operation locks can carry a financial reason, which pairs with the
customer's "will not start" report. Treat an expiry stop as account lifecycle, not a
fault: point at renewal in the billing console, and offer a custom image in the meantime if
the environment must survive. The expiry timestamp the customer sees in their own instance
list is authoritative -- this skill does not assert it from anywhere else.

## Evidence to include in every answer

1. status per instance, and dwell minutes (or the explicit note that the start minute was not given);
2. whether a scheduled system event or an abnormal health status exists;
3. which side of the baseline the dwell is on, quoting the table above;
4. Cloud Assistant presence, if a guest reading was needed;
5. the console entries: `https://ecs.console.aliyun.com/server/region/<regionId>` and
   `https://ecs.console.aliyun.com/snapshot/region/<regionId>`.

## Source documents

- Instance stays in `Stopping` after a console stop/reboot:
  `https://help.aliyun.com/zh/ecs/support/when-an-ecs-instance-is-stopped-or-restarted-in-the`
- Stop/reboot succeeded but the page still shows the old state:
  `https://help.aliyun.com/zh/ecs/the-ecs-instance-remains-in-the-stopped-state-when-it-is-successfully-stopped-or-restarted-in-the-console`
- Reboot an instance (manual operation reference):
  `https://help.aliyun.com/zh/ecs/user-guide/restart-instances`
