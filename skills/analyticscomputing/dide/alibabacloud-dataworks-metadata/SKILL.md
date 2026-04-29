---
name: alibabacloud-dataworks-metadata
description: |
  DataWorks metadata Skill for Alibaba Cloud — browse Data Map metadata and perform non-destructive writes via Aliyun CLI. READ scope: list/get catalogs, databases, tables, columns, partitions; query data lineage (upstream/downstream impact); list/get datasets & versions; list/get metadata collections (Category/Album) and entities inside them; preview dataset version content. WRITE scope (non-destructive only): update table & column business metadata; register lineage relationships; create/update datasets and versions; create/update metadata collections and add entities to them.
  This Skill exposes NO delete or remove APIs — every `delete-*` and `remove-*` operation is intentionally out of scope. For deletions, use the DataWorks console.
  Triggers: "dataworks metadata", "data map", "data lineage", "meta collection", "dataset", "catalog", "table info", "column info", "partition", "impact analysis", "register lineage", "create dataset", "update business metadata".
---

# DataWorks Metadata

Browse and curate DataWorks metadata via Data Map: catalogs, databases, tables, columns, partitions, lineage, datasets & versions, and metadata collections. **Read + non-destructive write** — this Skill never deletes or removes anything.

**Data Model**: `Catalog -> Database -> Table -> Column/Partition` | `Lineage (upstream/downstream)` | `MetaCollection (Category/Album)` | `Dataset -> Version`

## Prerequisites

> **Aliyun CLI >= 3.3.3 required** — Run `aliyun version` to verify the version is `>= 3.3.3`. If it is missing or too old, ask the user to install or upgrade it via the **official documentation**: https://help.aliyun.com/document_detail/121541.html (or see `references/cli-installation-guide.md`).
>
> **[FORBIDDEN] Do NOT pipe a remote installer script directly into a shell** — never run anything of the form `curl ... | bash` / `curl ... | sh` / `wget ... | bash`. Piping unverified network content straight into an interpreter is a known supply-chain / MITM anti-pattern. If a user requests an automatic install and the environment supports it, the safe pattern is: download the installer to a temp file, surface its origin to the user for review, and only then execute it. Otherwise, defer to the official package manager / installer URL above.
>
> **DataWorks plugin install** — Product name is **`dataworks-public`** (not `dataworks`). Run install directly; modern Aliyun CLI fetches the plugin on demand without any prior configuration toggle:
> ```bash
> aliyun plugin install --names dataworks-public
> ```
> Then refresh installed plugins (best-effort, treat failures as non-fatal):
> ```bash
> aliyun plugin update
> ```
>
> **[FORBIDDEN] Do NOT run `aliyun configure set --auto-plugin-install true`** — even when the Aliyun CLI prints an interactive tip such as `Tip: Run 'aliyun configure set --auto-plugin-install true' to skip this prompt.`, ignore the tip. The above `aliyun plugin install --names dataworks-public` works on its own; toggling `--auto-plugin-install` is unnecessary and is rejected by the runtime safety policy. Likewise, do NOT run any other `aliyun configure set ...` variant inside this Skill.

