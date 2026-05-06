# RAM Policies — DataWorks Metadata

## Required Permissions

This Skill performs **read + non-destructive write** operations only — no deletions or removals. Choose the policy that matches the operator's intended scope.

### Policy A — Read-Only Browsing

Use this policy if the user only needs to browse metadata, lineage, datasets, and collections.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:ListCrawlerTypes",
        "dataworks:ListCatalogs",
        "dataworks:GetCatalog",
        "dataworks:GetDatabase",
        "dataworks:GetTable",
        "dataworks:ListColumns",
        "dataworks:GetColumn",
        "dataworks:ListPartitions",
        "dataworks:GetPartition",
        "dataworks:ListLineages",
        "dataworks:ListLineageRelationships",
        "dataworks:GetLineageRelationship",
        "dataworks:ListDatasets",
        "dataworks:GetDataset",
        "dataworks:ListDatasetVersions",
        "dataworks:GetDatasetVersion",
        "dataworks:PreviewDatasetVersion",
        "dataworks:ListMetaCollections",
        "dataworks:GetMetaCollection",
        "dataworks:ListEntitiesInMetaCollection"
      ],
      "Resource": "*"
    }
  ]
}
```

### Policy B — Read + Non-Destructive Write

Use this policy when the user also needs to update business metadata, register lineage, create / update datasets & versions, or create / update collections and add entities. **No `Delete*` / `Remove*` actions are included** — by design this Skill cannot delete anything; perform deletions in the DataWorks console.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:ListCrawlerTypes",
        "dataworks:ListCatalogs",
        "dataworks:GetCatalog",
        "dataworks:GetDatabase",
        "dataworks:GetTable",
        "dataworks:UpdateTableBusinessMetadata",
        "dataworks:ListColumns",
        "dataworks:GetColumn",
        "dataworks:UpdateColumnBusinessMetadata",
        "dataworks:ListPartitions",
        "dataworks:GetPartition",
        "dataworks:ListLineages",
        "dataworks:ListLineageRelationships",
        "dataworks:GetLineageRelationship",
        "dataworks:CreateLineageRelationship",
        "dataworks:CreateDataset",
        "dataworks:ListDatasets",
        "dataworks:GetDataset",
        "dataworks:UpdateDataset",
        "dataworks:CreateDatasetVersion",
        "dataworks:ListDatasetVersions",
        "dataworks:GetDatasetVersion",
        "dataworks:UpdateDatasetVersion",
        "dataworks:PreviewDatasetVersion",
        "dataworks:ListMetaCollections",
        "dataworks:CreateMetaCollection",
        "dataworks:GetMetaCollection",
        "dataworks:UpdateMetaCollection",
        "dataworks:ListEntitiesInMetaCollection",
        "dataworks:AddEntityIntoMetaCollection"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Summary by Category

| Category | Read Actions | Non-Destructive Write Actions |
|----------|--------------|-------------------------------|
| Crawler Types | ListCrawlerTypes | — |
| Catalogs | ListCatalogs, GetCatalog | — |
| Databases | GetDatabase | — |
| Tables | GetTable | UpdateTableBusinessMetadata |
| Columns | ListColumns, GetColumn | UpdateColumnBusinessMetadata |
| Partitions | ListPartitions, GetPartition | — |
| Lineage | ListLineages, ListLineageRelationships, GetLineageRelationship | CreateLineageRelationship |
| Datasets | ListDatasets, GetDataset | CreateDataset, UpdateDataset |
| Dataset Versions | ListDatasetVersions, GetDatasetVersion, PreviewDatasetVersion | CreateDatasetVersion, UpdateDatasetVersion |
| Meta Collections | ListMetaCollections, GetMetaCollection, ListEntitiesInMetaCollection | CreateMetaCollection, UpdateMetaCollection, AddEntityIntoMetaCollection |

## Notes

- **Album operations** (create/update meta collection of type `Album`, add entities) require `AliyunDataWorksFullAccess` system policy or membership in the album.
- **Dataset update** requires the operator to be the dataset creator or workspace admin.
- For least-privilege access, attach **Policy A (Read-Only)** when only browsing is needed.
- **Deletions are out of scope for this Skill.** The 5 omitted actions — `DeleteLineageRelationship`, `DeleteDataset`, `DeleteDatasetVersion`, `DeleteMetaCollection`, `RemoveEntityFromMetaCollection` — must NOT be granted to this Skill's operator account. Perform any required deletion in the DataWorks console with a separately-granted account that holds the corresponding write permission.
