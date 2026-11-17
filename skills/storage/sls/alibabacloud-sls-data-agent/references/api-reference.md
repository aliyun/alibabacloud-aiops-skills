# Execution interfaces

Use the selected workflow for command templates. Authentication and permissions are described in [Installation and configuration](cli-installation-guide.md) and [RAM permissions](ram-policies.md).

## DataAgent Chat

| Entry point | SLS API |
| --- | --- |
| `aliyun sls list-data-agents` | `ListDataAgents` |
| `chat.py send` when creating a thread | `CreateThread` |
| `chat.py send`, `respond`, and `reconnect` | `CreateChat` |
| `aliyun sls get-thread-data` | `GetThreadData` |
| `aliyun sls create-chat --action stop` | `CreateChat` |

Use the confirmed DataAgent resource `name` and Chat service region. Script execution returns one complete JSON object on stdout; progress and diagnostics use stderr. Continue and recover requests according to [DataAgent Chat](data-agent-chat.md).

## Model queries

| Entry point | SLS API |
| --- | --- |
| `model_qa.py context-model list` | `ListContextModels` |
| `model_qa.py context-model catalog overview/get/resolve` | `QueryContextModel` |
| `model_qa.py source-model status` | `GetSourceModelStatus` |
| `model_qa.py source-model query` and `catalog overview/get` | `QuerySourceModel` |
| `model_qa.py query` | `GetLogsV2` |
| `aliyun sls get-index` | `GetIndex` |

The bundled model entry point uses the SLS `2020-12-30` API through the SDK. The official model-list operation is `ListContextModels` (`GET /context-models`). Use the permission reference for RAM authorization.

## Optional Source Model operations

`aliyun sls create-source-model` and `regenerate-source-model` are used only for explicitly requested operations under the existing management/HIL flow. See [Source Model readiness](model-data-qa/source-model-readiness.md). Python model commands provide reads only.
