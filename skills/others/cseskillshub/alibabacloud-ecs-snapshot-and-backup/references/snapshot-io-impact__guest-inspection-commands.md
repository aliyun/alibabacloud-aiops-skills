# In-guest inspection: frozen command set and refusal rules

This file is the human-readable twin of `GUEST_COMMANDS`, `REFUSED_GUEST_TOOLS`
and `REJECTED_COMMAND_TOKENS` in `../scripts/_constants.py`. If the two disagree,
the constant is authoritative - the script enforces it, this file only explains
it.

## 1. What this channel is, and is not

It exists because no cloud API reports what a file system looks like from inside
the guest. `DescribeInvocations` returns the *record* of a past delivery, never
live state, so a current reading has to be produced by running something.

Two properties define the channel:

- **The delivered commands only print.** None of them alters data on the disk.
- **The delivery itself is a write.** Sending a command creates a Cloud
  Assistant invocation record on the customer's instance. That is why this class
  sits behind a confirmation gate instead of running automatically with the cloud
  reads.

One command per call. Never a script, never a compound line, never a loop.

## 2. Honest limitation of this channel for this tier

Every command below reports **capacity or file-handle state**. Not one of them
measures block-device latency, queue depth, or in-flight I/O - which is the
quantity this tier's subject actually turns on.

Their value is corroboration: a volume at 95 per cent full makes write paths
slower on its own, so a snapshot window on the same disk hurts more. A `df -h`
line may be cited as that context and nothing more. It must never be presented
as an I/O measurement, and it must never be used to upgrade a B2 verdict to B1.

The tools that would answer the latency question directly are listed in section
5 as refused. The customer runs those themselves and pastes the output.

## 3. The whitelist

Selection is by `--command-key`, never by free text. The script looks the key up
in the frozen table and assembles the command line itself.

| Command key | What runs | Path argument | What it reports |
|---|---|---|---|
| `disk-usage` | `df -h` | no | How full each file system is right now |
| `inode-usage` | `df -i` | no | Inode pressure, which also slows writes |
| `directory-volume` | `du -x --max-depth=1` | **yes** | How much one directory level holds |
| `deleted-open-files` | `lsof +L1` | no | Space held by files deleted while still open |
| `mount-map` | `findmnt` | no | Which device backs which mount point |
| `path-stat` | `stat` | **yes** | One path's metadata, contents untouched |
| `directory-listing` | `ls -l` | **yes** | One directory's entries, nothing followed or modified |
| `line-count` | `wc -l` | **yes** | Line count of one file, e.g. an application log |

`mount-map` is usually the right first call: it maps the cloud disk id's device
name to the mount point that the capacity rows are then read against.

`-x` on `du` keeps it inside one file system, and `--max-depth=1` keeps its cost
bounded; `lsof` can be slow on a host with very many open handles, which the
disclosure in section 6 has to mention.

### Path argument rules

A path is accepted only when it is a plain absolute path: it must start with `/`,
contain no `..` traversal, and stay inside the character class the validator in
`../scripts/_constants.py` defines. Anything else is rejected before the network
is touched. Do not "fix" a rejected path by guessing what the customer meant -
ask which exact path they want inspected.

## 4. Structural guarantees

These are enforced in code, not by convention. They are recorded so the agent
trusts the gate rather than re-implementing it in prose:

- The assembled command is rejected if it contains **any** shell metacharacter:
  `;` `&` `|` `>` `<` backtick `$` `(` `)` newline or backslash. Concatenation,
  redirection and substitution are therefore impossible by construction.
- Execution goes through an argument list with a per-call timeout, never through
  a shell.
- The target instance id must be repeated verbatim in the confirmation flag.
- Output passing back through the script is masked for credential-shaped values.
- Only Linux is enabled on this channel in this release; a Windows target stops
  at the gate and stays manual (see section 7).

## 5. Refused and rejected

Three distinct outcomes. Keep them apart, because the answer to the customer
differs in each.

### 5.1 Outside the whitelist (not found by key)

A command key that is not in section 3 does not exist for this skill. The script
names the key as unrecognised. The correct response is to say which inspections
are available - not to find another way to run what was asked.

### 5.2 Refused because they measure the right thing

These tools answer the latency question and are deliberately **not** dispatchable
in this batch: `iostat`, `iotop`, `pidstat`, `sar`, `vmstat`, `dmesg`,
`journalctl`, `fio`, `dd`, `blktrace`, `perf`, `atop`.

Refusing them is not a judgement that they are dangerous - most of them only
print information. It is the whitelist rule holding: the callable set is frozen
for this batch, and a skill that grows its own command set at runtime has no
boundary at all.

The response is guidance, not a command line: ask the customer to run the tool
themselves over the same window, paste the output, and say which figure is being
asked for (for example average write wait time per device). Treat the paste as
customer-supplied evidence and attribute it as such in the report.

### 5.3 Rejected for side effects

Any token implying a state change is refused outright and never offered as an
executable line, not even "for you to run yourself": removal, moving, copying,
writing, truncating, formatting, checking or repartitioning a file system,
mounting, unmounting, signalling a process, restarting or shutting down, changing
a service, toggling the page cache, changing ownership or permissions, and any
network fetch.

Where the customer genuinely needs one of these, describe the outcome they want
in words and name the console entry point or the owning tier in
[handoffs.md](handoffs.md). Describing an outcome is not supplying a command.

## 6. The confirmation gate, in practice

Before any delivery, the agent shows the customer:

1. **Target** - the instance id and region.
2. **The exact command** - the assembled line as it will run.
3. **What it returns** - one sentence from section 3.
4. **State change** - none inside the guest; one invocation record on the Cloud
   Assistant side, which is why the call is a write.
5. **Reversibility** - nothing to roll back; the reading is transient.
6. **Blast radius** - one inspection command, one instance, with the timeout
   that bounds it.

Then stop and wait for an explicit yes.

A confirmation covers **one command on one target at one time**. It does not
carry over to the next command, the next disk, or the next run, and it is not
inferred from the customer asking a broad question, from "go ahead and check", or
from a previous session. Each new command needs its own disclosure and its own
yes. Re-ask after any change to the target or the path argument.

The script implements this as a flag that must repeat the exact instance id, so a
forgotten gate fails closed rather than open. If the customer declines, the run
continues on cloud evidence alone and the report says the guest reading was
declined - not that it was unobtainable.

### When the channel itself is unavailable

Cloud Assistant agent missing, offline, or the delivery permission denied: stop,
report the reason with the returned code, and fall back to asking the customer to
run a whitelisted command and paste the output. Never ask for an instance
password to work around it, and never treat a delivery failure as evidence about
the disk.

## 7. Windows

Not enabled on this channel for this tier, and no Windows case was supplied to
justify it. Windows capacity questions stay manual: point the customer at the
console disk view, or ask them to report volume free space themselves.

The reason for the hard "no" rather than a soft "maybe" is specific: NTFS has no
inode counter, so `df -i` has no equivalent, and a whitelist row whose semantics
differ between operating systems invites a false comparison between the two. If
Windows support is added later, it needs its own table with that difference
stated per row.
