# Scenario Description: WAF OpenAPI Error Diagnosis

The source-of-truth document for this skill's scenario: what problem it solves, how it decomposes, and where
each piece of domain knowledge came from.

## 1. Problem Statement

A developer or operator calls an Alibaba Cloud WAF OpenAPI — via the Aliyun CLI plugin, an SDK, or raw RPC —
and the call fails. They report things like:

- "调用 WAF OpenAPI 报错 InvalidParameter / MissingParameter，不知道哪个参数错了";
- "WAF API 调用报错，参数明明按文档填了还是失败";
- "`aliyun waf-openapi create-domain` returns an error — which parameter is wrong?";
- "This command is not available in the current API version (2021-10-01)".

The skill answers exactly one question: **which request parameter — by name, format, value, or required-ness —
deviates from the official spec for that action and version, and what is the corrected call.** It covers both
WAF generations:

- **WAF 2.0** — API version `2019-09-10`, domain/CNAME-centric
  (https://api.aliyun.com/document/waf-openapi/2019-09-10/overview);
- **WAF 3.0** — API version `2021-10-01`, object/template/rule-centric
  (https://api.aliyun.com/document/waf-openapi/2021-10-01/overview).

> WAF 2.0 actually spans six version strings (`2016-03-10` … `2021-07-27`), but only `2019-09-10` (2.0) and
> `2021-10-01` (3.0) are documented on the public portal, so those two are the spec source for a customer-facing
> diagnosis. `2021-07-27` is **WAF 2.0** despite its year — never infer the generation from the version year.

It is a **static, read-only** diagnosis of the request against the published parameter spec. It does not
execute write actions, does not change any WAF configuration, and needs no credentials for the core diff.

## 2. Objects Involved

```
Failing call
  ├── channel: CLI plugin | SDK | raw RPC | portal
  ├── version: 2019-09-10 (WAF 2.0) | 2021-10-01 (WAF 3.0)
  ├── action:  e.g. CreateDomain (2.0) | CreateDefenseRule (3.0)
  ├── params:  the names + values actually sent
  └── error:   Code + Message (+ RequestId)
                    │
                    ▼
Authoritative spec (public metadata endpoint / `aliyun ... --help`)
  └── parameters[]: name, in, type, required, enum, example, format
```

## 3. Workflow Decomposition

**Gate — Classify the error first**: parameter-class (in scope) vs auth / RAM / throttling / not-purchased /
  server-side / transient (out of scope, route out before any tool call). Wrong-version counts as in scope.
**Phase 1 — Capture the failing call**: version, action, channel, params, error Code + Message + RequestId. Action
  and version are blocking; a missing message or redacted value is non-blocking.
**Phase 2 — Confirm action and version**: ask and wait when either is missing; a known cross-generation action
  may use only the unversioned discovery call before presenting both WAF choices.
**Phase 3 — Fetch the authoritative spec** for the explicitly confirmed action + version.
**Phase 4 — Diff param-by-param** across the 10 dimensions (version, name/style, required, type, enum, format,
  region value, nested/array notation, cross-param dependency, well-formed-but-nonexistent).
**Phase 5 — Locate the offender; invoke `--cli-dry-run` only when the customer requests verification.**
**Phase 6 — Emit the corrected call** in the same channel + version, repeating the exact Action and error code.

## 4. Knowledge Sources

| Knowledge | Source |
|-----------|--------|
| WAF 2.0 parameter specs | `https://api.aliyun.com/meta/v1/products/waf-openapi/versions/2019-09-10/apis/{Action}/api.json` |
| WAF 3.0 parameter specs | `https://api.aliyun.com/meta/v1/products/waf-openapi/versions/2021-10-01/apis/{Action}/api.json` |
| CLI plugin behaviour (`--api-version`, `--biz-region-id`, flag style) | `aliyun waf-openapi <action> --help` (plugin `aliyun-cli-waf-openapi`) |
| Error-code semantics | WAF common error codes / full error-code explanation and troubleshooting guide (help.aliyun.com) |
| Diagnosis portal for ambiguous RequestIds | https://next.api.aliyun.com/home |
| Endpoints / supported regions | `https://api.aliyun.com/meta/v1/products/waf-openapi/endpoints.json` (only `cn-hangzhou` & `ap-southeast-1`) |

## 5. Scope Boundaries

- **In scope**: parameter name / format / value / required-ness defects, and version mismatch, for any WAF
  OpenAPI action, in any channel.
- **Out of scope**: credential / signature problems, RAM permission denials, throttling, feature-not-purchased /
  edition limits, server-side 5xx, and the *behavioural* correctness of a successful call (e.g. "why is my rule
  not effective" → the rule-effectiveness skill; "why was this request blocked" → the block-reason skill).
