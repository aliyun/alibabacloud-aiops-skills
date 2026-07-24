# Initialization Guide (Onboarding)

This guide is for **first-time use of alibabacloud-sre-toolkit** or when environment dependencies are missing. It completes a one-time initialization in dependency order: aliyun CLI -> profile credentials -> Python dependencies -> STAROps digital employee setup. The onboarding process may include user-triggered write actions (`CreateDigitalEmployee` / `DeleteDigitalEmployee`) for STAROps digital employee management. Credentials are managed by aliyun CLI and are never persisted. No **cloud infrastructure** resource write operations are performed.

## 1. Applicable Scenarios and Triggers

- **Auto-detect on first launch**: After skill loads, run `env-check`; if any of `aliyun_cli` / `starops` / `python_deps` / `accounts` is `fail`, initialization is considered incomplete and this wizard is entered automatically.
- **Dedicated trigger**: `sre-init`. When matched, enter the wizard. Can also be used in configured environments for re-checking / reconfiguring.

> When initialization is incomplete (`env-check` not `pass`), **do not proceed to Step 3 and subsequent diagnostic/inspection workflows**.

## 2. Initialization Detection Matrix

Run an environment check first to get the overall status:

```bash
python3 <skill-root>/scripts/session_manager.py env-check --cwd "$PWD"
```

| Check Item | Source | Missing Indication | Guide |
|-----------|--------|-------------------|-------|
| aliyun CLI installation & version (>=3.3.3) | `env-check.checks.aliyun_cli` | Not installed / version too low | Step 1 |
| profile valid credentials | `env-check.checks.aliyun_cli.profiles[]` | No profile with `has_credentials` | Step 2 |
| Python dependencies | `env-check.checks.python_deps` | `requests` / `alibabacloud_credentials` missing | Step 3 |
| STAROps configuration | `env-check.checks.starops` / `accounts` | Missing `employeeId` / `uid` | Step 4 |

## 3. Step-by-Step Wizard (each item: detect -> guide -> re-check)

### Step 1 - aliyun CLI
- Verify version: `aliyun version`, requires >= 3.3.3.
- Not installed / version too low: Install or upgrade via [cli-installation-guide.md](cli-installation-guide.md).

### Step 2 - profile Credentials
- Check: `aliyun configure list`, confirm a valid profile exists (AK / STS / OAuth).
- If missing, guide the user to run `aliyun configure` (or `aliyun configure --profile <name>`) to complete configuration.
- **Security rules**: Do not read/echo/print AK/SK. Do not let the user input AK/SK directly in the session. Do not use `aliyun configure set` to hardcode plaintext credentials. Only use `aliyun configure list` to check credential status. Credentials must be configured outside the session.

### Step 3 - Python Dependencies
```bash
pip3 install -r <skill-root>/scripts/requirements.txt
```
After installation, `env-check.checks.python_deps` should be `pass` (`requests` / `alibabacloud-credentials` available).

### Step 4 - STAROps Digital Employee Setup
- **Prefer auto-discovery** (when profile credentials exist): Follow Step 2 "Digital Employee Smart Discovery" - ask user to confirm selected profile -> call `aliyun sts get-caller-identity --profile` via `aliyun` CLI to resolve UID -> `starops_manager.py list-employees --profile` to enumerate -> user selects digital employee -> `account-add` to write uid->profile->employeeId mapping (workspace optional, credentials not persisted).
  ```bash
  python3 <skill-root>/scripts/session_manager.py account-add --cwd "$PWD" \
    --uid "<resolved-UID>" --employee-id "<selected-name>" \
    --profile "<selected-profile>" [--workspace "<workspace>"]
  ```
- **Fallback manual configuration**: When auto-discovery is not possible, use `account-add` or `configure-set` to register manually (see [starops-config.md](starops-config.md) for parameters).

## 4. Single-Account Auto-Skip

When `env-check` reports `credential_mode: "single"` (one aliyun profile or env vars only), the UID selection step is automatically skipped:
- The credential is auto-selected without user interaction
- `init` auto-resolves UID via `aliyun sts get-caller-identity`
- Proceed directly from `env-check` to `init`

Multi-account mode (`credential_mode: "multi"`) retains the current behavior: user must explicitly select a UID via `list-accounts`.

## 5. Completion Criteria

Re-run `env-check` until `"status": "pass"`. Prompt the user that initialization is complete. They can then initiate operations for the corresponding scenario via `sre-observability` / `sre-incident` / `sre-capacity` / `sre-architecture` / `sre-security`.

## 6. Constraints

- The diagnostic/inspection workflow is read-only. Onboarding may include user-triggered STAROps write actions (`CreateDigitalEmployee` / `DeleteDigitalEmployee`). No **cloud infrastructure** resource write operations are performed.
- Credentials are managed by aliyun CLI and are **never persisted**. Do not read/echo/hardcode AK/SK.
- Built-in script logic is not modified. Detection fully reuses `env-check` output.
