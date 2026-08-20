# Javamem Envelope Interpretation Guide

Use after `sysom-osops memory javamem` returns an envelope. Pair with
`glossary.md` for term definitions.

## Read order

1. `ok` and `error` (if any)
2. `agent.summary`
3. `agent.findings[]` — sort by: `root_cause` category if present, then severity, then match to user symptom
   - **Snapshot findings analysed by java_agent use `root_cause` / `observation` / `config` as `category`.** Pick the primary cause from the `root_cause` entries; `config` entries are configuration risks (usually not the trigger), `observation` entries are supporting context.
   - Older/local-analyser envelopes instead use `javamem.{domain}` categories (`javamem.heap`, `javamem.rss_gap`, …) and encode strength in `severity` only. In that case pick the primary cause(s) by **`severity` high first + largest magnitude in `detail` + user-symptom match** — there may be more than one.
4. `agent.next_steps[]` — priority plan, not a checklist
5. `agent.session_id` (if present) — the multi-hop session handle; see "Multi-hop sessions"

Required entities (PID, sizes, mechanism) must appear in `summary` or
`findings[].detail`. Do not invent numbers.

## Presenting quantitative evidence

Every number you show the user must come from `summary` or `findings[].detail` —
those are the only fields carrying quantitative evidence. (There is no separate
structured `evidence` object in this envelope; do not look for one.)

When a `detail` states a metric, keep these three parts together in your answer:

1. **Magnitude with unit** — e.g. "Metaspace 85 MB". Convert bytes to MB/GB for
   readability, but never re-derive a number the envelope did not state.
2. **The stated ratio basis** — if `detail` says `used/max`, keep that framing.
   **If `detail` says there is no limit (`max = -1`, e.g. `-XX:MaxMetaspaceSize`
   not set), do not present any "usage percent" for that region** — report the
   absolute size plus "no configured ceiling" instead. `used` sitting close to
   the committed size is normal JVM behaviour, not a risk signal.
3. **What is missing** — if `detail` declares a premise as unknown (JDK version,
   thread count, cgroup limit, growth trend), repeat that caveat. A single
   snapshot cannot prove growth over time; do not upgrade a "suspicion" into a
   confirmed leak.

Present numbers inline in prose or a small table; do not dump raw field paths at
the user unless they ask where a number came from.

## Multi-hop sessions

Java diagnosis is session based: `agent.session_id` ties follow-up hops to the
same backend conversation, so the next hop can reference the previous hop's
evidence instead of re-collecting it.

- When `agent.session_id` is present, **carry it into the next java command**:
  append `--session-id <id>` (the backend also injects it into any
  `next_steps[].command` it generates, and injection is idempotent — never add
  it twice).
- This applies to follow-up questions too, not just to the commands listed in
  `next_steps`: if the user asks a new java-memory question about the same
  process, reuse the session id so context is preserved.
- Sessions are capped (4 hops) and expire; if the backend returns a new
  `session_id`, switch to it. If `session_id` is absent, simply omit the flag.
- Never invent or hand-edit a session id.

## Snapshot vs profiling envelopes

| Command shape | Backend path | Findings expected |
|---------------|--------------|-------------------|
| `javamem` (no `--duration`) | Snapshot: sysak `-g`, analysed by java_agent | `root_cause` / `observation` / `config` (legacy path: `javamem.heap`, `javamem.native_memory`, `javamem.rss_gap`, …) |
| `javamem --pid P --duration N` | Profiling only: Top-N stacks | `javamem.profiling` and/or `data_quality` |

Profiling envelope does **not** replace snapshot domain findings. If you only
have a profiling envelope, recall the **previous snapshot** when narrating.

> Snapshot data is now collected through `sysom-osops collect memory-javamem`
> (envelope mode). The user-readable entities still live in `summary` /
> `findings[].detail`; nothing changes in how you read them.

## Process-discovery envelope (no pid / no pod)

When the user asks for Java memory diagnosis **without** naming a pid or pod, the
backend first runs a lightweight discovery collector (`memory-javaproc`, a pure
`/proc` scan — no sysak) and returns a **candidate list** instead of a diagnosis:

- `agent.findings[]` are `info` (category `observation`), one per candidate,
  carrying `PID`, a command-line summary, `RSS`, and — when containerized —
  `pod` (`namespace/name`); otherwise `service`/`cgroup`.
