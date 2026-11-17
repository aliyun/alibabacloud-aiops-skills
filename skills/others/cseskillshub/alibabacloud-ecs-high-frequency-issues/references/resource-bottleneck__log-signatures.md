# Log and alarm signatures: how each is read

This page supports rule **R9** (`references/resource-bottleneck__diagnosis-rules.md`). It exists because
in this tier customers paste a kernel line or an alarm name and the wrong
conclusion follows immediately from the name alone: a "blocked" task gets blamed
for the freeze, a "SYN flooding" notice gets read as an attack, a "throttled"
alarm gets read as "buy a bigger disk".

The detection strings the parser actually matches are in
`guest_evidence.py::parse_guest_findings`. This page adds the *interpretation*,
which is not in the code and must not be improvised per-ticket.

## Recognised signatures

| String seen (substring match) | Finding id | Level | Reading | Not what it means |
| --- | --- | --- | --- | --- |
| `kswapd` (e.g. `kswapd0` high in `top -bn1`) | `G-KSWAPD` | high | the kernel swap daemon is paging: **memory** pressure is driving the reading | "CPU is the bottleneck" — the CPU cost here is reclaim, not the workload (rule R1) |
| `out of memory`, `oom`, `oom-killer` | `G-OOM` | high | memory exhaustion reached process-kill level | "the killed process was the leak" — confirm which allocation drained memory before naming a culprit |
| `blocked for more than` | `G-BLOCKED` | high | a task waited past the hung-task limit; it is the **victim** of IO pressure, usually paging-induced | "this process caused the hang" (ticket T-BF2F77A0, where the pasted `journalctl` line was `task AliYunDunMonito:5860 blocked`) |
| `possible syn flooding` | `G-SYN` | info | the kernel's half-connection queue was full at that moment | "under attack" or "a defect" — judge together with bandwidth and connection counts (ticket T-F5D78C4B) |
| load-average line in `top`/`uptime` output | `G-LOAD` | info | runnable + queued work expressed as a multiple of the vCPU count, taken as the 1-minute `/proc`-style value | treating the raw number as "cores busy": a load of 8 on 2 vCPU is a 4x queue, and a load of 8 with 0.5 CPU-busy means waiters, not compute (rule R3) |
| any process line at >= 50% of a processor | `G-TOP` | info | names the busiest process, quoted, with the raw line kept for traceability | interpreting *what that process is for* — the code deliberately does not (see below) |

## Disk-throttle alarms

A CloudMonitor disk read/write throttled alarm says the disk reached its
throughput ceiling. It does **not** say the disk is the cause. Order of checking,
from this tier's evidence:

1. Is memory paging concurrently high (R1)? `kswapd` present in guest output, swap
   activity in `vmstat`, `free -m` available near zero.
2. Is the shape a sustained application IO pattern, or a spike co-timed with CPU
   (R4)? Use the co-peak timestamp, not the alarm name.
3. Only then is the ceiling itself the question — and the ceiling number belongs to
   the disk IO tier (`references/resource-bottleneck__escalation-map.md`), not computed here
   (ticket T-CC0FA37F).

## What the parser deliberately does not do

`_top_cpu_lines` quotes the process **name** and the raw line, and stops. Two
reasons are recorded in the code comment and hold as policy:

- Customers repeatedly misremembered which process it was (php versus `beam.smp`
  in ticket T-88D2167B), so the raw line must be in the report;
- deciding whether that process *should* be busy is a business question, and the
  finding text asks the customer to confirm the volume is expected instead of
  asserting it.

## Unrecognised strings

The tier spec records that this batch has **no** quotable error strings beyond the
signatures above. Consequences:

- An unknown kernel line or alarm text is **reproduced verbatim** in the report and
  escalated, not interpreted. The report says "no catalogued reading for this
  string" rather than offering a plausible-sounding one.
- A signature is never *inferred* from a metric shape. `G-*` findings exist only
  when the string is present in actual guest output.
- Adding a signature requires: the string as it appeared in a ticket, the reading,
  the not-what-it-means reading, and the rule it belongs to. That is a change to
  `guest_evidence.py` and this page together, with the ticket id in both.

## Cross-checks before quoting any signature back to a customer

1. Does it come from **this** instance and **this** window? (rule R8 — a pasted log
   may be from another machine, another time, or from a screenshot of an unrelated
   console page; ticket T-72D9DFCB's first "black screen" screenshot was actually a
   vulnerability detail page.)
2. Is it masked? Credentials appearing inside a pasted log or command output are
   masked on the way out (`_cli.mask_credentials`), and the reminder to rotate a
   disclosed secret is part of the reply — see `references/resource-bottleneck__evidence-and-privacy.md`.
3. Which metric field corroborates it, and what is that field's caliber? A
   signature without a corroborating reading stays at `info` or `warn`; it does not
   become the conclusion.
