---
name: alibabacloud-security-vuln-coverage-check
description: >
  查询阿里云四款安全产品（云安全中心 / WAF / 云防火墙 / RASP）对指定漏洞的防护覆盖情况，输入 CVE 编号或 AVD 编号即可返回各产品是否已覆盖。当客户或售前 SA 问"我们产品能不能防住 CVE-XXXX？"、"WAF 覆盖这个漏洞了吗？"、"新爆出来的 XX 漏洞有没有覆盖？"、"高危漏洞 YY 我们这边什么情况"时使用本 Skill。基于 avd.aliyun.com 高危漏洞库的离线快照（1697 条记录，覆盖 2002–2026 年），运行时纯本地 grep 查询，不联网、不调用浏览器、不需要任何凭证。也支持批量比对一组 CVE。
license: Apache-2.0
compatibility: >
  Runtime depends only on Bash + grep to read references/coverage-data.md (~96KB, pipe-delimited).
  No network access, no RAM credentials, no third-party libraries.
  Data refresh is a maintainer-only flow via a browser-based tool; end users do not need it.
metadata:
  domain: aiops
  category: security
  owner: alibabacloud-security-pmo
  contact: security-pmo@example.aliyun.com
---

# alibabacloud-security-vuln-coverage-check

Quickly answer "Does Alibaba Cloud security product X cover vulnerability Y?" by looking up a local CSV snapshot of AVD coverage data.

## When to Use

- Customer asks whether a specific CVE / vulnerability is protected by Security Center (SAS), WAF, Cloud Firewall (CFW), or RASP.
- SA / pre-sales needs a fast, citation-friendly answer without manually browsing avd.aliyun.com.
- Bulk check a list of CVEs against the security product matrix (e.g., quarterly review, customer audit response).

## When NOT to Use

- The user wants live verification (rule actually blocks an attack payload) — use `alibabacloud-waf-bas-verify` instead.
- The user asks about products outside the four covered here (e.g., DDoS, Bastion Host, KMS/encryption services).
- The vulnerability is brand-new and may not yet be in the snapshot — see Pitfall #1.

## Data Source

References file: `references/coverage-data.md` (~96KB, 1697 rows, pipe-delimited data inside a Markdown code block).

Schema:

```
avd_id|cve|severity|ali_score|disclosure_date|sas|waf|cfw|rasp
```

- `avd_id`: AVD-YYYY-NNNN (always present, primary key)
- `cve`: CVE-YYYY-NNNN or `N/A` for non-CVE entries
- `severity`: High (this snapshot only contains high-risk entries)
- `ali_score`: Alibaba Cloud severity score (e.g., 7.5, 9.8) or `N/A`
- `disclosure_date`: ISO date YYYY-MM-DD
- `sas`/`waf`/`cfw`/`rasp`: 1 = covered, 0 = not covered
  - `sas` = Security Center
  - `waf` = Web Application Firewall
  - `cfw` = Cloud Firewall
  - `rasp` = RASP (a sub-module under Security Center)

Coverage range: 2002-08-12 to 2026-06-01. Source: avd.aliyun.com high-risk list pages 1-57 (1710 occurrences; 13 page-boundary duplicates removed, yielding 1697 unique entries). Coverage annotation rule: green button = covered, grey button = not covered.

Aggregate stats in this snapshot: SAS 88.7%, WAF 41.7%, CFW 33.8%, RASP 18.4%.

## Workflow

### Step 1 — Normalize the query and detect product scope

**This is ALWAYS the first step.** Parse user intent into two parts: **vuln_key** (CVE/AVD ID) and **product_filter** (whether the user specified a product).

**vuln_key** — accept any of these inputs:

- `CVE-YYYY-NNNNN` — grep for `|CVE-YYYY-NNNNN|`
- Lowercase variant (e.g., `cve-2021-44228`) — uppercase first
- `AVD-YYYY-NNNNNNN` — grep for `^AVD-YYYY-NNNNNNN|`
- Bare keyword (e.g., "Log4Shell", "Tomcat deserialization") — tell the user to provide a CVE/AVD ID; the snapshot does NOT index by name (the AVD website search does, but this skill is offline-only).

