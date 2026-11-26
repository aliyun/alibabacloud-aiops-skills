# Required permissions for read-only knowledge retrieval

## required_permissions

The package supports five read Actions. Grant only those needed by the workflow, not all five by default:

- `dataworks:RetrieveKnowledgePoints` - retrieve points, paths, and candidates for business questions; required for core retrieval.
- `dataworks:GetKnowledgePoint` - read content or a one-hop graph using a returned identity triple; required for core retrieval.
- `dataworks:ListKnowledgePoints` - add only when browsing a specified base's point catalog.
- `dataworks:ListKnowledgeBases` - add only when listing management-visible bases.
- `dataworks:GetKnowledgeBase` - add only when locating/reading base metadata.

## Minimum core retrieval policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "dataworks:RetrieveKnowledgePoints",
        "dataworks:GetKnowledgePoint"
      ],
      "Resource": "*"
    }
  ]
}
```

Authorization documentation for these APIs currently specifies all resources (`*`), hence `Resource="*"`. This is a resource scope, not an Action wildcard: never use `dataworks:*` or claim unsupported resource-ARN restrictions.

When catalogs are needed, add the corresponding read permissions individually to `Action`. Add no build, write, administration, or grant Actions.

## RAM and business access both apply

RAM allows API invocation, not arbitrary base access. Retrieval/details still require the caller's corresponding base permissions; catalogs/metadata require visibility. `AccessRole` is a returned role description, not a request parameter or substitute for retrieval authorization.

A sharing recipient may retrieve/read points even when management `ListKnowledgeBases` omits that base. Retrieve a known shared base directly; do not require management listing/details first.

Referenced workspaces, data sources, connectors, and files retain their own source-asset permissions. Retrieval permission does not imply full-file access; missing source links do not imply absent provenance. This package performs no grant, revocation, or delegated authorization. Report missing capabilities and let an authorized person use the existing management process.
