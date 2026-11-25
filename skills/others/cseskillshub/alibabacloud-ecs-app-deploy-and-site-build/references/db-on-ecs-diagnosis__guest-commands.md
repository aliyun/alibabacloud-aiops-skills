# Guest command map

Cloud APIs cannot see what runs inside the operating system: whether the
database process is alive, which port it actually listens on, what it is bound
to, how full the filesystem is, or whether the account the client used is
granted for remote hosts. On the tickets behind this tier, every one of those
readings came from a human typing a command inside the instance and pasting the
output back.

This map splits the same readings into three classes. The classes are
hard-coded in `scripts/axes/db_on_ecs_diagnosis/_constants.py` (`AUTO_GUEST_COMMAND_EXACT`,
`AUTO_GUEST_COMMAND_FAMILIES`, `HUMAN_ONLY_GUEST_COMMANDS`,
`NEVER_AUTO_GUEST_COMMANDS`), and the entry script refuses anything not
covered by them.

| Class | What the skill does | Gate |
| --- | --- | --- |
| `auto` | Submits exactly ONE command through Cloud Assistant, reads the output back, parses it | Per-call confirmation, one dispatch = one acknowledgement |
| `human` | Prints the exact command text for the customer to run inside the instance, then interprets the pasted output via `explain` | None (the customer runs it) |
| `never` | Refused outright; even a confirmation does not unlock it. Service, firewall, partition and destructive edits stay manual console or documented steps | Blocked |

## A. Auto-dispatchable whitelist (non-mutating)

These commands only observe state. They are the batch-approved low-risk set;
`du` and `lsof +L1` are carried here strictly as triage - "is the database
failure caused by capacity?" - and once that is confirmed the cleanup itself
is handed to the capacity tier, never executed here.

Linux:

| Command | Approved arguments | Reading it yields |
| --- | --- | --- |
| `df -h` | exact | Filesystem capacity: which mount is at 100 percent |
| `df -i` | exact | Inode exhaustion: `No space left on device` with free bytes left |
| `findmnt` | exact | What is mounted where; orphaned data directory |
| `stat` | path argument | Timestamps and size of a file (error log, pid file, backup) |
| `ls` | `-l` `-1` `-a` `-h` `-d` `-L` | Directory inventory |
| `wc -l` | file argument | Row or line count of a log |
| `du` | `-x` `-s` `-h` `--max-depth` `--inodes` `--apparent-size` + path | Largest directories under a log or data path |
| `lsof +L1` | exact | Deleted-but-still-open files still holding written space |

Windows (PowerShell type, and `fsutil` query subcommands):

| Command | Approved form | Reading it yields |
| --- | --- | --- |
| `Get-Volume` | exact | NTFS free space per volume |
| `Get-PSDrive` | exact | Drive usage summary |
| `Get-ChildItem` | listing switches only | Directory inventory |
| `fsutil volume diskfree <drive>:` | query prefix | Free bytes on a volume |

Dispatch rules enforced by the code:

* One command per `RunCommand` submission, verbatim from the whitelist after
  argument validation. The submission is made with plain-text content
  encoding; the payload is echoed to the operator before dispatch.
* Any shell composition - pipes, chaining, redirection, subshells, variables,
  backticks, line continuation - is refused outright, so no mutating step can
  ride along inside an approved listing command. Redirection is refused even
  when its target is a scratch path.
* `sudo` does not unlock anything: a command that needs privilege to be
  meaningful and is off the whitelist stays a human step.
* The acknowledgement covers this dispatch only. Each further command - even
  the next drill-down level of the same `du` walk - needs its own disclosure
  and confirmation.
* Readiness first: the instance must pass the Cloud Assistant status check,
  otherwise the dispatch is skipped and the class-B paste-back path is
  printed. A running instance whose agent is offline degrades; it never
  changes the diagnosis verdicts that cloud data already supports.

## B. Human-run, paste-back commands (the rest of the decision tree)

These readings decide most layers of the connectivity tree but are NOT on the
batch whitelist for this tier, so the skill never dispatches them
automatically. The customer runs them inside the instance (console connection
or their own SSH/RDP session) and pastes the raw output; `explain` then
interprets it. The wording below matches what support engineers asked for on
the tickets behind this tier.

Linux:

```text
ss -antp | grep -w <port>          # listener on the database port? who owns it?
netstat -antlp | grep <port>       # same on older distributions
systemctl status <service>         # mysqld / redis / mongod / postgresql state
free -m                            # available memory before blaming the database
top -bn1 | head -25                # which process actually saturates the cpu
ps aux --sort=-%cpu | head         # process-level attribution
iptables -nL                       # in-guest netfilter rules
firewall-cmd --list-all            # firewalld zones, services, ports
ip route | grep default            # routing sanity
last                               # login and reboot corroboration
```

Windows:

```text
Get-Service | Where-Object {$_.Name -like "*sql*"}
Get-NetTCPConnection -LocalPort <port>
Test-NetConnection -ComputerName <target> -Port <port>
tasklist | findstr <process>
```

Third-party security software (firewall/antivirus suites installed inside the
guest) sits in this class too: the customer checks its allow-list in the
product's own user interface, because rule changes there are service-affecting
edits the skill never performs.

## C. Never executed by this skill

* Any file deletion, truncation or "cleanup" of logs and data;
* `mkfs`, `fdisk`, `parted`, `fsck`, `growpart`, `resize2fs`, `xfs_growfs`,
  `tune2fs`, mount or swap edits, `chmod` or `chown` on database directories;
* `kill`, `systemctl start|stop|restart`, service reboots, instance reboots;
* package installs or removals, security-software configuration changes;
* `iptables -F` or `firewalld` zone/port changes (opening a port is a change);
* any database client statement that grants accounts, changes authentication
  mode, or restores and detaches databases.

The report gives the human procedure, the blast radius, and the prerequisite
snapshot for each of those; the decision to run one is always the customer's.
