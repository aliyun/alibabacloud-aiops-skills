# Profiling Hotspot Deep Interpretation

Use **after** snapshot + profiling envelopes are both available, especially when
`javamem.profiling` findings contain Top stacks. Pair with `glossary.md`.

Goal: **depth** = plain-language mechanism + calibrated conclusion—not stack
dumping, not default "memory leak" labels.

## Mandatory read order for final answer

1. Snapshot envelope → dominant region and **resident** magnitudes (GB/MB)
2. Profiling envelope → **incremental** Top stacks and event type
3. This guide → interpret stacks; separate app vs tool vs transient JIT
4. `case-library.md` Case E → shape check

## Do not default to "memory leak"

| Say this | Only when |
|----------|----------|
| **High native memory / elevated off-heap usage** | Snapshot shows large JNI/Other or RSS gap |
| **Allocation hotspots within sampling window** | Profiling Top stacks present |
| **Suspected leak** | `nativememleak` event dominates, or sustained growth evidence—not alloc-only |
| **Memory leak (confirmed)** | Repeated snapshots show monotonic RSS growth **and** leak stacks match business code paths—not JIT/profiler alone |

**Wrong:** Title "JNI/Native memory leak" when only `nativealloc` + JIT/profiler stacks exist.

## Profiling event types

| Event in envelope | Meaning | Agent emphasis |
|-------------------|---------|----------------|
| `nativealloc` | Allocations observed **during the window** | "Who allocated **while we watched**"—not always leak |
| `nativememleak` | Leak-suspect stacks (if present) | Stronger leak language; still explain stack in plain terms |
| `alloc` | Java heap allocations during window | Object allocation heat, not RSS gap by itself |

## Common stack patterns (plain language)

### C2 / JIT compiler + Arena::grow / malloc

- **What it is:** JVM optimizing hot Java methods; compiler uses temporary native
  **Arena** buffers while compiling. Often **releases after compile batch**.
- **Plain language:** "During sampling, the JVM was **compiling Java methods to
  native code** and temporarily asked the OS for native memory. This is common
  when many complex methods compile at once—not always a leak."
- **When to worry:** RSS stays high **after** compile traffic stops; constant
  recompilation (dynamic proxies, heavy reflection, bad code cache settings).
- **Do not:** Call it leak solely because Arena/malloc appears on stack.

### Profiler / agent dump (Profiler::dump, listThreads, JFR, async-profiler)

- **What it is:** **Diagnostic tool activity during the same window** as profiling.
- **Plain language:** "Part of what we captured is the **profiler itself** walking
  threads or dumping data—not your application's normal steady-state allocation."
- **Rule:** If a stack clearly names profiler/agent/JFR/dump paths, **label it
  as tool overhead** and **do not** rank it as the app's primary production issue.
- **Share %:** High share may **understate** app hotspots and **overstate** tool
  noise—say this explicitly.

### JNI / native library malloc

- **What it is:** Application or middleware calling native code (Netty, RocksDB,
  custom JNI, etc.).
- **Plain language:** "Your Java code (or a library it uses) called into **native
  code** that allocated memory outside the Java heap."
- **Next:** Map frames to known libraries; check if resident size grows over days.

## Five-part combined answer (snapshot + profiling)

Use this structure for non-expert users:

1. **What the user feels:** "Process **PID** uses about **X GB** more RAM than
   normal Java heap would explain."
2. **Term translation (one sentence each):** RSS gap; JNI/Other = off-heap native
   **already in the process**; profiling = **new allocations during N minutes**.
3. **Resident vs incremental:** "About **4 GB** is **already resident** (snapshot).
   During **5 minutes** of profiling, the hottest **new** allocations were …"
4. **Per-hotspot interpretation:** For each Top stack—**what it does in plain
   language**, app vs JIT vs profiler, leak vs transient.
5. **Calibrated conclusion + next step:** What is still unknown (NMT split?);
   what to do in change window; **avoid** kill/restart commands unless user asks.

**Forbidden:** Bullet list of frame names only; table of jargon without translation.

## Example (illustrative — JIT + profiler artifact)

**Snapshot:** JNI/Other ~4 GB; RSS−JVM ~4 GB; heap gap small; NMT off.

**Profiling:** 66% C2 Compile/Arena; 34% Profiler dump/listThreads.

**Good conclusion excerpt:**

> Most of the **4 GB** is **already sitting in off-heap native memory**, not Java
> objects. In the 5-minute sample, **new** allocations were dominated by (1) the
> JVM **C2 compiler** temporarily growing compiler buffers—often normal during
> heavy compilation, not proof of leak by itself—and (2) the **profiler agent**
> dumping thread info, which is **measurement overhead**, not your app's usual
> behavior. We still cannot split the 4 GB into thread stacks vs GC vs libraries
> without **NMT after restart**. Next: check if compilation storms are ongoing;
> if RSS stays high when load is flat, re-profile at peak or enable NMT.

**Bad conclusion excerpt:**

> Problem type: JNI memory leak. Top stacks: Compile::Code_Gen, Profiler::dump.
> Enable NMT.

## Checklist before sending javamem final answer

- [ ] Explained RSS gap and JNI/Other in plain language (not raw labels)
- [ ] Separated **resident GB** (snapshot) from **window hotspots** (profiling)
- [ ] Did not use "leak" unless `nativememleak` or strong growth evidence
- [ ] Identified profiler/tool stacks as diagnostic overhead when present
- [ ] Explained JIT/Arena as possibly transient, not automatic leak
- [ ] Stated what NMT would add vs what profiling already proved
- [ ] No stack-only dump; each hotspot has **so what for the user**
