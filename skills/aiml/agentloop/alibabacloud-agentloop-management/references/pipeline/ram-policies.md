# RAM Policies

## Required Actions

Pipeline RAM actions follow the AgentLoop `agentloop:<ApiName>` convention. The
API names are the ones declared for this skill in `related_apis.yaml`.

| API | RAM action | Category |
| --- | --- | --- |
| CreatePipeline | `agentloop:CreatePipeline` | Mutation |
| GetPipeline | `agentloop:GetPipeline` | Read |
| ListPipelines | `agentloop:ListPipelines` | Read |
| UpdatePipeline | `agentloop:UpdatePipeline` | Mutation |
| DeletePipeline | `agentloop:DeletePipeline` | Destructive |
| PausePipeline | `agentloop:PausePipeline` | Lifecycle |
| ResumePipeline | `agentloop:ResumePipeline` | Lifecycle |
| TerminatePipeline | `agentloop:TerminatePipeline` | Destructive |
| PreviewPipeline | `agentloop:PreviewPipeline` | Processing (billable) |
| RunPipeline | `agentloop:RunPipeline` | Processing (billable) |
| CancelPipelineRun | `agentloop:CancelPipelineRun` | Lifecycle |
| GetPipelineRun | `agentloop:GetPipelineRun` | Read |
| ListPipelineRuns | `agentloop:ListPipelineRuns` | Read |
| GetPipelineStats | `agentloop:GetPipelineStats` | Read |
| GetAgentSpace | `agentloop:GetAgentSpace` | Read (used by `doctor --agent-space`) |

A Pipeline reads from an SLS LogStore and writes to an AgentLoop Dataset, so an
end-to-end run also needs:

- read permission on the source SLS project and LogStore, granted through SLS
  RAM actions on the source resource, not through `agentloop:*`;
- the Dataset actions in [references/dataset/ram-policies.md](../dataset/ram-policies.md)
  when the same identity also creates or inspects the sink Dataset.

Do not use a wildcard action pattern such as `agentloop:*` in a policy.

Pipeline resource ARN:

```text
acs:agentloop:<region_id>:<account_id>:agentspace/<agent_space_name>/pipeline/<pipeline_name>
```

`ListPipelines` uses the Pipeline wildcard under one AgentSpace:

```text
acs:agentloop:<region_id>:<account_id>:agentspace/<agent_space_name>/pipeline/*
```

`GetAgentSpace` is not a Pipeline-scoped action. Grant it on the AgentSpace ARN:

```text
acs:agentloop:<region_id>:<account_id>:agentspace/<agent_space_name>
```

Confirm the exact ARN shape against the account's RAM console or an authorization
error message before hardcoding it in a production policy; the error message for
a denied request names the resource that was evaluated.

## Read-Only Template

Use this for inspection-only work: `doctor`, listing, and reading runs or stats.
It cannot create, modify, preview, or run anything.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "agentloop:ListPipelines",
        "agentloop:GetPipeline",
        "agentloop:GetPipelineRun",
        "agentloop:ListPipelineRuns",
        "agentloop:GetPipelineStats"
      ],
      "Resource": "acs:agentloop:<region_id>:<account_id>:agentspace/<agent_space_name>/pipeline/*"
    },
    {
      "Effect": "Allow",
      "Action": "agentloop:GetAgentSpace",
      "Resource": "acs:agentloop:<region_id>:<account_id>:agentspace/<agent_space_name>"
    }
  ]
}
```

## Create-and-Validate Template

Use this for the documented core workflow: dry-run, `preview-pipeline`, create,
and then inspect the result. It excludes every destructive action.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "agentloop:ListPipelines",
        "agentloop:GetPipeline",
        "agentloop:GetPipelineRun",
        "agentloop:ListPipelineRuns",
        "agentloop:GetPipelineStats",
        "agentloop:PreviewPipeline",
        "agentloop:CreatePipeline",
        "agentloop:RunPipeline"
      ],
      "Resource": "acs:agentloop:<region_id>:<account_id>:agentspace/<agent_space_name>/pipeline/*"
    },
    {
      "Effect": "Allow",
      "Action": "agentloop:GetAgentSpace",
      "Resource": "acs:agentloop:<region_id>:<account_id>:agentspace/<agent_space_name>"
    }
  ]
}
```

`PreviewPipeline` and `RunPipeline` read real source data and execute nodes.
When the spec contains `llm-call` or `agentic-call`, granting them also grants
the ability to spend model quota. Keep them out of any identity that must not
incur processing cost.

## Lifecycle and Destructive Actions

Grant these separately, per Pipeline, and only for the duration of the requested
change:

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "agentloop:UpdatePipeline",
        "agentloop:PausePipeline",
        "agentloop:ResumePipeline",
        "agentloop:CancelPipelineRun",
        "agentloop:TerminatePipeline",
        "agentloop:DeletePipeline"
      ],
      "Resource": "acs:agentloop:<region_id>:<account_id>:agentspace/<agent_space_name>/pipeline/<pipeline_name>"
    }
  ]
}
```

`UpdatePipeline` replaces each supplied configuration block as a whole, so it can
silently drop nodes; treat it as a mutation with the same care as delete.

## Data Flow Declaration

| Direction | Data | Destination |
| --- | --- | --- |
| Outbound | Pipeline spec, node expressions, prompts for AI nodes | AgentLoop API in the configured region |
| Inbound | Sampled source rows from `preview-pipeline`, run status, statistics | Local session output |
| Service-internal | Source LogStore rows processed into Dataset rows | SLS source and Dataset sink in the same account |

Preview responses can contain real user content from the source LogStore,
including prompts, messages, tool arguments, and model output. Treat that output
as sensitive: do not copy it into commit messages, issue trackers, or any
external service.

## Permission Failure Handling

1. Record the API action, denied action, HTTP status, and request ID.
2. Do not print request signing material or credentials.
3. Compare the denied action with the tables above.
4. Invoke `ram-permission-diagnose` if installed. Otherwise present the smallest
   required action and scoped resource ARN.
5. Ask the user to attach the approved policy through the Alibaba Cloud RAM
   console.
6. Wait for confirmation before retrying.