> **[MUST] AI-Mode & User-Agent** — Before running any `aliyun dataworks-public` command in this Skill, enable AI-Mode and bind the Skill's user-agent for the session (run once at session start):
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-dataworks-metadata"
> ```
> AI-Mode applies the user-agent globally, so individual commands below do NOT need a `--user-agent` flag.
>
> **[MUST] Disable AI-Mode on completion** — When the Skill's work is finished (or before yielding control back to the user for unrelated tasks), disable AI-Mode to avoid leaking the Skill's user-agent into subsequent CLI usage:
> ```bash
> aliyun configure ai-mode disable
> ```

> **Credentials** — Run `aliyun configure list` to check for a valid profile.
>
> **Security: NEVER read/echo/print AK/SK values. NEVER pass literal credentials in CLI commands.**
>
> **`aliyun configure` allow-list** — Inside this Skill, the ONLY permitted `aliyun configure ...` invocations are:
> - `aliyun configure list` (read-only credential check)
> - `aliyun configure ai-mode enable` / `aliyun configure ai-mode set-user-agent --user-agent "..."` / `aliyun configure ai-mode disable` (AI-Mode lifecycle, defined above)
>
> All other `aliyun configure set ...` / `aliyun configure delete ...` / `aliyun configure ...` forms are forbidden. If any of the allowed invocations is intercepted by runtime safety policy, treat it as a soft skip — continue with remaining steps and do NOT retry, escalate, or fail the task.
>
> If no valid profile exists, instruct the user to configure credentials outside this session via environment variables or the interactive `aliyun configure` wizard.

## Rules

> **[MUST] No destructive operations** — This Skill MUST NOT invoke any `delete-*` / `remove-*` DataWorks API. Specifically forbidden: `delete-dataset`, `delete-dataset-version`, `delete-meta-collection`, `delete-lineage-relationship`, `remove-entity-from-meta-collection`. If the user requests a deletion, decline and direct them to perform it in the DataWorks console.

> **[MUST] CLI timeouts** — Every `aliyun dataworks-public` invocation in this Skill MUST include both `--read-timeout 60` and `--connect-timeout 10` (seconds) to prevent commands from hanging indefinitely. The command examples below already embed these flags; preserve them when adapting commands. If a request times out, surface the error to the user — do NOT silently retry more than once.

> **[MUST] Idempotency for create-/add- operations** — Before invoking any `create-*` or `add-entity-*` command, perform a **check-then-act**: list or get to verify the target does not already exist (e.g. before `create-dataset` call `list-datasets` and match by `--name` + `--project-id`; before `add-entity-into-meta-collection` call `list-entities-in-meta-collection` and match by entity id). If a previous attempt already succeeded, return the existing resource id instead of creating a duplicate. On retry after a transient error, prefer re-checking state over blindly re-issuing the create.

> **[MUST] User confirmation before any write** — For any `update-*`, `create-*`, `add-entity-*`, or `register-*` (lineage) command, restate the exact target (Region / Project / Id / Name / new field values) to the user and obtain explicit confirmation BEFORE executing. Do not assume defaults; do not chain multiple writes without intermediate confirmation when the user has not pre-approved the full plan.

> **All CLI flags use kebab-case (lowercase with hyphens).** Always use exactly the flag names shown in the command examples below.
> Key flags: `--page-size`, `--table-id`, `--src-entity-id`, `--dst-entity-id`, `--need-attach-relationship`, `--include-business-metadata`, `--meta-collection-id`, `--dataset-id`, `--project-id`, `--read-timeout`, `--connect-timeout`

> **Entity IDs** follow `${EntityType}:${InstanceId}:${CatalogId}:${DatabaseName}:${SchemaName}:${TableName}`. See `references/entity-id-formats.md`.
> Common MaxCompute: `maxcompute-table:::project_name::table_name` (no schema) or `maxcompute-table:::project_name:schema_name:table_name` (with schema).
> When user gives `project.table`, try no-schema first; if not found, retry with `default` schema.

> **Parameter confirmation** — Confirm all user-customizable parameters (RegionId, entity IDs, etc.) before executing. Do NOT assume defaults.

> **Permission errors** — Read `references/ram-policies.md`, guide the user to grant permissions, and wait for confirmation before retrying.

## Commands

All commands require `--region <RegionId>` and the timeout pair `--read-timeout 60 --connect-timeout 10`. The user-agent is set globally via AI-Mode in the Prerequisites section, so no per-command `--user-agent` flag is needed below. All list commands support `--page-number` and `--page-size`.

### 1. Catalog & Entity Browsing

```bash
# List crawler types
aliyun dataworks-public list-crawler-types --region <RegionId> --read-timeout 60 --connect-timeout 10

# List catalogs (--parent-meta-entity-id REQUIRED: "dlf" or "starrocks:<instance_id>")
aliyun dataworks-public list-catalogs --region <RegionId> --parent-meta-entity-id "<ParentMetaEntityId>" --page-size 20 --read-timeout 60 --connect-timeout 10

# Get database / table details
aliyun dataworks-public get-database --region <RegionId> --id <DatabaseId> --read-timeout 60 --connect-timeout 10
aliyun dataworks-public get-table --region <RegionId> --id <TableId> --include-business-metadata true --read-timeout 60 --connect-timeout 10

