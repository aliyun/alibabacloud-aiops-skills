# In-guest diagnostic commands (class B)

These commands exist because a large part of this tier's facts are invisible to the cloud
API: what the guest actually reports about memory, mounts, name resolution, listeners and
boot autostart. Each entry only prints a reading -- it changes no file, no service and no
mount state, and that is exactly why it is allowed at all.

Sending one of them calls `RunCommand` (RAM action point `ecs:run-command`), a **write-class**
API even when the payload only reports. So the gate is explicit every single time.

## Dispatch rules (hard)

1. `DescribeCloudAssistantStatus` must show the agent installed and online; otherwise no
   command is sent and the fallback below applies.
2. The command must be an **exact key** of the whitelist; free text is never accepted.
3. Exactly one command per confirmation. A new command needs a new confirmation.
4. Before sending, tell the customer: the command text, the target instance, that it only
   reports, and that nothing has to be undone because nothing changes.
5. Only the entries marked *auto-sendable* below may be dispatched. Everything else is
   handed to the customer to run and paste back.
6. Any entry containing a side-effecting token is refused with a reason, never sanitised
   and then run. Banned: `rm`, `mv`, `cp`, `dd`, `mkfs`, `fdisk`, `parted`, `truncate`,
   `kill`, `pkill`, `reboot`, `shutdown`, `halt`, `poweroff`, `init`, `mount`, `umount`,
   `sed -i`, `chmod`, `chown`, `chattr`, `useradd`, `userdel`, `passwd`, `iptables`,
   `service`, `systemctl` change verbs (start/stop/restart/enable/disable), `curl`, `wget`,
   `format`, `diskpart`, and the redirectors `>` / `>>`.
   Matching is on whole words, so `findmnt` is not blocked by `mount`.

## Auto-sendable (on the approved batch list)

| Key | Command | OS | Reading it gives here |
|---|---|---|---|
| `disk-usage` | `df -h` | linux | whether the system disk is full, which can block boot-time initialization |
| `disk-inodes` | `df -i` | linux | exhausted inodes, which block login and service start alike |
| `mount-table` | `findmnt` | linux | what is actually mounted, versus what auto-mount expects |
| `windows-volume-usage` | `Get-Volume` | windows | volume free space on a Windows guest |
| `memory-usage` | `free -h` | linux | available memory and swap; the OOM-hang story in most "server hung" tickets |
| `fstab-content` | `cat /etc/fstab` | linux | auto-mount entries pointing at devices that no longer exist |
| `sshd-effective` | `sshd -T` | linux | the include-merged **effective** daemon config: password/root-login policy and port as actually applied |

`memory-usage` and `fstab-content` were promoted to this list after measured legs proved the
fact was only readable inside the guest; `sshd-effective` was promoted after a real injected
fault (a `sshd_config.d` drop-in setting `PasswordAuthentication no`) was missed by a leg, because
`cat /etc/ssh/sshd_config` shows only the `Include` line and `ls -l` only shows that a drop-in
exists - neither gives the applied value. Do not read an older list of "four required reads" as a
limit: this table is the current set, and the dispatcher sends the tier-1 group on every
instance-scoped call.

## Evidenced for this tier but not yet dispatchable (customer runs and pastes)

These are needed by the ticket evidence but are not on the approved auto-dispatch list yet,
so this skill refuses to send them and asks for the output instead. Do not "temporarily"
send one.

| Key | Command | Why this tier needs the reading |
|---|---|---|
| `oom-traces` | `dmesg \| tail -n 100` | kernel ring tail carrying the out-of-memory records |
| `dns-resolver` | `cat /etc/resolv.conf` | a missing or wrong resolver breaks services at start time |
| `listening-ports` | `netstat -lntu` | whether a service is really up, which kills most wrong hypotheses |
| `service-autostart` | `systemctl is-enabled sshd NetworkManager` | boot autostart state, using the status verb only |
| `atop-present` | `command -v atop` | whether any history exists to attribute the incident minute |

When the channel is missing entirely (agent uninstalled, destroyed by an intrusion, or
permission-blocked), say which reading is missing, give the customer the single exact
command, and mention the Workbench entry point
`https://help.aliyun.com/zh/ecs/user-guide/workbench-system-management.md` as the
console-side alternative to SSH or VNC.

## How the script exposes this

```
python3 scripts/areas/instance_state_diagnosis/diagnose_instance_state.py --region-id cn-hangzhou \
  --instance-id i-xxxxxxxx --symptom unreachable-after-reboot \
  --guest-command disk-usage
```

Tier-1 (`auto_sendable`) entries are query-only reads and are dispatched without a
confirmation round (the report carries an `auto-approved` line); with a
non-auto-sendable key it prints the "run it yourself and paste the output" instruction;
with an unknown key it refuses and lists the valid names. After a successful dispatch the
report carries the `InvokeId` **and the read-back stdout**: the script polls
`DescribeInvocations` with `IncludeOutput=true` (up to 60s) and prints the guest output
lines directly into the report.

### MUST-LEAD lines are binding, not advice

When a read-back actually proves a fault, the script appends a line starting with
`MUST-LEAD:` naming the anomaly and quoting the measured numbers (a system filesystem at
>=95%, `MemAvailable` at <=10% of total, or `PasswordAuthentication no` in the effective sshd
config). That line is computed from the output, not from a guess, and it decides the ordering
of the report: the named anomaly is delivered as the **#1 confirmed root cause with its
numbers**, ahead of any security-group, DNS, upstream-service or fail2ban hypothesis, and the
report may not conclude `UNDETERMINED` nor ask the customer for data this line already carries
while it is unaddressed. A `MUST-LEAD` line that is dropped from the final report is a defect
of that report, not of the diagnosis.

## Result handling

- Quote returned stdout verbatim, never paraphrase a number.
- A reading that contradicts the hypothesis replaces the hypothesis; say so.
- Empty output from a command that normally prints is a finding in itself (for example an
  empty mount list where auto-mount expects an entry) -- interpret it, do not re-run.
- Resource-hungry processes can only be attributed after the fact when `atop` was installed
  beforehand. The install step is a customer-executed change; see the atop guidance in
  `snapshot-first-checklist.md`.
- Memory exhaustion relief (swap) and any service restart are class D: guidance only.
