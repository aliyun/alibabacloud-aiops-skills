---
name: alibabacloud-sysom-diagnosis
description: >
  Use when troubleshooting Linux server performance or stability issues —
  CPU saturation, high load, scheduling delay, memory pressure, OOM events,
  high RSS, page cache / shared memory growth, memory cgroup residue, Java
  heap issues, disk IO saturation or latency, packet loss, network jitter,
  or a server that is slow, stuck, or unstable. Performs diagnosis and
  surfaces recommendations; does not apply fixes automatically.
license: Apache-2.0
compatibility: >
  Requires sysom-osops CLI. Remote diagnosis requires Alibaba Cloud credentials
  through AK/SK or an ECS RAM Role, an online Cloud Assistant on the target ECS,
  and a supported China Mainland or Hong Kong region.
metadata:
  domain: aiops
  product: sysom
  supported_domains:
    - cpu
    - io
    - memory
    - network
    - java
  owner: sysom-team
  contact: sysom-team@alibaba-inc.com
allowed-tools: Bash Read
---

# alibabacloud-sysom-diagnosis

Use SysOM CLI and backend envelopes as the diagnosis source of truth. This Skill
replaces the older SysOM diagnosis Skill and is the single entry point for SysOM
ECS performance and stability diagnosis.

## Immediate Route

When the user reports a symptom and has not provided fresh SysOM envelope output,
run the matching SysOM command from **Domain Routing** below before ad hoc Linux
inspection or manual probing. Then follow the returned `agent.summary`,
`agent.findings[].detail/category`, and `agent.next_steps[]`. Raw Linux commands
are bounded fallbacks only when a SysOM command is unavailable, outputs
contradict each other, or a required entity remains missing after the focused
SysOM command.

## Credential Security

Never print, echo, or ask for AccessKey ID or AccessKey Secret values. Remote
commands perform their own authentication checks. If a command returns an
authentication or permission error, explain the error and point the user to
`references/ram-policies.md`; credential setup must happen outside the
conversation.

## CLI Setup

Check whether the CLI is available:

```bash
command -v sysom-osops
```

If it is missing, install it:

```bash
curl -fsSL --connect-timeout 1000 https://sysom-prd-cn-hangzhou.oss-cn-hangzhou.aliyuncs.com/sysom_prd/skill_cli/install.sh | sudo bash
```

Then verify only the binary:

```bash
command -v sysom-osops
```

## Core Workflow

1. Classify the user's symptom into one SysOM domain: memory, IO, load/CPU,
   network, or Java (GC/memory/CPU).
2. Run the smallest SysOM command that matches that domain. Prefer a local
   memory classify for unclear memory symptoms; for other domains, use the
   matching documented remote action.
3. Read only the default envelope fields: `ok`, `error`, `command`, and
   `agent`.
4. **Load domain references before building the answer.** This step is mandatory
   and must not be skipped even when `agent.findings` and `agent.next_steps`
   appear complete. Which references to load depends on the domain:
   - Java (any type: gc/memory/cpu) → read `references/java/README.md` first
     for symptom routing and parameter validation; then by type:
     - gc: `references/java/gc/gc-guide.md`
     - memory: `references/java/memory/memory-guide.md` (then glossary, envelope
       guide, profiling playbook, decision tree under `references/java/memory/`)
     - cpu: `references/java/cpu/cpu-guide.md`
   - Other domains → load the matching reference from the References table below.
   References add interpretation rules, entity definitions, and answer-shaping
   guidance that the envelope alone does not convey. Do not infer Java terms,
   native memory categories, or profiling semantics from raw envelope text.
5. Relay the hop as visible progress: present `agent.summary` (plus key
   findings) to the user, interpreted through the reference material loaded in
   step 4. Keep evidence qualifiers that change interpretation, including
   currentness, unavailable direct signals, fallback evidence, and remediation
   preconditions.
