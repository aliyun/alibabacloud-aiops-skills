# API lookup rules: query OpenAPI definitions with the script

Every product uses the same approach with `scripts/aliyun_help.py` to locate APIs and verify fields: `api-products` determines the product code and version, `api-list` discovers APIs, `api-info` verifies the contract; Endpoints, regions, and usage limits come from the corresponding official doc bodies. Below, `<product-code>` means the OpenAPI product code (e.g., `live`); doc product codes, short names, and Chinese product names are also accepted — the script fuzzy-matches them in metadata (rules and ambiguity handling in Product code table, "What to do when a product code finds no body").

> **Boundary**: this file **does not teach how to call APIs and never executes calls**. Actually sending requests belongs to the CLI / server SDK's own capabilities and discipline — this Skill's job is to locate APIs precisely and verify fields precisely. When the user wants to run commands themselves for evidence, command forms are in CLI/SDK general rules and the product's SDK/CLI references.

## 1. Commands

The script anonymously accesses public metadata on `api.aliyun.com` (International site `api.alibabacloud.com`); no credentials needed:

| Command | Purpose | When |
|------|------|--------|
| `python3 scripts/aliyun_help.py api-products [keyword]` | confirm OpenAPI product code, default version, and per-version recommendation status; `--json` keeps raw fields | **always, before the first `api-list` / `api-info` of the session** — even for well-known products like ECS; never reuse a memorized code or version |
| `python3 scripts/aliyun_help.py api-list <product-code> [keyword]` | list the product's APIs (keyword matches apiName/title/summary) | to discover APIs when the apiName is unknown |
| `python3 scripts/aliyun_help.py api-info <product-code> <ApiName>` | request parameter table (name/position/type/required/description), error codes, RAM permission points, related doc links | **verify before giving field conclusions**; this is authoritative, not memory |
| `python3 scripts/aliyun_help.py api-info <product-code> <ApiName> --json` | full raw metadata (response schema, enums/defaults, examples, `systemTags`, complete `ramActions`) | to verify fields / read-only vs. mutating / risk; detailed authorization also needs the same-version RAM topic page (Section 5) |

- Discovering APIs: `api-list` fetches the full list live (default up to 50, `-n 0` for all). apiName is case-insensitive. Add `-V <version>` to pin a version.
- **Pure list requests** ("list all APIs related to X") follow the same chain: confirm the code and version with `api-products` first, take the list from live `api-list` output, and before delivering it verify at least one representative API with `api-info <product-code> <ApiName> --json` — never supplement the list from memory, and never skip `api-products` because the product feels familiar.
- Verifying fields: trust the parameter names (PascalCase) and required flags returned by `api-info`; responses are in `--json`'s `responses`. When metadata and doc bodies disagree, **metadata wins**.
- When an API does not exist the script prints `API '<name>' not found` and exits non-zero — go back to `api-list` to confirm the spelling; **never invent APIs**.

### API version recommendation and selection

- In `api-products --json`, `versions` is all versions, `defaultVersion` is used when `-V` is omitted, and `recommendVersions` is the official recommendation list, possibly recommending several versions at once. Judge the three separately; never derive recommendations from dates or ordering.
- When the recommendation list is valid, versions in it are `recommended`, other published versions are `not recommended`; missing or malformed fields mean `recommendation unknown`. An empty list explicitly means no recommended versions — different from a missing field. `--json` keeps raw fields and never fabricates a recommendation list.
- New integrations prefer recommended versions; the default version may be kept if it is in the list, otherwise check whether a recommended version contains the target API before choosing. With several recommended versions, choose by API support and user need — never just the newest date or first list item. When recommendation is unknown, the looked-up default version may be kept but its recommendation status must be stated as unverified; when no versions are recommended, say so — never label the default as recommended.
- When the user pins a version, check it exists in `versions`; flag not-recommended status without auto-replacing or forbidding it. Subsequent `api-list` / `api-info` / `sdk-doc` explicitly carry the same `-V`, so verification and code generation never use different versions.
- **Not recommended does not mean deprecated, discontinued, or unusable**; per-API `deprecated`, API-version recommendation, and SDK V2.0/V1.0 preference are different dimensions. Lifecycle and migration conclusions come from official bodies, never inferred from recommendation flags.

