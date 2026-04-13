# Verification Method — DataWorks Metadata

## 1. Catalog Browsing Verification

**Step**: List catalogs and verify response

```bash
aliyun dataworks-public list-catalogs \
  --region <RegionId> \
  --parent-meta-entity-id "dlf" \
  --page-size 5 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected**: JSON response with `CatalogList` array containing catalog items with `Id`, `Name`, `Type` fields.

**Step**: Get specific catalog detail

```bash
aliyun dataworks-public get-catalog \
  --region <RegionId> \
  --id <CatalogId_from_list> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected**: JSON with catalog detail including `Id`, `Name`, `Type`, and `Comment`.

## 2. Table & Column Verification

**Step**: Get table detail with business metadata

```bash
aliyun dataworks-public get-table \
  --region <RegionId> \
  --id <TableId> \
  --include-business-metadata true \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected**: JSON with table detail including `Id`, `Name`, `DatabaseId`, `Columns`, and business metadata fields.

**Step**: List columns of a table

```bash
aliyun dataworks-public list-columns \
  --region <RegionId> \
  --table-id <TableId> \
  --page-size 50 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected**: JSON with `ColumnList` array, each entry having `Id`, `Name`, `DataType`, `Comment`.

## 3. Partition Verification

```bash
aliyun dataworks-public list-partitions \
  --region <RegionId> \
  --table-id <TableId> \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills
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
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected**: JSON with lineage entity list showing downstream dependencies.

**Step**: Verify lineage relationship creation

```bash
# After creating a lineage relationship, verify by querying it
aliyun dataworks-public get-lineage-relationship \
  --region <RegionId> \
  --id <RelationshipId_from_create> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected**: JSON with relationship detail including `SrcEntity`, `DstEntity`, `Task` information.

## 5. Dataset Verification

**Step**: Create and verify dataset

```bash
# After create-dataset, list datasets to confirm
aliyun dataworks-public list-datasets \
  --region <RegionId> \
  --project-id <ProjectId> \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected**: New dataset appears in the list with matching `Name`, `Origin`, and `DataType`.

**Step**: Verify dataset version

```bash
# After create-dataset-version, list versions
aliyun dataworks-public list-dataset-versions \
  --region <RegionId> \
  --dataset-id <DatasetId> \
  --page-size 10 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected**: New version appears with matching `Comment` and incrementing version number.

## 6. Metadata Collection Verification

**Step**: Create and verify collection

```bash
# After create-meta-collection, query it
aliyun dataworks-public get-meta-collection \
  --region <RegionId> \
  --id <CollectionId_from_create> \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected**: JSON with collection detail matching provided `Name`, `Type`, and `Description`.

**Step**: Verify entity added to collection

```bash
# After add-entity-into-meta-collection, list entities
aliyun dataworks-public list-entities-in-meta-collection \
  --region <RegionId> \
  --id <CollectionId> \
  --page-size 20 \
  --user-agent AlibabaCloud-Agent-Skills
```

**Expected**: Added entity appears in the entity list with matching `Id`.

## Common Error Codes

| Error Code | Meaning | Resolution |
|-----------|---------|------------|
| `Forbidden.RAM` | Insufficient permissions | Grant required RAM permissions for DataWorks |
| `InvalidParameter` | Missing or invalid parameter | Verify parameter names and values |
| `InvalidType` | Invalid type value for meta collection | Use PascalCase: `Category`, `Album` (not uppercase) |
| `EntityNotExist` | Target entity not found | Confirm entity ID is correct |
| `QuotaExceeded` | Resource limit reached | Check dataset/version limits |
