# RAM Permission Declaration — alibabacloud-migration-cas-cutover-review

> This document explicitly declares the RAM (Alibaba Cloud Resource Access Management) permissions this skill requires during runtime,
> to facilitate audit and compliance review. Reference standard: "Tool-Invocation Skill Review Standard §1.1.2 RAM Permission Declaration".

## Conclusion

**The RAM permissions required by this skill are empty (`required_permissions: []`).**

This skill is a pure local CLI-script tool that **does not initiate any cloud-service API calls** at runtime, so it **does not need
any Alibaba Cloud RAM account, AK/SK, STS Token, or RAM role**.

## required_permissions List

```yaml
required_permissions: []   # empty — no RAM permissions required
```

| Cloud service | Action | Resource scope | Required |
|--------|--------|---------|---------|
| (none) | (none) | (none) | ❌ not required |

## Basis for Determination

### 1. Does not call any Alibaba Cloud OpenAPI

- All dependencies of the script `scripts/cutover_reviewer.py` are local libraries: `openpyxl`, `argparse`,
  `json`, `os`, `re`, `sys`, `signal`, `threading`, `datetime` (Python standard library + 1 third-party package)
- The code **does not contain** cloud-SDK references such as `aliyunsdk*` / `alibabacloud*` / `oss2` / `boto3`
- The code **does not contain** network calls such as `requests` / `urllib.request` / `http.client`

You can verify with a single command:

```bash
cd scripts
grep -rE "(aliyunsdk|alibabacloud|oss2|boto3|requests\.|urllib\.request|http\.client)" . || echo "No cloud SDK / network calls found"
```

### 2. Does not depend on any MCP tool

- The "MCP Tool List" section of SKILL.md already declares **no MCP dependency**
- Does not call any external interface / third-party API / Webhook

### 3. Does not read credential files

- The code **does not contain** logic to read `~/.aliyun/config.json` / `~/.aws/credentials` /
  environment variables `ALIBABA_CLOUD_ACCESS_KEY_*` / `AK` / `SK`, etc.
- It never touches any of the user's credential files

### 4. Only operates on the local file system

| Operation | Target | Permission requirement |
|------|------|---------|
| Read | user-specified `.xlsx` file | OS file-read permission (not RAM) |
| Write | `.md` / `.json` reports in the user-specified `-o` output directory | OS file-write permission (not RAM) |
| Network | none | — |
| Cloud service | none | — |

## Least-Privilege Principle Comparison

| Check item | Conclusion |
|-------|------|
| Calls cloud-service API | ❌ No |
| Needs a RAM account | ❌ No |
| Reads AK/SK | ❌ No |
| Needs STS Token | ❌ No |
| Needs RAM role assumption (AssumeRole) | ❌ No |
| Involves returning sensitive data to the cloud | ❌ No |

## Applicability Statement

This skill **does not belong** to the AIOps domain (AIOps-domain skills usually need RAM permissions for services such as CloudMonitor / ARMS / ActionTrail).
This skill belongs to the **document-review domain**; it only does structure matching and keyword detection on local `.xlsx` files
and produces local Markdown/JSON reports.

Therefore, strictly speaking, §1.1.2 of the standard **does not mandatorily apply** to this skill; this document is a **proactive supplementary declaration**
to improve audit readability and compliance transparency.

## Data Scope Declaration (§1.5 desensitization coverage)

**The data scope this skill processes does not cover end-user-level PII**, so PII such as ID numbers, bank-card numbers,
medical-insurance numbers, passport numbers, and license-plate numbers is not included in the desensitization regex list. The basis is as follows:

### 1. Business attributes of the input data

The only input of this skill is the **cutover manual `.xlsx`** — this is an **infrastructure ops document** written by SRE / DBA / ops teams
in cloud-migration and data-stack-migration scenarios, with content strictly limited to:

| Legal content category | Example |
|------------|------|
| Infrastructure identifiers | instance ID (rm-*/r-*/dds-*), IP, port, intranet domain, DNS record |
| Ops-personnel info | employee ID, name, corporate email, office phone (not customer info) |
| Process steps | work phase, operation item, start/end time, time cost, dependencies |
| Rollback actions | trigger conditions, execution steps, owner, verification method |
| Domain list | source resolution, Alibaba Cloud resolution, switch status |

### 2. Data that explicitly does **not** appear

Per cutover-manual industry standards and business definitions, the following PII types **do not belong** to legal cutover-manual content:

| PII type | Why it does not appear |
|---------|----------|
| ID number | customer real-name data, belongs to the business database, not an ops object |
| Bank-card number / payment account | payment-business data, forbidden in ops documents |
| Medical-insurance / social-security number | business data, not within the cutover-step description scope |
| Passport number / license-plate number | same as above |
| Customer's real name | same as above |

### 3. Desensitization dimensions already covered (ops perspective)

The `redact_text()` in `scripts/cutover_reviewer.py` already covers **ops-level sensitive info**, meeting
the MUST-level requirements of §1.5:

| Type | Regex | Format after desensitization |
|------|------|----------|
| IPv4 address | `\b(?:\d{1,3}\.){3}\d{1,3}\b` | `***.***.***.***` |
| Email | username + `@domain` | `***@domain` (keeps the domain for audit) |
| Phone number | mainland 11-digit `1[3-9]\d{9}` | `***********` |
| Cloud instance ID | `rm-/r-/dds-/gp-/dts-/pc-/redis-/mysql-/kvstore-/drds-/polardb-/mongodb-` | `prefix-***` |
| Intranet domain | `*.internal / *-inc.com / *.work / *.corp / *.local` | `***.internal` |

### 4. Exception-handling convention

If, during review, customer PII is **unexpectedly found** in the manual (a very rare scenario, e.g., the author
pasted business sample data for a demo against the rules), the handling process is:

1. **Manual review must intervene**: the script will not auto-desensitize PII; the user must remove it and re-run
2. On termination, the Agent must clearly note: "the report may contain unrecognized PII; please perform manual
   desensitization confirmation before external release"
3. If such scenarios become common in the future, re-evaluate whether to incorporate PII regexes at the code level (updating
   this declaration and unit tests accordingly)

### 5. Scope of commitment

- This declaration is limited to the **compliance-review dimension** and does not constitute an absolute commitment to business-data security
- The user is responsible for ensuring the input cutover manual conforms to ops-document standards and does not carry customer PII
- If a data leak occurs, responsibility is determined by the actual input content and the user's operations

## Change and Maintenance

- If cloud-service calls are added in the future (e.g., directly reading a manual from OSS, integrating with ARMS alerts),
  this document **must be updated synchronously and re-submitted for permission review**.
- If an MCP tool dependency is added, it must be listed bidirectionally in the "MCP Tool List" of SKILL.md and in this document.

---

*Last updated: 2026-05-14*
*Document version: v1.0 — initial declaration*