## 2. Text output truncates enums

A description ending abruptly after the Chinese marker `取值：` ("values:") means truncation. **Always check `--json` for enum values, defaults, and response parameters** (`enum`/`default`/`description` inside `parameters[].schema`); never conclude from truncated text — a missed default can cause serious misjudgment.

**"Query all" does not mean parameters can be omitted**: some APIs that look like batch queries still mark an object name required and can only be queried one by one. Required flags come from `api-info`'s Required column; never infer "can query everything at once" from the API name.

## 3. `systemTags` in `--json` (read-only / mutating / risk classification)

`--json` outputs the metadata object itself; `systemTags` is at the **top level** (`.systemTags`). Note the text mode's `Read/Write` column comes from a different coarse-grained field (possibly `read`, `-`, or `readAndWrite`, inconsistent even within one product) and **must not** be used to classify read-only vs. mutating.

`systemTags` keys **vary per API; any may be missing** (`chargeType`, `riskType`, `abilityTreeCode` are absent on many APIs), so always read with `.get()` and treat missing as unknown:

- `operationType`: **present on every real API**; `get`/`list` = read-only, `update`/`create`/`delete` = mutating; any other value is treated as mutating. More authoritative than apiName prefixes — use it when available; otherwise fall back to prefixes: `Describe`/`Query`/`List`/`Get` are read-only, everything else (`Add`/`Create`/`Update`/`Set`/`Delete`/`Forbid`/`Stop`, etc.) is treated as mutating.
- `riskType`: `high` means a high-risk mutation. On `high`, explicitly tell the user the impact surface and suggest reading back with read-only APIs first; never just report the API name.
- `chargeType`: `free`/`paid`. **Missing means unknown — do not infer billing from it**, and never fill one in from memory; billing conclusions always come from official billing doc bodies, labeled "not yet verified" when unavailable.

Example:

    python3 scripts/aliyun_help.py api-info <product-code> <ApiName> --json 2>/dev/null \
      | python3 -c "import json,sys;print(json.load(sys.stdin).get('systemTags'))"

## 4. Site

- Query with the site and corpus language confirmed in `SKILL.md` "Step 1: Determine the site": add `--site <site> -L <language>` to `api-products` / `api-list` / `api-info`; `-L` sets the language of metadata titles, descriptions, and error messages (China site default `zh`, International site default `en`). "Related documentation" is retrieved for the same site and language; on no hit, `search` → `read` separately.
- Fields are usually identical across sites, but **regions, billing, and availability may differ**; such conclusions must come from the corresponding site's doc bodies — never apply the other site's.
- `RegionId` example values in metadata are mostly China-site regions; they are **not default regions** and must not be used as defaults, especially not for the International site. Use the resource's actual owning region confirmed by the user; `<region-id>` placeholder when unconfirmed. Verify region availability limits from the corresponding site's official bodies.
- Some fields may be untranslated; explain field meanings from the same-language per-API doc fetched with `read`, while parameter names, required flags, and types still come from metadata.
- Per-API docs can be found directly via `search <ApiName> -p <doc-product-code>` (add `--site intl -L <language>` on the International site); the "Related documentation" at the end of `api-info` output also gives the corresponding site's links.

## 5. API-version topic pages: detailed authorization, overview, endpoints, error codes

For detailed authorization or API-version-level explanations, fetch the topic body with `read` in addition to `api-info --json`. You may construct **candidate paths** per the conventions below, but never treat a constructed URL as an existing page:

