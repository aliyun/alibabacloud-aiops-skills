# Related CLI Commands

All cloud commands use plugin mode: lowercase product and hyphenated action names. Do not use PascalCase API names, `--force`, or generic RPC calls.

## Command Matrix

| Purpose | Product and action | Mode | Required parameters | Notes |
|---|---|---|---|---|
| Start or continue a readonly ApsaraDB request | `aliyun das get-yao-chi-agent` | DAS plugin | `--query`, `--source`, `--extra-info` | The bundled script forces `mode: readonly` and supplies endpoint, timeouts, and versioned User-Agent |
| Verify credentials | `aliyun configure list` | Local CLI utility | None | Never read or print credential values |
| Install a plugin | `aliyun plugin install --names aliyun-cli-<product>` | Local CLI utility | Plugin name | Prepare as an authorized local prerequisite before queries; DAS is mandatory |
| Enable automatic plugins | `aliyun configure set --auto-plugin-install true` | Local CLI utility | Non-secret setting only | Required by the official creator; do not change credentials |
| Update plugins | `aliyun plugin update` | Local CLI utility | None | Required by the official creator during local dependency preparation |
| Verify CLI version | `aliyun version` | Local CLI utility | None | Version 3.3.3 or later is required |

Use `scripts/call_apsaradb_agent.sh` for every agent request. Do not assemble the DAS command manually in a live workflow.

## GetYaoChiAgent Parameters

| CLI option | Required | Format |
|---|---|---|
| `--query` | Yes | Non-empty string, at most 4000 characters |
| `--source` | Yes | Supported console route listed in `related-apis.md` |
| `--extra-info` | Yes in the script | JSON object string; the script always sets `mode` to `readonly` |
| `--session-id` | No | UUID returned by a previous related turn |
| `--endpoint` | Script supplied | DAS hostname |
| `--read-timeout` | Script supplied | Positive seconds |
| `--connect-timeout` | Script supplied | Positive seconds |
| `--user-agent` | Required for actual execution | Double-quoted versioned Skill UA |

```bash
aliyun das get-yao-chi-agent --help
```
