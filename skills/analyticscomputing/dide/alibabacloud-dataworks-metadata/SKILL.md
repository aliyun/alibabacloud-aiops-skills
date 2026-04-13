---
name: alibabacloud-dataworks-metadata
description: |
  DataWorks metadata Skill for Alibaba Cloud. Provides metadata browsing (catalogs/databases/tables/columns/partitions),
  data lineage analysis, dataset & version management, and metadata collection operations via Aliyun CLI.
  Triggers: "dataworks metadata", "data map", "data lineage", "meta collection", "dataset", "catalog", "table info", "column info", "partition".
---

# DataWorks Metadata

Browse and manage DataWorks metadata via Data Map: catalogs, databases, tables, columns, partitions, lineage, datasets, and metadata collections.

**Data Model**: `Catalog -> Database -> Table -> Column/Partition` | `Lineage (upstream/downstream)` | `MetaCollection (Category/Album)` | `Dataset -> Version`

## Prerequisites

> **Aliyun CLI >= 3.3.1 required** — Run `aliyun version` to verify. If not installed, ask the user to install it first.
>
> **DataWorks plugin required** — Product name is **`dataworks-public`** (not `dataworks`):
> ```bash
> aliyun plugin install --names dataworks-public
> ```

> **Credentials** — Run `aliyun configure list` to check for a valid profile.
>
> **Security: NEVER read/echo/print AK/SK values. NEVER pass literal credentials in CLI commands.**
>
> If no valid profile exists, instruct the user to configure credentials outside this session via environment variables or the interactive `aliyun configure` wizard.

## Rules

> **All CLI flags use kebab-case (lowercase with hyphens).** Always use exactly the flag names shown in the command examples below.
> Key flags: `--page-size`, `--table-id`, `--src-entity-id`, `--dst-entity-id`, `--need-attach-relationship`, `--include-business-metadata`, `--meta-collection-id`, `--dataset-id`, `--project-id`

> **Entity IDs** follow `${EntityType}:${InstanceId}:${CatalogId}:${DatabaseName}:${SchemaName}:${TableName}`. See `references/entity-id-formats.md`.
> Common MaxCompute: `maxcompute-table:::project_name::table_name` (no schema) or `maxcompute-table:::project_name:schema_name:table_name` (with schema).
> When user gives `project.table`, try no-schema first; if not found, retry with `default` schema.

> **Parameter confirmation** — Confirm all user-customizable parameters (RegionId, entity IDs, etc.) before executing. Do NOT assume defaults.

> **Permission errors** — Read `references/ram-policies.md`, guide the user to grant permissions, and wait for confirmation before retrying.

## Commands

All commands require `--region <RegionId> --user-agent AlibabaCloud-Agent-Skills`. All list commands support `--page-number` and `--page-size`.

### 1. Catalog & Entity Browsing

```bash
# List crawler types
aliyun dataworks-public list-crawler-types --region <RegionId> --user-agent AlibabaCloud-Agent-Skills

# List catalogs (--parent-meta-entity-id REQUIRED: "dlf" or "starrocks:<instance_id>")
aliyun dataworks-public list-catalogs --region <RegionId> --parent-meta-entity-id "<ParentMetaEntityId>" --page-size 20 --user-agent AlibabaCloud-Agent-Skills

# Get database / table details
aliyun dataworks-public get-database --region <RegionId> --id <DatabaseId> --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public get-table --region <RegionId> --id <TableId> --include-business-metadata true --user-agent AlibabaCloud-Agent-Skills

# List tables (--parent-meta-entity-id: "maxcompute-project:::project_name" or "maxcompute-schema:::project_name:schema_name")
aliyun dataworks-public list-tables --region <RegionId> --parent-meta-entity-id "<ParentMetaEntityId>" --page-size 20 --user-agent AlibabaCloud-Agent-Skills

# Update table business metadata
aliyun dataworks-public update-table-business-metadata --region <RegionId> --id <TableId> --readme "description" --user-agent AlibabaCloud-Agent-Skills
```

### 2. Columns & Partitions

```bash
# List / Get / Update columns
aliyun dataworks-public list-columns --region <RegionId> --table-id <TableId> --page-size 50 --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public get-column --region <RegionId> --id <ColumnId> --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public update-column-business-metadata --region <RegionId> --id <ColumnId> --description "description" --user-agent AlibabaCloud-Agent-Skills

# List / Get partitions (MaxCompute / HMS only)
aliyun dataworks-public list-partitions --region <RegionId> --table-id <TableId> --page-size 20 --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public get-partition --region <RegionId> --table-id <TableId> --name <PartitionName> --user-agent AlibabaCloud-Agent-Skills
```

### 3. Data Lineage