6. Branch on `agent.status`:
   - `concluded` (or missing/unrecognized) → build the final answer from
     `agent.summary`, `agent.findings[].detail/category`, and
     `agent.next_steps[]`, then stop the loop.
   - `in_progress` → the backend is requesting another collection hop: take
     the `kind=command` entry from `agent.next_steps[]`, apply the
     confirmation rules below, run it, and feed the new envelope back into
     step 4.

**Guided-diagnosis loop hard rules** (Java multi-hop sessions):

- Pace ownership: never skip `agent.next_steps[]` to decide collection on
  your own, and never run diagnostic commands outside the envelope.
- Run commands **exactly as shown** — the gateway has already injected
  `--session-id`; never rewrite, add, or remove flags. If a command fails,
  relay the error envelope as-is instead of retrying with tweaked parameters.
- Hop limit: stop the loop after 4 hops in the same session even if the
  backend still says `in_progress`; present the conclusions so far and state
  the evidence limits (the backend force-concludes at the same ceiling —
  double safety).
- User refusal: if the user declines a proposed command, stop the loop,
  summarize from the evidence already collected, and state explicitly which
  conclusions remain unconfirmed because that hop was not run.

**Before executing a profiling or long-running follow-up command** (e.g.,
`java analyze --type memory --duration N`, any command that injects an agent
into the target process, or any command expected to run for multiple minutes):
- Tell the user what the command does, how long it takes, and what performance
  impact it may have on the target process (e.g., CPU overhead from sampling,
  extra memory from the injected agent, potential safepoint pauses).
- Ask the user whether to proceed. Do not run the command until the user
  confirms, or until the user has previously given a standing instruction to
  auto-run follow-ups.
- Once the command starts, tell the user the expected wait time and keep them
  informed if the operation is still in progress.

Read-only query commands (e.g. `java analyze --type cpu`) do not apply here —
see each domain guide's Execution Model for specifics.

When classify returns a command in `agent.next_steps[]` and no root-cause
finding already contains enough evidence to answer, run the first command next.
Do not replace an Agent-visible SysOM next step with manual shell probing. Raw
Linux checks are bounded fallbacks after the SysOM next step succeeds, fails, or
times out.

Use the documented commands exactly as shown by default. Do not add raw,
debug, or backend evidence expansion flags unless the user explicitly asks for
that view.

Final answers should name evidence, root cause, owner/scope, and operational
action targets. Do not add shell snippets for verification or remediation unless
the user explicitly asks for commands. Prefer phrases such as "review dependency
and disable or upgrade the leaking component in a change window" over raw module,
cgroup, sysctl, cache-drop, or process-kill commands.
Do not include command-looking inline snippets such as module inspection/removal,
memory summary commands, cgroup file writes, cache-drop controls, sysctl changes,
or process-kill commands as default final-answer steps.

The `agent` view must be self-contained for diagnosis. Structured evidence is a
backend/UI view and must not be treated as the default Agent source for required
entities.

## Domain Routing

| User symptom | First route |
|--------------|-------------|
| Unclear memory issue, OOM, high RSS, file cache, shmem/tmpfs, memory cgroup, socket memory, kernel memory | `sysom-osops memory classify` |
| Java issue (symptom unclear) | Follow the Symptom Triage rules in `references/java/README.md` — ask the user about the symptom, then route to the matching type |
| Java GC pause / frequent GC / low GC throughput | `sysom-osops java analyze --type gc` |
| Java heap / OOM / heap leak / native leak | `sysom-osops java analyze --type memory` — without a pid/pod it returns a candidate list; STOP and wait for the user to choose before retrying |
| Java CPU hotspot / high thread CPU / flame graph | `sysom-osops java analyze --type cpu --pid <PID>` |
| Slow disk, high iowait, disk latency, blocked IO | `sysom-osops io iofsstat`, then `io iodiagnose` if the overview points to slow IO |
| High load, runqueue backlog, task stuck waiting for CPU | `sysom-osops load loadtask` or `load delay` based on the visible symptom |
| Packet loss, retransmits, network timeout, jitter | `sysom-osops net packetdrop` for loss/drop symptoms; `net netjitter` for latency fluctuation |

