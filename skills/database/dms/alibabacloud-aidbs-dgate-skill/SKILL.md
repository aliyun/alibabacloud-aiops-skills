---
name: alibabacloud-aidbs-dgate-skill
description: >
  Connect a cloud or sandbox Agent to Alibaba Cloud Agent Data Gateway (Dgate) through its managed MCP service, or install/reinstall the Dgate CLI and its local Agent Skill/Rule bundle on macOS, Linux, or Windows. Use when the user asks to configure a Region-bound Dgate MCP endpoint and AccessToken, set up Dgate without installing a binary, install the dgate command, refresh the bundled dgate-cli skills, or verify either access path.
metadata:
  domain: aiops
  owner: alibabacloud-dms
---

# Connect Dgate MCP or install the CLI

This is a bootstrap Skill with two access paths. Its job is to connect the managed Dgate MCP service or install `dgate` with the matching managed `dgate-cli` Skill/Rule bundle. Do not duplicate business-operation guidance here: after setup, use the connected MCP tool descriptions or the installed local `dgate-cli` skills. Read [references/ram-policies.md](references/ram-policies.md) for the required RAM-permission declaration.

## Select the access path

1. If dedicated Dgate MCP tools are already connected, do not install anything. Verify the connection as described below and use those tools.
2. For a cloud, sandbox, or other managed Agent where installing a binary is inconvenient, prefer the managed Streamable HTTP MCP service.
3. For a local Agent IDE or a user who explicitly requests the `dgate` command, use the CLI path.
4. If the user chooses a path, honor it. Never install the CLI merely because MCP is available, or replace a requested CLI installation with MCP.

## Managed MCP path

1. Detect the current Agent host and its MCP configuration surface. Preserve every existing MCP server and unrelated setting.
2. Obtain the target Region and a Region-matched Agent Data Gateway AccessToken from the console. Treat the AccessToken as a secret: never ask the user to paste it into chat, print it, or place it in source, logs, URLs, screenshots, or artifacts. Have the user enter it through the host's encrypted secret or header configuration.
3. Configure a Streamable HTTP server named `dgate`. Replace only the placeholders below:

```json
{
  "mcpServers": {
    "dgate": {
      "url": "https://dgate-mcp-<REGION>.aliyuncs.com/mcp/dgate",
      "headers": {
        "Authorization": "Bearer <ACCESS_TOKEN>"
      }
    }
  }
}
```

For example, `cn-hangzhou` uses `https://dgate-mcp-cn-hangzhou.aliyuncs.com/mcp/dgate`. The endpoint Region and AccessToken Region must match.

4. Changing an Agent host's MCP configuration requires the user's explicit approval unless the current request already clearly authorizes that change. If the user asks for guidance only, provide the template and do not modify configuration or call tools.
5. Reload the MCP configuration, confirm that the `dgate` server connects, confirm that its tool list is discovered, then call the read-only `acl_whoami` tool. Report success only when all three checks pass. On failure, preserve the error code, short summary, and request or trace ID without exposing the AccessToken.

For MCP guidance and setup results, put the resolved Endpoint, encrypted `Authorization: Bearer` configuration, reload step, successful tool-list discovery, and `acl_whoami` verification directly in the final answer. Do not replace these facts with an artifact or file path.

After connection, use the dedicated Dgate MCP tool whose description and input schema match the user's request. Do not handcraft HTTP requests or install the CLI for business operations. The MCP tool catalog, schemas, Agent ACL, security policies, and audit trail govern what the Agent can do.

## CLI installation path

1. Read the official installation guide at `https://d.tb.cn/install_cli.md` and follow its current instructions.
2. Detect the target operating system and Agent IDE. Supported `--install-ide` values include `codex`, `cursor`, `qoder`, `qoderwork`, `claude`, `copaw`, `codebuddy`, and `opencode`. Ask only when they cannot be detected.
3. Obtain the target Region and a one-time install token from the Agent Data Gateway console. Treat the token as a secret: never print it, paste it into chat, or write it to source, logs, URLs, screenshots, or artifacts. Prefer the complete natural-language installation instruction copied from the console so the token stays in the user's trusted Agent session.
4. Installing or running downloaded software requires the user's explicit approval. If the user has not already approved installation, give instructions only and wait before executing a command.
5. Run the official command for the detected operating system, substituting the supplied Region, token, and IDE. Do not invent, replace, or expose credential values.

macOS or Linux:

```bash
curl --connect-timeout 10 --max-time 120 -fsSL https://d.tb.cn/i.sh | \
  bash -s -- \
    --install-token "$DGATE_INSTALL_TOKEN" \
    --region "$DGATE_REGION" \
    --install-ide codex
```

Windows PowerShell:

```powershell
Invoke-RestMethod -Uri https://d.tb.cn/i.ps1 -OutFile "$env:TEMP\i.ps1" -TimeoutSec 120
& "$env:TEMP\i.ps1" --install-token $env:DGATE_INSTALL_TOKEN --region $env:DGATE_REGION --install-ide codex
```

When a managed environment already provides `DGATE_ACCESS_TOKEN` and `DGATE_REGION`, the public installer can use those encrypted environment variables directly. For a binary-and-skill refresh that must not start Quick Start, run the matching installer with `--skip-quickstart --install-ide <detected-ide>`; do not place the AccessToken on the command line.

## Verify before reporting success

The installer may place `dgate` outside the current `PATH`. Resolve `command -v dgate` first; if it is absent, locate the executable installed under `/home/*/.local/bin/dgate` or `/root/.local/bin/dgate`, bind that absolute path once, and reuse it.

Run:

```bash
dgate version
dgate install skills --check --agents codex
dgate acl role current -o json
```

Replace `codex` with the detected IDE. Report success only when the CLI version command, managed Skill/Rule check, and identity check all succeed. If PATH repair requires a new terminal, say so. Do not perform business operations in this bootstrap Skill.
