---
name: alibabacloud-sas-multiaccount-manage
description: Manage multiple Alibaba Cloud accounts and batch-export Security Center (SAS) baseline and vulnerability reports via the aliyun CLI and Python scripts. Supports account list refresh, enable/disable, concurrent batch export of cloud platform configuration check (baselineCspm), system baseline risk (exportHcWarning), Linux/Windows/application/emergency vulnerability results across all managed accounts. Use this skill when users need to manage SAS multi-account settings, export baseline or vulnerability compliance data, or merge multi-account security reports into a single file.
---

# Alibaba Cloud Security Center Multi-Account Management and Baseline Report Export

Use aliyun CLI and Python scripts to manage multiple Alibaba Cloud accounts in a resource directory and batch-export Security Center baseline reports for each account.

## Prerequisites and Environment Setup

### 1. Install Alibaba Cloud CLI

```bash
# macOS
brew install aliyun-cli

# Or download from GitHub: https://github.com/aliyun/aliyun-cli/releases
```

Check credentials:

```bash
aliyun sts get-caller-identity
```

If the call fails, instruct the user to run `aliyun configure` and set up credentials (interactive step, must be completed by the user).

### 1.1 Configure AI mode and plugin mode (required)

This skill requires aliyun CLI plugin mode commands (kebab-case) and a fixed User-Agent declaration.

```bash
# Keep plugins up to date
aliyun plugin update

# Install required product plugins if missing
aliyun plugin install --names aliyun-cli-sts,aliyun-cli-sas

# Enable AI mode and set required UA segment
aliyun configure ai-mode enable
aliyun configure ai-mode set-user-agent --user-agent AlibabaCloud-Agent-Skills

# Optional checks / rollback
aliyun configure ai-mode show
aliyun configure ai-mode disable
```

### 2. Install Python ≥ 3.6

```bash
# Check version
python3 --version  # Requires 3.6+, 3.9+ recommended
```

### 3. Create Virtual Environment and Install Dependencies

Create a virtual environment in `<skill-path>/scripts/` and install dependencies declared in `pyproject.toml`:

```bash
cd scripts/

# Option A: use venv
python3 -m venv .venv
.venv/bin/pip install -e .

# Option B: use uv (optional)
uv sync

# Option C: if current Python version is unsupported, install as system dependencies
pip install -r requirements.txt
```

### 4. Run Commands

All scripts must be executed with **Python from the virtual environment** (whether created via venv, uv, conda, etc.). This document uses `.venv/bin/python` in examples; replace it with your actual virtual environment path.

---

## Working Directory

`accounts.json` and exported Excel files are saved in the **agent's current working directory** (the directory where the command is executed). Script files themselves are located in `<skill-path>/scripts/`. Do not switch into the `scripts` directory when running commands, or `accounts.json` location may shift unexpectedly.

```bash
# Example: run from any directory
.venv/bin/python /path/to/scripts/accounts.py refresh
```

## Feature 1: Account Management (`accounts.py`)

### Workflow

1. **First use**: run `refresh` to fetch account list from the resource directory.
2. **Filter as needed**: use `search` to find target accounts and get AccountId.
3. **Enable/disable control**: use `enable` / `disable` to decide which accounts participate in batch export.

### Quick Start

#### Refresh account list

Fetch the latest account list from Alibaba Cloud resource directory and write to `accounts.json`. Existing `enable` states are preserved; new accounts are enabled by default.

```bash
.venv/bin/python accounts.py refresh
```

#### List all accounts

```bash
.venv/bin/python accounts.py list
```

Sample output:
```
1225574417218097    cwx                     [enabled]
1234567890123456    prod-account            [disabled]
```

#### Search accounts

Fuzzy-search by DisplayName, returning AccountId and enable status.

```bash
.venv/bin/python accounts.py search cwx
.venv/bin/python accounts.py search prod
```

#### Enable / disable accounts

Control whether an account participates in subsequent batch exports.

```bash
.venv/bin/python accounts.py enable 1225574417218097
.venv/bin/python accounts.py disable 1234567890123456
```

### `accounts.json` Structure

```json
[
  {
    "AccountId": "1225574417218097",
    "DisplayName": "cwx",
    "FolderId": "r-1Q4pqB",
    "IsMaAccount": "NO",
    "SasVersion": "0",
    "enable": true
  }
]
```

---

## Feature 2: Batch Baseline Export (`baseline.py`)

Launch export tasks concurrently for all accounts with `enable=true`. After polling completion, files are downloaded, extracted, and merged into a single Excel file.

### Workflow

1. **Concurrent submission**: submit `export-record` requests for all enabled accounts (QPS ≤ 5).
2. **Concurrent polling**: poll `describe-export-info` for each account until export completes.
3. **Download and extract**: download zip and extract xlsx.
4. **Merge output**: merge all account xlsx files into one file via `merge.py`, appending a “Resource Directory Account” column.
5. **Cleanup temporary files**: delete per-account temporary xlsx files after merge.

### Prerequisites

- `accounts.py refresh` has been executed and account enable/disable configuration is complete.
- aliyun CLI is configured with valid credentials and has SAS `export-record` and `describe-export-info` permissions.
- Accounts must have Security Center purchased (free edition accounts are skipped automatically).

### Export cloud platform configuration check results (CSPM)

Export `baselineCspm` results for all enabled accounts and merge into `baseline-cspm-merged-{date}.xlsx`.