For command parameters, read `references/deep-actions.md` and
`references/parameter-guide.md`. For OS and region support, read
`references/supported-environments.md`. These references are Skill material; do
not use remote target file tools to open `.claude/skills` paths on the diagnosed
host.
For Java symptom-to-type routing, consult `references/java/README.md`.

## Memory Routing

Memory follows the same Core Workflow and Follow-up Rules as every domain: start
from `sysom-osops memory classify`, then pick the next action from visible output
or `agent.next_steps[]`. For choosing among memory deep actions or checking which
entity is still missing, load `references/memory-triage.md` (parallel to
`references/non-memory-triage.md` for other domains).

Note: Java-related memory symptoms (OOM in Java process, heap leak, native leak)
route to Java domain via `sysom-osops java analyze --type memory`, not through
memory classify. See Domain Routing table above.

Choose the next memory action from visible SysOM output. Do not infer a memory mechanism from symptom wording alone.

## Envelope Contract

Default command output is the Agent contract:

```json
{
  "ok": true,
  "command": "sysom-osops memory classify",
  "agent": {
    "status": "concluded",
    "session_id": "a1b2c3d4e5f6",
    "summary": "Concise diagnosis summary.",
    "findings": [
      {
        "severity": "high",
        "title": "Short finding title",
        "detail": "Root cause, key entities, and evidence summary.",
        "category": "root_cause"
      }
    ],
    "next_steps": [
      {
        "kind": "command",
        "label": "Run focused deep diagnosis",
        "command": "sysom-osops memory oom",
        "reason": "The missing entity this command can fill."
      }
    ]
  }
}
```

`agent.findings[]` may contain only `severity`, `title`, `detail`, and
`category`. Required entities such as PID, cgroup, service, file path, OOM
victim, limit/current, residue, holder, or cleanup target must be written in
`agent.summary` or `agent.findings[].detail`.

Field semantics for guided diagnosis sessions:

- `agent.status`: `in_progress` means the backend diagnosis agent requests
  another collection hop; `concluded` means diagnosis has converged. Treat a
  missing or unrecognized value as `concluded`. Legacy collector-level states
  (`success`, `warning`, ...) may still appear on non-Java actions; interpret
  them as before.
- `agent.session_id`: backend-generated multi-hop session identifier. Never
  generate or modify it; the gateway already injects it into `command`
  strings, so run them verbatim.
- `agent.next_steps[].kind`: `command` = backend-requested collection command
  (subject to the confirmation rules above); `info` = user-side suggestion —
  present it but never auto-run; `warning` = evidence or data-quality caveat.

## Follow-up Rules

- Prefer `category=root_cause`, then highest severity, then the finding that
  best matches the user's reported symptom.
- Treat `root_cause` as stop-ready when visible `detail` contains the entities
  needed to explain the symptom and a safe next action.
- Treat `agent.next_steps[]` as a priority plan, not a checklist.
- Run another SysOM command only when it can fill a named missing entity or
  change remediation.
- For long-running Java collection commands — `java analyze --type memory
  --duration N` (profiling; legacy `memory javamem --duration N`) and `java
  analyze --type gc` in `collect` mode (5–10 min JFR/GC collection) — the wait is
  minutes-scale: tell the user, size the tool timeout accordingly, and never
  re-fire the same command on client timeout. See
  `references/java/memory/profiling-playbook.md` (memory) and
  `references/java/gc/gc-guide.md` (gc).
- Preserve visible qualifiers that affect interpretation, such as current versus
  historical evidence, unavailable direct signals, fallback evidence used to
  close currentness, and safety preconditions for remediation.
- When a finding uses fallback evidence because a direct signal is unavailable,
  state both parts in the final answer. Do not reduce the conclusion to the
  fallback metric alone.
