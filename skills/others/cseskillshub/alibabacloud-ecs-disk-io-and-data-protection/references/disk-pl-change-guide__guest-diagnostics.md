# Module M4 — In-guest diagnostics: allowlist, confirmation gate, refusals

Knowledge module for `scripts/axes/disk_pl_change_guide/disk_pl_advisor.py` (`--mode guest`), plus the
reading rules used by `--mode bottleneck`. The authoritative tables live in
`scripts/axes/disk_pl_change_guide/_constants.py` (`GUEST_COMMAND_ALLOWLIST`,
`GUEST_ANNOUNCE_TEMPLATE`, `GUEST_COMMAND_REFUSALS`,
`GUEST_IO_ATTRIBUTION_COMMANDS`, `IOSTAT_READING_RULES`); this file is their
human-readable form with ticket provenance.

## 1. Boundary: guided listing vs. gated dispatch

This tier has two distinct paths into the guest, and they are not
interchangeable:

1. **Dispatched by the skill** — only the five fixed commands of
   `GUEST_COMMAND_ALLOWLIST`, only after the customer was told the exact
   command, the exact instance, and that it writes nothing, and only after an
   explicit confirmation for that one call (`--confirm`). A missing
   confirmation means no execution, ever.
2. **Customer-run self-service** — everything else (per-process and
   per-device IO attribution, log content). The skill hands over the exact
   command, the customer runs it and pastes the output, and the skill
   interprets what was pasted. Interpreting pasted output is always allowed.

Cloud resources are never modified from either path: no snapshot, no cleanup,
no config edit, no reboot, no component install, no file write. The change
itself stays a console action by the customer
([change-matrix.md](disk-pl-change-guide__change-matrix.md) §4), and this skill re-verifies
afterwards.

When asked to run something outside the allowlist, decline with
`REFUSE_WORDING`: "This command is not in the low-risk allowlist of this
skill, so the skill will not dispatch it. Run it yourself and paste the
output; I will interpret what you paste." This mirrors how the tier's real
tickets were resolved — the human agents also asked customers to install
tools and paste logs (tickets T-EE75C111 / T-CB4F17DF / T-CC0FA37F).

## 2. The dispatch allowlist (five fixed entries)

Requested as `--guest-command <key>` (the key, or the exact command text;
free-form text is never accepted). One command per confirmation.

| Key | Command | What it touches | Why it is here |
|---|---|---|---|
| `disk-usage` | `df -h` | every mounted filesystem | fill level around a suspected disk problem |
| `mount-table` | `findmnt` | the kernel mount table | which block device really backs the path (mount caliber) |
| `stat-root-fs` | `stat /` | metadata of one path | filesystem/device attributes of the root mount |
| `atop-logs-present` | `ls /var/log/atop` | one directory listing | whether atop ever recorded the incident window — the path the human agents used (tickets T-EE75C111 / T-CB4F17DF / T-CC0FA37F); reading those logs stays with the customer |
| `system-log-size` | `wc -l /var/log/messages` | one log file | how much log exists for the OOM check (ticket T-CB4F17DF); judging content needs the customer's own grep |

All five are one-shot listings that open nothing for writing, so there is
nothing to undo. They are dispatched through `ecs RunCommand` with the
instance passed as a single `InstanceId.N`, base64 `CommandContent`, a guest
`Timeout`, and a bounded result poll (`DescribeInvocations`, at most
`GUEST_POLL_MAX` × `GUEST_POLL_INTERVAL` seconds).

## 3. Confirmation gate (mandatory, printed before any dispatch)

Run `--mode guest --guest-command <key> --instance-id <i-xxxx>` **without**
`--confirm` first. That prints the notice built from
`GUEST_ANNOUNCE_TEMPLATE` and stops with `STATUS: DEGRADED` / "NOT
EXECUTED". Relay that notice to the customer verbatim; only after an explicit
yes, re-run with `--confirm`.

The notice has to carry, in this order:

