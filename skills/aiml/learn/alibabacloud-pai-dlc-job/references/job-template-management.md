# JobTemplate Management

A JobTemplate stores a complete `CreateJob` configuration as a versioned,
reusable template. A Job is launched via `create-job --template-id <id>`,
with non-locked fields overridable at launch time.

This document focuses on **what `--help` does not cover**: plugin gating,
multi-version semantics, Constraints language, JSONPath grammar, and design
patterns. For per-flag details run
`aliyun pai-dlc <create|get|list|update|set|delete>-job-template --help`.

## 1. Plugin Gating

All 6 JobTemplate subcommands require `aliyun-cli-pai-dlc` ≥ **0.3.1**.

```bash
aliyun pai-dlc create-job-template --help >/dev/null 2>&1 \
  || aliyun plugin update --name aliyun-cli-pai-dlc
```

> **Red line:** never fall back to ROA generic invocations
> (`--pathPattern` / `--method POST`) when the plugin is missing.

## 2. What a Template Captures

- **Content** — the full `CreateJob` payload as a JSON string
  (`JobType` / `JobSpecs` / `UserCommand` / `DataSources` / `CodeSource` /
  `Settings`, etc.).
- **Multi-version management** — every `update-job-template --content ...`
  creates a new version (`Version` auto-increments). One version is
  designated `DefaultVersion`.
- **Field constraints** — JSONPath-tagged rules that mark fields as
  `locked` / `overridable` / `required` (see §4).

## 3. CRUD Workflow Skeleton

The skeleton below shows the **flow** only; for parameter details consult
`--help`. All API calls require
`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job`.

```
[ create-job-template ]            # Version=1, DefaultVersion=1
        │
        ├──> [ list-job-templates ]            # workspace catalog
        ├──> [ get-job-template ]              # default version
        │       └─ --biz-version all          # full version history
        │
        ├──> [ update-job-template ]
        │      ├─ metadata only (no --content) → VersionCreated=false
        │      └─ with --content [+ --constraints] → new Version
        │              └─ --set-as-default true → promote new version
        │
        ├──> [ set-job-template-default-version --biz-version <N> ]
        │
        ├──> [ create-job --template-id <id> ]   # launch
        │       └─ template fields merged: locked wins, overridable can be replaced
        │
        └──> [ delete-job-template ]            # blocked while any job references it
```

> **`update-job-template` two modes** (per `--help`):
> - **Metadata-only** — pass `--description` / `--template-name` etc. without
>   `--content`. No new version (`VersionCreated=false`).
> - **New-version** — pass `--content` (and optionally `--constraints`,
>   `--set-as-default`). `--constraints` cannot be passed alone — it must
>   accompany `--content`.

> **Switching the default version** uses `set-job-template-default-version`,
> NOT `update-job-template --biz-version` (which is unsupported).

## 4. Constraints — Field-Level Rules

`--constraints` accepts a **JSON string with bash-escaped quotes**:

```bash
CONSTRAINTS='{\"JobSpecs[0].Image\":\"locked\",\"UserCommand\":\"required\"}'
```

The `\"` escaping is required because the value is parsed first by the shell
and then by JSON.

| Value | Behavior at `create-job --template-id` time |
|-------|---------------------------------------------|
| `locked` | Field is fixed; `create-job` arguments for this field are ignored. Template value wins. |
| `overridable` | Default. `create-job` arguments override the template value. |
| `required` | `create-job` MUST supply this field if the template doesn't. |

**JSONPath grammar:** dot-separated paths **without `$.` prefix** —
matches the server-side `pkg/utils/jsonpath/jsonpath.ParsePathSegment`
convention.

| Path example | Meaning |
|--------------|---------|
| `JobSpecs[0].Image` | The image of the first TaskSpec |
| `JobSpecs[0].EcsSpec` | Machine type of the first TaskSpec |
| `UserCommand` | Top-level startup command |
| `DataSources[0].MountPath` | First data-source mount point |

## 5. Design Recommendation

For shared team templates:

- **Lock the runtime stack** — `JobSpecs[N].Image`, `DataSources`,
  `Settings.EnableRDMA`, `Settings.EnableSanityCheck`.
- **Leave business knobs overridable** — `UserCommand`, `Envs`,
  `JobSpecs[N].PodCount`.
- **Mark inputs that must come from the consumer as `required`** —
  e.g. dataset paths that vary per experiment.

This keeps consumers focused on training-script parameters while the team
enforces the runtime contract.

## 6. `Content` is a JSON string

Per the OpenAPI contract, `Content` is typed `string`. Server stores it
verbatim; `get-job-template` returns `Versions[0].Content` as a JSON string
with outer quotes (e.g. `"{\"JobType\":\"PyTorchJob\",...}"`). To inspect
inner fields, parse with `jq` (`echo "$content" | jq .`) or equivalent.
`create-job --template-id` consumes the template directly — no manual
parsing needed.

## 7. Common Pitfalls

- ❌ `--content` not valid JSON / missing `JobType` / `JobSpecs` →
  `InvalidParameter.Content`. Test with `create-job --cli-dry-run`.
- ❌ `--constraints` value uses unescaped quotes (`{"Field":"value"}`) — shell
  eats the quotes. Always use `{\"Field\":\"value\"}` inside a single-quoted
  shell string.
- ❌ `--biz-version` on `update-job-template` to switch the operating version
  → unsupported. Use `set-job-template-default-version`.
- ❌ `Content.JobSpecs[].Image` not present in the latest
  `aliyun aiworkspace list-images` response → same red line as
  `create-job` (Image must come from `list-images`).
- ❌ `delete-job-template` while any Job still references it → blocked.
  Clean up referencing jobs first.
- ⚠ Without `--constraints`, field "locking" is agent-side discipline only —
  there is no server-side enforcement. Use `--constraints` for hard
  guarantees.
