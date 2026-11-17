# Read-only evidence: the guest whitelist and the customer-readback split

Two ways this skill learns what lives inside the instance, and the line
between them is hard:

- **Whitelisted probes** — executed by the skill through Cloud Assistant
  (`RunCommand`, class B) only after the customer confirms that one command;
  every entry reads state and writes nothing.
- **Customer readback** — everything else, including the readings this
  scenario's support threads used most (`bt` menu commands, listening ports,
  service state, firewall state, resource numbers, dependency versions):
  those sit OUTSIDE the low-risk list, so the skill declines to dispatch them
  and instead prints the exact command for the customer's own session and
  continues on the pasted result. Refusing is not a bug to route around: a
  command absent from the list stays out even if it looks harmless, and no
  request may be rewritten into a different command that passes.

## The whitelist (class B, one command per consent)

| Key | Assembled command | Reads | Evidence it settles (case) |
| --- | --- | --- | --- |
| `stat_path` | `stat -- <path>` | existence, size, blocks of one file | certificate file missing or empty; `port.pl` gone (T-76855857, T-84281A4D) |
| `ls_dir` | `ls -lh -- <dir>` | long listing of one directory | the panel's cert dir vs the path the web error names (T-76855857) |
| `wc_lines` | `wc -l -- <file>` | line count, contents never printed | an empty file where content is expected (T-76855857) |
| `df_h` | `df -h` | byte usage per mounted volume | disk watermark behind "panel and sites are slow/dead" (T-7726D6AA) |
| `df_i` | `df -i` | inode usage per volume | "cannot create new file" with free bytes left |
| `findmnt` | `findmnt` | the mount table | a vanished data-disk mount under site directories |
| `du_top` | `du -x --max-depth=1 -- <dir>` | size of each direct child, no mount crossing | which site dominates the volume before the customer's own cleanup (T-7726D6AA) |
| `get_volume` | `Get-Volume` | Windows volume health and free space | full volume on a Windows panel host (T-EF9EA87F) |
| `get_childitem` | `Get-ChildItem -Force <path>` | directory listing incl. hidden | panel/site file presence under a Windows panel root (T-EF9EA87F) |

Windows limits worth stating: there is no whitelisted equivalent for Windows
service state or IIS bindings, so any Windows conclusion beyond volume and
directory readings carries an explicit low-confidence marker in the report.

## The consent gate (every probe, no exceptions)

1. Run `probe` without `--confirm`: it assembles the one command string and
   prints the disclosure — exact string, single instance, read-only, nothing
   reversible because nothing changes, cost, purpose, the token's single-use
   scope.
2. Relay the disclosure to the customer **verbatim** and get agreement to
   that one command.
3. Re-run with the printed `--confirm` token. A different combination of
   region, instance, key or target invalidates it; a second command needs a
   second consent.
4. Output is read back via `DescribeInvocations` and masked before display.

Agent offline, dispatch refused, or consent withheld → `STATUS: DEGRADED`:
the same command string is handed to the customer to run in Workbench/SSH,
and the tree continues on the pasted output.

## Rejected for dispatch — printed as customer self-checks instead

The left column is what the threads actually ran; none of it is whitelisted
here, all of it belongs to the customer's own session:

| Command family | Why outside | Self-check template | Cases |
| --- | --- | --- | --- |
| `bt default`, `bt 14`, the whole `bt` menu | prints live panel credentials; menu entries also write (password resets, service restarts) | `panel_entry_default`, `panel_entry_info_menu` | T-C9CE1F85, T-7AD5DAC8, T-952279A8 |
| `ss -lntp`, `netstat` | outside the low-risk list | `listen_ports` | T-952279A8, T-21252C12 |
| `systemctl status ...`, `service ...` | `systemctl` is a banned token: the same binary starts and stops units | `service_status` | T-38543E1F, T-943A6E7E |
| `iptables -S`, `firewall-cmd --state` | firewall readers sit next door to writers; not on the list | `os_firewall_state` | T-45CF3415, T-14A38F29 |
| `top`, `free`, `ps -fp <pids>` | resource readers are not on the list; support collected these from customers too | `resource_readings` | T-E279891E, T-48B136B7 |
| `openssl version`, `pip show urllib3` | dependency version reads are not on the list; the fixes are changes | `dependency_versions` | T-C714FE28 |
| `journalctl`, log tails, `cat/tail/head` of any file | content readers can expose secrets; the whitelist counts lines, never contents | (triage wording) | — |
| anything that writes, kills, restarts, installs, opens, or deletes | class D, never executed by design | manual steps only | — |

The assembled command of any probe is re-checked token by token against a
reject list before dispatch, so a parameter cannot smuggle a second command;
`--target` accepts one absolute path, no whitespace, no dots-dot, no
metacharacters.

## Masking and credentials

Guest output is scrubbed with the same patterns as CLI errors:
`AccessKeyId`, `AccessKeySecret`, `SecurityToken`, `Signature`, and
password/username shaped values are replaced with `***REDACTED***` — that is
why a `bt default` paste survives contact with the report, and why the
templates still tell the customer to send back only the address line. The
skill never asks for, stores or prints credential values; identity comes
solely from the default CLI credential chain.
