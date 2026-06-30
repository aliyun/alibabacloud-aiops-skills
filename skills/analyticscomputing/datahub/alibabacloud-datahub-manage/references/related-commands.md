# Related CLI Commands: DataHub Resource Management

## Project Management

| CLI Command | Description | Required Parameters | Optional Parameters |
|------------|-------------|---------------------|---------------------|
| `aliyun datahub list-projects` | List all projects in a region | — | `--region`, `--keyword`, `--max-results`, `--next-token`, `--skip`, `--pure` |
| `aliyun datahub create-project` | Create a new project | `--project-name`, `--comment` | `--region` |
| `aliyun datahub get-project` | Query project details | `--project-name` | `--region` |
| `aliyun datahub update-project` | Update project description | `--project-name` | `--region`, `--comment` |
| `aliyun datahub delete-project` | Delete a project | `--project-name` | `--region` |

## Topic Management

| CLI Command | Description | Required Parameters | Optional Parameters |
|------------|-------------|---------------------|---------------------|
| `aliyun datahub list-topics` | List all topics in a project | `--project-name` | `--region`, `--keyword`, `--max-results`, `--next-token`, `--skip`, `--pure` |
| `aliyun datahub create-topic` | Create a new topic | `--project-name`, `--topic-name`, `--shard-count`, `--lifecycle`, `--record-type`, `--comment` | `--region`, `--record-schema`, `--enable-schema-registry`, `--expand-mode` |
| `aliyun datahub get-topic` | Query topic details | `--project-name`, `--topic-name` | `--region` |
| `aliyun datahub update-topic` | Update topic description | `--project-name`, `--topic-name` | `--region`, `--comment` |
| `aliyun datahub delete-topic` | Delete a topic | `--project-name`, `--topic-name` | `--region` |

## Subscription Management

| CLI Command | Description | Required Parameters | Optional Parameters |
|------------|-------------|---------------------|---------------------|
| `aliyun datahub list-subscriptions` | List subscriptions under a topic | `--project-name`, `--topic-name` | `--region`, `--keyword`, `--max-results`, `--next-token`, `--skip` |
| `aliyun datahub create-subscription` | Create a subscription | `--project-name`, `--topic-name`, `--application`, `--comment` | `--region`, `--subscription-id` |
| `aliyun datahub get-subscription` | Query subscription details | `--project-name`, `--topic-name`, `--subscription-id` | `--region` |
| `aliyun datahub delete-subscription` | Delete a subscription | `--project-name`, `--topic-name`, `--subscription-id` | `--region` |

## Global Parameters (applicable to all commands)

| Parameter | Description |
|-----------|-------------|
| `--region` | Override region ID for the endpoint (e.g., `cn-hangzhou`) |
| `--endpoint` | Override service endpoint URL |
| `--connect-timeout` | Connection timeout in seconds |
| `--read-timeout` | I/O read timeout in seconds |
| `--user-agent` | Custom User-Agent string |
| `--cli-query` | JMESPath expression to filter output |
| `-q` / `--quiet` | Suppress output (quiet mode) |

## Naming Conventions

| Resource | Rules |
|----------|-------|
| Project Name | Starts with a letter, contains only letters/digits/underscores, 3-32 characters, unique within a region |
| Topic Name | Starts with a letter/digit/underscore, may contain hyphens, 3-128 characters, unique within a project |
| Subscription ID | Starts with a lowercase letter, contains only lowercase letters/digits/underscores, 4-40 characters (optional — auto-generated if not specified) |
