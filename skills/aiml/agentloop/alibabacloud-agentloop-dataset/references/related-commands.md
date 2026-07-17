# Related CLI Commands

The AgentLoop plugin fixes the API version at `2026-05-20`; do not add a CMS product or a different API version.

| Area | Command | Purpose | Help validation |
| --- | --- | --- | --- |
| Dataset | `aliyun agentloop create-dataset` | Create a Dataset and schema. | `aliyun agentloop create-dataset --help` |
| Dataset | `aliyun agentloop list-datasets` | List and filter Datasets. | `aliyun agentloop list-datasets --help` |
| Dataset | `aliyun agentloop get-dataset` | Get one Dataset and its schema. | `aliyun agentloop get-dataset --help` |
| Dataset | `aliyun agentloop update-dataset` | Update description or add schema fields. | `aliyun agentloop update-dataset --help` |
| Data | `aliyun agentloop add-dataset-data` | Append structured rows atomically. | `aliyun agentloop add-dataset-data --help` |
| Data | `aliyun agentloop execute-query` | Execute read-only SQL, SearchExpr, or pipe queries. | `aliyun agentloop execute-query --help` |

## Parameter Inventory

| Command | Required | Optional |
| --- | --- | --- |
| `create-dataset` | `--agent-space`, `--dataset-name`, `--schema` | `--description`, `--client-token`, `--region` |
| `list-datasets` | `--agent-space` | `--dataset-name`, `--max-results`, `--next-token`, `--region` |
| `get-dataset` | `--agent-space`, `--dataset-name` | `--region` |
| `update-dataset` | `--agent-space`, `--dataset-name` | `--description`, `--schema`, `--client-token`, `--region` |
| `add-dataset-data` | `--agent-space`, `--dataset-name`, `--data-array` | `--client-token`, `--region` |
| `execute-query` | `--agent-space`, `--dataset-name`, `--type`, `--query` | `--from`, `--to`, `--offset`, `--length`, `--max-output-length`, `--biz-version`, `--region` |

Use `--cli-dry-run` for request inspection, `--cli-query <jmespath>` for output filtering, and `--pager` for supported pageable APIs.

## Published Surface Note

The current public `aliyun-cli-agentloop 0.7.1` command surface does not expose create/list/delete version commands. Do not invent CLI subcommands for them. `execute-query --biz-version` may read an already existing snapshot version; the CLI serializes this flag as the request-body field `version`.
