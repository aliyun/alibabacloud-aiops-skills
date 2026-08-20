<!--
 * @Descripttion: 
 * @version: 
 * @Author: Jietao Xiao
 * @Date: 2026-07-16 12:12:42
 * @LastEditors: Jietao Xiao
 * @LastEditTime: 2026-07-17 11:05:03
-->
# CPU Hotspot Analysis Guide

## Applicable Scenarios
- High thread CPU usage
- Slow application response (GC already ruled out)
- Flame graph needed to locate hotspot method stacks

## Command

`sysom-osops java analyze --type cpu --pid <PID>`

| Parameter | Description |
|-----------|-------------|
| --pid | Recommended — target Java process PID. If omitted, the call returns a Java process candidate list first |

> If you are unsure of the PID, run `--type cpu` **without**
> a pid directly — the CPU path performs Java process discovery itself and
> returns the candidate list. After the
> user picks a PID, re-run `--type cpu --pid <PID>` for the actual flame graph.

## Execution Model

`--type cpu` is a **read-only query** over profiling data that is **already being
collected continuously**. On-CPU profiling starts automatically once the instance
is managed in the console, and samples are stored server-side (the `prof_on`
dataset). The command retrieves roughly the **last 5 minutes** of already-collected
samples for the target PID and runs LLM analysis on them.

Because of this:
- It does **not** launch an on-demand perf run against the target, does **not**
  inject any agent, and adds **no measurable CPU overhead** to the process.
- It returns quickly (query + analysis) — there is **no ~60s sampling wait**.
- There is **no `--duration`** for cpu (see parameter table), and it does **not**
  need the pre-profiling overhead confirmation from the skill's general profiling
  guidance.

When confirming this action with the user, describe it as "view the last ~5
minutes of continuously-collected CPU flame graph data". Do **not** say it
performs ~60s perf sampling or imposes CPU load on the target — that describes
on-demand profiling (e.g. `--type memory --duration N`), not this path.

## Prerequisites

- **The instance must be managed in the Alibaba Cloud Linux console** (the system auto-detects; returns guidance when not managed)

## Result Interpretation

Returns flame graph LLM analysis conclusions:
- Hotspot method stacks and call chains
- On-CPU time proportion per method
- Potential performance bottleneck identification

### Common Patterns

| Pattern | Symptoms | Recommendation |
|---------|----------|----------------|
| Spin lock contention | Significant time spent on lock/CAS operations | Check concurrent data structure usage |
| Frequent object allocation | Hotspots concentrated on new/allocate paths | Combine with `--type memory` to analyze allocation trends |
| System call blocking | Hotspots on read/write/poll system calls | Check IO or network blocking |
| Serialization/deserialization | High proportion of JSON/Protobuf processing | Evaluate serialization strategy or data volume |

## Cross-Domain Diagnosis

- **Heavy object allocation found in CPU hotspots** → Combine with `--type memory --duration 5` to track allocation trends
- **Suspected GC threads consuming CPU** → First `--type gc` to confirm GC frequency and pause duration
- **High CPU but no obvious flame graph hotspot** → Likely an off-CPU issue (waiting on IO/locks); check IO domain
