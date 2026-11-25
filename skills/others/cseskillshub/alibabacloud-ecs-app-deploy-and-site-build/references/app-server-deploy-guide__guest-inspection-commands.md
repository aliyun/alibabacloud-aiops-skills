# Guest inspection commands (class B, per-call confirmation)

There is no cloud API that returns what is happening inside a guest: process
state, free inodes, or whether the files landed on the intended disk all live
inside the instance. What exists here instead is a short frozen list of
inspection commands that this skill can dispatch through Cloud Assistant --
each one prints state and changes nothing, each one needs its own explicit
confirmation, and nothing outside the list is ever dispatched. The list
mirrors the batch-approved low-risk command set; widening it requires a
review of that set first, never an in-session decision.

## The published list

| Probe name | Exact command | What it proves | When it matters here |
|---|---|---|---|
| `space` | `df -h` | Free space per mounted file system, human units | Any fresh install: the target file system must have room before a server package is unpacked |
| `inodes` | `df -i` | Free inodes per mounted file system | "cannot create new file" or file-count symptoms when raw space looks fine -- an exhausted inode table, which the capacity tier then owns |
| `mounts` | `findmnt` | The live mount table: which device backs which directory | An install that "disappeared": game files written to the system disk because a data disk was never mounted where the customer expected |
| `root-usage` | `du -x --max-depth=1 /` | One-level usage of the root file system, staying on one device | A space check came back full and the biggest top-level directories need naming before handoff |
| `deleted-open` | `lsof +L1` | Files still held open after deletion | Right after a cleanup, when `df` still says full but usage does not add up: a running process is still holding the space |

Every entry is one complete fixed command string. The script compares the
confirmation to that string character for character, refuses anything else,
and puts at most one command on one confirmed call.

## The gate, in order

Before ANY dispatch the reply to the customer must state:

1. the exact command that will run and its probe name from the table above;
2. where it runs: inside the guest of one named instance;
3. that the command only prints state -- it changes nothing on disk;
4. that the approval covers this one call, and the next reading needs its own
   confirmation.

Only then may the entry script run with both `--probe <name>` and
`--confirm-probe "<exact command string>"`. Without the matching confirmation
the transport layer raises `ConfirmationRequired` and nothing is dispatched.

The result comes back through the invocation history query, is masked for any
credential-shaped material, and is truncated. A dispatched reading whose
result cannot be fetched back is reported as `DEGRADED` with the invoke id --
never as a guessed output.

## What is deliberately not on the list

Service, port, process and package-manager queries are not in the approved
command whitelist for this tier. A "the server is installed but not
reachable" check therefore stays a human step:

* listening sockets: the customer runs `ss -tlnp` themselves and pastes the
  output;
* service state: the customer runs their own service status command;
* runtime versions (`java -version`, `node -v`): customer-side;
* installing anything, starting anything, editing anything: never dispatched,
  under any confirmation, because they are outside this skill entirely.

Windows guests: the published readings are Linux shell probes only this
release. On a Windows instance the skill does not dispatch; it prints the
equivalent human checks and asks for pasted output.

## If the customer prefers not to run the gate

The skill is useful without class B: every cloud-side fact (existence, status,
type, zone, stock) still returns. Ask the customer to run `df -h` and `df -i`
themselves and paste the two blocks; the decision tree reads them just the
same, and the capacity handoff carries the evidence either way.

## After an inode or space reading comes back exhausted

Snapshot-first, always: no cleanup is guided until a snapshot of the affected
disk exists (`--snapshot-disk-id` with its own confirmation, or the same
console step done by the customer). `ecs:create-snapshot` is billable storage
until a human deletes it, and deleting files is never part of this package --
see [handoff-boundaries.md](handoff-boundaries.md) for the capacity tier
handoff wording.
