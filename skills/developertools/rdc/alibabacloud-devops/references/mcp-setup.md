# MCP Server Setup

> **Note**: If you have the Alibaba Cloud CLI (`aliyun devops` command) installed, it can also be used to interact with Yunxiao DevOps. The MCP Server configuration below is an alternative approach suitable for environments where the CLI is not available.

This Skill communicates with the Yunxiao DevOps platform via the Yunxiao MCP Server (`alibabacloud-devops-mcp-server`). Three connection modes are supported.

## Recommended: Pre-install Dependencies

To avoid downloading external code from the npm registry at runtime, it is recommended to globally install the required packages in advance:

```bash
# Use the Alibaba Cloud mirror registry (recommended)
npm install -g alibabacloud-devops-mcp-server@0.3.38 mcporter@0.11.1 --registry=https://registry.npmmirror.com
```

After pre-installation, all `npx -y` commands below will use the locally installed versions without fetching from the network.

## Mode 1: Stdio (Recommended)

The IDE/Agent launches the MCP Server directly as a subprocess. This is the simplest approach with the lowest latency.

```json
{
  "mcpServers": {
    "yunxiao": {
      "command": "npx",
      "args": ["-y", "alibabacloud-devops-mcp-server@0.3.38"],
      "env": {
        "YUNXIAO_ACCESS_TOKEN": "<YOUR_TOKEN>",
        "YUNXIAO_API_BASE_URL": "https://openapi-rdc.aliyuncs.com"
      }
    }
  }
}
```

## Mode 2: Docker

Suitable for scenarios requiring a unified image, offline intranet environments, or enterprise governance.

```json
{
  "mcpServers": {
    "yunxiao": {
      "command": "docker",
      "args": [
        "run", "-i", "--rm",
        "-e", "YUNXIAO_ACCESS_TOKEN",
        "-e", "YUNXIAO_API_BASE_URL",
        "build-steps-public-registry.cn-beijing.cr.aliyuncs.com/build-steps/alibabacloud-devops-mcp-server:latest"
      ],
      "env": {
        "YUNXIAO_ACCESS_TOKEN": "<YOUR_TOKEN>",
        "YUNXIAO_API_BASE_URL": "https://openapi-rdc.aliyuncs.com"
      }
    }
  }
}
```

## Mode 3: SSE

Suitable for remote public services or multi-client sharing scenarios.

```json
{
  "mcpServers": {
    "yunxiao": {
      "url": "http://localhost:3000/sse"
    }
  }
}
```

Start the SSE endpoint:

```bash
MCP_TRANSPORT=sse PORT=3000 \
  YUNXIAO_ACCESS_TOKEN=<YOUR_TOKEN> \
  npx -y alibabacloud-devops-mcp-server@0.3.38
```

## Environment Variables

| Variable | Required | Description | Example |
|----------|----------|-------------|---------|
| `YUNXIAO_ACCESS_TOKEN` | Yes | Yunxiao personal access token | `pt-xxx` |
| `YUNXIAO_API_BASE_URL` | No | OpenAPI base URL | `https://openapi-rdc.aliyuncs.com` |
| `MCP_TRANSPORT` | No | Transport mode (set to `sse` for SSE mode) | `sse` |
| `PORT` | No | Port for SSE mode | `3000` |
| `DEVOPS_TOOLSETS` | No | Enabled toolsets (comma-separated) | `code-management,pipeline-management` |

## Enable Toolsets on Demand

Use `DEVOPS_TOOLSETS` or the command-line flag `--toolsets` to control which toolsets are loaded, reducing context usage:

```bash
npx -y alibabacloud-devops-mcp-server@0.3.38 \
  --toolsets=base,code-management,project-management,pipeline-management
```

Available values: `base`, `code-management`, `organization-management`, `project-management`,
`pipeline-management`, `packages-management`, `application-delivery`, `test-management`.

## Debugging: List Tool Schemas

```bash
npx -y mcporter@0.11.1 list --stdio "npx -y alibabacloud-devops-mcp-server@0.3.38" --schema
```

Invoke a tool directly:

```bash
npx -y mcporter@0.11.1 call --stdio "npx -y alibabacloud-devops-mcp-server@0.3.38" \
  list_repositories organizationId:"your-org-id"
```
