# Curl Shell Compatibility Guide

AgentExplorer HTTP APIs use the same URL, query parameters, and headers on every operating system. Only shell syntax differs: quoting, line continuation, and UTC timestamp generation.

## Bash-compatible Shells

Use this template on macOS, Linux, WSL, and Git Bash:

```bash
curl -sS -G --connect-timeout 10 --max-time 30 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' \
  --data-urlencode 'categoryCode=computing' \
  --data-urlencode 'maxResults=20' \
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' \
  -H 'x-acs-version: 2026-03-17' \
  -H "x-acs-date: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
```

Debian/Ubuntu, CentOS/RHEL, and ARM64 Linux use the same syntax. If `curl` is missing, install it with the system package manager first.

## Key Differences

| Part | macOS / Linux / WSL / Git Bash | Windows |
| --- | --- | --- |
| Shell | Bash-compatible shell | `powershell -NoProfile -Command` |
| Curl executable | `curl` | `curl.exe` |
| UTC timestamp | `$(date -u +%Y-%m-%dT%H:%M:%SZ)` | `[DateTimeOffset]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ')` |
| Line continuation | `\` | PowerShell backtick inside the command string |

## Windows

Use this one-line PowerShell invocation for AgentExplorer API calls on Windows:

```powershell
powershell -NoProfile -Command "curl.exe -sS -G --connect-timeout 10 --max-time 30 'https://agentexplorer.aliyuncs.com/openapi/for-agent/skills' `
  --data-urlencode 'categoryCode=computing' `
  --data-urlencode 'maxResults=20' `
  -H 'User-Agent: AlibabaCloud-Agent-Skills/alibabacloud-find-skills' `
  -H 'x-acs-version: 2026-03-17' `
  -H ('x-acs-date: ' + [DateTimeOffset]::UtcNow.ToString('yyyy-MM-ddTHH:mm:ssZ'))"
```

Keep the `x-acs-date` header as the expression above. Do not replace it with a literal timestamp such as `YYYY-MM-DDT00:00:00Z`.

## Translation Rules

- Keep the same AgentExplorer endpoint and query parameters on every shell.
- Keep the same required headers: `User-Agent`, `x-acs-version`, and `x-acs-date`.
- Keep `--connect-timeout 10 --max-time 30` on AgentExplorer HTTP calls.
- On Windows, use `curl.exe`, not `curl`.
- Generate the Windows `x-acs-date` header inline with `[DateTimeOffset]::UtcNow`; do not precompute it in a separate `$date` variable or hardcode it as a clock value.
