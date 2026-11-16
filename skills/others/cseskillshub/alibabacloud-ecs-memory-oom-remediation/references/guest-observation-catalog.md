# In-guest observation catalog

Every key returned by the frozen collector payload in `scripts/memory_diagnosis.py`,
what it means, and which decision it feeds. The payload is a constant: it takes no
arguments, reads no customer-supplied path, and contains no `eval`.

| Key | Source inside the guest | Judgement it feeds | Notes |
|---|---|---|---|
| `mem_total_kb` | `/proc/meminfo` MemTotal | used-memory percentage | compared against the spec memory from `DescribeInstances` |
| `mem_available_kb` | `/proc/meminfo` MemAvailable | memory-pressure evidence | the used percentage must be at least 85 to count as a signal |
| `swap_total_kb` | `/proc/meminfo` SwapTotal | is Swap already configured | zero with a memory-pressure signal points at the Swap lane |
| `swap_free_kb` | `/proc/meminfo` SwapFree | how hard Swap is being used | a near-zero value with rising I/O is the swap-thrashing pattern |
| `oom_evidence` | `journalctl -k` then `dmesg`, counted lines matching the out-of-memory patterns | the evidence gate | `recent:N`, `none`, or `unknown` when neither log source is readable; needs a privileged reader |
| `io_status` | `iostat -x 1 2`, per-device `%util` of the last sample | the IOPS lane | loop, ram, cdrom and floppy lines are excluded. **`vda:0.00` means measured and idle; `unknown` means not measured** - the two are never merged, and the report says so in words: `vda:0.00 (measured, max %util 0.00)` versus `unknown (iostat absent or unparsable)` |
| `io_measured` | set to `1` whenever the last iostat sample yielded at least one parsable device line | decides whether the IOPS lane needs the CloudMonitor fallback | when `iostat` is missing, prints nothing, or yields no parsable line the key stays `0`, the substitution is logged as a `[WARN]` degradation, and CloudMonitor `disk_readiops` / `disk_writeiops` are read instead. Note the sampling boundary: a live test measured `%util 89` by hand seconds before the collector sampled `18` on the same machine, so this key describes the two seconds that were watched, not the incident - a burst that has already passed is found with the atop replay, not here |
| `disk_rotational_<dev>` | `lsblk -dn -o NAME,ROTA,TYPE`, falling back to the block queue attribute | local view of media type | cross-checked against the disk category from the control plane, which is authoritative for the basic-cloud-disk rule |
| `disk_avail_kb` | `df -kP /` free space | the 5 GiB precondition | when the collector did not run, CloudMonitor `diskusage_avail` for the **root mount only** is used instead (that metric carries one row per device and mount point, so a data-disk row must never be read as the system disk); when neither source is available the precondition is UNKNOWN, which blocks the change |
| `rss_top_N` | `ps -eo pid,rss,args` sorted by resident size, first five | the memory holder list | PID, command name and resident size only |
| `node_N` | the same `ps` snapshot, filtered to the node interpreter | the runtime-limit lane | reports `max_old_space_size` as found, `not_set` when absent, plus a masked command line |
| `atop_installed` | presence of the atop binary | whether replay is possible | install guidance lives in [atop.md](atop.md) |
| `atop_history` | a usable atop log file was located (the running atop's `-w` target, else the newest `atop_*`) | whether the incident window can be replayed | absence is reported as an explicit limitation; a file existing somewhere is no longer treated as coverage |
| `atop_active_file` | absolute path of the log file atop actually writes | which file the replay must open | parsed from the running atop's `-w` argument, falling back to the most recently modified `atop_*`; measured live: with rotation inactive this is a previous day's file |
| `atop_last_sample` | the last `ATOP` header line of the active file | how far the history reaches | read with a capped `atop -r` scan; `unknown` when the scan yields nothing |
| `atop_rotation` | `current` when the active file is dated today, else `stale` | whether daily rotation is working | `stale` triggers the rotation-troubleshooting guidance instead of a coverage claim |
| `swap_plugin` | presence of the Cloud Assistant plugin manager | the Swap delivery lane | this is what makes the plugin path versus manual path decision evidence-based; an earlier revision of this skill had no probe for it |
| `collector_exit` | constant terminator | payload integrity | absence means the output was truncated |

## Masking

Any argument that looks like a password, passwd, token, secret, credential, access key
or secret key is replaced by `<redacted>` before it is returned, and each command line
is cut off after 160 characters. This is deliberate: a top-memory Java or agent process
often carries connection strings on its command line.

## What is intentionally absent

- No `operable` self-declaration. Whether the instance can be reached is decided by the
  Cloud Assistant status read plus the instance status, never by a constant.
- No file contents, no user lists, no network configuration. This skill needs memory
  evidence, not a general inventory of the machine.
- No customer-authored command. The only second payload that can be delivered is the
  frozen Swap plugin command, and only behind `--confirm-swap-change`.

## Cross-check table

| Guest key | Control-plane read | Which one wins |
|---|---|---|
| `disk_rotational_<dev>` | `DescribeDisks` category | the category, because the media class is a property of the disk |
| `mem_total_kb` | `DescribeInstances` memory | they must agree; a mismatch means the guest is not the instance under diagnosis |
| `disk_avail_kb` | `DescribeDisks` size | the guest, because the control plane does not know filesystem free space |
| `oom_evidence` | none | the guest is the only source; CloudMonitor memory utilisation is a corroborating signal |