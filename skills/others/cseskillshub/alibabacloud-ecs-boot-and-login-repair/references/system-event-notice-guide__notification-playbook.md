# Notice wording to answer

The customer quotes a notice, not an internal category. Match the wording, then
answer the four standing questions: why, do I still act, by when, what happens to
my data and my IP.

The script matches `--notice-text` against the keys below, which live as the
`NOTICE_FAMILIES` constant in `scripts/axes/system_event_notice_guide/_constants.py`. Keys are English, so when
the customer's notice is in another language, render the key phrase into the
English wording in this table before running the script, and keep the original
text visible in the conversation.

## 1. Wording map

| Wording the customer reports | Family | First sentence of the answer |
|---|---|---|
| "reboot required due to system maintenance", "scheduled maintenance notice", "maintenance window", "operation and maintenance notice" | `scheduled-maintenance-reboot` | The platform found a potential hardware or software fault risk on the host your instance runs on, and is asking for a reboot so the instance can be placed on a healthy host at a moment you choose. |
| "the event was automatically canceled", "the notice disappeared", "why was it canceled" | `event-canceled` | Canceled means the risk was resolved or the task changed before execution, so there is nothing left for you to do. |
| "I already rebooted, why does it say avoided", "state shows avoided" | `event-avoided` | `Avoided` is the expected result of your own reboot; `Executed` is reserved for actions the platform performed. |
| "my server restarted on its own", "unexpected restart", "down migration", "host fault" | `unplanned-down-migration` | An actual fault on the underlying host made the platform move and reboot the instance; that action is finished. |
| "Instance:StoragePerformanceReachLimit", "storage performance", "disk throughput limit" | `storage-performance-limit` | This code is about block storage throughput reaching the limit of the disk configuration, not about your public bandwidth. |
| "region closure", "cease of service", "shutdown notice for the region" | `region-shutdown` | The region or zone is being retired, so you have to move the instance yourself before the cut-off date. |
| "redeploy", "local disk will be cleared" | `local-disk-redeploy` | This is the one family where data on locally attached disks is re-initialised, so back it up first. |
| "does it repeat every week", "auto shutdown timer", "scheduled start and stop" | `auto-start-stop-confusion` | A maintenance event happens once; a repeating start or stop comes from your own auto start/stop setting. |
| "all my programs stopped", "the firewall was turned on", "was it OOM", "who changed my server" | `os-internal-cause` | Let us separate the two possible causes: whether the platform has any event for that moment, and what your own operating system logs say. |
| "resource reservation", "capacity reservation expiring" | `resource-reservation-event` | That is a reservation family, not host maintenance; the rules and the page are different. |

## 2. The seven recurring misreadings

Each entry is a wrong belief customers bring in, and the correction to give.

1. **"Canceled means nothing was wrong, so the notice was a mistake."**
   The notice and the cancellation are two moments of one lifecycle: the risk was
   detected, then removed or mitigated before the automatic execution time, or the
   maintenance task was completed or adjusted. Nothing contradicts anything else,
   and no action is left.
2. **"I rebooted, so it should say Executed."**
   `Avoided` records that the customer removed the exposure before the deadline.
   `Executed` records that the platform did it. A manual reboot producing
   `Avoided` is the system working as intended.
3. **"A maintenance reboot is a re-deployment, so I lose data."**
   A reboot stops processes and keeps cloud disks. It is not a re-deployment. Only
   a redeployment class event re-initialises locally attached disks, and that
   distinction is the reason backup advice differs between the two.
4. **"The notice is in my console to-do list, so I set the restart time there."**
   The automatic fallback time is already fixed when the notice is issued. The
   customer may reboot earlier or, where the console offers it, schedule inside the
   window; there is no self-service entry to push the automatic time later, and
   that request is handled by a ticket.
5. **"Will the reboot change my IP?"**
   No. A maintenance reboot keeps the private and the public address of the
   instance. Addresses do change when the customer creates a new instance in
   another region, which is a different situation.
6. **"This restarts every week."**
   Maintenance events are one-off. A repeating pattern comes from the customer's
   own auto start/stop configuration. Check that before accepting the premise.
7. **"`Instance:StoragePerformanceReachLimit` is a bandwidth problem."**
   It is block storage read/write throughput hitting the limit of the disk
   configuration. Public bandwidth has its own metrics and its own codes, and the
   event does not carry a disk identifier or a percentage.

## 3. Answer templates

Fill from the script report; never invent a value the report does not carry.

```
What you received: <family title from the report>
Why: <the platform-side or configuration reason, with its source>
Current instance facts: <status, region, zone, addresses from the reads>
Do you still need to act: <yes/no, and what the state means>
Latest time: <the automatic execution time stated by the notice, or the rule>
Your data: <reboot keeps cloud disks / redeployment clears local disks>
Your IP: <unchanged for a reboot / new for a cross-region rebuild>
What you do now: <console steps the customer performs>
What this skill cannot check: <event records in this build, host health, OS logs>
```

For a batch of instances, keep one row per instance with the selector that
resolved and the status that came back, and call out every selector that returned
nothing instead of dropping it from the table.

## 4. When the reads come back empty

- No instance matched the ID or IP: state the region used and ask for the region
  the instance lives in, or for the ID from the console. Do not conclude anything
  about events.
- The identity lacks permission: report `NoPermission` or `ImplicitDeny`, name the
  missing action, and point to
  [ram-policies.md](ram-policies.md).
- The notice wording matched nothing: ask for the exact sentence in the notice.
  Guessing the family is the fastest way to give a wrong deadline.
