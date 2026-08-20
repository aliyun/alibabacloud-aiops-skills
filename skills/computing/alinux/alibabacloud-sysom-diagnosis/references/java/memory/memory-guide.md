# Java Memory Diagnosis Guide

Use this guide when running or interpreting `sysom-osops java analyze --type memory`
(equivalent to `sysom-osops memory javamem`).
Backend envelopes are the source of truth; these references teach how to
**translate, narrate, and decide follow-ups** for non-expert users.

## When to Read (mandatory)

| Trigger | Read |
|---------|------|
| About to run `--type memory` **without a pid/pod** (returns process-discovery candidates, not a diagnosis) | `javamem-envelope-guide.md` -> "Process-discovery envelope" |
| About to run or just ran `--type memory` (snapshot, no `--duration`) | `glossary.md` + `javamem-envelope-guide.md` |
| Envelope has `javamem.native_memory` or `javamem.rss_gap` | Above + `decision-tree.md` (how to follow backend `next_steps`) |
| `next_steps` recommends `--duration`, or user agrees to profiling | `profiling-playbook.md` (before starting the command) |
| Profiling envelope has `data_quality` or summary mentions missing Top stacks | `profiling-playbook.md` + `case-library.md` |
| Final answer is for a non-expert user | `case-library.md` (correct vs incorrect narrative) |

## No pid/pod -> discovery first

When the user asks for Java memory diagnosis **without** naming a pid or pod, the
first call returns a **process-discovery candidate list** (the backend runs a
lightweight `/proc` scan), not a diagnosis:

- **STOP and present the candidates as a table** with PID / cmdline / RSS and a **pod (`namespace/name`) column** when containerized (else service/cgroup), so container users can filter quickly — the `pod:` value is already in each finding's `detail`. The `next_steps` are `info` **choices, not commands to auto-run**.
- **Do not auto-run a diagnosis, even if there is only one candidate.** After the user picks a PID, run with `--pid <PID>` for the real snapshot.
- No Java process found -> ask the user to confirm the target or supply a pod.
- **Never invent a PID.** See `javamem-envelope-guide.md` -> "Process-discovery envelope".

## Two-hop model

1. **Snapshot** (`duration=0`, default): domain analysis (heap, native, glibc, RSS gap).
2. **Profiling** (`--duration N`, minutes): incremental allocation Top stacks only.

Do not treat profiling as a repeat snapshot. Do not re-run the same `--duration`
command on client timeout.

## Answer discipline

- **If you name a memory contributor, gloss it** — give a one-line plain-language
  explanation from `glossary.md` the **first time each term appears**, not only
  for the dominant one. This covers `JNI/Other`, `RSS gap`, `heap gap`,
  `glibc resident/fragmentation`, `Metaspace/non-heap`, and `NMT`. Never list a
  contributor as a bare number (e.g. "heap gap 21 MB", "glibc 7 MB") with no
  explanation — either gloss it briefly, or omit a negligible line entirely.
- Explain each term once, then conclude. Do not paste finding titles as a raw table.
- Numbers (PID, GB/MB) must come from envelope `summary` or `findings[].detail`.
- Follow `agent.next_steps[]` for commands; use these references for **why** and **how to say it**.

## Supporting References (this folder)

| File | Purpose |
|------|---------|
| `glossary.md` | Plain-language terms (JNI/Other, RSS gap, NMT, …) |
| `javamem-envelope-guide.md` | How to read snapshot/profiling envelopes by `category` |
| `profiling-playbook.md` | `--duration` wait time, timeouts, empty Top stacks |
| `profiling-interpretation.md` | Interpreting profiling Top stacks |
| `decision-tree.md` | Following backend `next_steps` in multi-hop sessions |
| `case-library.md` | Example envelopes and good/bad user-facing narratives |
