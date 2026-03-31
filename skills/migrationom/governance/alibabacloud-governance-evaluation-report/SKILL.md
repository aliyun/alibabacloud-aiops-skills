---
name: alibabacloud-governance-evaluation-report
description: |
  Alibaba Cloud Governance Center evaluation report skill.
  Use for querying governance maturity check results, generating structured risk reports, and account compliance analysis.
  Triggers: "云治理", "成熟度检测", "合规检查", "安全风险", "治理检测", "governance evaluation",
  "maturity check", "compliance report", "risk report", "governance center".
---

# Alibaba Cloud Governance Center Evaluation Report

Guide users to discover governance risks, focus on critical issues, and take remediation actions through a progressive drill-down workflow.

## Scenario Description

This skill is a **problem-discovery and resolution guide** — not a comprehensive audit report generator. It operates as a progressive disclosure funnel:

1. **Overview (quick diagnosis)** — Score + pillar distribution + top critical risks → guide user to choose a direction
2. **Pillar analysis (focused drill-down)** — All risks in a specific domain, controlled by severity → guide user to specific items
3. **Detail (deep dive)** — Single check item with full remediation steps → guide user to related items or resources
4. **Resources (action)** — Non-compliant resource listing for targeted remediation

Each layer focuses on **the most important information** and guides the user to the next level. Avoid information overload — keep output concise and actionable.

**Architecture**: `Governance Center API → CLI (aliyun governance) → governance_query.py (merge + cache) → JSON output → Agent report`

## How It Works

**Data Sources** — Three APIs provide all data:
1. `list-evaluation-metadata` — Check item definitions (name, description, pillar, level, remediation)
2. `list-evaluation-results` — Actual results (status, risk, compliance rate, score)
3. `list-evaluation-metric-details` — Non-compliant resource details for a specific check item

**Processing** — The script ([governance_query.py](scripts/governance_query.py)) merges data sources and caches results for 1 hour. It provides 4 query modes: `overview`, `pillar`, `detail`, `resources`.

**Output** — Structured JSON for Agent to generate user-friendly reports. Reports are output directly in the conversation as formatted text, NOT written to files.

---

## Prerequisites

> **Pre-check: Aliyun CLI >= 3.3.0 required**
> Run `aliyun version` to verify. If not installed or version too low,
> see [references/cli-installation-guide.md](references/cli-installation-guide.md) for installation instructions.
> Then **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

```bash
aliyun version                                    # >= 3.3.0
aliyun configure set --auto-plugin-install true   # Enable auto plugin install
python3 --version                                 # Python 3.x
```

## Authentication

Configure CLI authentication (OAuth recommended):

```bash
# OAuth mode (recommended)
aliyun configure --mode OAuth

## RAM Policy

Requires Governance Center read permissions. See [references/ram-policies.md](references/ram-policies.md) for full policy.

Minimum required permissions:
- `governance:ListEvaluationMetadata`
- `governance:ListEvaluationResults`

Or attach system policy: **AliyunGovernanceReadOnlyAccess**

## Parameter Confirmation

This skill has minimal user-specific parameters. The following may require confirmation:

| Parameter Name | Required/Optional | Description | Default Value |
|----------------|-------------------|-------------|---------------|
| `--profile` | Optional | Aliyun CLI profile name | Default profile |
| `-c, --category` | Required (pillar mode) | Pillar category name | N/A |
| `--id` | Required (detail/resources mode) | Check item metric ID | N/A |
| `--keyword` | Optional (detail mode) | Search keyword for check items | N/A |
| `--max-results` | Optional (resources mode) | Max results per page | 50 |

## Verification

Verify setup before use:

```bash
# Test CLI connection
aliyun governance list-evaluation-results \
  --user-agent AlibabaCloud-Agent-Skills \
  --cli-query "Results.TotalScore"

