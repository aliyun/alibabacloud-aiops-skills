# RAM Permissions Required

## Summary Table

| Product | RAM Action | Resource Scope | Description |
|---------|-----------|----------------|-------------|
| DLF | dlfnext:ListCatalogs | * | List Catalogs |
| DLF | dlfnext:GetCatalog | * | Get Catalog details (by name) |
| DLF | dlfnext:GetCatalogById | * | Get Catalog details (by ID) |
| DLF | dlfnext:ListDatabases | * | List database names |
| DLF | dlfnext:ListDatabaseDetails | * | List database details |
| DLF | dlfnext:GetDatabase | * | Get a single database's details |
| DLF | dlfnext:ListTables | * | List table names |
| DLF | dlfnext:ListTableDetails | * | List table details |
| DLF | dlfnext:GetTable | * | Get a single table's details |

## RAM Policy Document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dlfnext:ListCatalogs",
        "dlfnext:GetCatalog",
        "dlfnext:GetCatalogById",
        "dlfnext:ListDatabases",
        "dlfnext:ListDatabaseDetails",
        "dlfnext:GetDatabase",
        "dlfnext:ListTables",
        "dlfnext:ListTableDetails",
        "dlfnext:GetTable"
      ],
      "Resource": "*"
    }
  ]
}
```

## DLF Data Permissions

In addition to RAM API permissions, the corresponding data permissions must be granted in the DLF console:

| Action | DLF Data Permission | Permission Level |
|------|-------------|---------|
| ListCatalogs | LIST | Account-level |
| GetCatalog / GetCatalogById | DESCRIBE | CATALOG |
| ListDatabases / ListDatabaseDetails | LIST | CATALOG |
| GetDatabase | DESCRIBE | DATABASE |
| ListTables / ListTableDetails | LIST | DATABASE |
| GetTable | DESCRIBE | TABLE |

> **Note:** DLF data permissions and RAM API permissions are two independent permission systems.
