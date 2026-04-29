# Verification Method — DataWorks Metadata

> **Note**: Each command MUST include `--read-timeout 60 --connect-timeout 10`. For every write step, perform a check-then-act read first to enforce idempotency, then verify success with a follow-up read.

## 1. Catalog Browsing Verification

**Step**: List catalogs and verify response

```bash
aliyun dataworks-public list-catalogs \
  --region <RegionId> \
  --parent-meta-entity-id "dlf" \
  --page-size 5 \
  --read-timeout 60 --connect-timeout 10
```

**Expected**: JSON response with `CatalogList` array containing catalog items with `Id`, `Name`, `Type` fields.

**Step**: Get specific catalog detail

```bash
aliyun dataworks-public get-catalog \
  --region <RegionId> \
  --id <CatalogId_from_list> \
  --read-timeout 60 --connect-timeout 10
```

**Expected**: JSON with catalog detail including `Id`, `Name`, `Type`, and `Comment`.

## 2. Table & Column Verification

**Step**: Get table detail with business metadata

```bash
aliyun dataworks-public get-table \
  --region <RegionId> \
  --id <TableId> \
  --include-business-metadata true \
  --read-timeout 60 --connect-timeout 10
```

**Expected**: JSON with table detail including `Id`, `Name`, `DatabaseId`, `Columns`, and business metadata fields.

**Step**: List columns of a table

```bash
aliyun dataworks-public list-columns \
  --region <RegionId> \
  --table-id <TableId> \
  --page-size 50 \
  --read-timeout 60 --connect-timeout 10
```

**Expected**: JSON with `ColumnList` array, each entry having `Id`, `Name`, `DataType`, `Comment`.

**Step**: After update-table-business-metadata, re-fetch and verify

```bash
aliyun dataworks-public get-table \
  --region <RegionId> \
  --id <TableId> \
  --include-business-metadata true \
  --read-timeout 60 --connect-timeout 10
```

**Expected**: `Readme` field reflects the new value.

## 3. Partition Verification

```bash
aliyun dataworks-public list-partitions \
  --region <RegionId> \
  --table-id <TableId> \
  --page-size 10 \
  --read-timeout 60 --connect-timeout 10
```

**Expected**: JSON with `PartitionList` array (if table has partitions). Empty list for non-partitioned tables.

## 4. Lineage Verification

**Step**: Query downstream lineage

```bash
aliyun dataworks-public list-lineages \
  --region <RegionId> \
  --src-entity-id <EntityId> \
  --need-attach-relationship true \
  --page-size 10 \
  --read-timeout 60 --connect-timeout 10
```

**Expected**: JSON with lineage entity list showing downstream dependencies.

**Step**: Idempotency check before create-lineage-relationship

```bash
aliyun dataworks-public list-lineage-relationships \
  --region <RegionId> \
  --src-entity-id <SrcEntityId> \
  --dst-entity-id <DstEntityId> \
  --page-size 10 \
  --read-timeout 60 --connect-timeout 10
```

**Expected**: If a relationship is already present, reuse its `Id` and skip the create. Otherwise proceed with `create-lineage-relationship` and verify by re-running the list.

## 5. Dataset Verification

**Step**: Idempotency check before create-dataset

```bash
aliyun dataworks-public list-datasets \
  --region <RegionId> \
  --project-id <ProjectId> \
  --page-size 50 \
  --read-timeout 60 --connect-timeout 10
```

**Expected**: Search the response for an existing dataset with the same `Name` + `Origin` + `DataType`. If present, return its `Id`; if absent, proceed with `create-dataset`.

**Step**: After create-dataset, list datasets to confirm

```bash
aliyun dataworks-public list-datasets \
  --region <RegionId> \
  --project-id <ProjectId> \
  --page-size 10 \
  --read-timeout 60 --connect-timeout 10
```

**Expected**: New dataset appears in the list with matching `Name`, `Origin`, and `DataType`.

**Step**: Idempotency check before create-dataset-version

```bash
aliyun dataworks-public list-dataset-versions \
  --region <RegionId> \
  --dataset-id <DatasetId> \
  --page-size 20 \
  --read-timeout 60 --connect-timeout 10
```

**Expected**: Search for an existing version with the same `Url` + `MountPath`. If present, reuse it; otherwise proceed with `create-dataset-version`.

**Step**: Verify dataset version

```bash
aliyun dataworks-public list-dataset-versions \
  --region <RegionId> \
  --dataset-id <DatasetId> \
  --page-size 10 \
  --read-timeout 60 --connect-timeout 10
```

**Expected**: New version appears with matching `Comment` and incrementing version number.

## 6. Metadata Collection Verification

**Step**: Idempotency check before create-meta-collection

```bash
aliyun dataworks-public list-meta-collections \
  --region <RegionId> \
  --type "<Category|Album>" \
  --page-size 50 \
  --read-timeout 60 --connect-timeout 10
```

**Expected**: Search for an existing collection with the same `Name` + `ParentId`. If present, return its `Id`; otherwise proceed with `create-meta-collection`.

**Step**: After create-meta-collection, fetch detail

```bash
aliyun dataworks-public get-meta-collection \
  --region <RegionId> \
  --id <CollectionId_from_create> \
  --read-timeout 60 --connect-timeout 10
```

**Expected**: JSON with collection detail matching provided `Name`, `Type`, and `Description`.

**Step**: Idempotency check before add-entity-into-meta-collection

```bash
aliyun dataworks-public list-entities-in-meta-collection \
  --region <RegionId> \
  --id <CollectionId> \
  --page-size 50 \
  --read-timeout 60 --connect-timeout 10
```

**Expected**: If the target entity id is already present, skip the add. Otherwise proceed.

**Step**: Verify entity added to collection

```bash
aliyun dataworks-public list-entities-in-meta-collection \
  --region <RegionId> \
  --id <CollectionId> \
  --page-size 20 \
  --read-timeout 60 --connect-timeout 10
```

**Expected**: Added entity appears in the entity list with matching `Id`.

## Common Error Codes

| Error Code | Meaning | Resolution |
|-----------|---------|------------|
| `Forbidden.RAM` | Insufficient permissions | Grant required RAM permissions for DataWorks (see `ram-policies.md`) |
| `InvalidParameter` | Missing or invalid parameter | Verify parameter names and values |
| `InvalidType` | Invalid type value for meta collection | Use PascalCase: `Category`, `Album` (not uppercase) |
| `EntityNotExist` | Target entity not found | Confirm entity ID is correct |
| `QuotaExceeded` | Resource limit reached | Check dataset (≤2000) / version (≤20) limits |
| `EntityAlreadyExists` / duplicate | Resource already present | The idempotency pre-check should have caught this; reuse the existing id rather than retrying |
| `RequestTimeout` / network timeout | Request took longer than `--read-timeout` / `--connect-timeout` | After timeout on a write, **verify state via list/get before any retry** to detect partial success — do NOT loop |
