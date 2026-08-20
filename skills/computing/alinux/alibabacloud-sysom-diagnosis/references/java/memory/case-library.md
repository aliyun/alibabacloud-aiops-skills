# Java Memory Case Library

Structured examples for Agent narrative regression. Envelope fields are
summarized; numbers are illustrative of real patterns.

## Case template

Each case includes:

- **Context**: user symptom
- **Envelope summary**: key summary / findings / next_steps
- **Correct narrative**: what to tell a non-expert user
- **Incorrect narrative**: patterns to avoid

---

## Case A: High off-heap native, empty profiling (anti-pattern replay)

### Context

User: "Java process memory high on instance i-xxx."

Agent ran snapshot javamem, then user agreed to profiling.

### Snapshot envelope (summary)

- `summary`: "Java process 3307705 has memory issues"
- `findings`:
  - `javamem.native_memory`: JNI/Other usage high; NMT not enabled
  - `javamem.rss_gap`: RSS−JVM gap ~3.97 GB; split: heap gap ~10 MB, JNI/Other ~3.96 GB, glibc ~6 MB
- `next_steps`:
  - `command`: `sysom-osops memory javamem --pid 3307705 --duration 5`
  - reason: capture native allocation path

### Profiling envelope (summary)

- First attempt: **client timeout 180s** (no envelope)
- Second attempt: `ok: true`, `summary`: profiling did not get usable Top stacks
- `findings`: `data_quality` — no alloc/leak Top stacks parsed
- Optional: `job_id` present in backend evidence

### Correct narrative

> The Java process **3307705** is using about **3.96 GB** in **off-heap native
> memory (JNI/Other)**, not in the Java object heap (only ~10 MB heap accounting
> gap). The OS sees roughly **3.97 GB** more RSS than the JVM reports; that matches
> native/off-heap dominance. glibc retained memory is only ~6 MB—not the main cause.
>
> We ran **5-minute** profiling to find **new** allocation paths. It did not return
> Top stacks—this often happens when the memory is **already resident** and the
> process had **little new allocation** during the window. That does **not** cancel
> the snapshot conclusion: native memory is still high; we just lack the exact
> calling code path.
>
> Next options: re-sample profiling during **peak load** (one run, full wait), or
> enable **NMT** and restart to split native categories—not proof the problem went away.

### Incorrect narrative (avoid)

- Pasting a table of "JNI/Other / heap gap / glibc" without explanation
- Treating `--duration 5` as **5 seconds** and using 180s timeout
- **Re-running** profiling immediately after timeout
- Saying "profiling completed but no data → memory may be fine"
- Jumping to only "enable NMT / check JVM args" without retaining snapshot conclusion

### Regression checklist (Case A)

- [ ] Explained JNI/Other in plain language
- [ ] Named dominant magnitude (~3.96 GB native vs ~10 MB heap gap)
- [ ] Distinguished quiet profiling window vs "no problem"
- [ ] Did not re-run profiling on timeout without user consent
- [ ] Offered peak re-sample or NMT as structured options

---

## Case B: Snapshot → profiling with Top stacks (happy path)

### Context

User: Java RSS high; snapshot shows JNI/Other elevated; user agrees to profiling.

### Snapshot envelope (summary)

- `javamem.native_memory` warning; `next_steps` command with `--pid 1234 --duration 5`

### Agent before profiling

> Profiling will run for about **5 minutes** on PID **1234**, plus analysis time.
> Please expect roughly **8–10 minutes** total. I will run it once and wait.

Tool timeout: ≥ 600s (prefer 480–600s minimum for duration 5).

### Profiling envelope (summary)

- `summary`: native allocation hotspots located
- `findings`: `javamem.profiling` with nativealloc Top stacks and share percentages in `detail`

### Correct narrative

> Snapshot showed high off-heap native usage. Five-minute profiling found the
> hottest allocation path: **[top frames from detail]**, accounting for **[share]%**
> of sampled native allocations. Focus remediation on that component or JNI bridge
> in a change window. No need to repeat the same profiling command.

### Incorrect narrative (avoid)

- Asking user to open a flame graph UI when `detail` already has stacks
- Running `--duration 5` again after success
- Ignoring snapshot and only listing stacks without connecting to user's RSS symptom

### Regression checklist (Case B)

- [ ] User warned about ~5 minute wait before command
- [ ] Adequate tool timeout
- [ ] Single profiling run
- [ ] Narrated Top stack from `detail`
- [ ] No duplicate profiling

---

## Case C: Snapshot only — heap dominant

### Snapshot envelope (summary)

- `javamem.heap` warning: old gen high, GC pressure in `detail`
- No large JNI/Other in `rss_gap`

### Correct narrative

> Memory pressure is mainly in the **Java object heap**, not off-heap native.
> [Sizes from detail]. Next step is heap dump or object analysis—not native profiling.

### Incorrect narrative (avoid)

- Recommending `--duration` profiling for JNI when heap dominates

---

## Case D: Client timeout with no envelope

### Context

Profiling command started; tool times out at 180s; no JSON returned.

### Correct narrative

> The profiling command likely needs the full **5-minute** sampling window plus
> backend time; a **3-minute** client timeout is too short. The job may still be
> running. I should **not** start a duplicate profiling run automatically. We can
> wait longer with a proper timeout or check whether the first job completed.

### Incorrect narrative (avoid)

- Immediate identical re-run
- Declaring profiling unsupported without checking wait time

---

## Acceptance scenarios (P0)

Use these four scenarios to validate Skill + references:

1. **Snapshot only** (Case C-like or A snapshot phase): plain-language dominant region
2. **Empty Top + high JNI snapshot** (Case A): quiet window; snapshot stands
3. **Profiling with Top stacks** (Case B): narrate stacks; no repeat
4. **CLI timeout** (Case D): no auto retry; explain minutes vs seconds
