---
name: alibabacloud-terraform-code-generation
description: |
  Use when the user wants Terraform HCL for Alibaba Cloud (Alicloud) infrastructure —
  new project or extending an existing one. Covers VPC, ECS, ApsaraDB RDS, OSS,
  SLB / ALB, Function Compute v3, ACK, and any other `alicloud_*` resource via the
  provider's own documentation fetched at generation time. For AWS → Alicloud
  migration or importing existing resources into state, use a different skill.
  Triggers: "write terraform for alicloud", "generate alibaba cloud terraform",
  "alicloud HCL", "create alibaba cloud vpc/ecs/rds", "生成阿里云 Terraform",
  "阿里云 HCL", "用 Terraform 部署阿里云", "alicloud provider", "aliyun/alicloud",
  "terraform-provider-alicloud".
---

# Alibaba Cloud Terraform Code Generation

Turn natural-language Alibaba Cloud infrastructure requirements into validated
Terraform for the current `aliyun/alicloud` provider. Resource knowledge is
pulled from the provider's own docs at generation time — no local gold examples
are maintained.

## Hard rules (never violate)

### 1. Credentials — never leak, never require

NEVER read, print, ask for, or write AK/SK values anywhere — HCL, comments, env
declarations, shell output, logs. The alicloud provider resolves credentials
through seven mechanisms (env AK/SK, shared `config.json`, ECS instance RAM
role, Assume Role, OIDC/RRSA, sidecar URI, static HCL) — see
`references/auth-and-network.md` for the full chain. All read by the provider
itself, never by this skill. Do NOT recommend the deprecated `ALICLOUD_*` /
`ALIBABACLOUD_*` (no-underscore) env-var names — the current names are
`ALIBABA_CLOUD_ACCESS_KEY_ID` / `_ACCESS_KEY_SECRET` / `_SECURITY_TOKEN`.

### 2. Honest reporting — never claim a step you didn't run

Never report `fmt: ok` / `validate: ok` / `plan: ok` unless the corresponding
command actually executed AND returned that status. When a step is skipped
(tool missing, user opt-out), state **"SKIPPED"** (or **"FAILED"**) with a
reason. Paraphrasing real output is fine; fabricating it is not.

### 3. `terraform apply` is off-limits

This skill NEVER runs `terraform apply`. `plan` is opt-in (Step 8); `apply` is
strictly the user's action.

## Environment (soft recommendations)

- **Terraform ≥ 1.5** recommended. Do not install or download Terraform
  automatically; Step 6 checks whether `terraform` is on PATH and reports
  the actual validation status.
- **Network** is required — Step 4.2 WebFetches each resource's provider doc.

## Workflow

### Step 1. Parse requirement

Extract:

- `region` — default `cn-hangzhou`.
- `resources[]` — `{ alicloud_type, quantity, attributes }`.
- Non-functional: multi-AZ, encryption, backup, HA, IOPS.

If ambiguous (e.g. "搭个数据库"), ask **at most one** clarifying question.

### Step 2. Resolve target directory

Extract `<target-dir>` from the user's request (explicit path like
`myshop-infra/` or current working directory if unspecified). All subsequent
`fmt` / `init` / `validate` commands run in this directory.

Before writing any `.tf` file, **MUST** create the directory:

```bash
mkdir -p <target-dir>
```

All file writes MUST prefix paths with `<target-dir>/` — never write to
the current working directory directly, never write to a generic `outputs/`
parent. After generation completes, verify the structure:

```bash
ls -R <target-dir>
```

### Step 3. Sketch architecture

Before any HCL, sketch a dependency table — one row per resource:

| resource | depends on | AZ / placement |
| --- | --- | --- |

- Expand `resources[]` with implied infra (VPC → VSwitch → SecurityGroup
  → workload); user parse often skips these.
- The expanded list is the input to Step 4's gate.

### Step 4. Pre-HCL gate (MANDATORY)

For every distinct `alicloud_*` type from Step 3 (resources **and** data
sources), execute 4.1 → 4.2 → 4.3. The calls per type are independent —
**issue them in parallel** across types.

#### 4.1 Pre-doc lookup (catalog + patterns, in parallel)

Two local lookups; **run them concurrently** before going to WebFetch:

