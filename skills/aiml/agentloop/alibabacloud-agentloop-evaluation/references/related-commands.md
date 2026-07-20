# Related CLI Commands — AgentLoop Evaluation

## AgentLoop plugin commands

| Product | CLI Command | Description |
|---------|-------------|-------------|
| AgentLoop | `aliyun agentloop get-agent-space` | Get AgentSpace details and resolve SLS project |
| AgentLoop | `aliyun agentloop list-evaluators` | List saved or built-in evaluators |
| AgentLoop | `aliyun agentloop get-evaluator` | Get evaluator details or validate a reference |
| AgentLoop | `aliyun agentloop create-evaluator` | Create a saved evaluator (AGENT, LLM, or CODE) |
| AgentLoop | `aliyun agentloop update-evaluator` | Update evaluator metadata or add a version |
| AgentLoop | `aliyun agentloop delete-evaluator` | Delete an evaluator version or whole evaluator |
| AgentLoop | `aliyun agentloop list-evaluator-skills` | List skills attached to an evaluator |
| AgentLoop | `aliyun agentloop get-evaluator-skill` | Inspect one evaluator skill |
| AgentLoop | `aliyun agentloop create-evaluator-skill` | Create an evaluator skill |
| AgentLoop | `aliyun agentloop update-evaluator-skill` | Update evaluator-skill metadata or files |
| AgentLoop | `aliyun agentloop delete-evaluator-skill` | Delete an evaluator skill |
| AgentLoop | `aliyun agentloop create-evaluation-task` | Create and start an evaluation task |
| AgentLoop | `aliyun agentloop list-evaluation-tasks` | List evaluation tasks |
| AgentLoop | `aliyun agentloop get-evaluation-task` | Get task state and last run |
| AgentLoop | `aliyun agentloop update-evaluation-task` | Update task fields or terminate a task |
| AgentLoop | `aliyun agentloop delete-evaluation-task` | Delete a task |
| AgentLoop | `aliyun agentloop list-evaluation-runs` | List runs for a task |
| AgentLoop | `aliyun agentloop get-evaluation-run` | Get run details and results |
| AgentLoop | `aliyun agentloop update-evaluation-run` | Update a run |
| AgentLoop | `aliyun agentloop delete-evaluation-run` | Delete a run |

## SLS plugin commands (result analysis)

| Product | CLI Command | Description |
|---------|-------------|-------------|
| SLS | `aliyun sls get-logs-v2` | Query the `evaluation_detail` Logstore |

## CLI utility commands

| Product | CLI Command | Description |
|---------|-------------|-------------|
| CLI | `aliyun version` | Check CLI version (>= 3.3.3 required) |
| CLI | `aliyun upgrade` | Self-update CLI (>= 3.3.5) |
| CLI | `aliyun plugin show --name aliyun-cli-agentloop` | Verify AgentLoop plugin installed |
| CLI | `aliyun plugin show --name aliyun-cli-sls` | Verify SLS plugin installed |
| CLI | `aliyun plugin update` | Update all installed plugins |
| CLI | `aliyun configure list` | Check credential profile status |
| CLI | `aliyun configure set --auto-plugin-install true` | Enable automatic plugin installation |

## Global flags

| Flag | Description |
|------|-------------|
| `--cli-dry-run` | Render request without sending mutation |
| `--region` | Override endpoint-selection region |
| `--endpoint` | Override service endpoint |
| `--log-level DEBUG` | Collect request diagnostics |
| `--cli-query '<JMESPath>'` | Filter response output |
| `--user-agent` | Observability user-agent string (required on all API calls) |