```bash
# Downstream: use --src-entity-id | Upstream: use --dst-entity-id
aliyun dataworks-public list-lineages --region <RegionId> --src-entity-id <EntityId> --need-attach-relationship true --page-size 20 --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public list-lineages --region <RegionId> --dst-entity-id <EntityId> --need-attach-relationship true --page-size 20 --user-agent AlibabaCloud-Agent-Skills

# Relationships between two entities
aliyun dataworks-public list-lineage-relationships --region <RegionId> --src-entity-id <SrcEntityId> --dst-entity-id <DstEntityId> --page-size 20 --user-agent AlibabaCloud-Agent-Skills

# Create (at least one side must be custom object) / Delete
aliyun dataworks-public create-lineage-relationship --region <RegionId> --src-entity.id <SrcEntityId> --src-entity.type <EntityType> --dst-entity.id <DstEntityId> --dst-entity.type <EntityType> --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public delete-lineage-relationship --region <RegionId> --id <RelationshipId> --user-agent AlibabaCloud-Agent-Skills
```

### 4. Datasets & Versions

```bash
# Dataset CRUD (--init-version is REQUIRED for create-dataset, JSON format with Comment/Url/MountPath)
aliyun dataworks-public create-dataset --region <RegionId> --project-id <ProjectId> --name "<Name>" --origin "DATAWORKS" --data-type "<DataType>" --storage-type "<StorageType>" --comment "<Desc>" --init-version '{"Comment":"<VersionComment>","Url":"<DataUrl>","MountPath":"<MountPath>"}' --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public list-datasets --region <RegionId> --project-id <ProjectId> --page-size 20 --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public get-dataset --region <RegionId> --id <DatasetId> --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public update-dataset --region <RegionId> --id <DatasetId> --name "<NewName>" --comment "<NewComment>" --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public delete-dataset --region <RegionId> --id <DatasetId> --user-agent AlibabaCloud-Agent-Skills

# Version CRUD (max 20 per dataset)
aliyun dataworks-public create-dataset-version --region <RegionId> --dataset-id <DatasetId> --comment "<Comment>" --url "<DataUrl>" --mount-path "<MountPath>" --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public list-dataset-versions --region <RegionId> --dataset-id <DatasetId> --page-size 20 --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public get-dataset-version --region <RegionId> --id <VersionId> --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public preview-dataset-version --region <RegionId> --id <VersionId> --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public update-dataset-version --region <RegionId> --id <VersionId> --comment "<NewComment>" --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public delete-dataset-version --region <RegionId> --id <VersionId> --user-agent AlibabaCloud-Agent-Skills
```

### 5. Metadata Collections

```bash
# Collection CRUD (type: Category or Album — PascalCase, NOT uppercase)
aliyun dataworks-public list-meta-collections --region <RegionId> --type "<Category|Album>" --page-size 20 --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public create-meta-collection --region <RegionId> --name "<Name>" --type "<Category|Album>" --description "<Desc>" --parent-id "<ParentId>" --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public get-meta-collection --region <RegionId> --id <CollectionId> --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public update-meta-collection --region <RegionId> --id <CollectionId> --name "<NewName>" --description "<NewDesc>" --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public delete-meta-collection --region <RegionId> --id <CollectionId> --user-agent AlibabaCloud-Agent-Skills

# Manage entities in collection
aliyun dataworks-public list-entities-in-meta-collection --region <RegionId> --id <CollectionId> --page-size 20 --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public add-entity-into-meta-collection --region <RegionId> --meta-collection-id <CollectionId> --id <EntityId> --remark "<Remark>" --user-agent AlibabaCloud-Agent-Skills
aliyun dataworks-public remove-entity-from-meta-collection --region <RegionId> --meta-collection-id <CollectionId> --id <EntityId> --user-agent AlibabaCloud-Agent-Skills
```

## Tips

- **Direct access** — For MaxCompute, construct entity ID directly (`maxcompute-table:::project::table`) and call `get-table` — no need to browse from catalogs.
- **Lineage direction** — `--src-entity-id` = downstream, `--dst-entity-id` = upstream. For full impact analysis, recursively query each downstream entity to trace multi-level lineage (ODS->DWD->DWS->ADS).
- **Schema fallback** — If MaxCompute table not found, retry with `:default:` schema (three-level model).
- **Limits** — Max 20 versions per dataset; Album operations require `AliyunDataWorksFullAccess` or creator/admin.
- **Cleanup order** — Remove entities from collections -> delete collections -> delete versions (non-v1) -> delete datasets -> delete lineage relationships.

## References

| File | Description |
|------|-------------|
| `references/entity-id-formats.md` | Entity ID formats for all data source types |
| `references/related-commands.md` | Complete CLI command reference |
| `references/ram-policies.md` | Required RAM permissions |
| `references/verification-method.md` | Success verification steps |