1. the exact command string and the exact instance id it goes to;
2. scope — what the command reads;
3. effect — that it prints only and writes nothing;
4. reversibility — nothing to undo;
5. purpose — which symptom it settles;
6. the limit of the grant: this confirmation covers this single command on
   this single instance; every further command needs a fresh confirmation;
7. the opt-out: answer "no" and the same command comes back as a self-check
   step for the customer to run.

Never batch, never paraphrase the command away, and never infer confirmation
from a prior call or from a general "do whatever you need".

## 4. Refused for dispatch (converted into customer-run steps)

| Refused request | Why not dispatched | What the skill does instead |
|---|---|---|
| atop / any package install | installing a tool mutates the system | customer installs per the atop docs below; afterwards the skill may check whether logs exist |
| `top`, `tload`, other continuous monitors | interactive long-running process, not a one-shot listing | customer runs it and pastes a screenshot |
| `lsblk -d -o name,rota` | guest device-model flag is not in the allowlist | customer pastes the reading (ticket T-0F3C602D path); unexplained cases escalate to human support |
| `iostat`, `sar` | not in the allowlist | customer pastes the reading; §5 rules then apply |
| `grep` / `cat` / `tail` of log **content** | body reading is content access outside the allowlist | customer greps the OOM / slow / access log and pastes the excerpt |
| any cleanup, restart, config edit, formatting, snapshot or agent install in the guest | mutating | console / in-guest steps performed by the customer, with the risk statement |

atop install and usage guidance (what the human agents pointed to):
- <https://help.aliyun.com/zh/ecs/how-to-use-the-linux-system-atop-monitoring-tools>
- <https://help.aliyun.com/zh/ecs/user-guide/use-the-atop-tool-to-monitor-linux-system-metrics>

The customer-run attribution list, verbatim from
`GUEST_IO_ATTRIBUTION_COMMANDS`:

```bash
lsblk -d -o name,rota                 # is the disk flagged rotational? (ticket T-0F3C602D)
iostat -x 1 5                         # %util vs await per device (ticket T-4F5CBA0C reading)
atop                                  # per-process IO attribution across a repro window
grep -i 'out of memory\|oom' /var/log/messages   # OOM evidence (ticket T-CB4F17DF)
```

Plus the workload-side logs named in the tickets: the database slow log and
the web-server access log around the incident window.

## 5. How to read the pasted output

- `%util` 97–99% with `await` below ~1 ms → the disk is busy but fast:
  random-read-heavy workload, **not** a disk bottleneck (ticket T-4F5CBA0C:
  MongoDB case closed with exactly this reading).
- Throughput pinned at the capacity-derived ceiling from
  performance-formulas.md (in alibabacloud-ecs-high-frequency-issues) §3 → disk side saturated;
  proceed to the change plan (`--mode assess`).
- `rota=1` on an ESSD/AutoPL disk → the guest sees an SSD as rotational.
  ESSD-family disks ARE SSD-backed; the flag is a guest-side device-model
  anomaly that can disable IO-scheduler optimizations. Ticket T-0F3C602D
  shows the correct terminal step: **escalate to human support** with the
  pasted readings — do not explain it away.
- IO spikes with no matching cloud-side ceiling hit → per-process behavior
  inside the guest; the atop window is the evidence path (tickets
  T-EE75C111 / T-CC0FA37F).

## 6. DEGRADED contract

`STATUS: DEGRADED` is emitted, with nothing executed and no invented
reading, when: the customer did not confirm; the command was outside the
allowlist; the instance is not visible in the authorized account and region;
Cloud Assistant is unreachable or the dispatch call fails; the poll expired
before a terminal status; or the customer simply cannot paste readings.

State in this order: what is missing, what the cloud side already proves
(ceilings, attachment, metrics), then hand back the §4 command list. A
denied permission is reported as `NoPermission` / `ImplicitDeny` naming the
exact action in [ram-policies.md](ram-policies.md) — never as "not found".

Windows instances: `OSType`/`OSName` from `DescribeInstances` stops the
dispatch (the allowlist is shell syntax, and this tier's ticket evidence is
Linux-only); the request goes to human support
(handoff-boundaries.md (in alibabacloud-ecs-high-frequency-issues)).
