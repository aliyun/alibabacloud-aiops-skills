# JobTemplate Management

JobTemplate stores a `CreateJob` configuration (`JobSpecs`, `UserCommand`,
`DataSources`, `CodeSource`, `Settings`, etc.) as a reusable, versioned template.
A Job can be launched from a template via
`aliyun pai-dlc create-job --template-id <id>`, with non-locked fields
overridable at launch time.

> **Plugin requirement:** All 5 JobTemplate subcommands require
> `aliyun-cli-pai-dlc` >= **0.3.1**.

## Pre-flight: Plugin Version Check

```bash
# Probe whether 0.3.1 subcommands are available; upgrade if missing
aliyun pai-dlc create-job-template --help >/dev/null 2>&1 \
  || aliyun plugin update --name aliyun-cli-pai-dlc

# To pin an explicit version:
#   aliyun plugin install --names aliyun-cli-pai-dlc --version 0.3.1
```

> **Red line:** Do NOT fall back to ROA generic invocations
> (`--pathPattern` / `--method POST`) when the plugin is missing. Install or
> upgrade the plugin instead.

## Constraints Format

When passing `--constraints` to `create-job-template` or `update-job-template`,
use escaped-quote JSON inside single-quoted shell string:

```bash
CONSTRAINTS='{\"JobSpecs[0].Image\":\"locked\",\"UserCommand\":\"locked\",\"JobType\":\"locked\"}'

aliyun pai-dlc create-job-template \
  --region <region> \
  --workspace-id <workspace-id> \
  --template-name "my-template" \
  --content "$CONTENT" \
  --constraints "$CONSTRAINTS" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

Note the double-escaped quotes inside the JSON: `\"` is required because the
value goes through shell parsing first, then JSON parsing.

If constraints are not needed, omit `--constraints` entirely.

## What Is a JobTemplate?

A JobTemplate captures:

- **JobSpecs / UserCommand / DataSources / CodeSource / Settings** — anything
  you would otherwise pass to `create-job`.
- **Multi-version management** — Each `update-job-template --content ...` creates
  a new version (auto-incremented `Version`).
- **Default version** — Each template has a single `DefaultVersion`. A
  `create-job --template-id <id>` invocation uses that default version unless
  overridden.
- **Field constraints (`Constraints`)** — JSONPath-tagged rules marking fields
  as `locked` (cannot be overridden), `overridable` (default; can be overridden
  by `create-job` arguments), or `required` (must be supplied by `create-job`
  arguments when the template does not provide a value).

For the full schema, error codes, and JSONPath grammar, see the
"DLC JobTemplate API" chapter in [related-apis.md](related-apis.md).

## CRUD Workflow (CLI-Walkable Paths)

The examples below use placeholders. Replace `<region>`, `<workspace-id>`, and
`<template-id>` with confirmed values.

### Step A: Create Template (no `--constraints`)

```bash
CONTENT=$(cat <<'EOF'
{
  "JobType": "PyTorchJob",
  "JobSpecs": [{
    "Type": "Worker",
    "PodCount": 1,
    "Image": "<ImageUri-from-aiworkspace-list-images>",
    "EcsSpec": "ecs.gn6i-c4g1.xlarge"
  }],
  "UserCommand": "python -c 'print(123)'"
}
EOF
)

aliyun pai-dlc create-job-template \
  --region <region> \
  --workspace-id <workspace-id> \
  --template-name "pytorch-singlenode" \
  --content "$CONTENT" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
# To add constraints, see the Constraints Format section above.
```

The first create returns `Version=1` and `DefaultVersion=1`.

### Step B: List / Get

```bash
# List
aliyun pai-dlc list-job-templates \
  --region <region> \
  --workspace-id <workspace-id> \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Get default version
aliyun pai-dlc get-job-template \
  --region <region> \
  --template-id <template-id> \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

# Get all versions
aliyun pai-dlc get-job-template \
  --region <region> \
  --template-id <template-id> \
  --biz-version all \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

### Step C: Update

`update-job-template` has two distinct modes:

- **Metadata-only update** — pass `--description`, `--template-name`, etc.,
  WITHOUT `--content`. No new version is created (`VersionCreated=false`).
- **New-version update** — pass `--content` (and optionally
  `--set-as-default true|false`). A new version is created
  (`VersionCreated=true`, `Version` increments).

```bash
# Mode 1: metadata only (no new version)
aliyun pai-dlc update-job-template \
  --region <region> \
  --template-id <template-id> \
  --description "Updated description (no new version created)" \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job

aliyun pai-dlc update-job-template \
  --region <region> \
  --template-id <template-id> \
  --content "$NEW_CONTENT" \
  --constraints "$CONSTRAINTS" \
  --set-as-default true \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
# Note: --biz-version is NOT supported on update-job-template; to switch the
# default version, use set-job-template-default-version (Step D).
```

### Step D: Switch Default Version

```bash
aliyun pai-dlc set-job-template-default-version \
  --region <region> \
  --template-id <template-id> \
  --biz-version 2 \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

### Step E: Create Job from Template

Reuse a template's content and override per-launch fields (those not marked
`locked`).

```bash
aliyun pai-dlc create-job \
  --region <region> \
  --workspace-id <workspace-id> \
  --display-name "from-template-demo" \
  --template-id <template-id> \
  --user-command 'python train.py --epochs 10' \
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-pai-dlc-job
```

## Constraints (Field-Level Rules)

> **Constraints format:** Use escaped-quote JSON: `{\"Field\":\"locked\"}` (see
> Constraints Format section). This works via CLI when the value is properly
> escaped for shell parsing followed by JSON parsing.

| Value | Behavior |
|-------|----------|
| `locked` | Field is locked; `create-job` arguments for this field are ignored (template value wins). |
| `overridable` | Field can be overridden by `create-job` arguments (default behavior when no constraint is set). |
| `required` | Field MUST be supplied by `create-job` arguments when the template does not provide a value. |

**JSONPath grammar:** Constraint keys are dot-separated field paths (e.g.,
`JobSpecs[0].Image`, `UserCommand`). The path **does NOT** include a `$.`
prefix — this is the convention used by the server-side
`pkg/utils/jsonpath/jsonpath.ParsePathSegment`.

### Design Recommendation

For shared team templates:

- Mark infrastructure fields `locked`: `JobSpecs[N].Image`, `DataSources`,
  `Settings.EnableRDMA`.
- Mark business fields `overridable`: `UserCommand`, `Envs`, `JobSpecs[N].PodCount`.

This lets consumers focus on training-script parameters while the team enforces
the runtime stack.

## Common Pitfalls

- ❌ `--content` is not valid JSON or omits `JobType` / `JobSpecs` → server
  returns `InvalidParameter.Content`.
- ❌ `--constraints` value uses unescaped quotes (e.g. `{"Field":"value"}`) →
  shell interprets the quotes. Use `{\"Field\":\"value\"}` inside a shell string.
- ❌ Using `--biz-version` on `update-job-template` to switch the operating
  version → field is unsupported; use `set-job-template-default-version`
  instead.
- ❌ `Content.JobSpecs[].Image` value is not present in the most recent
  `aliyun aiworkspace list-images` response → same red line as the Pre-Create Resource Discovery section in SKILL.md. Always pull a real `Images[].ImageUri` first.
- ⚠ Templates created via the CLI without constraints store
  `Versions[0].Content` as a JSON string (with outer quotes), differing from
  Web-UI templates which store a raw object. Both forms are accepted by
  `create-job --template-id`, but `get-job-template` returns differing shapes;
  automation scripts must handle both.