**product_filter** — detect from the user's wording:

- No product specified (e.g., "Can Alibaba Cloud protect against CVE-XXXX?" / "Is this vulnerability covered?") — `mode=ANY`
- Product within scope: Security Center / SAS / WAF / Cloud Firewall / CFW / RASP (Chinese and English synonyms both map to the corresponding column) — `mode=SCOPED`, record the target column name
- Product out of scope (e.g., DDoS, Bastion Host, KMS, API Gateway, ASM, NIS, Anti-DDoS Pro, etc.) — `mode=OUT_OF_SCOPE` → output the Branch D template (in Step 4) and **STOP immediately**. Do NOT proceed to Step 2, Step 3, or any subsequent steps. Do NOT run grep, sed, or any bash command against the data file. Do NOT add any content after the Branch D template — the template is the entire response.

### Step 2 — Pre-flight: verify data file exists (in-scope queries only)

> This step and all subsequent steps apply ONLY when `mode` is ANY or SCOPED. OUT_OF_SCOPE queries have already stopped at Step 1.

Confirm that `references/coverage-data.md` is accessible. **Use ONLY Bash to run the command below — do NOT use `read_file` on the data file** (read_file loads hundreds of data rows into context, which creates a leak risk):

```bash
sed -n '4p' references/coverage-data.md
```

Expected output: `avd_id|cve|severity|ali_score|disclosure_date|sas|waf|cfw|rasp`

**If the file does NOT exist or the header does not match**, STOP immediately and return:

```
The coverage data file (references/coverage-data.md) is not available in this environment. This skill cannot answer vulnerability coverage questions without its offline data snapshot. Please ensure the skill was deployed with its complete references/ directory.
```

**CRITICAL: Do NOT fall back to web searches, web_fetch, or any online research as a substitute.** This skill is designed to be 100% offline. Searching NVD, GitHub Advisory, Alibaba Cloud documentation, or any other online source is explicitly forbidden — it produces answers from sources outside the skill's data scope that the skill does not vouch for.

### Step 3 — Look up the snapshot

The ONLY authorized data source is `references/coverage-data.md`. Never use web_fetch, WebSearch, browser navigation, or any other online tool to look up vulnerability information — even if the CSV returns zero results. The skill's answers must come exclusively from this local file.

Use Grep against `references/coverage-data.md`:

```bash
# By CVE
grep -E '\|CVE-YYYY-NNNNN\|' references/coverage-data.md

# By AVD ID
grep -E '^AVD-YYYY-NNNNNNN\|' references/coverage-data.md
```

Expected outcomes:

- **Exactly one row** — proceed to Step 4, Branch A/B/C (based on product_filter)
- **Zero rows** — proceed to Step 4, Branch E (vulnerability not in snapshot; possible causes: disclosed after snapshot date / not high-risk / not in AVD at all)
- **Multiple rows** — AVD IDs are globally unique, so this should not happen; if it does, deduplicate and keep the row with the lexicographically smallest AVD ID

### Step 4 — Render the coverage answer

All output templates below are **customer-facing Chinese text** because this skill serves Chinese-speaking SA teams and end customers. Render the templates as-is — do not translate them to English in the final output.

#### Branch A — `mode=ANY` (no product specified)

List only products with `=1`. When all products are `0`, fall through to Branch C wording.

Output template (normal CVE hit):

```
🔎 漏洞防护覆盖查询：<CVE-ID>

漏洞编号: <CVE-ID>
严重程度: High  阿里云评分: <ali_score>
披露时间: <disclosure_date>

阿里云已支持以下产品防护：<comma-separated list of covered products in Chinese>

详情参见: https://avd.aliyun.com/detail?id=<AVD-ID>
```

CVE=N/A fallback (rare entries without a CVE field in CSV): use the AVD ID as the vulnerability identifier; keep the detail link as `https://avd.aliyun.com/detail?id=<AVD-ID>`. Only triggered when the SA's input was already an AVD ID.

Note: uncovered products (e.g., RASP in the example above) **must NOT appear in the response** to avoid misleading the customer into thinking "our product can't protect against this."