- After a focused SysOM command closes a root cause, answer from it. Do not run
  extra commands to make the report comprehensive, and do not chase earlier
  classify anomalies or observations unless they share the same entity and
  expose a named evidence gap.
- Do not call backend-only collectors or private helper commands directly.
- Do not re-check a PID, cgroup, file, limit, or event that SysOM already named
  in `summary` or `detail`.
- After a SysOM deep command returns `category=root_cause` with the required
  entities visible, answer from that envelope. Raw Linux checks are only for
  contradictions, command errors, or a clearly missing entity.
- In the final answer, do not turn already-closed entities into extra raw Linux
  verification commands. Express remediation as dependency-aware action targets
  and change-window plans unless the envelope itself provides an executable safe
  next step.
- Avoid executable shell snippets in the final answer. If a command is useful
  only for post-change verification, name the SysOM check or metric to re-run
  instead of raw Linux commands.
- This includes inline command names for module inspection/removal, memory
  summary commands, cgroup file writes, cache-drop controls, sysctl changes, and
  process-kill actions; describe the dependency gate and operational action
  target in prose.
- Pivot across domains when the current envelope does not explain the reported
  symptom and another SysOM domain names a stronger root cause.
- During diagnosis, do not execute remediation commands that change target
  state, such as killing processes, removing files, changing sysctl values, or
  writing to cache-drop controls. Present those as recommendations unless the
  user explicitly asks you to perform the repair.
- For non-memory findings, keep the same rule: one focused deep command, then
  answer when the required entities are visible.

## Error Handling

| `error.code` | Action |
|--------------|--------|
| `Sysom.TargetRequired` | Ask for instance ID and region, or explain ECS metadata auto-detection requirements |
| `Sysom.FallbackClassify` | Present the local classify result and continue only if a focused next step is available |
| `Sysom.PermissionDenied` | Use `references/ram-policies.md` to explain required RAM permissions |
| `Sysom.AuthenticationFailure` | Ask the user to configure credentials outside this session |
| `Sysom.InvalidParameter` | Ask the user to correct the instance, region, or command parameter |
| `Sysom.DiagnosisVersionNotSupported` | Explain that the target instance diagnosis components need an update |
| `Sysom.DiagnosisJsonParseFailed` | Retry once only when the user still needs the same evidence |
| `Sysom.PollError` | Retry the same focused action once when the missing evidence is still required |

## References

| Reference | Use when |
|-----------|----------|
| `references/classify-output-guide.md` | Reading local memory classify output |
| `references/memory-triage.md` | Choosing a memory deep action or checking memory entity completeness |
| `references/non-memory-triage.md` | Routing IO, load/CPU, network diagnosis |
| `references/deep-actions.md` | Looking up SysOM commands by domain |
| `references/parameter-guide.md` | Validating command parameters |
| `references/report-interpretation.md` | Interpreting envelope fields and answer shape |
| `references/ram-policies.md` | Explaining RAM permissions |
| `references/supported-environments.md` | Checking OS, architecture, and region support |

### Java Analysis References

| Reference | Use when |
|-----------|----------|
| `references/java/README.md` | **Primary Java entry point**: symptom triage, parameter guide, sub-domain index |
| `references/java/gc/gc-guide.md` | Running or interpreting `--type gc` results |
| `references/java/cpu/cpu-guide.md` | Running or interpreting `--type cpu` results |
| `references/java/memory/memory-guide.md` | `--type memory` interpretation and discovery-first flow entry |
| `references/java/memory/glossary.md` | Java memory terminology |
| `references/java/memory/javamem-envelope-guide.md` | Interpreting `--type memory` envelope structure |
| `references/java/memory/profiling-playbook.md` | Preparation and expected behavior before `--duration` collection |
| `references/java/memory/decision-tree.md` | Following backend `next_steps` in Java multi-hop sessions |
| `references/java/memory/case-library.md` | Case library and anti-patterns |
