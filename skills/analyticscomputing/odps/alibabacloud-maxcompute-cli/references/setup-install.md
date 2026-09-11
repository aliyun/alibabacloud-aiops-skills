> Load on demand for Alibaba Cloud CLI or standalone maxc installation, update, and verification. Skip when the selected entry provides the commands and flags required for the current task.

# Install and verify the MaxCompute CLI

Use Alibaba Cloud CLI for public-cloud Agent work. Keep the standalone Python entry for compatibility and development scenarios.

Authoritative references:

- [MaxCompute CLI](https://help.aliyun.com/zh/maxcompute/user-guide/maxcompute-cli)
- [Install or update Alibaba Cloud CLI](https://help.aliyun.com/zh/cli/install-update-alibaba-cloud-cli)

Installing or updating a CLI changes the user's environment. Explain the required change and obtain confirmation before running it. Do not install or upgrade Python itself without explicit authorization.

Reuse the session User-Agent declared in SKILL.md for every command below that calls a cloud API: `--user-agent "$MAXC_AGENT_UA"`. Local version, help, `agent context`, and `agent manifest` calls may omit it.

## Preferred public-cloud entry

The `aliyun maxc` entry requires Alibaba Cloud CLI 3.3.19 or later:

```bash
aliyun version
aliyun maxc --version
aliyun maxc --help
```

If these commands succeed and runtime help exposes the commands needed for the request, continue without changing the installation. This Skill is synchronized with MaxCompute CLI 0.5.2 or later, but runtime help and the generated `agent manifest` remain authoritative.

If `aliyun` or `aliyun maxc` is missing, too old, or lacks a required command, identify the current installation method before updating. For an identified non-Homebrew Alibaba Cloud CLI 3.3.5 or later that supports self-upgrade, use this only after user approval:

```bash
aliyun upgrade
```

Versions earlier than 3.3.5 do not provide that updater. For Homebrew, Linux, Windows, offline packages, pinned versions, or manual upgrades, follow the applicable method in the official installation guide after the user confirms the change. Do not invent an installer URL. Keep stdout and stderr visible because the first `aliyun maxc` invocation can download or refresh its bundled component.

## Standalone Python entry

Use the standalone entry only when the user explicitly wants the PyPI distribution or Alibaba Cloud CLI is unavailable. It requires Python 3.9 or later:

```bash
python3 --version
python3 -m pip --version
```

Only after the user authorizes the package change:

```bash
python3 -m pip install --upgrade maxc-cli
maxc --version
maxc --help
```

For a user-local environment, `python3 -m pip install --user --upgrade maxc-cli` is available. If the package is installed but `maxc` is not on `PATH`, use `python3 -m maxc_cli` for the current task. Do not modify shell startup files unless the user asks.

## Verify the selected distribution

Use the selected invocation rather than switching entry points during verification:

```bash
aliyun maxc --version
aliyun maxc agent context --json
aliyun maxc agent manifest --json
```

`agent context` and `agent manifest` are local-only. If authentication is not configured and the session is interactive, current supported releases provide direct OAuth:

```bash
aliyun maxc auth login --oauth --user-agent "$MAXC_AGENT_UA" --json
```

Use `--no-browser` only when automatic browser opening is unavailable; the OAuth callback still has to reach the loopback listener on the CLI host. Managed runtimes that explicitly require injected credentials must use their approved `auth login --from-env` flow once and must not also start OAuth.

Finish remote verification with:

```bash
aliyun maxc agent doctor --online --user-agent "$MAXC_AGENT_UA" --json
```

Continue only when `data.ready=true`. Inspect `status`, `error`, and `agent_hints` before retrying.

## Optional MCQA

Use a command-level flag only when the user wants that execution mode, and resolve quota names from verified configuration or user input:

```bash
aliyun maxc query "SELECT 1" --mcqa --user-agent "$MAXC_AGENT_UA" --json
aliyun maxc query "SELECT 1" --maxqa --quota "<verified-quota-name>" --user-agent "$MAXC_AGENT_UA" --json
```

Change persistent MCQA settings only when the user wants subsequent queries to inherit them.
