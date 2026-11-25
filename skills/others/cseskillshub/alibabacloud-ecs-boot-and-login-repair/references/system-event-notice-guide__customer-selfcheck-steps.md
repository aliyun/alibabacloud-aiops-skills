# Steps the customer performs

Everything here is done by the customer, in the console or inside their own
instance. This skill explains the path and waits; it never logs into an instance,
runs a command inside one, or clicks on the customer's behalf. Console menu names
shift between console versions, so describe the area rather than promising an
exact label, and ask the customer to confirm what they see.

## 1. See whether an event exists and in what state

1. Open the ECS console and switch to the region that holds the instance.
2. Open the events area for scheduled operations and maintenance (wording varies
   by console version; it is reached from the instance or overview navigation).
3. Filter by the instance ID from the notice.
4. Read the state and the automatic execution time; this is the authoritative
   view, because this skill cannot read event records.
5. If the customer rebooted moments ago, refresh before concluding: the state can
   lag behind the action.

If the console shows nothing but the customer received a notice, the discrepancy
is a ticket item - do not assert that no event exists.

## 2. Reboot now, inside the window

1. Create snapshots of the data disks first when the workload matters (step 4).
2. Stop the application gracefully so buffers are flushed.
3. Reboot from the instance list in the console during a low-traffic moment.
4. After the instance returns, start the workload and confirm the service answers.
5. Re-read the events area: the state should now show that the risk was handled.

## 3. Schedule the reboot

1. Open the event row for the instance in the console events area.
2. Where the row offers a reschedule or maintenance-window choice, pick a moment
   inside the window the notice allows.
3. Note that the automatic fallback time printed in the notice still applies if
   nothing is chosen.
4. If no such option is offered for this event, the time cannot be moved by
   self-service: submit a ticket asking for the specific alternative time, and
   state the business window in the request.

## 4. Snapshot before a platform-initiated reboot

1. Open the storage or snapshots area of the ECS console for the same region.
2. Create a snapshot for each disk that holds data written since the last backup.
3. Wait until every snapshot reports a completed state before the reboot.
4. Keep the snapshot IDs so a rollback can reference them.

Local disk data is not covered by disk snapshots; for locally attached disks the
customer copies the data to a cloud disk or to object storage beforehand.

## 5. Make services come back on their own

1. Register the application as a boot-time service, for example a systemd unit
   enabled at the default target on Linux, or a Windows service set to automatic.
2. Verify once inside a low-traffic window by rebooting and confirming the service
   starts without a manual command.
3. For stateful workloads, make the application recover its own queues, caches, and
   connections rather than depending on a manual start.

## 6. Read the operating system's own logs

The customer runs these inside the instance. This skill can explain what a pasted
log line means, but does not fetch logs.

Linux:

1. `journalctl -b -1` for the previous boot, `journalctl -b` for the current one.
2. `grep -i -E "oom|killed process|panic|segfault" /var/log/messages` (or
   `/var/log/syslog` on Debian family releases).
3. `grep -i -E "Accepted|Failed|sudo" /var/log/secure` (or `/var/log/auth.log`)
   around the reported minute, to see who was in the instance.
4. `crontab -l`, `systemctl list-timers --all` for jobs that could have restarted
   services.
5. `last -x` and `uptime` for the reboot moment.

Windows:

1. Open Event Viewer and read the System log around the reported time; filter for
   critical and error levels, in particular unexpected shutdown entries.
2. Read the Security log for logon events at that minute.
3. Check Task Scheduler for tasks able to restart the machine or the service.
4. Note the exact timestamps so they can be compared with the platform-side time
   window.

What to do with the finding: if the guest log shows an in-guest cause (a crash, an
out-of-memory kill, a scheduled task, security software), that is the answer and
the maintenance event is unrelated. If the customer cannot or does not want to read
logs, that investigation belongs to a skill that works inside the instance.

## 7. Ask about compensation

1. Read the availability SLA terms of the affected product; each product has its
   own thresholds and claim window.
2. Open the SLA compensation page of the account centre after the reporting window
   the SLA describes: `https://usercenter2.aliyun.com/sla/availabilityhome`.
3. Submit the claim there. This skill states the rule and the page only; it cannot
   judge eligibility, and it does not file the claim.

## 8. Move an instance because a region is closing

Only the notice is interpreted here; the customer performs the migration, and the
commercial part is handled elsewhere.

1. Create a custom image from the instance:
   `https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-an-instance`
2. Copy that image to the destination region:
   `https://help.aliyun.com/zh/ecs/user-guide/copy-an-image`
3. Create the new instance from the copied image:
   `https://help.aliyun.com/zh/ecs/user-guide/create-an-ecs-instance-by-using-a-custom-image`
4. Expect new addresses, then update DNS, allow-lists, and any licence bound to the
   old address.
5. Ask about the remaining subscription value of the retired instance through the
   billing channel; that decision is not made by this skill.

These three URLs were quoted by support when the case was handled; they have not
been re-fetched by this build.