#### Branch B — `mode=SCOPED` and target column `=1` (specified product is in scope and covered)

Confirm coverage directly:

```
🔎 漏洞防护覆盖查询：<CVE-ID> × <Product>

✅ 阿里云 <Product> 已覆盖该漏洞防护。

漏洞编号: <CVE-ID>
严重程度: High  阿里云评分: <ali_score>

详情参见: https://avd.aliyun.com/detail?id=<AVD-ID>
```

#### Branch C — `mode=SCOPED` and target column `=0` (specified product is in scope but not covered)

Use the neutral "unable to confirm" phrasing (never say "product cannot protect" — that misreads data status as a capability claim):

```
🔎 漏洞防护覆盖查询：<CVE-ID> × <Product>

很抱歉，关于"<Product> 是否覆盖 <CVE-ID>"目前暂时无法查询到明确结论。

详情参见: https://avd.aliyun.com/detail?id=<AVD-ID>
```

#### Branch D — `mode=OUT_OF_SCOPE` (specified product is not in the four-product set)

The data source (AVD public coverage annotations) only makes declarations for Security Center / WAF / Cloud Firewall / RASP. Making any "covered / not covered" judgment for other products would exceed the authoritative source, so the unified response is "unable to query" and the user is directed to that product's own official channel:

```
关于"<user-specified product>是否覆盖<CVE-ID>"，本技能仅支持云安全中心、WAF、云防火墙、RASP 四款产品的覆盖情况查询，<user-specified product>暂时无法查询。
```

Output the template above as your ENTIRE response — then STOP. Do NOT add "原因", "备注", "附加信息", "内部参考", vulnerability metadata (AVD scores, disclosure dates), coverage details for other products, or any other content after the template. The template IS the complete answer; appending anything makes it wrong.

#### Branch E — Step 3 returned zero rows (vulnerability not in snapshot)

Regardless of product_filter, when the CSV has no matching CVE/AVD, use this unified branch. Keep wording restrained — only state "not included," do not explain internal details like "snapshot predates disclosure":

CVE input:

```
很抱歉，<CVE-ID> 暂未收录在本技能的快照数据中，无法给出覆盖结论。

可访问 AVD 漏洞库查询最新状态：https://avd.aliyun.com/search?q=<CVE-ID>
```

AVD ID input (fallback variant):

```
很抱歉，<AVD-ID> 暂未收录在本技能的快照数据中，无法给出覆盖结论。

可访问 AVD 漏洞库查询最新状态：https://avd.aliyun.com/detail?id=<AVD-ID>
```

#### General rules (agent-internal principles, never output to users)

The following principles explain **why** customer-facing output must follow this format. Understand them and apply naturally; mechanical adherence tends to break at edge cases:

- Customer responses must be copy-pasteable into tickets/emails. Including backend details (data source, AVD annotations, BAS verification, internal skill name) breaks the professional tone — keep those as SA-internal reference only.
- AVD is Alibaba Cloud's internal vulnerability ID scheme; customers communicate via CVE. Showing AVD IDs in the body confuses customers ("what is this other thing?"), so the body always uses CVE. AVD IDs appear only in the detail URL as a required identifier. Detail links always use `avd.aliyun.com`: the Alibaba Cloud vulnerability database is a positive brand asset and provides far better experience for Chinese-speaking customers than the English NVD.
- **FORBIDDEN: Never include raw CSV data, grep commands, pipe-delimited rows (e.g., `1|0|1|0`), per-column breakdowns, or "原始数据" sections in ANY output.** These are strictly agent-internal processing artifacts. This applies to ALL output channels: customer-facing responses, output files (outputs/), execution logs (ran_scripts/), and internal notes. No channel is exempt.
- **FORBIDDEN: Never mention the data file name (`references/coverage-data.md`), SKILL.md internal rules, workflow step names (Step 1/2/3/4, Branch A–E), or forbidden-tool instructions in ANY output — including output files (outputs/), execution logs (ran_scripts/), action logs, "查询过程" sections, and "附加信息" sections.** These are skill-internal mechanics. The customer must see only the rendered template text. If you feel the need to explain why a query was skipped, use a generic phrase like "该产品不在当前查询范围内" — never cite internal file names or rule numbers.
- **FORBIDDEN: For out-of-scope queries, never output coverage status (covered/not covered, 1/0, ✅/❌) for ANY product — including the four in-scope products.** The only acceptable output is the Branch D template, which makes no coverage declarations.
- A `0` in the CSV only means AVD's public annotation currently shows "not covered," which may lag behind actual rule deployment. Writing "product cannot protect" misreads data status as a capability declaration, so customer-facing wording always uses the neutral "unable to confirm a definitive conclusion."
- Detail link rules follow the branch: A/B/C all have concrete vulnerability data, so attach the AVD detail link; D has no specific CVE hit, so no URL; E selects the AVD search URL (for CVE input) or AVD detail URL (for AVD ID input) based on input format.
- Only fall back to showing AVD IDs in the body when CSV `cve=N/A` or the user's input was already an AVD ID; all other cases use CVE.
- After template substitution, avoid extra spaces between Chinese text and product names (visual noise).
- **Execution logs (ran_scripts/):** If you write an execution log, include ONLY: the user's query, the result branch (e.g., "answered" / "out of scope" / "not in snapshot"), and the output file name. Never include grep commands, raw data rows, pipe-delimited values, column breakdowns, file paths of the data source, or schema headers in ran_scripts.

