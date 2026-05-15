# Related CLI Commands

All commands use plugin mode and must include `--api-version 2024-03-30`.

| Area | Command | Purpose | Help Validation |
| --- | --- | --- | --- |
| Store | `aliyun cms --api-version 2024-03-30 create-context-store` | Create memory or experience stores. | `aliyun cms --api-version 2024-03-30 create-context-store help` |
| Store | `aliyun cms --api-version 2024-03-30 get-context-store` | Get one store and inspect `contextType`. | `aliyun cms --api-version 2024-03-30 get-context-store help` |
| Store | `aliyun cms --api-version 2024-03-30 list-context-stores` | List stores, optionally filtered by type. | `aliyun cms --api-version 2024-03-30 list-context-stores help` |
| Store | `aliyun cms --api-version 2024-03-30 update-context-store` | Update mutable store configuration and description. | `aliyun cms --api-version 2024-03-30 update-context-store help` |
| Store | `aliyun cms --api-version 2024-03-30 delete-context-store` | Delete a ContextStore. | `aliyun cms --api-version 2024-03-30 delete-context-store help` |
| Context | `aliyun cms --api-version 2024-03-30 add-contexts` | Batch write memory or experience records. | `aliyun cms --api-version 2024-03-30 add-contexts help` |
| Context | `aliyun cms --api-version 2024-03-30 get-context` | Get one context record. | `aliyun cms --api-version 2024-03-30 get-context help` |
| Context | `aliyun cms --api-version 2024-03-30 search-context` | Semantic search over records. | `aliyun cms --api-version 2024-03-30 search-context help` |
| Context | `aliyun cms --api-version 2024-03-30 update-context` | Merge-update one context record. | `aliyun cms --api-version 2024-03-30 update-context help` |
| Context | `aliyun cms --api-version 2024-03-30 delete-context` | Delete one context record. | `aliyun cms --api-version 2024-03-30 delete-context help` |
| Context | `aliyun cms --api-version 2024-03-30 delete-contexts` | Batch delete by IDs or filter. | `aliyun cms --api-version 2024-03-30 delete-contexts help` |
| API Key | `aliyun cms --api-version 2024-03-30 create-context-store-api-key` | Create a store-scoped API key. | `aliyun cms --api-version 2024-03-30 create-context-store-api-key help` |
| API Key | `aliyun cms --api-version 2024-03-30 list-context-store-api-keys` | List API keys for one store. | `aliyun cms --api-version 2024-03-30 list-context-store-api-keys help` |
| API Key | `aliyun cms --api-version 2024-03-30 delete-context-store-api-key` | Delete a store-scoped API key by name. | `aliyun cms --api-version 2024-03-30 delete-context-store-api-key help` |

## Required Common Parameters

| Parameter | Commands | Notes |
| --- | --- | --- |
| `--workspace` | All ContextStore commands | Required workspace ID. |
| `--context-store-name` | All except `list-context-stores` | Required store name. |
| `--context-type` | `create-context-store`, `add-contexts` | `memory` or `experience`. |
| `--memory-type` | `add-contexts` for memory only | `short` or `long`; forbidden for experience. |
| `--items` | `add-contexts` | JSON array. |
| `--context-id` | `get-context`, `update-context`, `delete-context` | Single context ID. |
| `--context-ids` | `delete-contexts` | Comma-separated IDs. Mutually exclusive with `--filter`. |
| `--filter` | `search-context`, `delete-contexts` | JSON filter string. |
| `--query` | `search-context` | Semantic query text. |
| `--name` | API key create/delete | API key name. |
