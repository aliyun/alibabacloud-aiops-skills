# Resource discovery

Resolve resources from broad to specific and carry exact parent identifiers forward:

```text
catalog -> database -> table -> column or index
```

## Stable identifiers

- `catalogUuid` starts with `mc-` and identifies a catalog or instance.
- `databaseUuid` starts with `md-` and identifies a database.
- `dataSourceUuid` identifies a datasource control-plane record and is not interchangeable with `catalogUuid`.
- A table is addressed by `databaseUuid` plus the exact table `qualifiedName` returned by table listing.
- Columns and indexes are scoped to their table; their names are not globally unique.

Do not construct, truncate, normalize, or guess UUIDs and qualified names. A database object's `qualifiedName` is not a table's `qualifiedName`.

## Resolution procedure

1. If the user supplies a valid exact identifier, retrieve that resource and verify its returned identity.
2. Otherwise, list or search the parent scope with filters.
3. Continue pagination while `hasMore=true`, retaining the same filters on each page.
4. Verify name, type, Region, environment, and parent identity before selecting a candidate.
5. If more than one candidate remains, show the distinguishing fields, report the unresolved identifiers and knowledge gap, then stop. This Skill version does not open a user-selection flow.

Do not use name similarity as authorization to choose a resource. Do not use a table UUID where the metadata surface requires `databaseUuid` and `tableQualifiedName`.