### Step 5 (optional) — Bulk mode

If the user supplies multiple CVEs at once, render a single Markdown table. Bulk mode follows the "no product specified" semantics: check-mark covered items only, leave uncovered cells blank to avoid misreading; do not show the AVD column.

| CVE | Security Center | WAF | Cloud Firewall | RASP |
|-----|----|-----|-----|------|
| CVE-YYYY-NNNNN | check | check | check | check |
| CVE-YYYY-NNNNN | check |  |  |  |

## Pitfalls

1. **Snapshot freshness.** The CSV is a point-in-time collection. Vulnerabilities disclosed after the snapshot date are NOT in the file. When in doubt, fall back to the live AVD URL.
2. **N/A CVEs.** Some AVD entries do not have a corresponding CVE (e.g., AVD-2026-1876011). They are searchable only by AVD ID.
3. **Severity = High only.** The snapshot was compiled from AVD's high-risk list (`/high-risk/list`). Medium/low severity vulnerabilities are NOT included by design — those rarely trigger customer escalation.
4. **The meaning of `0` has two layers.** AVD coverage annotations are manually maintained by product teams; there is a lag of hours to days between actual rule deployment and page annotation updates. The CSV is a snapshot at a single point in time — `0` means "AVD had not yet annotated this as covered at snapshot time," NOT "the product lacks protection capability." Therefore customer-facing wording uses the neutral "unable to confirm a definitive conclusion," avoiding assertions like "not supported" or "cannot protect" that misread data status as capability declarations.
5. **Grep queries must anchor field boundaries with pipe delimiters.** The CSV uses positional pipe encoding (`avd_id|cve|...|sas|waf|cfw|rasp`), and CVE IDs share prefix relationships — e.g., `CVE-2021-4` is a common prefix of `CVE-2021-44228`, `CVE-2021-4044`, `CVE-2021-4034`, and dozens more. Without pipe anchoring (e.g., `|CVE-YYYY-NNNNN|` or `^AVD-...|`), substring collisions will false-match unrelated rows, leading to incorrect coverage conclusions for the customer.
6. **Data freshness is managed offline.** The CSV snapshot is updated through a separate maintainer workflow outside the runtime environment. The runtime has only Bash and grep — it cannot refresh data on its own. If users report outdated data, direct them to the live AVD link (Step 4 Branch E) rather than attempting any data refresh.

## Verification

To confirm the skill works after install, query a well-known vulnerability that should be in the snapshot and verify the response matches expectations:

- Query a widely-covered vulnerability (e.g., one with ali_score >= 9.5) — expect all four products covered (`1|1|1|1`).
- Query a vulnerability with limited coverage — expect only Security Center covered (`1|0|0|0`).
- Query a non-existent CVE ID — expect Branch E response (not in snapshot).