```bash
# Export for all enabled accounts
.venv/bin/python baseline.py export-cspm

# Export for one specific account
.venv/bin/python baseline.py export-cspm --account-id 1225574417218097
```

### Export system baseline risk list

Export `exportHcWarning` risk list (high/medium/low, all statuses) for all enabled accounts and merge into `system-warning-merged-{date}.xlsx`.

```bash
# Export for all enabled accounts
.venv/bin/python baseline.py export-system-warning

# Export for one specific account
.venv/bin/python baseline.py export-system-warning --account-id 1225574417218097
```

### Output Files

| File | Description |
|------|------|
| `baseline-cspm-merged-{date}.xlsx` | Merged cloud platform configuration check results, including “Resource Directory Account” column |
| `system-warning-merged-{date}.xlsx` | Merged system baseline risk list, including “Resource Directory Account” column |

### Error Handling

| Scenario | Behavior |
|------|------|
| `FreeVersionNotPermit` | Silently skip this account and continue others |
| `NoPermission` / `Forbidden` | Silently skip this account |
| Export failed (server-side error) | Print `[failed]` message and continue with other accounts |
| All accounts skipped | Print message and exit without output file |

---

## Feature 3: Batch Vulnerability Export (`vuln.py`)

Launch vulnerability export tasks concurrently for all accounts with `enable=true`. Supports four vulnerability types. After polling completion, files are downloaded, extracted, and merged automatically.

### Workflow

1. **Concurrent submission**: submit `export-vul --force` requests for all enabled accounts (QPS ≤ 5).
2. **Concurrent polling**: poll `describe-vul-export-info --force` for each account until export completes.
3. **Download and extract**: download zip and extract xlsx.
4. **Merge output**: merge all account xlsx files into one file via `merge.py`, appending a “Resource Directory Account” column.
5. **Cleanup temporary files**: delete per-account temporary xlsx files after merge.

> When the current account is the same as the caller's primary account, `--ResourceDirectoryAccountId` is omitted automatically.

### Prerequisites

- `accounts.py refresh` has been executed and account enable/disable configuration is complete.
- aliyun CLI is configured with valid credentials and has SAS `export-vul` and `describe-vul-export-info` permissions.
- Accounts must have Security Center purchased (free edition accounts are skipped automatically).

### Export Linux software vulnerabilities (CVE)

Export unresolved Linux software vulnerabilities (high/medium/low priority) for all enabled accounts and merge into `vul-cve-merged-{date}.xlsx`.

```bash
# Export for all enabled accounts
.venv/bin/python vuln.py export-cve

# Export for one specific account
.venv/bin/python vuln.py export-cve --account-id 1225574417218097
```

### Export Windows system vulnerabilities

Export unresolved Windows system vulnerabilities (high/medium/low priority) for all enabled accounts and merge into `vul-sys-merged-{date}.xlsx`.

```bash
.venv/bin/python vuln.py export-sys
.venv/bin/python vuln.py export-sys --account-id 1225574417218097
```

### Export application vulnerabilities (including SCA)

Export unresolved application vulnerabilities (ECS + container, including software composition analysis) for all enabled accounts and merge into `vul-app-merged-{date}.xlsx`.

```bash
.venv/bin/python vuln.py export-app
.venv/bin/python vuln.py export-app --account-id 1225574417218097
```

### Export emergency vulnerabilities

Export emergency vulnerabilities (at-risk status) for all enabled accounts and merge into `vul-emg-merged-{date}.xlsx`.

```bash
.venv/bin/python vuln.py export-emg
.venv/bin/python vuln.py export-emg --account-id 1225574417218097
```

### Output Files

| File | Description |
|------|------|
| `vul-cve-merged-{date}.xlsx` | Merged Linux software vulnerability list, including “Resource Directory Account” column |
| `vul-sys-merged-{date}.xlsx` | Merged Windows system vulnerability list, including “Resource Directory Account” column |
| `vul-app-merged-{date}.xlsx` | Merged application vulnerability list (including SCA), including “Resource Directory Account” column |
| `vul-emg-merged-{date}.xlsx` | Merged emergency vulnerability list, including “Resource Directory Account” column |

### Export Parameter Details

| Type | `export-vul` parameters |
|------|----------------|
| `export-cve` | `--Type cve --Necessity asap,later,nntf --Dealed n` |
| `export-sys` | `--Type sys --Necessity asap,later,nntf --Dealed n` |
| `export-app` | `--Type app --Necessity asap,later,nntf --AttachTypes sca --AssetType ECS,CONTAINER --Dealed n` |
| `export-emg` | `--Type emg --RiskStatus y --Dealed n` |

### Error Handling

| Scenario | Behavior |
|------|------|
| `FreeVersionNotPermit` | Silently skip this account and continue others |
| `NoPermission` / `Forbidden` | Silently skip this account |
| Export failed (server-side error) | Print `[failed]` message and continue with other accounts |
| All accounts skipped | Print message and exit without output file |

---

## Notes

- Scripts must run in a virtual environment. Examples use `.venv/bin/python`; replace with your actual virtual environment path.
- Manage aliyun CLI credentials with `aliyun configure`; do not hardcode AK/SK.
- SAS API supports only two endpoints: `cn-shanghai` (China mainland) and `ap-southeast-1` (outside China mainland).
