# Rule Sources and Cache

Ticket rules tell the client which products and issue types exist, which keywords identify
them, which category hints to search, and which fields to suggest collecting. Rules are data,
never code: nothing downloaded here is executed, and no customer content is uploaded here.

## Fixed order and fixed coordinates

1. GitHub, with compiled-in coordinates that neither environment variables nor command-line
   flags can change:

   | Item | Value |
   |---|---|
   | owner | `aliyun` |
   | repository | `alibabacloud-aiops-skills` |
   | branch | `master` |
   | directory | `skills/others/cseskillshub/alibabacloud-support/products/` |

   `api.github.com` resolves the current `master` commit SHA first, then the contents API and
   the raw downloads are pinned to that single 40-character SHA. Each file is validated by the
   declared size, the Git blob SHA-1, UTF-8 decoding, the rule JSON schema and the whole-set
   checks. Only `api.github.com` and `raw.githubusercontent.com` are allowed, and only their
   default HTTPS ports.
2. OSS, only when step 1 fails. The built-in source is the bucket root
   `https://aliyun-cse-support.oss-cn-hangzhou.aliyuncs.com/` with an empty prefix, so rules
   are the direct `products/*.json` objects. Anonymous `ListObjectsV2` and `GetObject` are the
   only required permissions. A custom domain, a path, a query string, credentials in the URL
   or the legacy `aliyun-support-rules` prefix are rejected. `--oss-url ""` temporarily
   disables the fallback.

Configuration precedence for every setting is command-line flag, then
`ALIBABACLOUD_SUPPORT_*`, then the read-only legacy `ALIYUN_SUPPORT_*`, then the built-in
default. `doctor.legacyConfiguration` reports which legacy values are still in use, and
`configurationSource` reports `built_in_default`, `environment` or `legacy_environment`.

## Measured state of the sources (2026-10-10)

- `master` of the pinned repository resolves correctly and contains
  `skills/others/cseskillshub/`, but the `alibabacloud-support/products/` directory does not
  exist yet, so the GitHub step returns 404 and the client continues with OSS. This is the
  expected behaviour of a fresh release, not a failure of the rule update.
- The OSS bucket serves the current rule set, verified through the client itself: two objects,
  `products/ecs.json` and `products/bailian.json`, fetched into a snapshot whose `manifest.json`
  records the exact file set, per-file size and SHA-256, and reports `sourceType: "oss"` with
  `degraded: false`.
- Because both sources can fail at once (no network, blocked egress, empty bucket), the
  fallback path is a first-class state: `match` and `draft` keep working on the built-in
  generic issue template.

## Cache layout

Under `ALIBABACLOUD_SUPPORT_HOME`:

- `packages/<contentDigest>/products/*.json` — one immutable snapshot per content digest;
- `packages/<contentDigest>/manifest.json` — schema version, fetch time, source root, per-file
  size and SHA-256, and the set digest; the manifest is the only trusted index, the older
  ZIP-era `verification.json` is not accepted and no ZIP is produced or downloaded;
- `state.json` — `active` and `previous` snapshot names, the effective source, the last check
  time and the recorded errors, written atomically through a temporary file and `os.replace`.

Integrity rules:

- a snapshot is used only after every file passes the manifest digest and the rule schema;
  a file that fails validation is quarantined, never executed or matched against;
- when the active snapshot is missing or damaged, the client falls back to the last verified
  snapshot, and only then to an empty rule set with the built-in generic template;
- `sourceRoot`, `sourcePrefix` or the pinned source changing invalidates the seven-day short
  circuit, so configuration changes always re-fetch;
- an incomplete download never overwrites a complete snapshot.

## Rule schema that the client accepts

| Level | Allowed keys |
|---|---|
| product | `product`, `aliases`, `issueTypes` |
| issue type | `name`, `keywords`, `categoryKeywords`, `categoryHints`, `collect` |
| collection field | `field`, `label`, `required`, `type`, `description`, `example`, `enum`, `maxLength` |

Any other key, a URL, a shell command, a script, SQL, a regular expression, or credential-like
content is rejected before the snapshot can become active. Collection fields may never ask for
the raw value of a password, private key, cookie, Authorization header or AccessKey secret;
only the five non-secret credential metadata fields `authorizationStatus`,
`authorizationScope`, `tokenUsage`, `apiKeyPrefix` and `apiKeyType` are allowed, and their
labels and descriptions must match that meaning and carry no example value.

## Built-in generic template

When no rule matches, `match` and `draft` use the compiled-in generic issue template, which
suggests occurrence time, issue description and impact scope, plus region, resource identifier,
error code, error message, request identifier and runtime environment as optional fields. A
fallback result always reports `ruleMatched: false` and a `fallbackReason` of
`product_not_found` or `issue_type_not_found`; it must never be presented as a rule hit.