- `agent.next_steps[]` are `info` options (one per candidate); the matching
  `sysom-osops memory javamem --pid <PID>` string is shown in the option's
  `reason` for the user to pick — it is **not** an auto-runnable command.
- If no Java process is found, a single `info` / `data_quality` finding says so
  and there are **no** `next_steps` (ask the user to confirm target or supply a pod).

Agent behavior:

1. **STOP and present the candidate list to the user** as a table that includes
   PID, command summary, RSS, and a **pod (`namespace/name`) column** for
   containerized candidates (fall back to service/cgroup for host processes) so
   container users can filter quickly — the `pod:` value is already in each
   finding's `detail`. The discovery `next_steps` are `info` options (no
   auto-runnable `command`) — **choices, not a to-do list**. Do **not** auto-run
   a diagnosis, **even if there is only one candidate**.
2. Let the **user pick** the target PID (largest RSS is listed first, but the
   user may want a specific service/pod). Only after the user chooses, run
   `sysom-osops memory javamem --pid <PID>` for that PID.
3. **Never invent a PID.** Only diagnose a PID that appears in the candidate list
   (or one the user explicitly provides).

## Three-part answer template (snapshot)

For each user-facing answer after snapshot:

1. **Dominant contributor**: Heap vs off-heap (JNI/Other) vs glibc—use magnitudes in `detail`.
2. **Scale**: PID and approximate GB/MB from envelope text.
3. **Evidence gap**: Missing allocation path? Missing NMT split? Point to `next_steps`.

**Do not** output findings as a jargon table without translation.

### Example shape (illustrative)

> Process **3307705** uses most of its RAM in **off-heap native memory (~3.96 GB)**,
> not the Java object heap (heap accounting gap ~10 MB). The OS sees ~3.97 GB more
> RSS than the JVM ledger explains; **JNI/Other** is the main part of that gap.
> glibc retained memory is only ~6 MB—not the primary cause. We still lack the
> **specific native allocation call path**; profiling during load can fill that gap.

## By `category`

### `javamem.heap`

- Focus: heap utilization, young/old gen, GC hints in `detail`.
- User message: "Object heap pressure" vs "native" if both present—state which dominates.
- Follow-up: heap dump / ATP per `next_steps`; not another snapshot javamem.

### `javamem.nonheap`

- Focus: Metaspace, DirectBuffer, CodeCache in `detail`.
- Distinguish class/metadata growth vs direct buffer leak suspicion.

### `javamem.native_memory`

- Focus: JNI/Other or NMT-other high usage.
- Always translate JNI/Other (see glossary).
- If NMT disabled in `detail`, say native **categories** cannot be split further without restart.

### `javamem.rss_gap`

- Focus: RSS − JVM total and split lines (heap gap, JNI/Other, glibc, NMT other).
- Identify **largest line item** before recommending actions.
- Small heap gap + large JNI/Other → narrative centers on native, not heap.

### `javamem.glibc_fragmentation`

- Focus: arena/fragmentation mechanism in `detail`.
- Only treat as primary if magnitude supports it (usually not when JNI/Other is GB-scale).

### `javamem.profiling` (profiling hop only)

- Focus: Top stacks in `detail` (share % and reversed frame list).
- Explain what the top frame **means** operationally (e.g. JNI bridge, allocator).
- Do not request flame UI.

### `data_quality`

- Snapshot: missing fields → "this dimension unavailable," not "normal."
- Profiling: empty Top stacks → read `profiling-playbook.md`; **preserve snapshot conclusion**.

## Profiling-only envelope with no prior snapshot in thread

If the user jumped straight to `--duration` without snapshot:

- Answer from profiling findings only for **incremental** path.
- Note that **resident** breakdown may still need a prior or follow-up snapshot.

## `next_steps` kinds

| kind | Agent action |
|------|--------------|
| `command` | Run exact CLI string when user agrees and entity gap remains |
| `info` | Explain in prose; no automatic extra command |

In a **process-discovery** envelope the candidate `next_steps` are `info`
options (choices for the user to pick). **Never auto-run them**; wait for the
user to select a PID, even when only one candidate is listed.

When `command` includes `--duration`, read `profiling-playbook.md` **before** executing.
