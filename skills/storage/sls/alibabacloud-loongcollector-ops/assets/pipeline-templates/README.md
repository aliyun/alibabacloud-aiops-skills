# Pipeline templates

Native-first, minimal-viable Logtail pipeline configs. Source:
`loongcollector-oncall/knowledge/base/collection-config/recipes.md` (template library §2).

| File | Scenario | input |
|---|---|---|
| `host_file.json` | Host / ECS file log (JSON body) | `input_file` |
| `docker_stdio.json` | Pure Docker stdout/stderr | `input_container_stdio` |
| `k8s_stdio.json` | K8s DaemonSet stdout, filtered | `input_container_stdio` |
| `host_agentsight.json` | Agentloop host eBPF AgentSight (empty ProbeConfig default) | `input_agentsight` |
| `host_agentsight_probe_mask.json` | Same names, probe lists + masking example | `input_agentsight` |

`host_agentsight` names are product-fixed (`runtime-ebpf-agentsight-config` → `ebpf-event`). Existing config is lock-and-skip, never overwrite. Details: `references/agentsight-agentloop.md`.

## Usage

1. Copy the template that matches the classified scenario (`references/scenario-matrix.yaml`).
2. Replace every `<...>` placeholder. Keys prefixed with `_` are annotations only — strip them before sending to the CLI.
3. Resolve the collector version first, then confirm the plugin set against `references/plugin-version-gates.yaml` (native requires collector `>=3.x`; `1.x/2.x` are gated).
4. Render + validate:
   ```bash
   SKILL_SESSION_ID=$SID python3 scripts/render_pipeline.py --input task.json > rendered.json
   SKILL_SESSION_ID=$SID python3 scripts/validate_pipeline.py --file rendered.json --collector-version <v>
   ```
5. If processors add/rename fields, emit the index update diff in the SAME batch (`references/index-coupling.md`), `--cli-dry-run`, get approval, then apply.

File-log templates use native processors only (never mix native + extended). `host_agentsight` default has no processors; the mask variant uses `processor_spl` alone (cannot mix with native/extended).
