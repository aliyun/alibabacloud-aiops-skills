# Query Construction Methodology

Unified guidance for constructing effective search queries against the Alibaba Cloud
help center with `scripts/aliyun_help.py`. It consolidates this skill's measured
search behavior, the retrieval-first methodology described in SKILL.md, and the
error-code workflow from SKILL.md. Apply it to every `search` invocation; the
same principles hold whether or not a product filter (`-p`) is used.

## Query construction principles

- **Extract core entities and attributes.** Keep the product/feature entity (e.g. an
  instance family name, a storage class, a networking concept) and the attribute being
  asked about (billing, quota, configuration, troubleshooting); drop conversational
  filler such as "how do I", "please tell me", "what is the difference between" —
  retain only the terms that index titles and summaries.
- **Prefer documentation/API terminology over colloquial wording.** Document titles and
  summaries use official terminology, so terminology-based queries match far better
  than paraphrases. When the user phrases something colloquially, translate it to the
  documented term before searching.
- **Split multi-intent questions into multiple queries.** One query should carry one
  intent; "billing and quotas and best practices" is three queries, not one. Combined
  queries dilute relevance and frequently return nothing.
- **Keep the query short and keyword-like.** Two to five terms is the sweet spot;
  full sentences rarely match. The backend is keyword-oriented, not conversational.
- **Scope with `-p` when the product is known.** Product-scoped search uses server-side
  category filtering plus a fused index leg and is far more precise; use the unscoped
  path mainly as a retry when the scoped search comes back empty.

## Good vs. weak queries

| User intent (gist) | Weak query | Good query |
|---|---|---|
| Difference between two instance families | colloquial paraphrase: `search "difference"` | documentation terminology + product filter: `search "g6 c6 instance family" -p ecs` |
| What machine options exist | vague noun: `search "machines" -p ecs` | terminologized entity: `search "instance type family" -p ecs` |
| Charging for a stopped pay-as-you-go instance | fragmented verbs: `search "stop charge" -p ecs` | full terminology chain: `search "pay-as-you-go stopped instance billing" -p ecs` |
| Cross-account access to a bucket | colloquial sentence: `search "let another account read my bucket"` | terminology + product filter: `search "cross-account access bucket policy" -p oss` |
| Why a CDN request returns 502 | bare symptom in prose: `search "my website is broken"` | symptom token + product filter: `search "502" -p cdn` |

Pattern: weak queries are colloquial paraphrases or bare filler; strong queries are
documentation terminology, keyword-like, optionally combined with a product filter.

## Alias and synonym expansion

Product names appear in two forms — the short code-like alias (e.g. EIP, SLB, OSS) and
the full official product name in the local language — and documentation titles may use
either, which historically caused empty results when the query used one form while the
documents used the other.

The script handles this automatically:

- A built-in bidirectional alias dictionary (`QUERY_SYNONYMS` in
  `scripts/aliyun_help.py`) maps high-frequency product alias pairs (short alias and
  full official name) to each other. The dictionary performs alias-level expansion
  only — never general translation.
- **Original query first.** The query as written is always searched first. Only when
  the result count is below the low-result threshold (2) and the dictionary can
  generate a different expanded query does the script retry once with the expansion
  term appended, then merge and deduplicate both rounds by normalized URL. Every
  expansion retry leaves an INFO trace on stderr.
- Expansion applies to both product-scoped and unscoped paths and follows the current
  path semantics (including the fused full-text + index legs).
- Official product codes can be verified at any time with `list-products`, which
  prints every valid help-center code. Beware of non-obvious aliases: Function
  Compute's canonical code is `functioncompute` (not `fc`), and Elastic IP Address is
  an independent product with its own code rather than part of VPC.

## Error-code query guidance

- **Search error codes verbatim.** CamelCase error codes (e.g. SignatureDoesNotMatch,
  InvalidAccessKeyId) should be passed to `search` exactly as written — the script
  detects such CamelCase shapes in the query and notes on stderr that the query is
  treated as an error-code lookup; narrative troubleshooting documents explain common
  causes, impact, and remediation and are the right source for "why did I get this
  error and how do I fix it".
- **Use `api-info` for the contract-level list.** When an exhaustive, per-API error
  code enumeration is required (which codes can a specific API return, with HTTP
  status), use `api-info <product> <ApiName>` — the metadata enumerates codes
  authoritatively but without remediation context. The stderr hint printed on
  CamelCase detection points to this division of labor.
- Do not rewrite or translate error codes; partial or paraphrased codes break the
  match.

## Result-feedback rephrasing

When the first round comes back empty or off-topic, do not repeat the same query:

1. Inspect whatever partial results did come back — the terms in their titles and in
   the `categoryName`/product fields reveal the terminology the documentation actually
   uses for this topic.
2. Rebuild the query from those terms (replacing the weak token with the observed
   official term), keeping the product filter if it was correct.
3. If still empty, degrade along the chain: narrow (product-scoped) → broad (drop
   `-p`) → rephrase with synonyms; as a final fallback use WebSearch with
   `site:help.aliyun.com` (optionally scoped with `/zh/{product_code}/`).

This feedback loop complements the automatic alias expansion: the script covers
known alias pairs mechanically, while rephrasing from observed result terminology
covers topics that no dictionary anticipates.