# Test script
python3 scripts/governance_query.py overview
```

See [references/verification-method.md](references/verification-method.md) for detailed steps.

---

## Core Workflow

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., `--profile`, `--category`, `--id`, `--keyword`,
> `--max-results`, etc.) MUST be confirmed with the user.
> Do NOT assume or use default values without explicit user approval.

> **IMPORTANT: Output Format** — Reports are format specifications for conversation output only.
> Always output report content directly in the chat message as formatted Markdown.
> Do NOT create or write report files (e.g., `.md`, `.txt`, `.html`). No file generation is needed.

Script location: [scripts/governance_query.py](scripts/governance_query.py)

### Global Options

| Option | Description |
|--------|-------------|
| `--refresh` | Force refresh cache (default: 1-hour TTL) |

---

### Mode 1: `overview` — Overall Maturity Report

**When to use**: User asks about overall account health, maturity score, or wants a summary.

```bash
python3 scripts/governance_query.py overview
python3 scripts/governance_query.py overview -r Error              # Only high-risk items
python3 scripts/governance_query.py overview -r Error,Warning      # High + medium risk
python3 scripts/governance_query.py --refresh overview             # Force fresh data
```

**Options**:

| Option | Description |
|--------|-------------|
| `-r, --risk` | Filter RiskyItems by risk level (comma-separated: `Error`, `Warning`, `Suggestion`). PillarSummary and RiskDistribution are always complete. |

**Output JSON fields**:
- `TotalScore` — Overall maturity score (0.0-1.0)
- `PillarSummary` — Per-pillar statistics (checked/risky counts, always unfiltered)
- `RiskDistribution` — Count by risk level (always unfiltered)
- `RiskyItems` — Items with risk, filtered by `--risk` if specified, sorted by severity
- `RiskFilter` — Applied risk filter values (only present when `--risk` is used)

**Report format**: Read [references/report-format-overview.md](references/report-format-overview.md) for the exact output format.

---

### Mode 2: `pillar` — Pillar-Specific Report

**When to use**: User asks about a specific domain (security, reliability, cost, etc.).

```bash
python3 scripts/governance_query.py pillar -c <Category> [options]
```

**Options**:

| Option | Description |
|--------|-------------|
| `-c, --category` | **Required**. Pillar name (see below) |
| `--risky` | Only show items with risk (exclude compliant) |
| `-l, --level` | Filter by recommendation level (comma-separated) |
| `-r, --risk` | Filter by actual risk level (comma-separated) |

**Category values**:
- `Security` — 安全
- `Reliability` — 稳定
- `CostOptimization` — 成本
- `OperationalExcellence` — 效率
- `Performance` — 性能

**Level values**: `Critical`, `High`, `Medium`, `Suggestion`

**Risk values**: `Error`, `Warning`, `Suggestion`, `None`

**Examples**:
```bash
# 安全支柱所有风险项
python3 scripts/governance_query.py pillar -c Security --risky

# 仅严重和高优先级的错误/警告
python3 scripts/governance_query.py pillar -c Security -l Critical,High -r Error,Warning --risky
```

**Output JSON fields**:
- `Category`, `CategoryCN` — Pillar name
- `MatchedCount` — Number of matched items
- `Items` — List of check items with status

**Report format**: Read [references/report-format-pillar.md](references/report-format-pillar.md) for the exact output format.

---

### Mode 3: `detail` — Check Item Detail

**When to use**: User asks about a specific check item or how to fix an issue.

```bash
python3 scripts/governance_query.py detail --id <metric-id>
python3 scripts/governance_query.py detail --keyword <search-term>
```

**Options**:

| Option | Description |
|--------|-------------|
| `--id` | Check item ID (e.g., `apbxftkv5c`) |
| `--keyword` | Search by name/description (if multiple matches, shows list) |

**Examples**:
```bash
# 按 ID 查询
python3 scripts/governance_query.py detail --id apbxftkv5c

# 按关键字搜索
python3 scripts/governance_query.py detail --keyword "MFA"
```

**Output JSON fields**:
- Basic info: `Id`, `DisplayName`, `Description`, `Category`
- Status: `Status`, `Risk`, `Compliance`, `NonCompliant`
- `Remediation` — Fix steps (Manual/Analysis/QuickFix)

**Report format**: Read [references/report-format-detail.md](references/report-format-detail.md) for the exact output format. The detail format also covers the resources listing when needed.

---

### Mode 4: `resources` — Non-Compliant Resources

**When to use**: User wants to see which specific resources failed a check item.

```bash
python3 scripts/governance_query.py resources --id <metric-id>
```

**Options**:

| Option | Description |
|--------|-------------|
| `--id` | **Required**. Check item ID |
| `--max-results` | Max results per page (default: 50) |

**Examples**:
```bash
# 查询未启用 MFA 的 RAM 用户列表
python3 scripts/governance_query.py resources --id apbxftkv5c

