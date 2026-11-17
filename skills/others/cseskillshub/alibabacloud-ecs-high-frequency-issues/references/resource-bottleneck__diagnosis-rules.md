# Diagnosis rules R1-R9

Every conclusion this skill states is produced by one of the rules below. The
machine-readable copy lives in `RULES` in `scripts/areas/resource_bottleneck/_constants.py` and is applied
by `evaluate()` in `scripts/areas/resource_bottleneck/resource_bottleneck_diagnose.py`; a finding in the
report carries the rule id that produced it. If a reading cannot be attached to a
rule, it is printed as a measurement, not as a conclusion.

The rules exist because the tier's ticket corpus shows the same small set of
mistakes repeating: judging by peak instead of mean, blaming the process that was
observed blocked, trusting a cloud metric whose agent was not installed, and
recommending a spec upgrade for what was a memory-leak or an IO ceiling.

Two priors (`P1`, `P2`) sit alongside the rules. They are not conclusions about
the incident; they are statements about the machine's size that change how a
reading should be interpreted.

---

## R1 — Memory-driven chain

**Trigger.** Memory utilisation high, plus a paging signal (`kswapd` in guest
output, swap in/out active, `available` memory near zero), plus elevated disk
read/write BPS, plus CPU high.

**Conclusion.** Memory exhaustion — not compute demand — drives the freeze. The
dominant causal chain of this tier is:

```
memory exhausted -> kswapd0 paging -> disk IOPS/BPS pinned -> instance frozen
                 -> SSH / VNC / RDP unreachable -> human reboot is the only way out
```

**Do not** read the CPU figure as "the business needs more CPU" while R1 holds,
and do not propose a spec change as the diagnosis. The CPU reading is a symptom
of paging.

**Evidence.** Tickets T-B8B16499, T-D25A9845, T-3941829E. Supporting fields:
`memory_usedutilization` (percent) and `free -m` (absolute MiB) together,
`DiskReadBPS` / `DiskWriteBPS`, `CPUUtilization`, guest `kswapd` / OOM lines.
Percent alone is insufficient on a small instance: 90% of 2 GiB and 90% of 64 GiB
are different situations, which is what priors P1 and P2 exist to say out loud.

## R2 — Compute saturation

**Trigger.** CPU high while memory and IO are calm.

**Conclusion.** This is a compute-bound reading, and it is **incomplete**: the
cloud-side metric cannot name the eating process. Before any conclusion, the
process must be identified in-guest (`top -bn1`, or `ps aux --sort=-%cpu`, gated
per `references/resource-bottleneck__guest-commands.md`).

**Burstable note.** On a `t5`/`t6` family instance, 100% means the CPU **baseline
or credit exhaustion**, not "the instance has no headroom"; the reading and the
family are stated together, and credit balance is a declared gap
(`references/resource-bottleneck__metric-catalog.md`) rather than something inferred.

**Evidence.** Tickets T-1D5C74FB, T-1BBB1704, T-408C886A. Supporting fields:
`CPUUtilization` (mean and max together), instance type family, in-guest process
ranking.

## R3 — Load caliber

**Trigger.** Load average high while CPU utilisation is calm.

**Conclusion.** The load is being carried by tasks in `D` state / io-wait, not by
runnable compute. The correct next reading is `vmstat 1 3` (r and b columns) and
`iostat -x 1 3` (`%util`, `await`), then hand off on R4 if IO-bound.

**Known limitation.** No ratified CloudMonitor metric name exists for the load
family in this package's evidence set, so load is obtained from the guest, not
from the cloud. That is a declared gap; it is not silently skipped.

## R4 — IO co-saturation

**Trigger.** Disk BPS peaks coincide with CPU peaks — a timestamp where both
series are within `CO_PEAK_PROXIMITY_RATIO` of their own window peak.

**Conclusion.** The freeze pattern at the IO area. A process observed *blocked* at
that moment is the **victim** of IO pressure, not its cause: the classic error is
to name the hung process as the culprit (ticket T-BF2F77A0). Disk throughput
ceilings belong to the disk tier and are **escalated, never computed here**
(ticket T-CC0FA37F) — this skill reports the observed rate and the co-peak
timestamp, and hands the ceiling question to `area:resource-bottleneck`.

**Evidence.** Tickets T-CC0FA37F, T-1BBB1704, T-BF2F77A0. Supporting fields:
`DiskReadBPS` / `DiskWriteBPS` series, `CPUUtilization` series, `findmnt` for
device-to-mount attribution, `iostat -x 1 3` for per-device share.

## R5 — Negative conclusion

**Trigger.** Every evidenced area is calm over the window.

