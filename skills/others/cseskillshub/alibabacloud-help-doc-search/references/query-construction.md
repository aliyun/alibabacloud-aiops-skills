# Query Construction Methodology

Unified guidance for constructing effective search queries against the Alibaba Cloud
help center with `scripts/aliyun_help.py`. It consolidates this skill's measured
search behavior, the retrieval-first methodology described in SKILL.md, and the
error-code workflow from SKILL.md. Apply it to every `search` invocation; the
same principles hold whether or not a product filter (`-p`) is used. Every query is
also scoped to exactly one `(site, language)` pair — see the next section.

## Site and language scope of a query

- The default scope is the `cn` portal in Chinese (`--site cn --lang zh`); omitting both
  flags reproduces it exactly. Switch scope only when the user asks for it: an explicit
  international-portal request, a non-Chinese document request, or a question about a
  product that only the other portal documents.
- Language and site are orthogonal dimensions: the `cn` portal also serves English, and
  the international site also serves Chinese. "The user wrote in Chinese" is therefore
  not evidence for choosing the `cn` portal.
- Write the query in the language of the chosen corpus. A Chinese query issued against
  an English corpus is accepted by the endpoint without an error and answers with
  unrelated hits (measured: one Chinese billing query returned a single unrelated
  document, another produced a whole-corpus match of 13618 items), so translate the
  terms first; the script additionally warns on stderr when it detects this mismatch.
- Never answer a scoped question by re-running the same query on the other portal. The
  two portals document different products, regions, prices and compliance rules; a
  cross-portal "something" is a wrong answer, not a fallback. An empty scoped result
  means the topic is not documented on that portal, and the answer should say so.
- Product codes are per portal: verify a code with `list-products` run with the same
  `--site`/`--lang` before trusting a negative result. Only five aliases are normalized
  by the script (`PRODUCT_CODE_ALIASES`); everything else must already be a real slug.

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
| Difference between two instance families, asked colloquially | colloquial literal: `search "difference"` | documentation terminology + product filter: `search "instance type family" -p ecs` |
| Whether another account can read a bucket, asked colloquially | colloquial full sentence: `search "can others read my bucket"` | terminology + product filter: `search "cross-account access bucket policy" -p oss` |

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
- **Chinese colloquial wording bridge.** When a query carries a translated or
  colloquial Chinese error description (e.g. signature mismatch / missing access key /
  request throttled),
  the script prints an INFO hint mapping it to the canonical CamelCase code
  (e.g. SignatureDoesNotMatch) — rerun `search` with that code verbatim for the
  narrative troubleshooting documents. The bridge only hints; it never rewrites the
  query itself.

## Result-feedback rephrasing

When the first round comes back empty or off-topic, do not repeat the same query:

1. Inspect whatever partial results did come back — the terms in their titles and in
   the `categoryName`/product fields reveal the terminology the documentation actually
   uses for this topic.
2. Rebuild the query from those terms (replacing the weak token with the observed
   official term), keeping the product filter if it was correct.
3. If still empty, degrade along the chain: narrow (product-scoped) → broad (drop
   `-p`) → rephrase with synonyms; as a final fallback use WebSearch scoped to the
   portal that was asked for — `site:help.aliyun.com` for a `cn` query, or
   `site:www.alibabacloud.com/help/` for an `intl` query (optionally narrowed with
   `/{lang}/{product_code}/`). Never widen the fallback to the other portal.

This feedback loop complements the automatic alias expansion: the script covers
known alias pairs mechanically, while rephrasing from observed result terminology
covers topics that no dictionary anticipates.

## Index-leg phrasing and the bilingual vocabulary (F3, F6)

- The index leg now ranks by coverage, so a query phrased differently from the titles is no
  longer hopeless. Keep it to the concept words anyway: a partial match has to cover at least a
  third of the query's tokens before it counts.
- An error code, a parameter name or a quota number is never recalled from the index leg; that
  is the metadata leg's job, and an empty answer for such a query says so out loud.
- For an English corpus, write the query in English. The script maps a Chinese query onto
  documented English wording when it recognises the terms and says so; when it recognises
  none, it declines the English full-text leg instead of returning noise.