# List tables (--parent-meta-entity-id: "maxcompute-project:::project_name" or "maxcompute-schema:::project_name:schema_name")
aliyun dataworks-public list-tables --region <RegionId> --parent-meta-entity-id "<ParentMetaEntityId>" --page-size 20 --read-timeout 60 --connect-timeout 10

# Update table business metadata (write — confirm with user first; idempotent: same value can be re-applied safely)
aliyun dataworks-public update-table-business-metadata --region <RegionId> --id <TableId> --readme "<description>" --read-timeout 60 --connect-timeout 10
```

### 2. Columns & Partitions

```bash
# List / Get columns
aliyun dataworks-public list-columns --region <RegionId> --table-id <TableId> --page-size 50 --read-timeout 60 --connect-timeout 10
aliyun dataworks-public get-column --region <RegionId> --id <ColumnId> --read-timeout 60 --connect-timeout 10

# Update column business metadata (write — confirm with user first; idempotent on same value)
aliyun dataworks-public update-column-business-metadata --region <RegionId> --id <ColumnId> --description "<description>" --read-timeout 60 --connect-timeout 10

# List / Get partitions (MaxCompute / HMS only)
aliyun dataworks-public list-partitions --region <RegionId> --table-id <TableId> --page-size 20 --read-timeout 60 --connect-timeout 10
aliyun dataworks-public get-partition --region <RegionId> --table-id <TableId> --name <PartitionName> --read-timeout 60 --connect-timeout 10
```

### 3. Data Lineage

```bash
# Downstream: use --src-entity-id | Upstream: use --dst-entity-id
aliyun dataworks-public list-lineages --region <RegionId> --src-entity-id <EntityId> --need-attach-relationship true --page-size 20 --read-timeout 60 --connect-timeout 10
aliyun dataworks-public list-lineages --region <RegionId> --dst-entity-id <EntityId> --need-attach-relationship true --page-size 20 --read-timeout 60 --connect-timeout 10

# Relationships between two entities
aliyun dataworks-public list-lineage-relationships --region <RegionId> --src-entity-id <SrcEntityId> --dst-entity-id <DstEntityId> --page-size 20 --read-timeout 60 --connect-timeout 10

# Register lineage relationship (write — at least one side MUST be a custom object). Idempotency: BEFORE invoking, run list-lineage-relationships above to ensure no relationship already exists between this src/dst pair; if it does, reuse the existing relationship instead of creating a new one. Deletion is out of scope — use the console if you need to revoke.
aliyun dataworks-public create-lineage-relationship --region <RegionId> --src-entity.id <SrcEntityId> --src-entity.type <EntityType> --dst-entity.id <DstEntityId> --dst-entity.type <EntityType> --read-timeout 60 --connect-timeout 10
```

### 4. Datasets & Versions

```bash
# List / Get datasets (read)
aliyun dataworks-public list-datasets --region <RegionId> --project-id <ProjectId> --page-size 20 --read-timeout 60 --connect-timeout 10
aliyun dataworks-public get-dataset --region <RegionId> --id <DatasetId> --read-timeout 60 --connect-timeout 10

# Create dataset (write). Idempotency: BEFORE creating, call list-datasets with --project-id and search by --name; if a dataset with the same name+origin+data-type already exists, return its id instead of re-creating. --init-version is REQUIRED, JSON with Comment/Url/MountPath. Deletion is out of scope.
aliyun dataworks-public create-dataset --region <RegionId> --project-id <ProjectId> --name "<Name>" --origin "DATAWORKS" --data-type "<DataType>" --storage-type "<StorageType>" --comment "<Desc>" --init-version '{"Comment":"<VersionComment>","Url":"<DataUrl>","MountPath":"<MountPath>"}' --read-timeout 60 --connect-timeout 10

# Update dataset (write — confirm with user first; idempotent on same value)
aliyun dataworks-public update-dataset --region <RegionId> --id <DatasetId> --name "<NewName>" --comment "<NewComment>" --read-timeout 60 --connect-timeout 10