# 查询开放高危端口的安全组
python3 scripts/governance_query.py resources --id a9g6pv7r5b
```

**Output JSON fields**:
- `MetricId` — Check item ID
- `TotalCount` — Number of non-compliant resources
- `Resources[]` — List of resources:
  - `ResourceId`, `ResourceName`, `ResourceType`
  - `RegionId`, `ResourceOwnerId`
  - `Classification` — Risk classification
  - `Properties` — Resource-specific attributes

---

## Mode Selection Guide

| User says... | Use mode | Command | Report format |
|--------------|----------|---------|---------------|
| "查查我的账号安全吗" / "成熟度得分" / "分析下治理检测结果" | `overview` | `overview` | [overview](references/report-format-overview.md) |
| "有哪些高风险项" / "看下所有高风险" | `overview` | `overview -r Error` | [overview](references/report-format-overview.md) |
| "中风险以上的问题" | `overview` | `overview -r Error,Warning` | [overview](references/report-format-overview.md) |
| "安全方面有哪些问题" / "XX支柱的风险" | `pillar` | `pillar -c Security --risky` | [pillar](references/report-format-pillar.md) |
| "网络安全相关的检测项" / "数据库风险" | `pillar` + keyword filter | `pillar -c Security --risky` then filter by keyword | [pillar](references/report-format-pillar.md) |
| "高优先级的问题" | `pillar` | `pillar -c Security -l Critical,High --risky` | [pillar](references/report-format-pillar.md) |
| "MFA怎么修" / "XX检测项详情" | `detail` | `detail --keyword "MFA"` | [detail](references/report-format-detail.md) |
| "哪些用户没开MFA" / "不合规资源有哪些" | `detail` + `resources` | `detail --id xxx` then `resources --id xxx` | [detail](references/report-format-detail.md) |

**Default**: If user doesn't specify pillar or check item, use `overview`.

**Report format selection**: After determining the query mode, read the corresponding report format reference file before generating output. Only read the format file that matches the user's intent — do not read all format files at once.

## Field Reference

| Field | Values | Note |
|-------|--------|------|
| `Risk` | `Error`(高风险) > `Warning`(中风险) > `Suggestion`(低风险) > `None`(合规) | Actual detected risk |
| `RecommendationLevel` | `Critical` > `High` > `Medium` > `Suggestion` | Recommended priority |
| `Status` | `Finished` / `NotApplicable` / `Failed` | Check execution status |
| `Compliance` | 0.0 - 1.0 | 1.0 = fully compliant |

## Cache & Cleanup

Only metadata (check item definitions) is cached locally — results are always fetched in real-time.

- Cache location: `~/.governance_cache/metadata.json`
- TTL: 24 hours (metadata rarely changes)
- `list-evaluation-results` and `list-evaluation-metric-details` are **never cached**

```bash
# Force refresh metadata cache
python3 scripts/governance_query.py --refresh overview

# Clear cache manually
rm -rf ~/.governance_cache/
```

## Best Practices

1. **Focus, don't dump** — Each report layer should highlight what matters most, not list everything. Read the corresponding report format reference for quantity control rules
2. **Follow the funnel** — Start with `overview`, guide user to `pillar`, then to `detail`. Don't skip layers unless user explicitly asks for a specific item
3. **Use `--risky` filter for pillar mode** — Reduces noise by hiding compliant items when investigating issues
4. **Prioritize by Risk + Level** — Focus on `Error` risk with `Critical`/`High` recommendation level first
5. **Follow remediation guidance** — Use `detail` mode to get actionable fix steps before modifying resources
6. **Always guide next steps** — Every report must end with follow-up guidance based on actual data, helping users continue exploring
7. **Cache management** — Only metadata is cached (24h TTL); results are always real-time. Use `--refresh` to force metadata refresh

## References

| File | Content |
|------|---------|
| [report-format-overview.md](references/report-format-overview.md) | Report format: overall governance overview |
| [report-format-pillar.md](references/report-format-pillar.md) | Report format: pillar / keyword aggregated analysis |
| [report-format-detail.md](references/report-format-detail.md) | Report format: single check item detail + resources |
| [related-apis.md](references/related-apis.md) | CLI commands and API details |
| [ram-policies.md](references/ram-policies.md) | Required permissions |
| [verification-method.md](references/verification-method.md) | Verification steps |
| [cli-installation-guide.md](references/cli-installation-guide.md) | CLI installation |
