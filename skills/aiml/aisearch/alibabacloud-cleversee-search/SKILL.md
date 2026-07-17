---
name: alibabacloud-cleversee-search
description: |
  Alibaba Cloud cleversee CLI skill. web-search is a general-purpose, AI/agent-oriented
  internet search providing high-quality, low-latency neural knowledge retrieval and web
  content scraping across any topic and real-time information.
  Triggers: "cleversee", "web search", "AI 搜索", "联网搜索", "查资料", "实时信息".
---

# cleversee CLI — Web Search

## Scenario Description

cleversee is a standalone CLI tool for Alibaba Cloud users that provides:

- **Web Search** (`web-search`): AI-powered internet search for agents — high-quality, low-latency retrieval of relevant results and page content across any topic and real-time information, with optional date-range and domain filtering. It creates no cloud resources and requires no cleanup.

## Installation

**Pre-check: cleversee CLI required**
> [MUST] Verify: `cleversee --help` — must succeed.
> - **Install:** `npm install -g @cleversee/cli@1.0.5 --registry https://registry.npmjs.org`

## Environment Variables

cleversee does not require any environment variables. It reuses Aliyun CLI's credential profile system.

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **ONLY** use `cleversee doctor` to check credential status
>
> **Verification:**
> ```bash
> cleversee doctor
> ```
> Check the output for profile validity.
>
> **If no valid profile exists:**
> Configure credentials using `cleversee auth set` (see Authentication Configuration below).

### Authentication Configuration

| Mode | Interactive | Non-Interactive Command |
|------|-------------|------------------------|
| **OAuth** | Yes (browser required) | Not supported |
| **RamRoleArn** | No | `cleversee auth set --mode RamRoleArn --access-key-id <id> --access-key-secret <secret> --arn <arn>` |

**Interactive commands** (cannot be used in non-interactive/automated contexts):
- `cleversee auth set` (no parameters)
- `cleversee auth switch`
- `cleversee auth --mode OAuth` — OAuth login; skips the mode-selection prompt but still opens a browser, so it requires a present user

## RAM Policy

This skill requires `AliyunCleverSeeAISearchPlatformUserAccess` permission.
See [references/ram-policies.md](references/ram-policies.md) for the full permission list and policy document.

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., search query, limit, search-type, region,
> date ranges, domain lists, profile name, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

### Web Search Parameters

| Parameter | Required | Default | Description |
|-----------|----------|---------|-------------|
| `--query <query>` | Yes | — | Search keywords |
| `--limit <n>` | No | `10` | Result count, range 1-10 |
| `--search-type <type>` | No | `pro` | `pro` (advanced, global sources) or `lite` (fast, low-cost) |
| `--region <region>` | No | `mainland_china` | `mainland_china` or `global` (pro mode only). |
| `--start-time <date>` | No | — | Start date `YYYY-MM-DD` |
| `--end-time <date>` | No | — | End date `YYYY-MM-DD` |
| `--include-domain <d1 d2...>` | No | — | Domain whitelist, space-separated (pro only; forces `--region global` automatically) |
| `--exclude-domain <d1 d2...>` | No | — | Domain blacklist, space-separated (pro only) |
| `--table` | No | — | Output as a table view (default web-search view is a card list) |

### Global Parameters

Apply to `web-search` (and `--profile` also applies to `auth`). `doctor` accepts no options.

| Parameter | Default | Description |
|-----------|---------|-------------|
| `--profile <name>` | `defaultProfile` | Aliyun CLI profile name |
| `-o, --output <json\|table>` | `table` | Output format (`table` for human-readable, `json` for program parsing) |
| `-V, --version` | — | Print cleversee version |

## Core Workflow

### Workflow A: Web Search

```
Step 1: Verify environment     →  cleversee doctor
Step 2: Confirm search params  →  Ask user for query, limit, search-type, region, dates, domains
Step 3: Execute search         →  cleversee web-search --query "<user-confirmed query>" [options] -o json
Step 4: Parse results          →  Check JSON output for at least one result
```

**Example (parameters must be confirmed with user first):**

```bash
# Step 1: Verify environment
cleversee doctor

# Step 2-3: Execute search with user-confirmed parameters
cleversee web-search \
  --query "What are the latest battery breakthroughs in electric vehicles?" \
  --limit 5 \
  --search-type pro \
  -o json
```

### Workflow B: Credential Management

```
Step 1: Check current status   →  cleversee doctor
Step 2: Configure credentials  →  cleversee auth set --mode <mode> [params]
Step 3: Verify                 →  cleversee doctor
```

**Example:**

```bash
# Step 1: Check current status
cleversee doctor

# Step 2: Configure RamRoleArn (parameters provided by user)
cleversee auth set --mode RamRoleArn \
  --access-key-id <user-provided-id> \
  --access-key-secret <user-provided-secret> \
  --arn <user-provided-arn>

# Step 3: Verify
cleversee doctor
```

## Success Verification

**Quick checks:**
- `cleversee doctor` exits with code 0 and all checks pass
- `cleversee web-search` exits with code 0 and returns at least one result

## Cleanup

cleversee web-search is a **read-only operation** — it creates no cloud resources and requires no cleanup.

For credential cleanup, reconfigure or remove profiles via `cleversee auth set` or Aliyun CLI profile management.

## Best Practices

1. **Run `cleversee doctor` first** — always verify environment health before searching
2. **Use `-o json`** — for programmatic result parsing
3. **Run `cleversee doctor`** — to diagnose environment or credential issues when a command fails
4. **Use `--search-type lite`** — for quick searches that don't need advanced filtering
5. **Use `--include-domain` / `--exclude-domain`** — in pro mode to focus on authoritative sources
6. **Use `--start-time` / `--end-time`** — to get recent content within a specific date range
7. **Use `cleversee auth set` for automation** — never use interactive `auth` or `auth switch` in non-interactive contexts
8. **Use `--profile`** — manage multiple account credentials
9. **Use `--help`** — every command level supports `--help` for accurate parameter discovery

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/ram-policies.md](references/ram-policies.md) | RAM permission list and policy document |
| [references/acceptance-criteria.md](references/acceptance-criteria.md) | Acceptance criteria with correct/incorrect patterns |
