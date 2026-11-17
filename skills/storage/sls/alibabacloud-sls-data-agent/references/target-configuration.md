# Specifying DataAgents, models, and logstores

Specify the resources in the current request, or record frequently used resources in the project's `AGENTS.md`.

Context Model and Source Model calls derive the service endpoint from Region by default. To use a specific endpoint, add an `Endpoint` column to the corresponding table; that address takes precedence.

## DataAgents

| DataAgent | Chat Region |
| --- | --- |
| `<DataAgent-resource-name>` | `cn-beijing` |

Chat Region identifies the conversation service region. Supported regions: `cn-beijing` and `ap-southeast-1`.

## Context Models

| Context Model | Region |
| --- | --- |
| `<model-name-or-UUID>` | `cn-beijing` |

Region identifies the model service region. Supported regions: `cn-beijing` and `ap-southeast-1`.

## Source Models

| Project | Logstore | Region |
| --- | --- | --- |
| `<project-name>` | `<logstore-name>` | `cn-shanghai` |

Source Models support all available SLS regions. Use the Project's actual region.