**Conclusion.** "It is not the resources" is a valid, reportable output. It ships
with a handoff direction chosen from `references/resource-bottleneck__escalation-map.md` — application
behaviour, network path, or an event log question — rather than with a shrug. A
negative on the evidenced areas is **not** a negative on the unevidenced ones; if a
gap exists (R6), say which question remains open.

**Evidence.** Tickets T-4C13A2DB, T-F5D78C4B.

## R6 — Missing metric / evidence gap

**Trigger.** A queried metric returned no datapoints, errored, or the reading
depends on an agent that is not installed (CloudMonitor agent for in-guest
memory, `sysstat` for `iostat`/`sar`, `atop` for historical replay).

**Conclusion.** State the gap, name the withheld conclusion, and name the
fallback that would close it. Never substitute a guessed value, and never read an
empty series as "0%" or as "normal".

**Evidence.** Tickets T-36BC7559, T-CC0FA37F. The full list of unratified metric
families lives in `GAPS_DECLARED` (`scripts/areas/resource_bottleneck/_constants.py`) and is printed in the
report, so a reader cannot mistake a gap for a measured zero.

## R7 — Caliber disputes

**Trigger.** Any quoted reading, always.

**Conclusion.** Host-view versus in-guest `cpu_total`, mean versus peak, percent
versus absolute, instance aggregate versus single-disk ceiling: each reading ships
with the caliber it was taken in. Tickets T-46B31B3D and T-3941829E show customer
and engineer reaching opposite conclusions from the same machine because only one
caliber was on the table, so `summarize_points()` always returns `avg` **and**
`mx` in one record.

On ARM (Yitian `*8y`-style) families, the host-view CPU metric carries
virtualisation accounting differences; the gap is stated **qualitatively** — no
overhead percentage is quoted, because none is evidenced in this package.

**Evidence.** Tickets T-6F5DD9E4, T-46B31B3D, T-3941829E.

## R8 — Identity / existence guard

**Trigger.** An instance, disk or region the customer named is not present in the
inventory the API returned; or the resource exists but belongs to a different
account than the credential's.

**Conclusion.** **Stop.** Report the existence mismatch. Do not continue the
diagnosis on a resource that was not returned, and do not describe a resource,
snapshot, agent or log that the calls did not show. Ticket T-50C39C59 is the
lesson: an answer that confidently referenced things which did not exist cost the
customer a wasted operation.

This rule also covers the `--check-auth-only` path: the account label derived from
`sts:GetCallerIdentity` is printed as `account:uid-****<last4>` so a report can be
traced to the account that produced it without disclosing credentials.

**Evidence.** Tickets T-3EA06F17, T-50C39C59.

## R9 — Quoted log / alarm string reading

**Trigger.** The customer pastes a kernel message, console alarm or error string.

**Conclusion.** Interpret by fixed caliber, never by the alarm's name alone:

| Quoted text | What it does mean | What it does **not** mean |
| --- | --- | --- |
| `blocked for more than <N> seconds` (hung task) | a task waited on IO past the hung-task limit | that this process caused the problem — it is the victim (R4; ticket T-BF2F77A0) |
| `Possible SYN flooding on port ...` | the kernel's half-connection queue was full at that moment | an attack, or a defect, by itself (ticket T-F5D78C4B) — judge with bandwidth and connection counts |
| disk read/write throttled alarm | the disk hit its throughput ceiling | "buy a bigger disk" as the first answer — check memory-driven paging (R1) and application IO shape first |
| `Killed process ... (out of memory)` / OOM killer | memory exhaustion reached process-kill level | the killed process was the leak — confirm which allocation drained memory before recommending anything |

The exact strings the parser looks for are in
`guest_evidence.py::parse_guest_findings` (`G-KSWAPD`, `G-OOM`, `G-BLOCKED`,
`G-SYN`, `G-LOAD`, `G-TOP`); the interpretation table is
`references/resource-bottleneck__log-signatures.md`.

**Evidence.** Tickets T-BF2F77A0, T-F5D78C4B.

---

## Spec priors (P1, P2)

Not rules about the incident — statements about the machine that change how a
reading must be read.

- **P1** — memory at or below `SMALL_SPEC_MEM_MIB` (4096 MiB): the spec leaves
  little room for the OS plus the workload; paging pressure at a modest-looking
  percentage is expected, and that must be said before any "abnormal" language.
  At or below `TINY_SPEC_MEM_MIB` (2048 MiB) the prior is stronger and is reported
  as `high`.
- **P2** — small-spec / burstable shape: report the family and its semantics
  (baseline, credit) alongside the number, without recommending a spec change.

## What no rule may do

No rule may produce: a spec or instance-type recommendation, a refund or pricing
statement, a claim about a resource the calls did not return, an executed
mutating action, or a conclusion whose supporting reading is absent from the
report. When the reading is absent, R6 applies and the conclusion is withheld.
