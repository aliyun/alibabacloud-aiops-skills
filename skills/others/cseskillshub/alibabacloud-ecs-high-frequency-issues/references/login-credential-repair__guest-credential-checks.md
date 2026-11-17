# In-guest credential readings (customer-executed)

## 1. Why these exist, and who runs them

Several facts this tier needs are not visible from any cloud API: which logon
users actually exist inside the guest, what the SSH daemon is configured to
accept, the effective lockout threshold, whether the account is disabled or
merely locked, and which port the remote service really listens on.

**The scripts of this skill execute nothing inside the guest.** The in-guest
command whitelist available to this batch covers the disk-capacity area and was
not extended to the credential area (open point 1 in
[login-credential-decision-tree.md](login-credential-repair__login-credential-decision-tree.md)). Until
that grant exists, every command on this page is run **by the customer** in
their own console session - Workbench or the session manager - and the output
is pasted back. That is the same thing a human engineer asks for, with two
improvements: the command type and the success criterion are stated up front,
and the request is one line at a time.

Rules for asking:

1. Say which single line will run, what it reads, and that it changes nothing.
2. One line per request. Do not batch, do not chain with redirection.
3. Ask for the **output**, never the password. Tell the customer to mask
   anything secret-looking before pasting.
4. If the customer cannot sign in at all, these readings are unavailable by
   definition: route to the console session path, or hand off, rather than
   guessing the answer.
5. If a reading comes back empty or refused, report it as unknown. An empty
   result is a finding, not a licence to infer.

## 2. Linux readings

| Fact needed | Line for the customer to run | How to read the output |
| --- | --- | --- |
| Which logon users really exist | `getent passwd` | First column is the account name; look for `root`, `ecs-user`, `cloud-user`, or a custom name. No `root` line means the assumed user does not exist (LC6) |
| Whether SSH forbids root / password / key logon | `grep -Ei 'PermitRootLogin\|PasswordAuthentication\|PubkeyAuthentication' /etc/ssh/sshd_config` | `PermitRootLogin no` explains a root refusal with a correct password; `PasswordAuthentication no` explains a password refusal on any account. Effective settings may also come from drop-in files under `sshd_config.d`, so an empty result here is not proof |
| Account lock and password-expiry state | `passwd -S <user>` then `chage -l <user>` | A leading `L` means locked, `P`/`NP` means password set / not set; an expired date explains a forced-change failure loop |
| Failed logon attempts and their source | `faillock --user <user>` then `lastb` | Per-source failure counters and the bad-login log. Empty output usually means the logs are not retained, which is itself the answer |

## 3. Windows readings

Command context matters: the query lines below are command-prompt commands, and
in the console command page the type has to be **Bat**, not Shell - the
symmetric mistake to the Linux one. Inside an interactive session either a
command prompt or PowerShell works (Win+R, then `powershell`, or search the
Start menu).

| Fact needed | Line for the customer to run | How to read the output |
| --- | --- | --- |
| Effective lockout policy | `net accounts` (query form, no parameters) | The lockout threshold, lockout duration and observation window. Threshold 0 means no lockout protection is configured; threshold 5 is a common default. This is also how a threshold change is verified |
| State of one local account | `net user <name>` (query form) | "Account active" Yes/No and the "account expires" field distinguish disabled from locked |
| Local accounts and whether they are enabled | `Get-LocalUser \| Format-Table Name,Enabled` | `Enabled False` is disabled. A locked account keeps `Enabled True` and still fails logon - that contrast is the whole point of LC5 versus LC6 |
| Who is logged on remotely | `query user` | Session names and states; no line means nobody has a remote session |
| The real remote-desktop listening port | `netstat -ano \| findstr 3389` | Nothing on 3389 means the service listens elsewhere or is stopped. This is how a non-default port is confirmed instead of guessed |
| Where the failed attempts came from | `Get-WinEvent -FilterHashtable @{LogName='Security';Id=4625} -MaxEvents 20 \| Format-Table TimeCreated,Message` | The logon-failure entries carry the attempted account and the source address. Empty output usually means event-log access is restricted |

Confidence note: the Windows account-state commands are quoted from support
practice in this tier, not from a located official page. Treat the interpretation
as medium confidence and prefer the observable field ("threshold reads 5",
"Account active No") over any conclusion drawn from it.

## 4. Commands this skill refuses to automate

Everything below changes state. They appear in reports only as numbered human
steps with the risk statement attached, and the skill will not wrap, complete,
or dispatch any of them:

| Command | What it actually does | Required framing when guided |
| --- | --- | --- |
| `net accounts /lockoutthreshold:0` | Writes the account lockout policy; it is not "the unlock command" despite being quoted that way in this tier | Policy write; removes brute-force protection; snapshot first; must be followed by restoring a sane threshold |
| `net user <name> <newpassword>` | Changes a password from inside the guest | Password write; the customer types it themselves, never through this conversation |
| `net user <name> /active:yes` | Enables an account | Account attribute write; only correct when the account really is disabled (LC6), not when it is locked (LC5) |
| `passwd <user>`, `usermod -U <user>`, `faillock --user <user> --reset` | Linux password change, unlock, counter reset | Each is a write; snapshot first |
| Editing `/etc/ssh/sshd_config` and reloading the daemon | Changes what the server accepts | Configuration write plus a service reload; a bad value can lock everyone out, so console session access must be verified first |
| `gpedit.msc` / local security policy edits, registry port edits | Windows policy and port changes | Manual, documented steps only |
| `bt 5` and similar application-panel commands | Changes an application password | Not an ECS logon credential at all: out of scope, see [handoff-scripts.md](login-credential-repair__handoff-scripts.md) |

The rejection is syntactic as well as policy: a command string that contains
redirection, removal, move, truncate, `dd`, `kill`, service control, reboot,
registry writes, or any password argument is refused even if the surrounding
request looks harmless.

## 5. Known gaps to state plainly

- **Failed logon attempt counts and their sources** are the most-requested
  reading in this tier and are not covered today: they live in the guest event
  log, and no in-guest execution is authorized. The honest answer is "this flow
  cannot retrieve the count; here is where it lives".
- **Security-group source ranges** are not read by this skill, so an exposure
  claim stays a hypothesis with a named measurement the customer can do in the
  console.
- **Disk free space** is not read either; when a reset fails with a disk-space
  message, that message is the evidence and the case goes to the disk capacity
  area.
- **Snapshot rollback history**: if a rollback happened recently, warn that the
  logon password may have rolled back with the system disk to the snapshot
  creation time. That is a low-confidence operational note from a single
  summary in the evidence, with no located official page - never state it as
  the cause.
