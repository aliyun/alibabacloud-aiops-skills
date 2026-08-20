# Java Profiling Playbook

Use when `next_steps` or the user requests `memory javamem --pid P --duration N`,
or when a profiling envelope returns no Top stacks.

## Before starting profiling

### Duration unit

- `--duration N` means **N minutes**, not seconds.
- `--duration 5` ≈ five minutes of sampling **plus** backend parse/upload time.

### Tell the user first

Before running the command, say something like:

> Profiling needs about **N minutes** on the target Java process (plus a few
> minutes for upload and analysis). You can continue other work while it runs;
> I will wait for the full result before concluding.

### Tool timeout

Set the shell/tool timeout to at least **`(N + 3) × 60` seconds**; prefer
**`(N + 5) × 60`** for `--duration 5` → **8–10 minutes minimum**.

Do **not** use 120–180 second timeouts for `--duration 5`.

### Run once

- Launch **one** profiling command per PID and duration window.
- On **client timeout with no envelope**, do **not** auto-re-run the same
  `--pid --duration` command. Say the command may still be running; ask whether
  to wait longer or check task status—do not start a second concurrent sample.

## After profiling returns

### Success: `category=javamem.profiling`

- Read Top stacks from `findings[].detail` (nativealloc, nativememleak, alloc).
- Narrate call paths in plain language.
- Do not ask for a separate flame graph UI.
- If `next_steps` says not to repeat `--duration`, do not re-run profiling.

### Empty Top stacks: decision table

| Snapshot context | Profiling result | What to tell the user |
|------------------|------------------|------------------------|
| JNI/Other already high (e.g. multi-GB) | No Top stacks, no error | **Quiet window**: memory is largely **already resident**; profiling only sees **new** allocations. Snapshot conclusion **still holds**; allocation **path** unknown. |
| JNI/Other high | `data_quality` + error / timeout | **Collection failure**: fix PID/permissions/timeout; **one** retry later under load—not immediate duplicate run. |
| Snapshot mostly normal | No Top stacks | Possible no significant **incremental** allocation in window; do not over-claim. |

### Do not say

- "Profiling succeeded" when there are no Top stacks.
- "Memory is fine" or "problem ruled out" when snapshot showed high JNI/Other.
- "JVM does not support profiling" as the only explanation when quiet window fits.

## When profiling is empty but snapshot showed high JNI/Other

Preferred option order:

1. **Explain quiet window** and keep snapshot conclusion (dominant off-heap native).
2. **Re-sample during business peak** (one new `--duration` after user agrees and wait time explained).
3. **NMT after restart** for resident native **category** split (not call path).
4. Avoid defaulting to only "enable NMT" without acknowledging snapshot evidence.

## NMT vs profiling (reminder)

| Need | Tool |
|------|------|
| Which **code path** allocates during the window | Profiling `--duration` |
| How much is in thread/GC/compiler **after restart** | NMT + javamem snapshot |

## Client timeout handling

If the tool times out before any JSON envelope:

1. Tell the user profiling may still be running on the backend (5+ minutes expected).
2. Do **not** immediately re-fire the same command.
3. If the user still needs the result, suggest waiting or re-running **once** after confirming the prior job finished—not in parallel.
