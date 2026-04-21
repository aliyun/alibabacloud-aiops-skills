# Agent Conventions (sysom-diagnosis)

This document was split out from `SKILL.md` and provides detailed agent behavior conventions. The main skill file keeps only core rules and index links.

## Execution Directory

- `./scripts/osops.sh` is a relative path and is only valid in the **skill root** (same level as `SKILL.md`).
- Recommended form: `cd <absolute skill root path> && ./scripts/osops.sh ...`.
- Commands in `agent.next.command` must also be executed with Bash in the skill root; do not switch to asking users to copy and run manually.

## Local First

- If users only describe generic symptoms like "high memory" or "OOM" and do not explicitly request remote diagnosis, run a local quick check first (choose subcommands via [memory-routing.md](./memory-routing.md)); do not request region/instance.
- If users explicitly request remote diagnosis, or `agent.next` already includes `--deep-diagnosis`, follow [invoke-diagnosis.md](./invoke-diagnosis.md) for local vs remote flow.

## Credentials and Security

- **Do not** collect AccessKey/Secret in chat.
- Guide users to run `./scripts/osops.sh configure` in their local terminal under the skill root, which writes to `~/.aliyun/config.json`.
- Without PTY: in COSH, enable "Interactive Shell (PTY)" via `/settings`, or enter an interactive Bash with `/bash`.

## Precheck Envelope Consumption

- Guide users to remediate in **order** based on `data.remediation` (standalone precheck) or `data.precheck_gate.remediation` (deep-diagnosis merged). If `primary_path` is locked, show only that path. For `configure_identity`, let users choose per `guidance.auth_path_choice`.
- If `data.precheck_gate` exists, treat it as authoritative and avoid repeating quick findings and precheck findings in full.

## Check and Usage Order

### A. Memory Domain

1. **Quick check**: choose local subcommands via [memory-routing.md](./memory-routing.md). Then read `agent.next`; key findings are in `agent.findings`.
2. **(Optional) `precheck`**: validate credentials and SysOM activation separately.
3. **Confirm target**: for current instance, do not pass `--region`/`--instance`; for other instances, users must provide region + instance-id.
4. **Deep diagnosis**: execute `agent.next.command`, or append `--deep-diagnosis`.
5. **Failure handling**: inspect `error`, `data` (including `remediation`, `precheck_gate`, etc.), and `agent.summary`.

### B. Non-Memory Domains (IO / Network / Load)

1. **Confirm current/other instance** (same as A) → run `./scripts/osops.sh <io|net|load> <subcommand> ...` (built-in environment check before invocation) → read `data.routing`/`data.remote` and `agent.findings`.
2. **Latency + socket queue backlog**: if `net netjitter`/`net packetdrop` has been run and results look normal, but `ss` shows high Send-Q/Recv-Q, cross-check with `memory memgraph --deep-diagnosis`. See [non-memory-routing.md](./non-memory-routing.md).
3. **Failure handling**: same as A.

## Boundary with Other Memory Skills

- This skill uses `./scripts/osops.sh` under `sysom-diagnosis/` (with `memory`/`io`/`net`/`load` support).
- Other skills or parent-repo entries may differ; for SysOM remote deep diagnosis, use the `osops` in this directory.
