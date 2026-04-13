# RAM Policies — DataWorks Metadata Exploration

## Required Permissions

The following RAM permissions are required for the metadata exploration Skill. Attach these to the RAM user or role that will execute the CLI commands.

### Read-Only Metadata Browsing

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

### Full Metadata Management (Read + Write)

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
        "dataworks:DeleteLineageRelationship",
        "dataworks:CreateDataset",
        "dataworks:ListDatasets",
        "dataworks:GetDataset",
        "dataworks:UpdateDataset",
        "dataworks:DeleteDataset",
        "dataworks:CreateDatasetVersion",
        "dataworks:ListDatasetVersions",
        "dataworks:GetDatasetVersion",
        "dataworks:UpdateDatasetVersion",
        "dataworks:DeleteDatasetVersion",
        "dataworks:PreviewDatasetVersion",
        "dataworks:ListMetaCollections",
        "dataworks:CreateMetaCollection",
        "dataworks:GetMetaCollection",
        "dataworks:UpdateMetaCollection",
        "dataworks:DeleteMetaCollection",
        "dataworks:ListEntitiesInMetaCollection",
        "dataworks:AddEntityIntoMetaCollection",
        "dataworks:RemoveEntityFromMetaCollection"
      ],
      "Resource": "*"
    }
  ]
}
```

## Permission Summary by Category

| Category | Actions | Min Permission |
|----------|---------|---------------|
| Crawler Types | ListCrawlerTypes | Read |
| Catalogs | ListCatalogs, GetCatalog | Read |
| Databases | GetDatabase | Read |
| Tables | GetTable, UpdateTableBusinessMetadata | Read / Write |
| Columns | ListColumns, GetColumn, UpdateColumnBusinessMetadata | Read / Write |
| Partitions | ListPartitions, GetPartition | Read |
| Lineage | ListLineages, ListLineageRelationships, GetLineageRelationship, CreateLineageRelationship, DeleteLineageRelationship | Read / Write |
| Datasets | CreateDataset, ListDatasets, GetDataset, UpdateDataset, DeleteDataset | Read / Write |
| Dataset Versions | CreateDatasetVersion, ListDatasetVersions, GetDatasetVersion, UpdateDatasetVersion, DeleteDatasetVersion, PreviewDatasetVersion | Read / Write |
| Meta Collections | ListMetaCollections, CreateMetaCollection, GetMetaCollection, UpdateMetaCollection, DeleteMetaCollection, ListEntitiesInMetaCollection, AddEntityIntoMetaCollection, RemoveEntityFromMetaCollection | Read / Write |

## Notes

- **Album operations** (create/update/delete meta collection of type ALBUM, add/remove entities) require `AliyunDataWorksFullAccess` system policy, or the operator must be the album creator or administrator.
- **Dataset operations** (update/delete) require the operator to be the dataset creator or workspace admin.
- For least-privilege access, use the **Read-Only** policy above when only browsing metadata.