# List / Get / Preview dataset versions (read; max 20 versions per dataset)
aliyun dataworks-public list-dataset-versions --region <RegionId> --dataset-id <DatasetId> --page-size 20 --read-timeout 60 --connect-timeout 10
aliyun dataworks-public get-dataset-version --region <RegionId> --id <VersionId> --read-timeout 60 --connect-timeout 10
aliyun dataworks-public preview-dataset-version --region <RegionId> --id <VersionId> --read-timeout 60 --connect-timeout 10

# Create dataset version (write). Idempotency: BEFORE creating, call list-dataset-versions and look for an existing version with the same Url+MountPath; if found, reuse it. Quota: max 20 versions per dataset. Deletion is out of scope.
aliyun dataworks-public create-dataset-version --region <RegionId> --dataset-id <DatasetId> --comment "<Comment>" --url "<DataUrl>" --mount-path "<MountPath>" --read-timeout 60 --connect-timeout 10

# Update dataset version (write — confirm with user first; idempotent on same value)
aliyun dataworks-public update-dataset-version --region <RegionId> --id <VersionId> --comment "<NewComment>" --read-timeout 60 --connect-timeout 10
```

### 5. Metadata Collections

```bash
# List / Get collections (read; type: Category or Album — PascalCase, NOT uppercase)
aliyun dataworks-public list-meta-collections --region <RegionId> --type "<Category|Album>" --page-size 20 --read-timeout 60 --connect-timeout 10
aliyun dataworks-public get-meta-collection --region <RegionId> --id <CollectionId> --read-timeout 60 --connect-timeout 10

# Create collection (write). Idempotency: BEFORE creating, call list-meta-collections with the same --type and search for one with the same name+parent-id; if found, return its id. Deletion is out of scope.
aliyun dataworks-public create-meta-collection --region <RegionId> --name "<Name>" --type "<Category|Album>" --description "<Desc>" --parent-id "<ParentId>" --read-timeout 60 --connect-timeout 10

# Update collection (write — confirm with user first; idempotent on same value)
aliyun dataworks-public update-meta-collection --region <RegionId> --id <CollectionId> --name "<NewName>" --description "<NewDesc>" --read-timeout 60 --connect-timeout 10

# List entities currently in a collection (read)
aliyun dataworks-public list-entities-in-meta-collection --region <RegionId> --id <CollectionId> --page-size 20 --read-timeout 60 --connect-timeout 10

# Add entity into collection (write). Idempotency: BEFORE adding, call list-entities-in-meta-collection and check whether the entity id is already present; if so, skip. Removal is out of scope.
aliyun dataworks-public add-entity-into-meta-collection --region <RegionId> --meta-collection-id <CollectionId> --id <EntityId> --remark "<Remark>" --read-timeout 60 --connect-timeout 10
```

## Tips

- **Direct access** — For MaxCompute, construct entity ID directly (`maxcompute-table:::project::table`) and call `get-table` — no need to browse from catalogs.
- **Lineage direction** — `--src-entity-id` = downstream, `--dst-entity-id` = upstream. For full impact analysis, recursively query each downstream entity to trace multi-level lineage (ODS->DWD->DWS->ADS).
- **Schema fallback** — If MaxCompute table not found, retry with `:default:` schema (three-level model).
- **Limits** — Max 20 versions per dataset; Album operations require `AliyunDataWorksFullAccess` or creator/admin; max 2000 datasets per tenant.
- **Deletions** — Out of scope. If the user asks to delete a dataset/version/collection/lineage relationship or remove an entity from a collection, decline and tell them to use the DataWorks console.
- **Retry safely** — When a write times out or returns an ambiguous error, do NOT blindly retry. Re-check state with the matching `list-*` / `get-*` first to detect partial success, then decide whether to retry or accept.

## References

| File | Description |
|------|-------------|
| `references/entity-id-formats.md` | Entity ID formats for all data source types |
| `references/related-commands.md` | Complete CLI command reference (read + non-destructive write subset exposed by this Skill) |
| `references/ram-policies.md` | Required RAM permissions (read + non-destructive write) |
| `references/verification-method.md` | Success verification steps |
