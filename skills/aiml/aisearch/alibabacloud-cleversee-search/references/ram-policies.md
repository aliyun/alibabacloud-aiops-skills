# RAM Policies — alibabacloud-cleversee-search

## Required Permission

| Permission Name | Description |
|-----------------|-------------|
| `AliyunCleverSeeAISearchPlatformUserAccess` | CleverSee AI Search Platform user access |

## Policy Actions

| Action | Service | Description |
|--------|---------|-------------|
| `aisearchengine:EngineSearch` | AI Search Engine | Execute web search via CleverSee |

## Policy Document

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": "aisearchengine:EngineSearch",
      "Resource": "*"
    }
  ]
}
```

## Applying the Permission

Grant the system policy `AliyunCleverSeeAISearchPlatformUserAccess` to the RAM user/role via the [RAM Console](https://ram.console.aliyun.com) or CLI.
