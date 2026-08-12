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

> **Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> use a package manager or the pinned, SHA256-verified packages in
> [references/cli-installation-guide.md](references/cli-installation-guide.md).
> Do not pipe a remotely downloaded installation script directly into a shell.
>
> Then [MUST] run `aliyun plugin update` to ensure that any existing plugins on your local machine are always up-to-date.
>
> **[MUST]** run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.

```bash
aliyun version                                    # >= 3.3.3
aliyun configure set --auto-plugin-install true   # Enable auto plugin install
python3 --version                                 # Python 3.x
```

## Observability

Every Alibaba Cloud API invocation made by this skill must include the complete
User-Agent template:

`--user-agent AlibabaCloud-Agent-Skills/{SKILL_NAME}/{session-id}`

For this skill, `{SKILL_NAME}` is
`alibabacloud-governance-evaluation-report`, so the concrete form is:

`--user-agent AlibabaCloud-Agent-Skills/alibabacloud-governance-evaluation-report/{session-id}`

Session ID rules:

1. Generate a new session ID once per session (one skill invocation) with
   `uuid.uuid4().hex`. It must be a 32-char hex UUID v4 value: exactly 32
   lowercase hexadecimal characters with no hyphens.
2. Reuse the same session ID for every Alibaba Cloud API call in that invocation,
   including direct CLI commands, helper-script calls, pagination, and retries.
3. Do not regenerate the session ID between related calls. Generate a new session
   ID only when a new skill invocation begins.
4. Set `ALIBABA_CLOUD_AGENT_SESSION_ID` to that 32-char hex session ID before running
   `governance_query.py`. The script validates and reuses the supplied UUID; when
   the variable is absent, it generates one 32-char hex UUID v4 per process and
   reuses it.
5. Never derive a session ID from account IDs, credentials, user data, or other
   sensitive values.

Before running `governance_query.py`, tell the user that it invokes the local
`aliyun` executable with their current CLI credentials and sends read-only
queries to Alibaba Cloud Governance Center. The script enforces a read-only
command allowlist, validates all dynamic arguments, and prints the resolved
executable and API action to stderr before each call.

## Authentication

Configure CLI authentication (OAuth recommended):

```bash
# OAuth mode (recommended)
aliyun configure --mode OAuth
```

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
  --user-agent AlibabaCloud-Agent-Skills/alibabacloud-governance-evaluation-report/{session-id} \
  --cli-query "Results.TotalScore"

# Test script
export ALIBABA_CLOUD_AGENT_SESSION_ID="{session-id}"
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
- `Security` — security and access controls
- `Reliability` — reliability and resilience
- `CostOptimization` — cost optimization
- `OperationalExcellence` — operational efficiency
- `Performance` — performance efficiency

**Level values**: `Critical`, `High`, `Medium`, `Suggestion`

**Risk values**: `Error`, `Warning`, `Suggestion`, `None`

**Examples**:
```bash
# All risky items in the Security pillar
python3 scripts/governance_query.py pillar -c Security --risky

# Only Critical/High-priority Error and Warning items
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
# Query by ID
python3 scripts/governance_query.py detail --id apbxftkv5c

# Search by keyword
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
# List RAM users without MFA enabled
python3 scripts/governance_query.py resources --id apbxftkv5c

# List security groups that expose high-risk ports
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
| "Is my account secure?" / "What is my maturity score?" / "Analyze my governance results" | `overview` | `overview` | [overview](references/report-format-overview.md) |
| "What high-risk items are there?" / "Show all high risks" | `overview` | `overview -r Error` | [overview](references/report-format-overview.md) |
| "Show issues at medium risk or above" | `overview` | `overview -r Error,Warning` | [overview](references/report-format-overview.md) |
| "What security issues exist?" / "Risks in a specific pillar" | `pillar` | `pillar -c Security --risky` | [pillar](references/report-format-pillar.md) |
| "Network security checks" / "Database risks" | `pillar` + keyword filter | `pillar -c Security --risky` then filter by keyword | [pillar](references/report-format-pillar.md) |
| "Show high-priority issues" | `pillar` | `pillar -c Security -l Critical,High --risky` | [pillar](references/report-format-pillar.md) |
| "How do I fix MFA?" / "Show check-item details" | `detail` | `detail --keyword "MFA"` | [detail](references/report-format-detail.md) |
| "Which users do not have MFA?" / "What resources are non-compliant?" | `detail` + `resources` | `detail --id xxx` then `resources --id xxx` | [detail](references/report-format-detail.md) |

**Default**: If user doesn't specify pillar or check item, use `overview`.

**Report format selection**: After determining the query mode, read the corresponding report format reference file before generating output. Only read the format file that matches the user's intent — do not read all format files at once.

## Field Reference

| Field | Values | Note |
|-------|--------|------|
| `Risk` | `Error` (high) > `Warning` (medium) > `Suggestion` (low) > `None` (compliant) | Actual detected risk |
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
