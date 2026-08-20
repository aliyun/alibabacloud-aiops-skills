# Java Memory Glossary

Use when narrating `memory javamem` findings to non-expert users. Each entry:
**definition → plain language → common mistake → what to check next**.

## Core memory regions

### Java Heap

- **Definition**: Memory for Java objects, managed by the JVM garbage collector.
- **Plain language**: "The part of JVM memory where your Java objects live."
- **Common mistake**: Assuming high process RSS always means heap leak.
- **Next**: If heap dominates findings (`javamem.heap`), consider heap dump / ATP—not another javamem snapshot.

### Non-heap (Metaspace, CodeCache, DirectBuffer)

- **Definition**: JVM memory outside the object heap but still JVM-accounted.
- **Plain language**: "Class metadata, JIT code, and direct buffers—still 'JVM inside' but not regular objects."
- **Common mistake**: Confusing Metaspace growth with native JNI leak.
- **Next**: Read `javamem.nonheap` detail; Metaspace vs DirectBuffer need different remediation.

### JNI/Other

- **Definition**: Process-resident memory attributed to native/off-heap usage outside classic heap accounting—often JNI libraries, thread stacks, other native buffers.
- **Plain language**: "Memory the OS sees in the Java process that is **not** mainly your Java object heap—often native libraries or off-heap buffers."
- **Common mistake**: Calling it "heap leak" or "GC problem."
- **Next**: Profiling (`--duration`, minutes) for **incremental** allocation paths, or NMT after restart for **resident** breakdown.

### RSS vs JVM gap

- **Definition**: Process RSS (OS view) minus JVM-reported used memory.
- **Plain language**: "The OS thinks the process uses more RAM than the JVM's own ledger explains—something is outside normal JVM heap/non-heap reporting."
- **Common mistake**: Ignoring the gap and only talking about heap usage percentage.
- **Next**: Split the gap using `javamem.rss_gap` detail (JNI/Other, heap gap, glibc); follow dominant line item.

### Heap gap

- **Definition**: Difference between OS-seen heap-related RSS and JVM heap `used`.
- **Plain language**: "Small differences between how the OS and JVM count heap pages—often normal padding/accounting."
- **Common mistake**: Treating a ~10 MB heap gap as the main cause when JNI/Other is multi-GB.
- **Next**: Only emphasize if it dominates the RSS−JVM split.

### glibc resident / fragmentation

- **Definition**: Estimated memory retained by the C library allocator (arena cache, fragmentation) not returned to the OS.
- **Plain language**: "Leftover pages from the C memory allocator—sometimes tens of MB, rarely the main story when native is multi-GB."
- **Common mistake**: Blaming glibc for a 3+ GB RSS when glibc line is only a few MB.
- **Next**: If `javamem.glibc_fragmentation` warns, discuss allocator tuning in a change window—not emergency cache drops.

## Diagnostic tools (not the same thing)

### Profiling (`--duration N`)

- **Definition**: Minutes-long sampling of **new** native/heap allocations; returns Top stacks in `javamem.profiling`.
- **Plain language**: "Watch **new** memory allocations for N minutes to see **which code paths** are allocating."
- **Common mistake**: Treating `--duration 5` as five **seconds**; expecting Top stacks when memory is already fully resident with no new alloc.
- **Next**: Read `profiling-playbook.md`.

### NMT (NativeMemoryTracking)

- **Definition**: JVM flag `-XX:NativeMemoryTracking=summary|detail`; breaks down native regions after **restart**.
- **Plain language**: "Turn on JVM native memory accounting and restart—helps split thread/GC/compiler/native **already resident**."
- **Common mistake**: Offering NMT as the only fix when profiling was empty but snapshot already shows large JNI/Other.
- **Next**: Use when you need resident category split, not incremental call paths.

## Finding `category` quick reference

| category | Domain | Agent focus |
|----------|--------|-------------|
| `javamem.heap` | Java heap usage / GC pressure | Heap dump, ATP—not repeat javamem |
| `javamem.nonheap` | Metaspace, DirectBuffer, CodeCache | Class leak vs buffer leak |
| `javamem.native_memory` | JNI/Other, NMT other | Off-heap native; profiling or NMT |
| `javamem.rss_gap` | RSS − JVM split | Name dominant contributor in gap |
| `javamem.glibc_fragmentation` | glibc arena/frag | Allocator tuning; not primary if MB-scale |
| `javamem.profiling` | Top allocation/leak stacks | Narrate stacks; no flame UI needed |
| `data_quality` | Missing data or empty profiling | Do not claim "all clear"; see playbook |
| `analyzer_error` | Plugin failure | Say analysis incomplete for that domain |
