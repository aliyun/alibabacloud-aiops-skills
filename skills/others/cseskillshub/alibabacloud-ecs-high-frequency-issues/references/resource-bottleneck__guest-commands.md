# Guest inspection commands and the confirmation gate

This skill can dispatch **one** command into the customer's instance through Cloud
Assistant (the gated `run-command` dispatch, Class B - no declared grant) and reads the result back with
`ecs:DescribeInvocations`. That dispatch is the reason this skill is **not**
declared observation-only: `RunCommand` is a write-flavored action even when what
it runs only inspects. Everything below is the contract that keeps it narrow.

The machine-readable source of truth is `GUEST_WHITELIST_LINUX` /
`GUEST_WHITELIST_WINDOWS` and `COMMAND_BLOCK_SUBSTRINGS` in
`scripts/areas/resource_bottleneck/_constants.py`; acceptance is implemented in
`scripts/areas/resource_bottleneck/guest_evidence.py::validate_guest_command`. This document explains that
contract; it does not add to it. If the two disagree, the script wins and this
page is a defect.

## The gate, in the order it is enforced

1. **Announce, verbatim, before anything is sent.** Present to the customer: the
   exact command text, the target instance id, that the command only inspects
   state and changes nothing inside the instance, and whether it can be reversed
   (the dispatch can be cancelled by not running it; the reading itself is
   harmless).
2. **Get approval for THIS run.** Re-run with
   `--confirmation "<quote of the approval>"`. An empty, placeholder or
   self-asserted confirmation is rejected — `yes`, `ok`, `confirm`, `approved`,
   `y`, `auto`, `true` are treated as no confirmation at all
   (`guest_evidence.py::is_valid_confirmation`).
3. **One approval buys exactly one whitelisted command.** A second command needs
   a second run with a second quote. There is no standing, batch or "run
   whatever you need" authorization.

A command that is rejected is turned into **manual guidance** (see
`references/resource-bottleneck__human-actions.md`). It is never rewritten and retried in the hope
that a near-miss passes.

## Linux templates (exact match, not prefix or substring)

| Command | What the reading gives |
| --- | --- |
| `uptime` | load averages, current user count — the entry point of rule R2 |
| `free -m` | memory used / available / swap in MiB — absolute values for rule R1 |
| `cat /proc/loadavg` | raw load triple plus run/total process counters |
| `top -bn1` | process-level CPU / memory ranking, kswapd0 paging evidence |
| `ps aux --sort=-%cpu` / `ps aux --sort=-%mem`, optionally `\| head -n <1-50>` | process ranking, capped |
| `vmstat 1 3` | r/b run-queue, D-state columns, si/so paging rates |
| `iostat -x 1 3` | per-device `%util` and `await` for the io-wait branch (needs `sysstat`) |
| `sar -q 1 3` / `sar -r 1 3` / `sar -b 1 3` | historical load / memory / IO rates (needs `sysstat`) |
| `findmnt` | mount table, for the rule R4 disk attribution |
| `atop -r /var/log/atop/atop_<YYYYMMDD> [-b hhmm] [-e hhmm]` | historical per-process replay over an explicit window (tickets T-3941829E, T-441637A1) |

`atop -r` is the only template that takes a path and a window. The path must be
the log file the customer names; the `-b` / `-e` values are what makes the replay
answer a question about a past minute instead of the present one. It requires
`atop` to have been installed **and** running before the incident — it cannot be
installed retroactively by this skill (see the "installation is a human action"
section below).

## Windows templates

| Command | What the reading gives |
| --- | --- |
| `tasklist` | process list with working-set memory (the console-side reading of ticket T-7E06B86C) |
| `Get-Process [\| Sort-Object CPU\|WS\|PM [-Descending]] [\| Select-Object -First <n> [-Property ...]] [\| Format-Table -AutoSize]` | process CPU / working-set ranking (ticket T-72D9DFCB) |
| `Get-Counter '\Category\Counter' [-ComputerName localhost]` | one named performance counter, e.g. `'\Memory\Available MBytes'` |
| `Get-Service -Name <name> [...] \| Select-Object -Property ... [\| Format-Table -AutoSize]` | state of named services (note: `-Name` is mandatory; a bare `Get-Service` listing is not whitelisted) |
| `Get-Volume` | volume inventory (existence cross-check on the Windows side) |
| `Get-PSDrive -PSProvider FileSystem` | drive inventory with free space |

