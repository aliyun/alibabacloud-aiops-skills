# RAM Policies — AgentLoop Evaluation

This document lists the Alibaba Cloud RAM (Resource Access Management) permissions required by the AgentLoop evaluation skill.

## AgentLoop service permissions

| API Action | CLI Command | Permission Required |
|---|---|---|
| GetAgentSpace | `agentloop get-agent-space` | `agentloop:GetAgentSpace` |
| ListEvaluators | `agentloop list-evaluators` | `agentloop:ListEvaluators` |
| GetEvaluator | `agentloop get-evaluator` | `agentloop:GetEvaluator` |
| CreateEvaluator | `agentloop create-evaluator` | `agentloop:CreateEvaluator` |
| UpdateEvaluator | `agentloop update-evaluator` | `agentloop:UpdateEvaluator` |
| DeleteEvaluator | `agentloop delete-evaluator` | `agentloop:DeleteEvaluator` |
| ListEvaluatorSkills | `agentloop list-evaluator-skills` | `agentloop:ListEvaluatorSkills` |
| GetEvaluatorSkill | `agentloop get-evaluator-skill` | `agentloop:GetEvaluatorSkill` |
| CreateEvaluatorSkill | `agentloop create-evaluator-skill` | `agentloop:CreateEvaluatorSkill` |
| UpdateEvaluatorSkill | `agentloop update-evaluator-skill` | `agentloop:UpdateEvaluatorSkill` |
| DeleteEvaluatorSkill | `agentloop delete-evaluator-skill` | `agentloop:DeleteEvaluatorSkill` |
| CreateEvaluationTask | `agentloop create-evaluation-task` | `agentloop:CreateEvaluationTask` |
| ListEvaluationTasks | `agentloop list-evaluation-tasks` | `agentloop:ListEvaluationTasks` |
| GetEvaluationTask | `agentloop get-evaluation-task` | `agentloop:GetEvaluationTask` |
| UpdateEvaluationTask | `agentloop update-evaluation-task` | `agentloop:UpdateEvaluationTask` |
| DeleteEvaluationTask | `agentloop delete-evaluation-task` | `agentloop:DeleteEvaluationTask` |
| ListEvaluationRuns | `agentloop list-evaluation-runs` | `agentloop:ListEvaluationRuns` |
| GetEvaluationRun | `agentloop get-evaluation-run` | `agentloop:GetEvaluationRun` |
| UpdateEvaluationRun | `agentloop update-evaluation-run` | `agentloop:UpdateEvaluationRun` |
| DeleteEvaluationRun | `agentloop delete-evaluation-run` | `agentloop:DeleteEvaluationRun` |

## SLS service permissions (result analysis only)

| API Action | CLI Command | Permission Required |
|---|---|---|
| GetLogsV2 | `sls get-logs-v2` | `sls:GetLogs` |

## Sample RAM policy

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "agentloop:GetAgentSpace",
        "agentloop:ListEvaluators",
        "agentloop:GetEvaluator",
        "agentloop:CreateEvaluator",
        "agentloop:UpdateEvaluator",
        "agentloop:ListEvaluatorSkills",
        "agentloop:GetEvaluatorSkill",
        "agentloop:CreateEvaluatorSkill",
        "agentloop:UpdateEvaluatorSkill",
        "agentloop:CreateEvaluationTask",
        "agentloop:ListEvaluationTasks",
        "agentloop:GetEvaluationTask",
        "agentloop:UpdateEvaluationTask",
        "agentloop:ListEvaluationRuns",
        "agentloop:GetEvaluationRun"
      ],
      "Resource": "*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "sls:GetLogs"
      ],
      "Resource": "*"
    }
  ]
}
```

> **Note:** Delete and terminate permissions (`DeleteEvaluator`, `DeleteEvaluationTask`, etc.) are intentionally omitted from the sample policy because this skill does not automate destructive operations. Grant them only when explicitly needed.

## Permission Failure Handling

When any command or API call fails due to permission errors at any point during execution, follow this process:

1. Read this file (`references/ram-policies.md`) to get the full list of permissions required by this skill.
2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions.
3. Pause and wait until the user confirms that the required permissions have been granted.
