# Parameter Spec Lookup and the Diff Method (Phase 3 / Phase 4 detail)

The single rule of this skill: **the official spec is the source of truth, never memory.** API metadata changes;
always re-fetch the spec for the exact action + version before declaring a parameter wrong.

## Authoritative spec sources

| Channel the customer used | Source of truth for parameter names | How to fetch |
|---------------------------|-------------------------------------|--------------|
| CLI plugin (`aliyun waf-openapi ...`) | The plugin's own help | `aliyun waf-openapi <kebab-action> [--api-version 2019-09-10] --help` |
| SDK / raw RPC / OpenAPI portal | The OpenAPI metadata (PascalCase) | metadata endpoint below, or `scripts/diagnose_openapi_error.py` |

**Metadata endpoint (public, no credentials):**
```
https://api.aliyun.com/meta/v1/products/waf-openapi/versions/{version}/apis/{Action}/api.json
```
- `{version}` = `2021-10-01` (WAF 3.0) or `2019-09-10` (WAF 2.0)
- `{Action}` = PascalCase action, e.g. `CreateDefenseRule`, `CreateDomain`
- Returns `parameters[]`, each with `name`, `in` (query/body), and `schema`
  (`type`, `required`, `enum`, `example`, `default`, `description`, `items`, `properties`).
- A wrong-version action returns HTTP 200 with `{"message":"api not found"}` — that itself is the
  wrong-version root cause (the version model is covered in SKILL.md and its version-differences reference).

**Doc pages** (human-readable, same content):
- WAF 3.0: `https://api.aliyun.com/document/waf-openapi/2021-10-01/{Action}`
- WAF 2.0: `https://api.aliyun.com/document/waf-openapi/2019-09-10/{Action}`

## The helper script

> All invocations carry the observability env vars `SKILL_SESSION_ID={session-id} SKILL_VERSION={skill-version}`
> (the version is supplied by the Agent — see the Observability section in SKILL.md); they are omitted below for brevity.

```bash
# Print the full parameter spec (name / type / required / enum / example) for an action
python3 scripts/diagnose_openapi_error.py --version 2021-10-01 --action CreateDefenseRule
python3 scripts/diagnose_openapi_error.py --version 2019-09-10 --action CreateDomain

# Diff the parameters the customer actually sent against the confirmed-version spec
python3 scripts/diagnose_openapi_error.py --version 2021-10-01 --action CreateDefenseRule \
  --params '{"RegionId":"cn-beijing","InstanceId":"waf_x","TemplateId":1122}'

# CLI channel: also validate the flag names against `aliyun ... --help`
python3 scripts/diagnose_openapi_error.py --version 2019-09-10 --action CreateDomain \
  --params '{"Domain":"www.example.com","InstanceId":"waf_x","IsAccessProduct":true}' --channel cli
```
Exit codes: `0` = params match the spec; `1` = at least one problem located;
`2` = a version/spec condition: action not in that version (wrong version), action present in **both**
documented versions (ambiguous — ask, do not auto-pick), or a legacy WAF 2.0 version with no public docs
(use `2019-09-10`); also a genuine fetch/network error.

> **`--version` is required for spec fetch and diff.** An omitted version puts the script in discovery-only mode:
> it reports candidate versions and exits `2`, without emitting a version-specific spec. The agent must obtain
> explicit user confirmation before rerunning with `--version`.
`--params` keys use the **API-level PascalCase** names (the script diffs at API level for both channels).

## The diff dimensions (Phase 4) — check every parameter on all of these

Walk the customer's parameters against the fetched spec in this order. If the server error code/message names
a field and constraint, that evidence is primary; generic missing-field findings from an abbreviated prompt are
secondary. Report the exact parameter, expected constraint, and safely displayable value.

| # | Dimension | What "wrong" looks like | Resulting error |
|---|-----------|-------------------------|-----------------|
| 1 | **Version** | Action belongs to the other WAF version | `api not found` / `This command is not available in the current API version` |
| 2 | **Name & style** | `regionId` instead of `RegionId` (SDK); `--RegionId`/`--region-id` instead of `--biz-region-id` (CLI); singular/plural typo | `unknown flag` / `InvalidParameter.<Name>` / param silently ignored |
| 3 | **Required present** | A `required:true` param is absent | `MissingParameter` / `*.NotEmpty` |
| 4 | **Type** | WAF 2.0 boolean-as-integer sent `true` instead of `1`; integer sent as list; list sent as scalar | `InvalidParameter` / `*.Malformed` |
| 5 | **Enum value** | Value outside the documented set (e.g. `DefenseScene`, `DefenseType`, `AccessType`) | `InvalidParameter.<Name>` / `*Invalid` |
| 6 | **Format** | JSON-string param (`Rules`, `Template`, `conditions`) malformed; `HttpPort` not a list string; IP/CIDR invalid; cert not PEM; time not the expected format | `InvalidParameter.Format` / `AclParamError` / `Cert*Error` / `DefenseIpBlacklistIpInvalid` |
| 7 | **Region value** | `RegionId` not `cn-hangzhou` / `ap-southeast-1` | `InvalidParameter` / `InvalidRegionId` |
| 8 | **Nested / array notation** | SDK: missing `Rules.1.` prefix; CLI: passing a JSON blob where discrete flags are expected | `InvalidParameter` / param dropped |
| 9 | **Cross-parameter dependency** | e.g. `HstsPreload=true` but `HstsIncludeSubDomain!=true`; `AccessType` implies other required fields | `InvalidIncludeSubDomainWithPreload` / conditional `MissingParameter` |
| 10 | **Value well-formed but nonexistent** | Correct format, but the `InstanceId` / `TemplateId` / `Resource` does not exist in that region | `*NotExist` / `InvalidInstanceId.NotFound` — **not** a format bug; verify the ID and region |

> Dimensions 1–9 are true parameter defects this skill fixes. Dimension 10 means the parameter *shape* is
> right but the referenced object is absent — say so and point the customer at verifying the ID/region rather
> than "reformatting" a correct value.

## Worked example

Customer (CLI, WAF 2.0): `aliyun waf-openapi create-domain --Domain www.a.com --InstanceId waf_x --IsAccessProduct true`
Error: `InvalidParameter`.

1. Version: `create-domain` → WAF 2.0, needs `--api-version 2019-09-10`. **Missing → dimension 1.**
2. Name/style: `--Domain` / `--InstanceId` are PascalCase flags → unknown in plugin mode; must be
   `--domain` / `--instance-id`. **Dimension 2.**
3. Type: `IsAccessProduct` is `integer` (`0`/`1`), not `true`. **Dimension 4.**
4. Required: `SourceIps` and `HttpPort`/`HttpsPort` are needed for onboarding. **Dimension 3.**

Corrected call is assembled from all four findings (the corrected-call templates are linked from SKILL.md).