**(a) Catalog lookup** — confirm the resource exists and check deprecation.
The catalog (`references/alicloud-providers.md`) is ~2600 lines; **do NOT
`Read` it whole** — use `grep`, which returns just the row(s) you need:

```bash
grep "alicloud_<name>" references/alicloud-providers.md
```

Three outcomes:

- **Row found, status column empty** → note the `[doc](<url>)` from the row;
  proceed to 4.2.
- **Row found, status `⚠️ 弃用 → `<new_name>`** → switch the plan to
  `<new_name>` and re-lookup. NEVER emit the deprecated name. Common catch:
  `alicloud_fc_function` → `alicloud_fcv3_function`.
- **Row not found** → stop. Ask the user whether the name was a typo;
  don't invent an `alicloud_<guess>`.

**(b) Pattern lookup** (conditional) — if the user's requirement matches a
product-specific idiom listed in `references/resource-patterns.md` (e.g.
RDS cross-AZ HA, OSS lifecycle noncurrent, VPC peering), read the
relevant section. These idioms are NOT in the provider doc's *Required*
list but are what the user actually wants (e.g. `zone_id_slave_a` for RDS
HA is optional per the doc but required for real cross-AZ placement).
Missing them produces "validates but silently wrong" output.

When a matching pattern section is found, **ALL attributes listed in that
section's "Required attributes" table MUST appear in the generated HCL**
— treat them as mandatory even if the provider doc marks them Optional.

```bash
# Quick check whether a relevant pattern exists, then Read only the section:
grep -in "<keyword>" references/resource-patterns.md
```

#### 4.2 Fetch provider doc (WebFetch)

WebFetch the doc URL from 4.1. If it fails or returns no useful content,
construct the raw URL directly from the catalog row's `doc` URL. Preserve
the catalog kind: resources use `website/docs/r/`, data sources use
`website/docs/d/`.

```
https://raw.githubusercontent.com/aliyun/terraform-provider-alicloud/master/website/docs/{r|d}/<doc_name>.html.markdown
```

**If both fail**, fall back to the local catalog row in
`references/alicloud-providers.md`. Prefix the recitation header with
`doc unreachable: used local catalog`. **Do NOT fetch any other URL** —
only the two URLs above or the local catalog are trusted sources.

#### 4.3 Recite (proof-of-read)

Before writing any HCL, emit and verify a complete per-resource brief:

- **Required** params (verbatim list from the doc, or from the local catalog
  if the 4.2 fallback was taken)
- **2–5 key Optional** params relevant to the user's requirement
- A minimal HCL snippet from the doc's "Example Usage" (omit with the note
  `no example available` only when the fallback was taken)

If Required or Optional params are missing, return to 4.2. Skipping or using
a partial recitation is a hard failure; WebFetch failure uses the 4.2 fallback,
not memory.

### Step 5. Generate

#### 5.1 Write HCL from the recitations, not memory

Use ONLY the params established in 4.3. If you need a param that wasn't in the
recited brief, re-fetch 4.2 with a deeper read; do not guess.

Before writing a field, look up the resource in
`references/deprecated-fields.md` (see §5.6 for the four row-kinds and
their handling rules):

```bash
grep '`alicloud_<resource>`' references/deprecated-fields.md
```

If the user's requirement touches a product with a specific usage pattern
(e.g. RDS cross-AZ HA, VPC peering, OSS lifecycle), also consult
`references/resource-patterns.md` for the non-obvious attributes.

#### 5.2 Data-source enforcement (MANDATORY — no hardcoded IDs)

Resolve via `data` blocks, never literals. These also pass Step 4's gate:

- `zone_id` → `data "alicloud_zones"` (filter by `available_resource_creation`).
- `image_id` → `data "alicloud_images"` (filter by `name_regex`, `owners = "system"`, `most_recent = true`).
- `instance_type` → `data "alicloud_instance_types"` (filter by `cpu_core_count`, `memory_size`, AZ).

#### 5.4 Provider block (content contract)

Two Terraform blocks must appear **somewhere** in the project's `*.tf`
files. Terraform merges all `*.tf` in a directory, so *file organization
is a style choice, not a contract* — see "File organization" below.

**Block 1 — `terraform { required_providers {} }`**:

```hcl
terraform {
  required_version = ">= 1.5"
  required_providers {
    alicloud = {
      source  = "aliyun/alicloud"
      version = "~> 1.274"
    }
  }
}
```

- Provider version: resolve the latest published stable `aliyun/alicloud` 1.x
  version, then write a pessimistic minor constraint (`1.278.0` -> `~> 1.278`).
  Lookup sources, in order:
  1. `https://registry.terraform.io/v1/providers/aliyun/alicloud/versions`
  2. `https://registry.terraform.io/providers/aliyun/alicloud/latest`
  3. `https://github.com/aliyun/terraform-provider-alicloud/releases` or
     `https://github.com/aliyun/terraform-provider-alicloud/tags`