## Rejections

Rejected before any whitelist lookup, because the whole command string is scanned
first (`COMMAND_BLOCK_SUBSTRINGS`):

- **chaining and redirection**: `&&`, `||`, `;`, `` ` ``, `$(`, `${`, `>`, `<`,
  `|&`, newline/CR (multi-line input is rejected outright — exactly one command
  per confirmed run), `>NUL`, `Out-File`, `Set-Content`, `Add-Content`
- **process and service control**: `kill`, `taskkill`, `Stop-Process`,
  `Stop-Service`, `systemctl`, `service start` / `service stop`,
  `Restart-Computer`, `shutdown`, `reboot`
- **memory and kernel configuration**: `sysctl`, `swapoff`, `swapon`
- **storage mutation**: `mkfs`, `fdisk`, `parted`, `truncate`, `dd if=`,
  `Remove-Item`, `Move-Item`, `del `
- **persistence and remote execution**: `reg add`, `reg delete`, `schtasks`,
  `Invoke-Expression`, `iex `, `iwr `, `curl `, `wget `
- **`rm -`** in any form

Rejected by the whitelist stage even when no block substring is present:

- anything that is *close to* a template but not one: `top` (no `-bn1`),
  `top -bn2`, a different `head -n` cap, an unquoted counter name;
- an empty command;
- a Linux template sent against a Windows instance or the reverse (the pattern
  set is selected by `--os-type`).

The rejection reason returned by the script names which stage refused, so the
operator can tell the customer *why* the requested command was not run rather
than reporting a bare "not allowed".

## Dispatch shape

`scripts/areas/resource_bottleneck/guest_evidence.py::dispatch_command` sends, and only sends:

```
ecs RunCommand
  RegionId       <region-id>
  Type           RunShellScript | RunPowerShellScript   (by --os-type)
  CommandContent <base64 of the exact command>
  ContentEncoding Base64
  InstanceId.1   <instance-id>
  Name           skill-ecs-resource-bottleneck
  Description    gated single whitelisted inspection command
  Timeout        30
```

`CommandContent` is base64-encoded and `ContentEncoding` is declared on the same
request, so the payload and the declared encoding cannot disagree. The result is
polled with `DescribeInvocations` (`IncludeOutput=true`) every 5 seconds for at
most 12 attempts, then decoded from base64 with a raw-text fallback. Output is
credential-masked before it is printed or parsed. A capture longer than
`MAX_OUTPUT_SNIPPET_LINES` is truncated in the report with an explicit marker;
the full capture stays on the terminal and is not silently shortened.

## What stays human, always

Installing or configuring anything is a human action, never a dispatch, even if
the customer approves it: CloudMonitor agent installation, `atop` or `sysstat`
installation, swap creation, `sysctl` / `vm.swappiness` changes, service restarts,
reboots, spec changes. See `references/resource-bottleneck__human-actions.md` for the ticket-derived
step text to give the customer instead.

## If Cloud Assistant itself is unavailable

`RunCommand` failing with `NoPermission` / `ImplicitDeny` means the RAM principal
lacks the gated `RunCommand` right under its own credentials (the skill declares
no grant for it); see `references/ram-policies.md`. A dispatch that is
accepted but never reaches a terminal status, or returns an agent error, is the
"instance frozen" branch: the guest agent cannot answer, which is itself evidence
and is reported as a DEGRADED result with the conclusion withheld
(rule R6, `references/resource-bottleneck__diagnosis-rules.md`). Do not conclude "no problem inside"
from a command that never ran.
