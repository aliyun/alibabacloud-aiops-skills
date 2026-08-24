# OpenAPI Metadata Endpoints

Structured API contracts served by `api.aliyun.com` (same source as OpenAPI Explorer,
public, no authentication required). Use these endpoints — via the `api-*` subcommands
of `scripts/aliyun_help.py` — to verify exact contract details such as parameter names,
types, required flags, enums, error codes, and RAM permission points. Help-center prose
may lag behind; when the two disagree, the metadata is authoritative.

Base URL: `https://api.aliyun.com/meta/v1`

## Endpoints

### Product catalog

```
GET https://api.aliyun.com/meta/v1/products.json
```

Returns a JSON array of all products, each with `code`, `name`, `versions`,
`defaultVersion`, `group`, and `shortName`.

### API list for a product version

```
GET https://api.aliyun.com/meta/v1/products/{Code}/versions/{version}/api-docs.json
```

Returns the full API inventory (`apis` map: name → title/summary/operationType/
deprecated) plus response structures. Note that `{Code}` is **case-sensitive**
(e.g. `Actiontrail`, not `actiontrail`). The script's `api-*` subcommands normalize
casing automatically by matching against `products.json`; raw `curl` calls require the
exact case.

### Single API contract

```
GET https://api.aliyun.com/meta/v1/products/{Code}/versions/{version}/apis/{ApiName}/api.json
```

Returns the structured contract for one API: request `parameters` (name/location/type/
required/description), `errorCodes` (grouped by HTTP status), `ramActions` (RAM
permission points), HTTP methods, operation type, deprecation flag, and response
schema/examples. Note that nonexistent API endpoints return an empty or
content-less JSON object rather than an HTTP error, so validity must be checked by
field presence (`title`/`methods`/`parameters`/`summary`).

## Case-sensitivity handling in the script

- Product codes are resolved case-insensitively against `code` and `shortName`, with a
  name-substring fallback.
- API names are matched case-insensitively against `api-docs.json` and retried with the
  exact name on mismatch.
- Versions default to the product's `defaultVersion` when `-v/--api-version` is omitted.

## Debug link

The human-oriented debug page for any API is:

```
https://api.aliyun.com/api/{Code}/{version}/{ApiName}
```