- If lookup fails, fall back to `~> 1.274`. Accepted form is `~> 1.<minor>`
  from a confirmed published 1.x release. Do NOT write open-ended constraints
  (`>= 1.x`, `>= 1.239.0`) or bare version strings.

**Block 2 — `provider "alicloud" {}`** with BOTH `region = var.region`
and `configuration_source`:

```hcl
provider "alicloud" {
  region               = var.region
  configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-terraform-code-generation"
}
```

- `configuration_source` is the attribution signature — required.
- `region` MUST reference `var.region`, not a hardcoded literal.

**File organization (recommended, not required)**: conventional split is
`terraform.tf` (Block 1) + `providers.tf` (Block 2). Also acceptable:
a single `versions.tf` containing both blocks, or either block at the
top of `main.tf`. Pick what fits the project — Terraform merges all
`*.tf` equivalently. Do NOT add a filename check; run the content check
below instead.

**Post-generation verification (cross-file content grep)**:

```bash
# 1. required_providers has aliyun/alicloud with a ~> 1.<minor> version
awk '
  /required_providers[[:space:]]*{/ { in_req=1 }
  in_req && /alicloud[[:space:]]*=[[:space:]]*{/ { in_ali=1 }
  in_ali && /source[[:space:]]*=[[:space:]]*"aliyun\/alicloud"/ { source=1 }
  in_ali && /version[[:space:]]*=[[:space:]]*"~>[[:space:]]*1\.[0-9]+"/ { version=1 }
  in_ali && /^[[:space:]]*}/ { in_ali=0 }
  END { exit(source && version ? 0 : 1) }
' <target-dir>/*.tf \
  && echo OK_VERSION || echo BAD_OR_MISSING_VERSION

# 2. configuration_source attribution present somewhere
grep -Rq 'configuration_source = "AlibabaCloud-Agent-Skills/alibabacloud-terraform-code-generation"' \
  <target-dir>/*.tf \
  && echo OK_CFG_SOURCE || echo MISSING_CFG_SOURCE

# 3. region uses variable, not hardcoded
grep -Rq 'region\s*=\s*var\.region' <target-dir>/*.tf \
  && echo OK_REGION_VAR || echo HARDCODED_REGION
```

All three must return OK. If any fails, fix the offending content and
re-run — do NOT proceed to Step 6 with failures.

#### 5.5 Style baseline

- 2-space indent; `=` aligned within a block; snake_case semantic resource labels
  (`alicloud_vswitch.app_a`, not `vsw1`).
- Every tag-supporting resource should carry a non-empty `tags` block for ops
  hygiene — pick reasonable keys for the scenario (common choices:
  `ManagedBy`, `Project`, `Environment`, `CreatedBy`). Skill does not
  prescribe specific tag keys or values.

#### 5.6 Deprecated-field audit — static grep pass (MANDATORY)

Run before `terraform` is needed — this is a pure-grep pass on the HCL you
just wrote. For every resource in this generation, grep the project against
`references/deprecated-fields.md` and handle each row-kind:

- **rename** row → if the old field name appears in HCL you just wrote,
  replace it with the new field name. Examples that show up most often:
    - `alicloud_ram_role`: `name` → `role_name`,
      `document` → `assume_role_policy_document`
    - `alicloud_security_group`: `name` → `security_group_name`
    - `alicloud_db_database`: `name` → `data_base_name`
- **split / soft-split** row → do NOT write the inline field on the parent.
  Declare the replacement sub-resource only when the user's requirement
  needs that capability, or when `references/resource-patterns.md` says the
  sub-resource has an explicit safe default. Example: for OSS buckets,
  `alicloud_oss_bucket_acl` defaults to `private`, but logging/CORS/website
  sub-resources are omitted unless the user asks for those features.
