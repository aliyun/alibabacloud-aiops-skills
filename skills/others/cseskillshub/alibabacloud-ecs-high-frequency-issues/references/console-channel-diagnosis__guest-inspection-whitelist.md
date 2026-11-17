# Guest Inspection Command Whitelist (Frozen) and Refusal Policy

The only in-guest capability this skill has is dispatching **one** command
that reads state, through the Cloud Assistant dispatch path, after a
confirmation. This file is the authority on which commands those are.
`AUTO_GUEST_COMMANDS_LINUX`, `AUTO_GUEST_COMMANDS_WINDOWS`,
`AUTO_GUEST_COMMAND_FAMILIES`, `REFUSED_SHELL_TOKENS` and
`REFUSED_PATH_FRAGMENTS` in `scripts/areas/console_channel_diagnosis/_constants.py` implement exactly this
list; if the two ever disagree, the code is what runs and the disagreement is
a defect.

## The gate is three separate things

1. **Tell.** Before the call, state in the conversation: the exact command
   string, the instance it runs on, that it only reads state and changes
   nothing, and that the answer authorizes this one call only.
2. **Confirm.** Only after an explicit yes, run `guest-probe` with
   `--user-confirmed` **and** `--approval-quote "<the customer's verbatim
   yes>"`. The script refuses to dispatch without both.
3. **One command per confirmation.** A second reading needs a second
   tell-then-confirm cycle. Never bundle, never reuse an earlier yes, and
   never treat "go ahead and check everything" as one confirmation.

Confirmation never unlocks a command that is not on this list. The whitelist
and the gate are independent controls: passing the gate does not widen it.

## Commands accepted verbatim

Linux:

| Command | What it reads | Why it is on this area |
| --- | --- | --- |
| `df -h` | filesystem size and usage, human readable | proves the "logged in but nothing works" pattern: a full filesystem breaks login services and web-terminal helpers while the instance looks healthy |
| `df -i` | inode usage | the same failure with free bytes but no free inodes |
| `findmnt` | what is actually mounted, where | a missing mount, or a volume mounted without write access, behind a login or write failure |
| `lsof +L1` | open files that have lost their directory link | space held by deleted-but-open files, which `df` alone cannot explain |

Windows:

| Command | What it reads |
| --- | --- |
| `Get-Volume` | per-volume size and free space |
| `Get-PSDrive` | drive-level free space as the shell sees it |
| `fsutil fsinfo drives` | which drives the system currently sees |

## Commands accepted with exactly one validated argument

The command token must match the prefix shown, and the argument is validated
separately - the script rebuilds the string from a validated prefix plus a
validated argument rather than passing anything through.

| Accepted form | Argument rule |
| --- | --- |
| `du -x -h --max-depth=1 <path>` | one plain absolute path |
| `ls -la <path>` | one plain absolute path |
| `stat <path>` | one plain absolute path |
| `wc -l <path>` | one plain absolute path |
| `fsutil volume diskfree <drive>` | one drive letter, colon form (`C:`) |

Windows has no argument-taking entry on this table. An absolute Windows path
needs path separators of the kind the composition guard refuses, so no
path-taking Windows command is auto-runnable here; the drive-letter form
above is the exception. Anything deeper on Windows - a directory listing, a
volume query by path - goes down the customer-paste lane into `explain`.

`ls -la /` on the instance root is the deliberate core-directory check: it is
how a lost `/bin`-style symlink chain or a missing system directory becomes
visible evidence for the OS-troubleshooting handoff, and it is still only a
directory listing.

## What makes a submission refuse, immediately

Any one of these is a refusal with a stated reason, not a warning:

* **Shell composition or quoting** - `;`, `&&`, `||`, `|`, backtick, `$(`,
  `${`, `>`, `<`, `&`, newline, backslash, single or double quote. One plain
  command per call; anything that could graft a second action onto it fails
  closed.
* **A refused path fragment anywhere in the string** - `crash`, `atop`,
  `dump`, `shadow`, `ssh`, `passwd`, `sudoers`, `systemd`, `init.`, `resolv`.
  These are credential files, service configuration, and forensic logs. Their
  content is interpreted through `explain` on pasted output instead.
* **Anything not on the two tables above** - not close, not merely because it
  only reads, not explicitly requested by a confirmed customer.

After a refusal: report the refusal and its reason, offer the manual path
(customer runs it, pastes the output into `explain`), and stop. Do not
renegotiate a different spelling of the same command.

## Deliberately absent, and what to do instead

This is the honest boundary of the tier. None of the following is
auto-inspectable here, in every case because the reading is a
configuration, credential or audit surface rather than a state reading:

| Fact worth knowing | Why it is not dispatched | Do this instead |
| --- | --- | --- |
| Which ports and addresses a service listens on (`ss`, `netstat`) | listener tables sit next to configuration surfaces; not on this tier's list | ask the customer to run it and paste into `explain` - the IPv6-only-bind pattern is read from the paste |
| Who logged in and when, and account or lockout state | login-audit and account readers are not on this tier's list | customer-run, pasted output; the lockout lane in [error-codes.md](console-channel-diagnosis__error-codes.md) |
| Service configuration (ssh daemon, PAM, firewall) | configuration review is out of scope; changes are always human | read the pasted file content offline; never toggle anything from here |
| Third-party tunnel software presence and settings | its control commands are configuration changes with side effects | ask whether such software exists, set `--third-party-network`, and hand the configuration decision to the customer |
| Process-level attribution for a hang | requires history that only exists if a monitor was already running | state the ceiling, then point at atop for the next occurrence |

## Degradation, in words the report actually uses

* Cloud Assistant agent not online: the guest leg is unavailable. `guest-probe`
  exits `STATUS: DEGRADED` and hands the command to the customer to run and
  paste. A guest that is hung badly enough frequently cannot answer its own
  agent, so this is expected, not a malfunction of the skill.
* Dispatch denied by policy: reported with `NoPermission` / `ImplicitDeny`
  and the missing fragment from [ram-policies.md](ram-policies.md); the
  cloud-side verdicts are still delivered.
* No output inside the polling budget: `STATUS: DEGRADED`, manual paste path
  again. Never claim a reading that did not arrive.

## Windows note

The Windows rows exist because this area includes Windows instances. They
cover only "which volumes exist and how full are they". Remote-desktop
service internals are a different skill's job; see
[channel-matrix.md](console-channel-diagnosis__channel-matrix.md) for the channel-difference reading
that keeps RDP out of this package's scope.
