# Knowledge retrieval and Session memory

Contract checked **2026-11-09** against the current [Create Agent](https://docs.bailian.console.aliyun.com/zh/model-studio/agent-create), [Create Session](https://docs.bailian.console.aliyun.com/zh/model-studio/session-create), and [Memory Store guide](https://docs.bailian.console.aliyun.com/zh/model-studio/managed-agents-memory-store). Use the corresponding `.md` pages when a cached HTML/search result omits newer fields. Availability and runtime results must still be checked in the target workspace.

REST verification in **cn-beijing**, using `qwen3.8-max`, confirmed retrieval through a published service, built-in file write-back and cross-Session reading, and Bailian memory asynchronous write-back, cross-Session reading and entity isolation. Rule/template binding was verified; extraction of skill memories and profile values was not covered by that verification.

## Choose the capability

| Need | Configuration | Data scope and access |
| --- | --- | --- |
| Retrieve enterprise documents | Agent `tools[].configs[]`: `search_knowledgebases` | A published knowledge retrieval service, identified by `aid-…` |
| Keep project notes and working files across Sessions | Session `resources[]`: `type=memory_store`, provider omitted or `default` | Built-in Memory Store file tree; file tools at the returned `/mnt/memory/…` path |
| Remember facts, reusable skills, or user profiles | Session `resources[]`: `type=memory_store`, `provider=agentstudio_memory` | **Bailian Memory Library**, scoped by library plus `entity_id`; memory tools, no filesystem mount |

Knowledge retrieval belongs to the Agent tool configuration. Memory belongs to each Session's resource bindings. An Agent can use knowledge retrieval together with either memory provider; the prohibition on mixing providers concerns memory bindings within one Session.

## Configure knowledge retrieval

Create and publish a [knowledge retrieval service](https://docs.bailian.console.aliyun.com/zh/model-studio/rag-knowledge-retrieval) in the intended workspace, with its knowledge bases and retrieval strategy configured. Use its **service ID**, not an individual knowledge base ID or an MA `agent_…` ID.

Add this entry to the existing `builtin_toolkit.configs[]`, preserving other tools:

```json
{
  "name": "search_knowledgebases",
  "enabled": true,
  "params": {
    "knowledge_application_id": "<published-retrieval-service-id>"
  }
}
```

`params` is a sibling of `name`, `enabled`, and optional `permission_policy`. Set `default_config.enabled: false` and explicitly enable needed tools as described in [tool configuration](tool-configuration.md). Knowledge retrieval is opt-in; an enabled toolkit default alone is not a substitute for this configuration. At most one `search_knowledgebases` entry is allowed.

When enabled, missing/null `params` or a missing, null, empty, whitespace-only, or non-string `knowledge_application_id` is invalid. Duplicate tool entries are also invalid. Disabled retrieval does not require a service ID. A syntactically valid ID can pass Agent creation even when the service does not exist: creation/read-back verifies configuration, not successful retrieval.

The model decides when to call the tool and forms a retrieval question from the conversation. For grounded answers, instruct it to retrieve relevant evidence and distinguish empty results from tool errors. In the console this is configured in the knowledge base retrieval strategy section, separately from the ordinary tool checklist. See [Agent tool documentation](https://docs.bailian.console.aliyun.com/zh/model-studio/managed-agents-builtin-tools).

When updating an Agent, use its current `version` and preserve other tool entries. Existing Sessions keep their snapshots; create a new Session or use an explicitly supported Session tool override to exercise a new configuration.

### Diagnose retrieval failures

Inspect the tool's actual `is_error`, error code and output, even if the turn ends with `idle/end_turn`. A completed turn can contain a failed retrieval.

If the tool fails, compare it with the [direct retrieval API](https://docs.bailian.console.aliyun.com/zh/model-studio/knowledgesearch) using the same workspace and service ID:

```text
POST https://<workspace-api-host>/api/v1/indices/knowledge/search
{"agent_id":"<published-retrieval-service-id>","query":"<question>"}
```

The direct API field is `agent_id`; the MA configuration field is `params.knowledge_application_id`. Retrieval routing, ranking and bound knowledge bases belong to the retrieval service configuration, not arbitrary additional MA tool parameters. Inspect HTTP status and business status together; preserve `request_id`. For `RagAgentGroupNotExist`, check the exact ID and workspace. For an unpublished service, publish its configured version before use. Do not silently switch workspaces or replace the ID with a knowledge base ID.

`KNOWLEDGE_SEARCH_INVALID_RESPONSE` is a tool failure, not an empty search. The upstream response can be more specific, so do not infer its cause from the wrapper error alone. Configuration acceptance or the model's promise to search is insufficient evidence of a working retrieval service.

## Create a Session with built-in memory

Create an MA Memory Store via `POST /memory_stores`, then attach its `memstore_…` ID:

```json
{
  "agent": {"type": "agent", "id": "<agent-id>"},
  "environment_id": "<environment-id>",
  "resources": [{
    "type": "memory_store",
    "provider": "default",
    "memory_store_id": "<built-in-memory-store-id>",
    "access": "read_write",
    "instructions": "Read existing project notes before working; save verified decisions and unfinished work."
  }]
}
```

Omitting `provider` selects this same built-in provider. Omitting `access` selects `read_write`. The response supplies `mount_path`; use `read` / `write` / `edit` / `glob` / `grep` on that path. These are virtual memory files: `bash` cannot access them. Enable the required file tools on the Agent.

Prefer Markdown note paths such as `/notes/handoff.md`. **Compatibility observation, 2026-11-09, one cn-beijing workspace:** equal-content `.md` writes succeeded while `.txt` writes returned HTTP 500 `api_error` / `Storage operation failed: OTSParameterInvalid`, including a 24-byte example. A 102400-byte `.md` write succeeded. This is an observed path compatibility problem, not a documented universal extension whitelist or a smaller file-size limit. After an ambiguous write failure, query the Store before retrying and retain the request ID for diagnosis.

The entire Store is shared by its mounted Sessions. `metadata.user_id` does not isolate it. Allocate separate Stores and enforce application authorization when users must not share data. Use `access: "read_only"` for a consumer that should only consult notes.

The file API, version history, conditional updates and archiving semantics remain specific to built-in memory; see [working-memory handoff](../cookbook/09-working-memory-handoff.md). Explicit file-tool write-back can be verified through the Memory API and a fresh Session. Do not equate that with automatic Dreaming completion.

## Create a Session with Bailian Memory Library

Enable the Bailian memory service and use a library created in that service. Its ID need not start with `memstore_`. MA's `/memory_stores` API manages built-in Stores, not Bailian libraries.

```json
{
  "agent": {"type": "agent", "id": "<agent-id>"},
  "environment_id": "<environment-id>",
  "resources": [{
    "type": "memory_store",
    "provider": "agentstudio_memory",
    "memory_store_id": "<bailian-memory-library-id>",
    "entity_id": "customer-001",
    "access": "read_write",
    "description": "Customer-confirmed preferences, project agreements, and reusable experience"
  }]
}
```

`agentstudio_memory` **means Bailian Memory Library**. `entity_id` is the business entity bound to this resource, not a cloud-account UID and not a Session top-level field. Surrounding whitespace is trimmed; IDs differing only by that whitespace are the same entity and count as duplicate bindings. The application must authorize the library/entity pair instead of trusting an arbitrary client-supplied entity ID. Distinct entities can use the same library without sharing their memories.

Optional extraction configuration belongs on the same resource object:

```json
{
  "project_ids": ["<existing-fact-rule-id>", "<existing-skill-rule-id>"],
  "profile_schema": "<existing-profile-template-id>"
}
```

Use IDs from the selected library's [memory rules](https://docs.bailian.console.aliyun.com/zh/model-studio/memory/configure-rules) and [profile templates](https://docs.bailian.console.aliyun.com/zh/model-studio/memory/create-schema). Omit optional keys when unused rather than filling them with invented IDs. A correctly typed but nonexistent rule/template can still fail resource validation.

- `project_ids`: one array combining fact and skill rule IDs, at most **5** per binding. IDs must be nonblank strings and unique. Omitted or `[]` uses default memory rules; `[]` does **not** disable extraction.
- `profile_schema`: one nonempty string ID, not an array or object. It does not count toward the five-rule limit. Omitted means profiles are not enabled; MA does not automatically attach a default template.
- `description`: caller-supplied purpose of this binding, retained separately from library metadata. Built-in memory instead uses `instructions` for its usage guidance.

The response has a server-generated resource `id` distinct from `memory_store_id`, plus provider/entity/access and optional selected rule/template fields. It may have an empty `name`. There is **no `mount_path`** for Bailian memory. Response omission of default rule IDs does not mean no rules are used; the response does not include memory content, extracted profile values, or complete rule definitions.

### Runtime use and persistence

Mounting provides memory operations to the Agent. Observed tool names include `search_memory`, `list_memory`, and `manage_memory`; use their actual runtime schemas rather than inventing a `builtin_toolkit` configuration or a filesystem path. Mount-local aliases such as `m1` are runtime identifiers, not library IDs.

Writes may return successful submission with `event_ids` and `events[].status: PENDING`; extraction happens asynchronously. Treat that as accepted, not yet persisted. Do not resubmit the same information because the initial response has no nodes. The application can inspect the [memory event API](https://docs.bailian.console.aliyun.com/zh/model-studio/memory/get-event) and later confirm through [memory listing](https://docs.bailian.console.aliyun.com/zh/model-studio/memory/list-memory) or a fresh Session. Do not force the conversational Agent to poll after a tool explicitly says submission is complete.

An empty semantic search is not proof that the entity has no stored memory. Where appropriate and authorized, inspect the scoped memory listing before concluding that a write was lost. Keep facts grounded in returned nodes. Separate the observations “write submitted,” “content persisted,” and “retrieval found the content.”

When diagnosing with the separate memory-service API, its corresponding scope fields are `memory_library_id` and `user_id` under `/api/v2/apps/memory`; MA uses `memory_store_id` and `entity_id` on the Session resource. Keep these API contracts distinct. If the service returns `403 ServiceNotOpened`, enable the service in the intended account rather than retrying unchanged or switching providers silently.

## Binding boundaries

| Boundary | Required behavior |
| --- | --- |
| Provider | Only omitted/`default` or `agentstudio_memory`; explicit null, empty string and other values are invalid |
| Memory count | At most **8 memory bindings** per Session |
| Mixed providers | All memory bindings in a Session must have the same provider |
| Built-in duplicates | The same Store cannot be mounted twice in one Session |
| Bailian duplicates | The same library/entity pair cannot appear twice; one library with different entities is allowed |
| Entity | Required for Bailian memory; must remain nonempty after trimming whitespace |
| Access | `read_only` or `read_write`; default is `read_write` |
| Built-in instructions | At most **4096 characters** per binding |
| Built-in file size | At most **102400 UTF-8 bytes** per file; bytes and characters differ |
| Binding lifecycle | Set memory bindings during Session creation; create a new Session to add, remove or change them. Runtime file-resource mounting does not support memory |

Use read-only mounts even if the Agent has write-capable tools. A model declining to write demonstrates its observed behavior, not backend enforcement by itself. Diagnose permissions using actual tool results and unchanged stored data; never infer enforcement merely from an assistant statement.
