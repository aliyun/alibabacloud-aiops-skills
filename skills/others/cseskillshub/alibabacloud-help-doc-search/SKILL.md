---
name: alibabacloud-help-doc-search
description: |
  Search Alibaba Cloud official help documentation (help.aliyun.com) with relevance-ranked search, and verify OpenAPI contracts (parameters, error codes, RAM permission points) against api.aliyun.com metadata. Use when the user asks how to use or configure an Alibaba Cloud product, looks up an error code or asks what an error message means, checks quota or usage limits, asks about billing rules, wants best practices or troubleshooting guides, confirms API parameter semantics, or wants to read a specific help document. Triggers: Alibaba Cloud documentation, help center, help.aliyun.com, product how-to guide, error code meaning, what does this error mean, how to fix this error, quota and limits, billing rules, RAM permission point, API reference, troubleshooting guide, best practice, read help document. Do not use this skill to execute changes on cloud resources, or to diagnose a specific product incident when a dedicated product diagnosis skill is installed and applicable.
metadata:
  keywords:
    - 帮助文档
    - 官方文档
    - 阿里云文档
    - 查一下文档
    - 错误码什么意思
    - 报错代码怎么解决
    - 配额和限制是多少
    - 计费规则查询
    - RAM 权限点
    - API 参考
    - 排查指南
    - 最佳实践
    - 读文档
    - help document
    - error code
---

# Alibaba Cloud Help Documentation Search and OpenAPI Verification

Search and read official Alibaba Cloud documentation on help.aliyun.com, and verify
OpenAPI contracts against the public metadata of api.aliyun.com.

## Capabilities

### Full-text documentation search

Search help documents by keyword with relevance-ranked results, returning title, URL,
and summary. An optional product filter narrows results to a single product such as
OSS or ECS. Passing `-p` is strongly recommended: it makes the results far more
precise (server-side product filtering plus a fused index leg), though it issues
no fewer requests than the unscoped path and is only faster in degraded scenarios.

```bash
python3 scripts/aliyun_help.py search "cross-origin" -p oss
```

### Read document content by URL

Fetch the full body of a document as clean Markdown by its URL (the `.md` suffix is
appended automatically).

```bash
python3 scripts/aliyun_help.py read "https://help.aliyun.com/zh/ecs/user-guide/create-a-custom-image-from-a-snapshot-1"
```

### Browse product documentation catalog

List all products, or list the full document catalog of one product (titles, links, and
summaries grouped by category).

```bash
python3 scripts/aliyun_help.py list-products
python3 scripts/aliyun_help.py list-docs oss -n 50
```

### OpenAPI metadata verification

Verify exact API contract details — parameter names, types, required flags, error
codes, and RAM permission points — against structured metadata, which is more
authoritative than narrative documentation.

```bash
python3 scripts/aliyun_help.py api-products actiontrail
python3 scripts/aliyun_help.py api-list actiontrail lookup
python3 scripts/aliyun_help.py api-info actiontrail LookupEvents
```

## Execution rules

Help documentation is narrative and may lag behind the actual API behavior, while the
OpenAPI metadata reflects the live contract; when the two disagree, the metadata is
authoritative and the answer should note the source of each claim. Use documentation
search and reading for "how to" and "why" questions, and metadata verification for
"what are the exact parameters, error codes, or permission points" questions; combine
both when background explanation is needed. When a search returns no results, suggest
using WebSearch with the keyword plus `site:help.aliyun.com` (optionally scoped with
`/zh/{product_code}/`) for broader coverage, and retrying with synonyms is also worth
trying; additionally, empty results with `-p` should be rechecked via `list-products`
(the product code may be wrong) and a retry without the product filter before
concluding nothing exists. Every quoted document must be accompanied by its original
URL so the user can open the source directly. All network calls in the scripts have
explicit timeouts, so a slow or hung endpoint degrades gracefully instead of blocking.

For error codes and error messages, the preferred workflow is two-layered: first run a
documentation search with the exact error code or the original error text, because the
narrative troubleshooting documents explain the common causes, the impact, and the
step-by-step remediation; only when a contract-level, exhaustive list of error codes
for a specific API is required should the api-info metadata be consulted, since the
metadata enumerates codes authoritatively but without remediation context.

When the question is about a new feature, a recent change, or changelog-like content,
prefer results whose `updated` date (shown in both the JSON output and the rendered
lines as `(updated: YYYY-MM-DD)`) is recent enough to cover the feature in question,
and say so in the answer; index-leg entries legitimately carry no `updated` field, so
an absent date is not by itself a sign of staleness, and when nothing looks fresh
enough the claim should be flagged as possibly outdated.

Search keywords should be constructed following the methodology in
`references/query-construction.md` — extract core entities and attributes, prefer
documentation terminology over colloquial wording, split multi-intent questions into
separate queries, and rely on the script's built-in alias expansion, error-code
detection, and low-result expansion retry rather than ad-hoc paraphrasing.

ECS knowledge questions (instance types and instance families, billing modes, quotas
and limits, best practices, API reference) follow the retrieval-first workflow in
`references/ecs-scenario-guide.md`: construct terminology-based queries, degrade
narrow → broad → rephrase when results are empty, answer with the retrieved details
and source URLs, and never answer ECS facts from model memory without retrieval.

Inline invocation budget inside an agent: keep the default `-n` limit unless there is
a concrete reason to raise it, and always pass `-p` when the product is known — the
unscoped path scans hundreds of product indexes and takes 10–20 seconds, so it should
be used sparingly and mainly as a retry when a product-scoped search comes back empty.

## Helper script

The entry script is `scripts/aliyun_help.py` (Python 3 standard library only, no
dependencies). Subcommands: `list-products`, `list-docs`, `search`, `read`,
`read-product`, `api-products`, `api-list`, `api-info`, with `-n` result limits,
`-l` line limits, and `--json` machine-readable output where applicable.

```bash
python3 scripts/aliyun_help.py search "snapshot" -p ecs -n 10
```

## Observability

This skill performs only anonymous HTTPS GET requests to public endpoints and never
invokes the aliyun CLI or any credentialed API. The helper script sends a fixed
User-Agent header on every request (`Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7)
QoderWork/1.0`), and every backend degradation during search is logged as a WARN line
on stderr so the fallback path is always traceable. Because no credentialed CLI or API
calls are made, session-id correlation is not applicable to this skill.

## Internal references

Implementation details are documented in the references directory: search backend
architecture and degradation behavior in `references/search-backend.md`, help-center
product codes in `references/product-codes.md`, OpenAPI metadata endpoints in
`references/api-metadata.md`, the ECS documentation scenario workflow (retrieval-first
query construction, degradation chain, and answer format) in
`references/ecs-scenario-guide.md`, the unified query construction methodology
(principles, good/weak examples, alias expansion, error-code guidance, and
result-feedback rephrasing) in `references/query-construction.md`, the ECS knowledge
FAQ (instance families, billing, quotas, best practices quick answers) in
`references/ecs-knowledge-faq.md`, and the declaration that this skill requires no RAM
permissions (zero-credential, anonymous read-only access) in `references/ram-policies.md`.
