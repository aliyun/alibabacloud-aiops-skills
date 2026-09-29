# WAF 2.0 vs WAF 3.0 — Version Differences That Cause Parameter Errors

WAF OpenAPI has **two live versions under the same product code `waf-openapi`**. Picking the wrong one — or
mixing one version's action/parameter naming into the other — is itself a root cause, not a value typo.

| | WAF 2.0 | WAF 3.0 |
|---|---------|---------|
| API version(s) | **six**: `2016-03-10`, `2016-07-18`, `2017-09-30`, `2018-01-17`, `2019-09-10`, `2021-07-27` | `2021-10-01` (the only 3.0 version) |
| Version with **public** API docs | `2019-09-10` only (the other five have no docs on api.aliyun.com) | `2021-10-01` |
| Overview doc | https://api.aliyun.com/document/waf-openapi/2019-09-10/overview | https://api.aliyun.com/document/waf-openapi/2021-10-01/overview |
| Protection model | **Domain**-centric (CNAME onboarding): domain + origin IPs + ports | **Object / template / rule**: protection object → template → rule |
| Typical actions | `DescribeInstanceInfo`, `CreateDomain`, `ModifyDomain`, `DescribeDomainNames`, `DescribeDomain`, `DescribeCertificates` | `DescribeInstance`, `CreateDefenseResource`, `CreateDefenseTemplate`, `CreateDefenseRule`, `DescribeDefenseRules`, `DescribeDefenseTemplates`, `CreateCloudResource` |
| CLI plugin default | **No** — must pass `--api-version 2019-09-10` | **Yes** — the plugin defaults to `2021-10-01` |
| Style | RPC | RPC |

### 🔴 The version-number trap (highest-value guardrail)

- **WAF 2.0 is NOT a single version.** It spans six version strings. A customer's SDK/POP log may legitimately
  carry `2021-07-27`, `2018-01-17`, etc.
- **`2021-07-27` belongs to WAF 2.0**, even though its year looks almost identical to WAF 3.0's `2021-10-01`.
  **Never infer the generation from the year** — only from this mapping.
- **Only `2019-09-10` (2.0) and `2021-10-01` (3.0) have public parameter docs.** For the other four 2.0
  versions the public metadata endpoint returns nothing; the spec lookup must fall back to `2019-09-10` (the
  documented 2.0 version) or the OpenAPI portal. This is a **doc-coverage gap, not "the action does not exist"**
  — say so explicitly (the diagnosis script emits this exact distinction).
- **Some actions exist in BOTH generations** (including `CreateDomain`, `ModifyDomain`, and
  `DescribeWafSourceIpSegment`). When the version is not stated, the name alone cannot settle it. Discovery lists
  both candidates but emits no version-specific spec; ask the customer to choose and wait.
- There is also an **internal `waf-inner` product line** (and a `2016-11-11` version) whose APIs are not
  published on the public portal at all. For a customer-facing diagnosis these are out of reach of the public
  spec source — route to the console/ticket rather than guessing.

### Secondary version signal

When the version string is unavailable, the instance ID prefix is a fallback signal: `waf_v2_*` → WAF 2.0,
`waf_v3_*` → WAF 3.0. State which signal the conclusion rests on. The version string (or the action's presence
in a version's public metadata) always outranks this prefix.

## How to tell which version the customer is on

1. **The version string, if present, is authoritative** — map it with the table above (remember `2021-07-27`
   = 2.0). Never rank versions by year.
2. **The customer's own words**: "WAF 2.0 / 3.0", "domain onboarding / CNAME 接入" (2.0) vs
   "protection object / template / 防护对象 / 防护模板" (3.0).
3. **The version they passed** in the SDK (`version='2019-09-10'`) or the CLI (`--api-version`).
4. **Do not silently infer from the action name or instance-ID shape.** If no authoritative version signal was
   supplied, obtain explicit confirmation. For a known cross-generation action, use discovery only to present
   both candidates before waiting for the customer's choice.

> **Never guess the version and never query the wrong one to "make it fit".** A wrong-version call produces
> misleading errors; confirm the version first, then diagnose parameters inside that version.

## CLI channel: the `--api-version` gate

The `aliyun-cli-waf-openapi` plugin serves both versions but **defaults to 2021-10-01**. A WAF 2.0 action
without the explicit version flag fails with:

```
Error: This command is not available in the current API version (2021-10-01).
Available versions for this command: [2019-09-10]
Please specify the API version explicitly:
  aliyun waf-openapi describe-instance-info --api-version 2019-09-10
```

- WAF 3.0 (default): `aliyun waf-openapi describe-instance --biz-region-id cn-hangzhou`
- WAF 2.0 (explicit): `aliyun waf-openapi describe-instance-info --api-version 2019-09-10 --biz-region-id cn-hangzhou`

## Parameter naming across channels (a frequent mismatch)

The **same** API parameter has different surface forms per channel. A correct SDK/raw parameter name is
**wrong** in CLI plugin mode, and vice versa.

| API-level name (SDK / raw RPC / metadata) | CLI plugin flag | Note |
|-------------------------------------------|-----------------|------|
| `RegionId` | `--biz-region-id` | **Renamed by the plugin** — `--region-id` / `--RegionId` are unknown flags |
| `InstanceId` | `--instance-id` | kebab-case |
| `IsAccessProduct` (integer, WAF 2.0) | `--is-access-product` | **integer `0`/`1`, not `true`/`false`** |
| `HttpPort` / `HttpsPort` (string, WAF 2.0) | `--http-port` / `--https-port` | a **JSON list string** like `["80"]`, not a bare int |
| `SourceIps` (string, WAF 2.0) | `--source-ips` | JSON list string of origin IPs |
| `Rules` (string, WAF 3.0) | `--rules` | a **JSON string** holding the rule object, not a nested flag tree |

- **CLI plugin mode** (`aliyun waf-openapi <kebab-action>`): flags are lowercase-hyphen. Get the exact set from
  `aliyun waf-openapi <kebab-action> [--api-version 2019-09-10] --help`. PascalCase flags (`--RegionId`) are
  **rejected as unknown flags**.
- **SDK / raw RPC mode**: parameter names are PascalCase exactly as in the metadata (`RegionId`, `InstanceId`).
  Nested/array params use dot + index notation (`Rules.1.xxx`, `HttpPort.1`).

## Version-specific value traps

- **WAF 2.0 booleans are integers.** `IsAccessProduct`, `HttpToUserIp`, `HttpsRedirect`, `SniStatus`,
  `AccessHeaderMode` are `integer` (`0`/`1`). Passing `true`/`false` → `InvalidParameter`.
- **WAF 2.0 ports/IPs are JSON list strings.** `HttpPort` / `HttpsPort` / `Http2Port` / `SourceIps` expect a
  stringified list (e.g. `"[80,443]"` / `"[\"1.2.3.4\"]"`), not a scalar.
- **WAF 3.0 `Rules` / `Template` are JSON strings.** The whole rule object is serialized into one string
  parameter; a malformed inner field surfaces as `AclParamError` or `Defense.Control.*ConfigInvalid`.
- **`RegionId` accepts only two values in both versions:** `cn-hangzhou` (Chinese mainland) and
  `ap-southeast-1` (outside the Chinese mainland). Any other region string → `InvalidParameter` /
  `InvalidRegionId`. (The metadata lists this in the description, not always as a formal enum — enforce it.)
