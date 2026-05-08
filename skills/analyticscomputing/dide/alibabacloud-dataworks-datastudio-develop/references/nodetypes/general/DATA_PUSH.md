# Data Push (DATA_PUSH)

## Overview

- Compute engine: `GENERAL`
- Content format: empty in the observed sample (`script.content` omitted)
- Extension: `.json` (legacy UI-facing config; the authoritative config lives in `*.spec.json`)

The Data Push node forwards data — typically query results produced by an upstream node — to an external messaging channel such as a DingTalk group, Feishu (Lark) group, WeCom group, Microsoft Teams channel, or email. It is a notification-style leaf node: it reads upstream outputs through context parameters and renders them into a message payload using a Markdown or table template defined in the platform UI.

Unlike code-bearing nodes (SQL, shell, Python), Data Push carries no executable code. Its entire configuration — target channel, webhook / robot binding, message template, and variable mapping — is managed by the platform and is not inlined into `script.content` in the observed sample.

## Prerequisites

- DataWorks service activated and a workspace created.
- A Serverless resource group created after 2024-06-28.
- The resource group has public-network egress enabled so that the push request can reach the external channel (DingTalk, Feishu, WeCom, Teams, or an SMTP endpoint).
- The upstream node that produces the data to push must be a SQL-query-style node or an assignment node; direct pushes from raw ODPS SQL output are not supported, so an assignment node should sit between the SQL and the push node.

## Restrictions

- A push node is a leaf (terminal) node for notifications; it should not be depended on by further compute logic.
- Size limits per message (platform-enforced):
  - DingTalk / Feishu: up to 20 KB.
  - WeCom: 20 messages per bot per minute.
  - Teams: up to 28 KB.
  - Email: one message body only.
- Supported only in a limited set of regions (China East 1 / Hangzhou, China East 2 / Shanghai, China North 2 / Beijing, and several others).
- The channel webhook URL, signing secret, and any access token are bound to the node via the platform UI. **Do not** hard-code credentials into any field that is committed to source.

## Schema

In the observed sample the DATA_PUSH node is extremely thin. The spec only declares:

1. `script.runtime.command` — fixed to `DATA_PUSH`.
2. Standard node metadata (name, trigger, runtimeResource, inputs, outputs, dependencies).

`script.content` is **omitted**. No `datasource` block and no `script.parameters` are present in the sample. The target channel, message template, and variable bindings are stored by the platform outside the spec (they appear in the UI form; the companion legacy `*.json` file that accompanies the spec may be empty in exported samples).

### `script`

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `runtime.command` | string | yes | Must be `DATA_PUSH`. |
| `runtime.cu` | string | optional | Small allocation (e.g. `"0.25"`) is sufficient; the node only formats and posts one HTTP request. |
| `content` | — | — | **Omit** in the observed sample. Do not hand-author a payload here. |

### Channel, template, and secrets (platform-managed)

The target channel configuration is **not present** in the observed spec sample and is therefore not documented as an inline field contract here. When cloning a working DATA_PUSH node, the following must be re-bound on the destination project via the platform UI (or whatever configuration surface the adapter exposes):

- Push target type (DingTalk / Feishu / WeCom / Teams / Email).
- Webhook URL, e.g. `${webhook_url}` — never commit a literal URL or token.
- Signing secret / access token, e.g. `<your-webhook-token>` — use a secret reference, not a literal.
- Message template (Markdown or table) and its `${variable}` placeholders.
- Upstream variable → template variable mapping.

If you hold an example where the channel configuration is inlined into `script.content` as structured JSON, treat that as a separate authoring form and document it only once a real sample is available.

## Full Example

A daily DATA_PUSH node `datapush1` that is triggered after the project root and depends on the platform-managed push target configuration.

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "datapush1",
        "id": "datapush1",
        "recurrence": "Normal",
        "timeout": 0,
        "timeoutUnit": "HOURS",
        "instanceMode": "T+1",
        "rerunMode": "Allowed",
        "script": {
          "runtime": {
            "command": "DATA_PUSH",
            "cu": "0.25"
          }
        },
        "trigger": {
          "type": "Scheduler",
          "cron": "00 11 00 * * ?",
          "cycleType": "Daily",
          "startTime": "1970-01-01 00:00:00",
          "endTime": "9999-01-01 00:00:00",
          "timezone": "Asia/Shanghai"
        },
        "runtimeResource": {
          "resourceGroup": "${spec.runtimeResource.resourceGroup}"
        },
        "outputs": {
          "nodeOutputs": [
            {
              "sourceType": "System",
              "refTableName": "datapush1"
            },
            {
              "sourceType": "System",
              "data": "${projectIdentifier}.datapush1",
              "refTableName": "datapush1"
            }
          ]
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "datapush1",
        "depends": [
          {
            "type": "Normal",
            "output": "${projectIdentifier}_root",
            "sourceType": "Manual"
          }
        ]
      }
    ]
  }
}
```

## Authoring Checklist

Before submitting a DATA_PUSH node, verify:

- [ ] `script.runtime.command` is `DATA_PUSH`.
- [ ] `script.content` is **omitted** (not `""` and not `"{}"`).
- [ ] `runtimeResource.resourceGroup` points to a Serverless resource group with public-network egress enabled.
- [ ] The upstream node that produces the push payload is a SQL-query-style node or an assignment node (not a raw ODPS SQL node pushing directly).
- [ ] The target channel, webhook URL (`${webhook_url}`), and signing secret (`<your-webhook-token>`) are configured via the platform UI or secret store — no literal credentials are committed to source.
- [ ] The message template and its variable bindings have been re-validated after any upstream schema change.
- [ ] The node is positioned as a notification leaf; no compute-bearing downstream depends on its output.

## Reference

- [Data Push Node](https://help.aliyun.com/zh/dataworks/user-guide/data-push-node)
