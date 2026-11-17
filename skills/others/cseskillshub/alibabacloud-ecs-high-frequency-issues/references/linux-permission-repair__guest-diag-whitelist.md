# In-guest inspection whitelist (approved commands only)

These are the only commands `scripts/areas/linux_permission_repair/permission_diagnosis.py guest-run` will send into an instance,
and each one still needs the customer's approval for that exact command (`../SKILL.md` section 3).
The rules below are not prose: `validate_guest_command()` in the entry point enforces them and
refuses before any cloud request is built.

## Allowed tools

| Tool | Accepted flags | Positional | Max paths | What it proves |
|---|---|---|---|---|
| `stat` | `-L`, `--dereference` | absolute paths | 4 | mode bits including setuid, owner, group, link target of one path |
| `ls` | `-l`, `-ld`, `-d`, `-n`, `-g`, `-h`, `-la`, `-al`, `-lh`, `-hl`, `-lnd` | absolute paths | 4 | mode and owner as seen by the shell, and whether a directory is traversable |
| `findmnt` | `-l`, `-P`, `-p`, `-t`, `-o`, `-M`, `-S`, `--noheadings`, `--raw`, `--list`, `--target`, `--source`, `--types`, `--options` | optional mount point after `-M`/`--target` | 2 | `nosuid` or `ro` on `/` or `/usr`, which defeats setuid and sudo even when the bits are correct |

Flags not in that column are refused, so no tool can be turned into a writer by an option
(`ls --output`, `stat --format` with a shell payload, `findmnt --options` feeding a command, and so
on). `stat -c`/`--format`, `ls -R`, `findmnt --submounts`-style recursion and any `-o exec` like
argument construction are deliberately absent.

## Structural rules

* **One** command per approval, one tool per command, executed against **one** instance.
* Absolute paths made of plain characters only: a leading `/`, then letters, digits, `.`, `_`, `-`,
  `/`. Anything else is refused.
* No shell syntax at all: no `;`, `&&`, `||`, `|`, backtick, `$(`, redirection, newline, `&`,
  `*`, `?`, `~`, `\`, or quotes. A glob is not a path: enumerate the path you want.
* No tool invoked by absolute path; call it by name.
* At most 6 arguments and 512 characters per command; the guest execution timeout is 20 seconds.
* Never `sudo` or `su` as the command itself. Cloud Assistant already runs the inspection with the
  privileges configured for the command sender, so an unprivileged `stat` reading of a mode bit is
  enough; the skill does not chain privilege inside the guest.

## Refused on purpose

Requests of this shape come up constantly. Each one is answered by handing the command to the
customer to run and asking for the pasted output - never by sending it:

```
cat /etc/sudoers                  # content, not metadata
cat /etc/ssh/sshd_config           # content, not metadata
grep root /etc/ssh/sshd_config     # content search
sudo -l                            # runs a privileged helper
visudo -c                          # parses and validates configuration
getfacl /home/admin                # extended ACLs, outside the tool set
lsattr /usr/bin/sudo               # attributes, outside the tool set
find /etc -perm -4000              # traversal plus globbing
rpm -Va sudo                       # package integrity sweep
chmod u+s /usr/bin/sudo            # repair - manual, after a snapshot
chown -R admin:admin /home/admin   # repair - manual, after a snapshot
usermod -aG sudo admin             # repair - manual, after a snapshot
passwd root                        # credential change - console path only
systemctl restart sshd             # service change - manual
```

The refusal is not a limitation to apologise for: it is the reason the customer can approve a
`guest-run` in one sentence, because the command provably changes nothing.

## Reading the output back

`guest-run` sends the command and then polls `ecs:DescribeInvocations` for up to about 30 seconds.
If no output has landed, it stops with `STATUS: DEGRADED` and a ready-made `guest-result` line;
that API lists **past** executions only, so a live value always needs a fresh `guest-run`.
Reading back an execution that was already approved sends nothing new into the instance, so it
needs no further approval. Any fresh reading is a fresh command, and a fresh command needs its own
approval under `../SKILL.md` section 3.

## Where capacity tools went

`df`, `du`, `lsof` and inode counters are not on the whitelist. They measure capacity, which is a
different symptom area and belongs to the capacity/inode skill of this batch (`../SKILL.md`
section 8). A permission fault is never proven by a usage number.
