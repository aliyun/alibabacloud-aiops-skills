# RAM Policies

## Required Actions

| API | RAM action |
| --- | --- |
| CreateDataset | `agentloop:CreateDataset` |
| ListDatasets | `agentloop:ListDatasets` |
| GetDataset | `agentloop:GetDataset` |
| UpdateDataset | `agentloop:UpdateDataset` |
| AddDatasetData | `agentloop:AddDatasetData` |
| ExecuteQuery | `agentloop:ExecuteQuery` |

Dataset resource ARN:

```text
acs:agentloop:<region_id>:<account_id>:agentspace/<agent_space_name>/dataset/<dataset_name>
```

`ListDatasets` uses the Dataset wildcard under one AgentSpace:

```text
acs:agentloop:<region_id>:<account_id>:agentspace/<agent_space_name>/dataset/*
```

## Least-Privilege Template

Replace all placeholders. Split read and write permissions when the identity does not need mutations.

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "agentloop:CreateDataset",
        "agentloop:ListDatasets",
        "agentloop:GetDataset",
        "agentloop:UpdateDataset",
        "agentloop:AddDatasetData",
        "agentloop:ExecuteQuery"
      ],
      "Resource": "acs:agentloop:<region_id>:<account_id>:agentspace/<agent_space_name>/dataset/*"
    }
  ]
}
```

For a single existing Dataset, narrow applicable actions to:

```text
acs:agentloop:<region_id>:<account_id>:agentspace/<agent_space_name>/dataset/<dataset_name>
```

Keep `ListDatasets` on the wildcard resource if listing is required. Confirm whether CreateDataset authorization needs the future Dataset ARN with the requested name in the target account.

## Query-Capable Template

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "agentloop:ListDatasets",
        "agentloop:GetDataset",
        "agentloop:ExecuteQuery"
      ],
      "Resource": "acs:agentloop:<region_id>:<account_id>:agentspace/<agent_space_name>/dataset/*"
    }
  ]
}
```

`ExecuteQuery` can execute mutations as well as reads. The RAM action has no statement-type condition, so a policy that grants it cannot enforce read-only SQL. Do not include `ExecuteQuery` in a security boundary that must prevent writes unless a more restrictive policy mechanism is available for that account.

## Permission Failure Handling

1. Record the API action, denied action, HTTP status, and request ID.
2. Do not print request signing material or credentials.
3. Compare the denied action with the tables above.
4. Invoke `ram-permission-diagnose` if installed. Otherwise present the smallest required action and scoped resource ARN.
5. Ask the user to attach the approved policy through the Alibaba Cloud RAM console.
6. Wait for confirmation before retrying.
