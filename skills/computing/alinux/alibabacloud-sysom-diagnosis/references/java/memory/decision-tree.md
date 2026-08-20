# Javamem Follow-up: Following Backend next_steps

> **Role change**: this document no longer decides follow-ups. Diagnosis
> pacing — what to collect next, when to converge, and cross-domain pivots —
> is owned by the backend Java diagnosis agent and delivered through
> `envelope.agent.status` + `envelope.agent.next_steps[]`. This file only
> explains how to *follow* those instructions correctly.

## Entry: no pid → discovery first

If the user requests Java memory diagnosis **without** a pid or pod, the backend
returns a **process-discovery envelope** (candidate list), not a snapshot:

- **STOP and present the candidates as a table** with PID / cmdline / RSS and a **pod (`namespace/name`) column** for containerized candidates (fall back to service/cgroup for host procs) so container users can filter — the `pod:` value is already in each finding's `detail`. The discovery `next_steps` are `info` **options, not a run list**.
- **Do not auto-run any diagnosis — even with a single candidate.** Wait for the user to pick a PID, then run `sysom-osops java analyze --type memory --pid <PID>` (legacy `sysom-osops memory javamem --pid <PID>`).
- No Java process found → ask the user to confirm the target or supply a pod.
- **Never invent a PID.** See `javamem-envelope-guide.md` → "Process-discovery envelope".

Once you have a real **snapshot** envelope, follow the rules below.

## Following agent.next_steps (the only rule)

1. **Read `agent.status` first**:
   - `concluded` (or missing/unrecognized) → answer from `summary`/`findings`;
     the loop ends.
   - `in_progress` → the backend requests another collection hop; take the
     `kind=command` entry from `agent.next_steps[]`.
2. **Confirm before heavy hops**: profiling / long-running commands
   (`--duration N`, minutes) must be confirmed with the user first — see
   `profiling-playbook.md`. Read-only snapshot commands may run directly.
3. **Run the command exactly as shown** — the gateway has already injected
   `--session-id`. Never rewrite, add, or remove flags; if the command fails,
   relay the error envelope as-is.
4. **The command output is the next hop envelope** → go back to step 1.
5. **Hard limits**:
   - Max **4 hops** per session. If the backend still says `in_progress` at
     the ceiling, stop, present the conclusions so far, and state the
     evidence limits (the backend force-concludes at the same ceiling).
   - If the user declines a proposed command, stop the loop, summarize from
     the evidence already collected, and state explicitly which conclusions
     remain unconfirmed because that hop was not run.

## What moved where

- Heap / native / glibc branch decisions (profiling vs NMT vs heap dump) →
  made by the backend memory-domain skill; its rationale arrives in
  `findings[]` and the requested hop in `next_steps[].command`.
- Cross-domain pivots (memory ↔ gc ↔ cpu) → declared by the backend via
  `next_steps[].command`; this skill keeps no pivot rules of its own.
- Multi-hop evidence chaining → the backend quotes prior-hop evidence in
  later hops; relay those references verbatim when narrating progress.

## Pair with

- Terms: `glossary.md`
- Envelope reading: `javamem-envelope-guide.md`
- Profiling execution & timeouts: `profiling-playbook.md`
- Examples: `case-library.md`
