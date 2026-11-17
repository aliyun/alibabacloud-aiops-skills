# Guest command whitelist

The commands in class B of `ram-policies.md`: run inside the customer instance to
obtain what no cloud API exposes. Used capacity, inode pressure, which directory
holds the space, which deleted file is still held open. The control plane reports
provisioned size and nothing else, so without these readings the disk-space
branch of the decision tree cannot close.

They are delivered by the `ecs` RAM action for `RunCommand`, which is a
write-class permission even when the command it carries only prints. That asymmetry is why every rule below is
enforced in code, not in prose.

## The rules, and where each is enforced

| Rule | Enforced by |
| --- | --- |
| Exactly one command per consent, and consent is bound to region, instance, probe and target | `guest_ack()` and the `--confirm` comparison |
| The command string is re-validated after assembly, so a parameter cannot smuggle a second command | `_validate_command_string()` |
| Shell metacharacters are rejected outright: `;` `|` `&` `$` backtick `>` `<` `*` `?` `(` `)` `{` `}` and any newline | `SHELL_METACHARACTERS` |
| A rejected-token list is applied to every word of the assembled string, not just the program name | `REJECTED_COMMAND_TOKENS` checked against `_REJECTED_TOKENS` |
| `--target` must be a POSIX absolute path, a bare drive letter, or a drive-rooted Windows path; must not traverse with `..`; must not contain whitespace | `_validate_target()` |
| Nothing is written to the instance. No output redirection, no candidate-list file | the rejection rules above; a redirect is a metacharacter |

The last row is a deliberate narrowing. An earlier design had the skill write a
cleanup-candidate list into `/tmp` inside the instance. Producing that file
requires a redirect, a redirect is a side effect, and a side effect violates the
whitelist. So the candidate list is printed in the report instead and the customer
decides. The write path was dropped rather than the rule bent.

## Whitelisted probes

Linux, delivered as `Type=RunShellScript`.

| Key | Command | Side effects | What it answers |
| --- | --- | --- | --- |
| `df_h` | `df -h` | none | which volume is full, and how full |
| `df_i` | `df -i` | none | a volume with free bytes but no free inodes |
| `findmnt` | `findmnt` | none | which device backs the path the job writes to, and its mount options |
| `du_top` | `du -x --max-depth=1 <path>` | none | which direct child of one directory holds the space; `-x` keeps it off other mounts |
| `lsof_deleted` | `lsof +L1` | none | files deleted but still held open, so space not yet returned |
| `stat` | `stat <path>` | none | size and block count of one suspected file |
| `ls_dir` | `ls -lh <path>` | none | individual large or unexpected entries in one directory |
| `wc_lines` | `wc -l <path>` | none | how big a log has grown, before a manual truncation decision |

Windows, delivered as `Type=RunPowerShellScript`.

| Key | Command | Side effects | What it answers |
| --- | --- | --- | --- |
| `get_volume` | `Get-Volume` | none | health, size and free space per volume |
| `get_psdrive` | `Get-PSDrive` | none | used and free bytes per drive letter |
| `get_childitem` | `Get-ChildItem -Force <path>` | none | listing including hidden entries under one path |
| `fsutil_diskfree` | `fsutil volume diskfree C:` | none | exact total, free and available bytes for one volume |

Probes taking a target are listed with `<path>`; the others reject `--target`
outright, so a caller cannot append an argument to `df -h`.

## Rejected regardless of how harmless it looks

Anything that removes, moves, truncates, formats, kills, restarts, mounts,
installs, writes, downloads or changes configuration. In particular the verbs
support engineers used in the source cases and that this skill will not reproduce:
stopping or disabling a service, changing the resolver, editing routes, resetting a
password, and any of the cleanup deletions that follow a `du_top` reading.

The PowerShell `Get-Service`, `Stop-Service` and `Restart-Service` cmdlets, and the
`Set-`, `Remove-`, `New-` and `Add-` verb families generally, are outside the list
because they are not the reading the tree needs, and because the naming is one
keystroke from a change.

## Network and resolver checks are not whitelisted

The three highest-value root causes in this tier live in here: an overlay network
claiming 100.64.0.0/10 or 100.100.0.0/16, a client overwriting the resolver, and
the Aliyun Assist service being stopped. The commands that prove each of them -
`ip route`, `route -n`, `ifconfig`, reading `/etc/resolv.conf`,
`Get-NetRoute`, `Get-DnsClientServerAddress`, `services.msc` - are the ones the
source cases actually used, and they are deliberately absent above.

Reason: the whitelist is defined by the low-risk operation list for this batch,
and that list covers capacity and file metadata, not network and service state.
Closing the gap by widening the list is not this skill's call.

So on the `CLOUD_ASSISTANT_UNREACHABLE` branch the script withholds probes
entirely and prints the self-check commands for the customer to run themselves.
Probing that branch through Cloud Assistant would also be circular: the probe
rides the channel under test.

## Reading the outputs

| Probe | Healthy | Failing, in this tier's sense |
| --- | --- | --- |
| `df_h` | every volume under about 90 percent | a volume at or near 100 percent, and it is usually the system volume rather than the data volume |
| `df_i` | IUse percent well below 100 | IUse at 100 with bytes free. The customer will insist the disk is not full, and both are true |
| `lsof_deleted` | nothing | a large deleted file held by a running process. Space returns when the process releases it, which is a service action and therefore manual |
| `du_top` | space concentrated where the customer expects it | one directory dominating; hand the deletion decision over with the size attached |
| `findmnt` | the backup target path sits on a cloud-backed volume | it sits on a tmpfs or an overlay, where a capacity alarm means something different |
| `get_volume`, `get_psd`, `fsutil_diskfree` | free space on the volume the job targets | the system volume is the full one, which is the case T-2E38E856 shape |

## Windows: the inode question has no equivalent, and the report must say so

NTFS has no `df -i` counterpart in this whitelist. A customer reporting "cannot
create new file" on Windows is usually out of bytes, not out of index entries; the
rare MFT-pressure case needs a tool this whitelist does not carry.

So on Windows, report what was measured and name what was not, in this shape:

> Measured on <instance-id> at <time>: volume <letter> shows <free> of <total>
> bytes free (`Get-Volume`, `fsutil volume diskfree`). Free space is the only
> capacity limit this probe set reads. This skill does not assess MFT or
> per-volume entry limits, so "no space left" cannot be separated from "cannot
> create new file" on this instance from these readings alone. If bytes show free
> yet file creation still fails, that needs an MFT-capable check, which is a
> manual diagnostic.

Never let an absent measurement be inferred as a passing one. An unmeasured limit
is not a healthy limit.

## Consent dialogue

The script refuses to act on a bare flag; it prints the disclosure and hands back
a token. Put the disclosure to the customer as four sentences, in this order:

1. the exact command string that will run;
2. that it inspects state and modifies nothing, inside one named instance;
3. that the Cloud Assistant agent must be online for it to arrive;
4. the token to repeat back.

The next command always needs its own consent, including a second `df` on a
different instance. `snapshot-guard` is a separate consent again, and it carries a
cost notice, because unlike a probe it creates a billed resource.

## Degraded mode

When the probe cannot be delivered - agent offline, `NoPermission`, polling budget
exhausted - the report prints the command for the customer to run and paste:

> The reading could not be collected automatically: <reason>. Please run
> `<command>` inside <instance-id> and paste the output. It changes nothing on
> the system.

Then resume the same branch. Customer-pasted output is admissible evidence here;
it is what the source cases ran on. Mark it as customer-supplied in the report
rather than presenting it as a measurement the skill took.