| Site/language | Candidate path |
| --- | --- |
| China site Chinese/English | `https://help.aliyun.com/<zh-or-en>/<doc-product-code>/developer-reference/api-<lowercase-apicode>-<apiversion>-<suffix>` |
| International site | `https://www.alibabacloud.com/help/<language>/<doc-product-code>/developer-reference/api-<lowercase-apicode>-<apiversion>-<suffix>` |

| Suffix | Content | When to read |
| --- | --- | --- |
| `ram` | RAM authorization: Action, granularity, Resource ARN, Condition, dependent operations | asked which permissions an API needs, resource-level authorization, or generating least-privilege policies |
| `overview` | the API version's overview, API categorization, integration notes | understanding API capabilities and organization; the full API list still comes from `api-list` |
| `endpoint` | service endpoints, regions, public/VPC addresses | verifying Endpoints and signing regions; a listed address does not mean the region is available — watch for shutdown markers |
| `errorcodes` | the product/API version's error-code list and explanations | cross-check when diagnosis yields a raw error code; identify applicable entries by error code, message, HTTP status, and target API — this is not evidence of an actual failure |

### Path construction and reading

1. First determine the **doc product code** (Product code table, `list-products`, doc catalog), the **OpenAPI product code**, and the **API version** (`api-products` / `api-info -V`). Directories and file names use the two different codes — they cannot substitute for each other; the version is not an SDK/Provider package version. For example, EBS `2021-07-30`'s page set lives under the `ecs` directory with file-name prefix `api-ebs-2021-07-30-`.
2. Choose the path for the confirmed site and language and hand the candidate URL to `read`; quote it only after exit code `0` and the body is confirmed to be the target product, version, and topic. When a product does not use this path, the language version does not exist, or only catalog text exists, relocate with `list-docs` or `search "<apicode> <version> <topic-keyword>" -p <doc-product-code>`; do not repeatedly guess paths or fall back across sites.
3. Chinese example (for English replace `/zh/` with `/en/`; International site uses the entry in the table above; verify each path separately):

       python3 scripts/aliyun_help.py read https://help.aliyun.com/zh/ecs/developer-reference/api-ebs-2021-07-30-ram

   Read `overview` / `endpoint` / `errorcodes` of the same set as needed; do not fetch unrelated topics for one authorization question. When diagnosis has a raw error code, always cross-check `errorcodes` even if an official solution was already obtained; integrate with logs and bodies per Error diagnosis rules. When topic pages are long or one code has many entries, locate the exact error code and judge with the error message; never assert "not listed" from truncated text.

### Per-API detailed authorization

1. First read the complete `ramActions` from `api-info <apicode> <ApiName> -V <apiversion> --json`. Text mode lists only permission points — **not enough to generate policies**; read Action, granularity, resource/ARN, conditions, etc. from the actual structure. Missing fields mean not yet verified; an empty `ramActions` still cannot prove "no authorization needed".
2. Then read the same-version `ram` page and find relevant rows by the **exact ApiName in the API column**; verify Action (never guess RAM prefixes from API names), access level, resource type/ARN, condition keys, and dependent operations, and read the Resource and Condition section definitions. A `*` before a resource type is the required marker, not a wildcard inside the ARN; "none" in the product-condition column (Chinese `无`) does not mean general conditions are absent.
3. When dependent operations are non-empty, verify each one's authorization requirements; never claim permissions are complete after granting only the main Action. When metadata and body authorization descriptions conflict, list both with sources; do not generate permission-widening policies before confirmation; request/response contracts still come from metadata.
4. Generate policies using only verified Actions, ARNs, and conditions; regions/accounts/resource identifiers use user-confirmed values or placeholders — never blanket-replace Resource with `*`. Policies are provided for user review only; never execute authorization changes. Record the target API and actual version internally, and end with titled doc links to the RAM page sources. Explain APIs only when the user explicitly asks about API authorization; never attach internal query commands.

## 6. When the script cannot fetch

On exit code `2` (network unavailable): state plainly that API definitions cannot be fetched right now, label affected fields "not yet verified", and **never interpret it as a service outage of the cloud product**; manual troubleshooting proceeds as usual.