# Related CLI Commands

All cloud commands use plugin mode: lowercase product and hyphenated action names. Do not use PascalCase API names, `--force`, or generic RPC calls.

## Command Matrix

| Purpose | Product and action | Mode | Required parameters | Notes |
|---|---|---|---|---|
| Start or continue a readonly ApsaraDB request | `aliyun das get-yao-chi-agent` | DAS plugin | `--query`, `--source`, `--extra-info` | The bundled script can request `mode: readonly` and supplies endpoint, timeouts, and versioned User-Agent |
| Verify credentials | `aliyun configure list` | Local CLI utility | None | Never read or print credential values |
| Install a plugin | `aliyun plugin install --names aliyun-cli-<product>` | Local CLI utility | Plugin name | Prepare as an authorized local prerequisite before queries; DAS is mandatory |
| Enable automatic plugins | `aliyun configure set --auto-plugin-install true` | Local CLI utility | Non-secret setting only | Required by the official creator; do not change credentials |
| Update plugins | `aliyun plugin update` | Local CLI utility | None | Required by the official creator during local dependency preparation |
| Verify CLI version | `aliyun version` | Local CLI utility | None | Version 3.5.0 or later is required |

Use `scripts/call_apsaradb_agent.sh` for every agent request. Do not assemble the DAS command manually in a live workflow.

## GetYaoChiAgent Parameters

| CLI option | Required | Format |
|---|---|---|
| `--query` | Yes | Non-empty string, at most 4000 characters |
| `--source` | Yes | Supported console route listed in `related-apis.md` |
| `--extra-info` | Yes in the script | JSON object string; omit mode for the standard session; explicitly select `readonly` for prechecks and verification |
| `--session-id` | No | UUID returned by a previous related turn |
| `--endpoint` | Script supplied | DAS hostname |
| `--read-timeout` | Script supplied | Positive seconds |
| `--connect-timeout` | Script supplied | Positive seconds |
| `--user-agent` | Required for actual execution | Double-quoted versioned Skill UA |

```bash
aliyun das get-yao-chi-agent --help
```

## Confirming an operation

`aliyun das create-yao-chi-agent-confirm --help` verifies command availability
without an API call. The helper supplies `--confirmation-id`, `--approved`,
`--session-id`, endpoint, profile and versioned User-Agent. Do not invoke the
callback yourself or pass `--tool-args`.

Use complete argument objects; missing, additional or duplicate alias keys
are rejected. API names may use the documented PascalCase or kebab-case
spelling. For example, the plan for a PolarDB MySQL description change has:

```json
{
  "tool": "ModifyDBClusterDescription",
  "source": "polardb-console",
  "args": {
    "DBClusterId": "<confirmed-cluster-id>",
    "region": "<confirmed-region>",
    "DBClusterDescription": "<approved-description>"
  }
}
```

For `CreateDatabase`, use `DBInstanceId`, `region`, `DBName`,
`CharacterSetName` and, if used, `DBDescription`. For
`ModifyDBInstanceDescription`, use `DBInstanceId`, `region` and
`DBInstanceDescription`. The helper accepts the equivalent kebab-case names
and conservative scalar values. Require the transport `--region` in the
server card (key `region`); an API parameter or profile default does not
bind the signing region. For database creation, do not supply account or
privilege arguments. Do not omit the resource or region or ask the
remote agent to fill defaults. Explicit approval is scoped to one fresh
request; it cannot be reused for another operation.

For RDS `CreateDatabase`, `region` is the CLI signing/routing option, not an
additional database API parameter. The [official API parameter list](https://help.aliyun.com/zh/rds/developer-reference/api-rds-2014-08-15-createdatabase)
does not list `RegionId`; the locally verified plugin command likewise has no
`--biz-region-id` option. Do not invent that argument or silently accept it in
a server card. Extra account, privilege, collation or other optional arguments
also need their own approved scope and are not part of this creation contract.

The approved-operation query asks the service to invoke its registered product
execution tool so that the server emits a structured `humanConfirm` event.
A Markdown table, a generated command or a narrative request to confirm is not
that event. Without a valid event the helper cannot approve an operation and
returns an unverified result; do not manufacture a card or call the callback
directly. For RDS database creation, the query explicitly tells the service to
follow the current API parameter list and generated CLI command when a legacy
quick-reference example conflicts with them. Extra arguments remain rejected.

| Additional supported action | Source | Complete argument shape (including CLI region) | Readonly verification |
|---|---|---|---|
| `ModifyDBInstanceMaintainTime` | RDS | `DBInstanceId`, `region`, `MaintainTime` | Check the instance's stored window |
| `ModifyDBClusterMaintainTime` | PolarDB | `DBClusterId`, `region`, `MaintainTime` | Check the cluster's stored window |
| `ModifyInstanceMaintainTime` | Tair | `InstanceId`, `region`, `MaintainStartTime`, `MaintainEndTime` | Check the instance's stored window |
| `CreateBackup` | PolarDB | `DBClusterId`, `region`, optional `Comment` | Query the returned backup or task ID; distinguish pending from successful |
| `ModifyDBClusterDeletion` | PolarDB | `DBClusterId`, `region`, `Protection` set to CLI string `"true"` | Verify deletion protection is enabled |

Maintenance times use explicit UTC `HH:MMZ` endpoints. RDS and PolarDB
use one `HH:MMZ-HH:MMZ` string; Tair uses two separate arguments. Show
the corresponding local window in the plan. Disabling deletion protection
is outside the allowlist. A backup request can have performance or storage
cost implications; verify state without starting another backup.
