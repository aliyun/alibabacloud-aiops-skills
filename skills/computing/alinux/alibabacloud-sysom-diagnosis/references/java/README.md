# Java Application Diagnosis Reference

Unified command for all Java diagnostics:

```
sysom-osops java analyze --type <gc|memory|cpu>
```

This document is the entry point for Java application diagnosis —
covering symptom triage, sub-domain guides, parameter quick-reference,
and combined-diagnosis strategies. Each sub-domain (gc / memory / cpu)
has its own folder under `references/java/`.

---

## Symptom Triage

### When the user's intent is unclear

If the user describes a vague Java problem (e.g., "is my Java process healthy",
"something seems wrong with my app") without mentioning specific symptoms from
the table below, ask **one** clarifying question:

> What is the primary symptom you are observing?
> 1. Application response is slow or has intermittent pauses
> 2. CPU usage is abnormally high
> 3. Memory keeps growing or OOM has occurred

Then route based on the answer:
- 1 → `--type gc` (latency-related symptoms are most often GC-induced)
- 2 → `--type cpu`
- 3 → `--type memory`

### Symptom → Diagnosis Type Mapping

When the symptom is already clear, route directly:

| Symptom | Recommended type | Description |
|---------|-----------------|-------------|
| Long GC pause / STW jitter | gc | Analyze GC event time-series and pause distribution |
| Frequent Full GC / old generation full | gc | Detect memory pressure source and promotion patterns |
| Low GC throughput / high application pause ratio | gc | Evaluate GC algorithm efficiency and tuning recommendations |
| OOM / sustained heap growth | memory | Deep diagnosis of heap/non-heap leaks |
| Native memory leak | memory | Analyze JNI/DirectBuffer usage |
| High thread CPU usage | cpu | Flame graph to locate hotspot method stacks |
| Slow application response (non-GC cause) | cpu | Analyze on-CPU time distribution |

---

## Sub-Domain Reference Index

| type | Folder / entry guide | Scope |
|------|----------------------|-------|
| gc | [gc/gc-guide.md](gc/gc-guide.md) | GC pauses, throughput, heap trend analysis |
| memory | [memory/memory-guide.md](memory/memory-guide.md) (+ `glossary`, `javamem-envelope-guide`, `decision-tree`, `profiling-playbook`, `profiling-interpretation`, `case-library` in `memory/`) | Heap/non-heap diagnosis, snapshots, allocation profiling |
| cpu | [cpu/cpu-guide.md](cpu/cpu-guide.md) | Flame graph, hotspot method stacks, on-CPU analysis |

---

## Parameter Quick-Reference

| Parameter | gc | memory | cpu |
|-----------|:---:|:------:|:---:|
| --pid | Optional | Optional | Optional (omit to get candidate list) |
| --duration | Seconds (default 60) | Minutes (0=snapshot) | N/A |
| --pod | Optional (container scenarios) | Optional | Not supported |

---

## Combined Diagnosis

When a single type cannot locate the root cause, combine multiple types:

1. **GC causing high CPU**: First `--type gc` to confirm GC frequency, then `--type cpu` to check GC thread proportion
2. **Memory leak causing frequent GC**: First `--type gc` to observe Full GC patterns, then `--type memory` for deeper heap analysis
3. **Heavy object allocation found in CPU hotspots**: First `--type cpu` to locate allocation hotspots, then `--type memory --duration 5` to track allocation trends

---

## Prerequisites

- `--type cpu` requires the instance to be managed in the Alibaba Cloud Linux console (the system auto-detects and provides guidance)

---

For memory-specific interpretation, the discovery-first flow, and answer
discipline, see [memory/memory-guide.md](memory/memory-guide.md).