- **deprecated-no-replacement** row → stop using the field, no substitute.

Applies only to files written in this generation — do NOT refactor
pre-existing user files you weren't asked to touch.

**Post-audit verification (bash grep — must return all OK)**:

```bash
# Walk deprecated-fields.md row by row and check whether any deprecated
# field that applies to a generated resource is still in use.
# Uses awk to extract individual resource blocks before field matching,
# so that short field names (name, document) don't falsely match
# substrings in compound field names (role_name, policy_document).
grep '| `alicloud_' references/deprecated-fields.md | while IFS='|' read _ resource field kind _; do
  resource=$(echo "$resource" | tr -d ' `')
  field=$(echo "$field" | tr -d ' ')
  kind=$(echo "$kind" | tr -d ' ')
  # Only check if this resource exists in the generated HCL
  if grep -Rq "resource \"$resource\"" <target-dir>/*.tf; then
    case "$kind" in
      rename|deprecated-no-replacement)
        awk -v res="$resource" -v fld="$field" '
          $0 ~ "resource \"" res "\"" { in_block=1; next }
          in_block && /^}/ { in_block=0 }
          in_block && $0 ~ "(^|[^_[:alnum:]])" fld "([^_[:alnum:]]|$)" { found=1; exit }
          END { exit found ? 0 : 1 }
        ' <target-dir>/*.tf \
          && echo "DEPRECATED: $resource.$field" || echo "OK: $resource.$field"
        ;;
      split|soft-split)
        grep -q "\b$field\b\s*=" <target-dir>/*.tf \
          && echo "DEPRECATED: $resource.$field (inline — use standalone sub-resource)" \
          || echo "OK: $resource.$field (not inline)"
        ;;
    esac
  fi
done
```

**HARD GATE: must pass before Step 6** — If the script above produces
any `DEPRECATED:` line:

1. Read each `DEPRECATED:` line — it names the resource and field.
2. Look up that resource+field in `references/deprecated-fields.md`
   to get the **Action** column (rename target, split sub-resource,
   etc.).
3. Apply the fix in the HCL.
4. Re-run the verification script.
5. Repeat until **every line returns `OK:`**. This is a blocking gate —
   do NOT proceed to Step 6 with any `DEPRECATED:` output. Do NOT claim
   "verified" unless the script produces all `OK:`.

### Step 6. Validate + provider deprecation detection

If `terraform` is on PATH:

```bash
(cd <target-dir> \
  && terraform fmt -recursive \
  && terraform init -backend=false \
  && terraform validate -json)
```

**Loop until both conditions are met** (max 3 fix attempts total):

1. Parse `validate -json`. If there are **errors** → fix the offending
   file, then go to step 3.
2. Scan `validate -json` `diagnostics[].summary` for `[DEPRECATED]`
   strings. The provider emits authoritative deprecation annotations
   (e.g. `"document": "[DEPRECATED] … New field
   'assume_role_policy_document' instead."`). If found → fix the
   matching field, then go to step 3.
3. Re-run `cd <target-dir> && terraform validate -json` and go back
   to step 1.

Exit the loop only when validate reports **no errors AND no
`[DEPRECATED]` diagnostics**. After 3 attempts without reaching this
state: proceed to Step 7 with `Validation: FAILED (<diagnostic excerpt>)`
and include the failing HCL verbatim in the optional notes.

**If `init` fails with a network error** (cannot reach `registry.terraform.io`):
not a config bug. Point the user at the mirror-source configuration in
`references/auth-and-network.md`, then proceed to Step 7 — the Summary
MUST use `Validation: SKIPPED (init failed — network/unreachable)`.
Do not retry blindly, do not write `~/.terraformrc` yourself.

If `terraform` is absent: SKIP this step and surface that fact in Step 7's
summary (Hard rule §2) with `Validation: SKIPPED (terraform binary not on PATH)`.

### Step 7. Coverage check + summarize

**MANDATORY — runs regardless of generation outcome.** Even if earlier
steps were interrupted (init network failure, validate loop exhausted,
terraform not on PATH), this step MUST execute. The `Files written:`
and `Validation:` lines are the final contract with downstream
evaluators — skipping them is a hard failure.

**Coverage check.** Enumerate resource blocks in the generated HCL and compare
with Step 3's sketch. If any sketch row is missing, return to Step 5 and add it
— do not skip a row because "the user didn't explicitly name it".

**Summary template** — print in the user's language, using **exactly this
structure** (fill `<bracketed>` placeholders, keep the two line labels
`Files written:` and `Validation:` verbatim):

```
Files written:
<path/to/file1>
<path/to/file2>
...

Validation: <one-of-four-exact-strings-below>

Deprecation routing: <If re-routed: `<original_name>` → `<new_name>`; else: None>

<optional: architecture notes, design decisions, deploy hints — free-form
here is fine, but NOT inside the lines above>
```

The `Validation:` line must be **one of these exact strings**, chosen from
what actually happened in Step 6. Do NOT paraphrase or fold it into prose:

- `Validation: terraform fmt+validate: ok`
- `Validation: SKIPPED (terraform binary not on PATH)`
- `Validation: SKIPPED (<reason>)`
- `Validation: FAILED (<diagnostic excerpt>)` — after 3 retries hit the cap

Edge cases:
- Init timeout → `Validation: FAILED (init timed out — provider installation exceeded time limit)`
- Init network-unreachable → `Validation: SKIPPED (init failed — network/unreachable)`
- Init failed after fmt succeeded → use the root-cause string above, not a
  hybrid status.

### Step 8 (optional). `terraform plan`

Only when the user asks. Pre-flight probes **all seven** credential paths
from `references/auth-and-network.md` without reading any value:

```bash
(
  [[ -n "${ALIBABA_CLOUD_ACCESS_KEY_ID:-}" ]] && [[ -n "${ALIBABA_CLOUD_ACCESS_KEY_SECRET:-}" ]] && echo "ready:env-ak-sk"
  [[ -f "$HOME/.aliyun/config.json" ]]                                                           && echo "ready:shared-config"
  { [[ -n "${ALIBABA_CLOUD_CREDENTIALS_FILE:-}" ]] && [[ -f "${ALIBABA_CLOUD_CREDENTIALS_FILE}" ]]; } && echo "ready:custom-credentials-file"
  [[ -n "${ALIBABA_CLOUD_ECS_METADATA:-}" ]]                                                      && echo "ready:ecs-ram-role"
  [[ -n "${ALIBABA_CLOUD_ROLE_ARN:-}" ]]                                                          && echo "ready:assume-role"
  [[ -n "${ALIBABA_CLOUD_CREDENTIALS_URI:-}" ]]                                                   && echo "ready:sidecar"
) | head -1
```

- **Any line of output** → a credential path is available:
  `(cd <target-dir> && terraform init && terraform plan -out=tfplan)`;
  surface the output.
- **Empty output** → `NO_CREDENTIALS`. Tell the user about **all** viable
  paths (env AK/SK, shared `~/.aliyun/config.json` + `ALIBABA_CLOUD_PROFILE`,
  ECS instance RAM role, Assume Role chain, OIDC/RRSA, sidecar URI) — do
  NOT just push env AK/SK. Point them at `references/auth-and-network.md`
  for the full setup. Then stop. Never read or print secret values.

## References

| Source | When to read |
| --- | --- |
| `references/alicloud-providers.md` (local) | Step 4.1 — resource existence, deprecation mark, doc URL |
| Provider doc (WebFetch of the URL from 4.1) | Step 4.2 — authoritative Required / Optional per resource |
| `references/deprecated-fields.md` (local) | Step 5.1 — known field-level renames not flagged by `terraform validate` |
| `references/resource-patterns.md` (local) | Step 5.1 — product-specific idioms not emphasized by the provider doc (RDS HA, …) |
| `references/auth-and-network.md` (local) | Step 6 failure branch — mirror-source config; Step 8 pre-flight — full credential chain |

The local catalog is one markdown table row per `alicloud_*` resource and
data source, with a `[doc](<url>)` cell and, for deprecated entries, a
`⚠️ 弃用 → `<new_name>`` marker. It is generated from the upstream provider
repo by `scripts/build_alicloud_providers.py`; re-run that script when a new
`aliyun/alicloud` release introduces or shifts deprecations.
