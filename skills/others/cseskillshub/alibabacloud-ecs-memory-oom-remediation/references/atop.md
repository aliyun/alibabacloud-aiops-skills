# atop: install, inspect, replay

All commands and metric wording follow the Alibaba Cloud document on using atop to
monitor Linux system metrics:
https://help.aliyun.com/zh/ecs/user-guide/use-the-atop-tool-to-monitor-linux-system-metrics

## Install (choose by distribution, do not invent a command)

Alibaba Cloud Linux 4/3/2, CentOS 7/8, Fedora:

```bash
sudo yum update -y
sudo yum install atop -y
```

Ubuntu or Debian:

```bash
sudo apt update -y
sudo apt install atop -y
```

CentOS Stream 9 and Rocky Linux 9 need the Extra Repositories first:

```bash
sudo dnf update -y
sudo dnf install epel-release -y
sudo dnf install atop -y
```

openSUSE takes the log service from a second package:

```bash
sudo zypper update -y
sudo zypper install atop atop-daemon -y
```

If the distribution cannot be identified, output the document entry point only and let
the customer choose. Never guess an installation command.

## Start, check and keep it running

```bash
sudo systemctl start atop
sudo systemctl status atop      # active (running) means the service answers
sudo systemctl enable atop      # survive the next reboot
```

Enabling the service matters: after a reboot the process information in memory is gone,
and without a recorder there is nothing to replay.

## Live view

Documented syntax: `atop [interval in seconds] [sample count]`.

```bash
atop          # default interval, refreshed every 10 seconds
atop 5        # every 5 seconds
atop 10 30    # 30 samples at 10 second spacing
```

Interactive keys: `m`/`M` memory view and memory sort (memory usage and page faults),
`d`/`D` disk view and disk sort, `g` generic view (default), `c` full command line,
`a` aggregated view, `h` help, `q` quit.

## Replay of a past window

Once the service runs, atop writes binary snapshots to a daily log file named
`atop_YYYYMMDD` under its log directory. Opening that file with a text editor shows
garbage: it is a binary format meant for atop itself.

```bash
atop -r                                                # today's log
atop -r /var/log/atop/atop_YYYYMMDD                     # one day
atop -r /var/log/atop/atop_20250815 -b 09:00 -e 09:30   # one time window, 24-hour clock
```

Replay keys: `t` jumps forward to the next sample, `T` backward to the previous sample,
`b` jumps to a typed `HH:MM`.

`atopsar` is the non-interactive reporter of the same package; it turns the binary log
into text output, which is the only form this skill can fetch on its own:

```bash
atopsar -c 5 12                                              # cpu report, 12 samples
atopsar -m -r /var/log/atop/atop_20250815 -b 18:00 -e 18:01  # memory report from history
```

## Locating the process that ate the memory

Use this when the failure moment is already gone: the process was killed, the instance
recovered on its own, or the workload hangs and the window must be reconstructed.

Preconditions: atop installed and started, and a log file that covers the window.

1. Confirm the log for the date exists:

   ```bash
   ls -lh /var/log/atop/
   ```

2. Replay the window:

   ```bash
   atop -r /var/log/atop/atop_YYYYMMDD -b 09:00 -e 09:30
   ```

3. Press `M` to sort processes by memory and read the process-level columns:

   | Column | Documented meaning |
   |---|---|
   | MEM% | share of memory used by the process |
   | VSIZE | total virtual address space requested |
   | RSIZE | resident physical memory held right now |
   | RGROW | growth of resident memory, positive means it is still growing |
   | VGROW | growth of virtual memory |

4. Press `c` to see the full command line of the suspect process.

5. Walk the samples with `t` and `T`, or jump with `b`, across the window:
   - the process with the highest MEM%, the largest RSIZE and a persistently positive
     RGROW is the memory holder at that moment;
   - a process that disappears after a certain sample was probably terminated; check
     the kernel log before stating that.

6. Corroborate the memory shortage with the system-level lines: in the `PAG` line a
   non-zero `stall` (the kernel stalled waiting for page reclaim) and rising `swout`
   (pages written out to swap); in the `SWP` line `vmcom` (virtual memory already
   committed) approaching `vmlim` (the commit limit).

7. When a text artifact is better than the interactive view, generate the memory report
   from the same log:

   ```bash
   atopsar -m -r /var/log/atop/atop_20250815 -b 18:00 -e 18:01
   ```

Every conclusion drawn this way must name its evidence source as atop history replay.

## Replay error: stat raw file: No such file or directory

Documented causes: atop was not running on that date; the file was deleted by the
retention policy (more generations kept than `LOGGENERATIONS` allows); the date asked
for is in the future. List the files that actually exist before concluding anything.

## Rotation troubleshooting: the active file is not today's file

Measured on a live evaluation instance (2026-11-12): `atop-rotate.timer` was inactive,
so the running atop kept appending to `atop_20261111` and no `atop_20261112` existed.
Two consequences:

- `atop -r /var/log/atop/atop_$(date +%Y%m%d)` fails with `stat raw file: No such file
  or directory` even though atop is running and recording.
- `-b`/`-e` are anchored to the **file's own date**. Asking today's window inside a
  file dated yesterday selects yesterday's window and can return empty output with
  exit code 0 - a silent miss, not an error.

Find the file atop actually writes before replaying:

```bash
ps -eo args | grep '[a]top -w'          # the -w argument is the active file
ls -t /var/log/atop/atop_* | head -1    # fallback: most recently modified
```

Replay that exact path. For a window that crosses midnight, walk the samples with
`t`/`T` from a sample before the incident instead of trusting `-b`/`-e`, and check
the `ATOP` header line of each sample for its real date and time. To restore daily
rotation, enable the distribution's atop rotate timer (for example
`systemctl enable --now atop-rotate.timer`) - a configuration change the customer
confirms, not something this skill performs.

## When the history is too coarse

Sampling and retention are configuration values, and the service must restart for a
change to apply. On Red Hat derived distributions (Alibaba Cloud Linux, CentOS, Fedora,
Rocky Linux) the file is under its system configuration directory for atop; on Debian
derived distributions and openSUSE it is under the default-environment file.

- `LOGINTERVAL`: sample interval in seconds, documented default 600 (one snapshot every
  10 minutes). Lower it, for example to 30, for finer detail, accepting more disk I/O
  and more CPU spent by atop itself.
- `LOGGENERATIONS`: how many days of logs are kept, documented default 28.

If history does not cover the window, give the current `ps` snapshot as a preliminary
answer and state explicitly that the moment itself cannot be reconstructed.

## Escalation

When neither history nor a usable snapshot supports a conclusion, say so and hand the
case over for manual analysis instead of publishing a confident answer.