---
name: alibabacloud-milvus-manage
description: >
  Alibaba Cloud Milvus full-stack Skill for two planes: control-plane instance management via aliyun CLI,
  and data-plane Milvus operations via pymilvus. Use when users want to create, inspect, scale, configure,
  network-enable, or whitelist Alibaba Cloud Milvus instances; or connect to Milvus and perform
  collection management, vector insert/search, hybrid search, full-text search, index management,
  partition/database management, or RBAC with Python.
license: MIT AND Apache-2.0
compatibility: >
  Control-plane requires Alibaba Cloud CLI (`aliyun` >= 3.0) with valid credentials and Milvus calls must use `--force`.
  Data-plane requires Python 3.8+ and `pymilvus`. Works on macOS and Linux.
metadata:
  domain: vector-database
  owner: milvus-team
  data-plane-author: jinchen
allowed-tools: Bash Read Write
---

# Alibaba Cloud Milvus Full-Stack Skill

Handle two distinct planes:

- **Control-plane**: manage Alibaba Cloud managed Milvus instances with `aliyun` CLI.
- **Data-plane**: operate Milvus with `pymilvus` Python code.

Treat `SKILL.md` as the router. Load `references/*.md` for detailed commands, parameters, and examples.

## Scope

Use this skill for:

- Alibaba Cloud managed Milvus instance lifecycle: create, inspect, scale, rename, configure, network, whitelist.
- Milvus Python SDK workflows with `pymilvus`: connect, collections, vectors, search, indexes, partitions, databases, RBAC.
- Retrieval use cases built on Milvus: semantic search, hybrid search, full-text search, RAG patterns.

Do not use this skill for:

- self-hosted Milvus deployment on Docker, Helm, Kubernetes, or Milvus Operator,
- Milvus Java / Go / Node SDKs,
- other Alibaba Cloud products such as ECS, RDS, OSS, EMR, Kafka, StarRocks,
- other vector databases such as Zilliz Cloud, Pinecone, Qdrant, or Weaviate.

## Route The Request

### Control-plane

Route here when the user asks about:

- creating, scaling, renaming, or inspecting a Milvus instance,
- connection address, component spec, configuration, public network, whitelist,
- VPC/VSwitch prerequisites for Alibaba Cloud Milvus,
- `aliyun milvus` APIs, creation parameters, or control-plane troubleshooting.

Read:

- first-time flow: [references/getting-started.md](references/getting-started.md)
- create / list / detail / scale / release: [references/instance-lifecycle.md](references/instance-lifecycle.md)
- config / network / inspection / troubleshooting: [references/operations.md](references/operations.md)
- creation field meanings and templates: [references/create-params.md](references/create-params.md)
- raw API field reference: [references/api-reference.md](references/api-reference.md)
- RAM permissions: [references/ram-policies.md](references/ram-policies.md)

### Data-plane

Route here when the user asks about:

- connecting to Milvus with Python,
- creating collections or schemas,
- inserting, upserting, querying, deleting, or searching vectors,
- hybrid search, BM25 full-text search, iterators, indexes,
- partitions, databases, users, roles, or privileges,
- Milvus-based RAG or semantic retrieval patterns.

Read:

- collection schema and lifecycle: [references/collection.md](references/collection.md)
- vector CRUD, search, hybrid search, full-text search: [references/vector.md](references/vector.md)
- index types and metrics: [references/index.md](references/index.md)
- partitions: [references/partition.md](references/partition.md)
- databases: [references/database.md](references/database.md)
- RBAC: [references/user-role.md](references/user-role.md)
- common solution patterns: [references/patterns.md](references/patterns.md)

## Shared Guardrails

- Decide the plane first. Do not mix control-plane instance operations with data-plane SDK code.
- Confirm destructive actions before execution.
- Validate untrusted user input before passing it into shell commands or code.
- Prefer loading a targeted reference doc instead of keeping large inline examples in this file.

## Control-Plane Rules

### Required Environment

- Reuse the configured `aliyun` profile. Check with `aliyun configure list`.
- Set the required User-Agent before Milvus API calls:

```bash
export ALIBABA_CLOUD_USER_AGENT="AlibabaCloud-Agent-Skills"
```

- Milvus OpenAPI calls through `aliyun` must include `--force`.

### Preconditions

Before create or major modify operations:

1. Confirm `RegionId` with the user.
2. Verify VPC and VSwitch resources in that region.
3. For create, record `ZoneId`, `VpcId`, and `VSwitchId`.
4. If the request is ambiguous, ask whether the user wants dev/test standalone or production HA cluster.

Baseline decision rule:

- `standalone_pro` is the default for dev/test.
- HA cluster is for production.
- In HA mode, `streaming`, `data`, `mix_coordinator`, and `query` must use at least 4 CU; `proxy` must use at least 2 CU.

Detailed templates and field definitions live in [references/instance-lifecycle.md](references/instance-lifecycle.md) and [references/create-params.md](references/create-params.md).

### CLI Calling Modes

Use the API's expected parameter mode. Do not improvise.

```bash
# get / delete: business params in URL query
aliyun milvus get "/path?RegionId=<region>&instanceId=<id>" --RegionId <region> --force

# post / put with request body: business params in --body JSON
aliyun milvus post "/path?RegionId=<region>" --RegionId <region> --body '{...}' --force

# post with query-style flags: business params as --Flag value
aliyun milvus post "/path" --RegionId <region> --InstanceId <id> --force
```

Rules:

- Always pass `--RegionId <region>`.
- For `CreateInstance` and `UpdateInstance`, use `--body`.
- For query-style POST APIs such as detail, config, network, ACL, and rename operations, use `--Flag value`.
- Do not put user-provided raw text directly into a shell command unless it has been validated.

### Runtime Safety

- Do not download and execute remote scripts or unaudited dependencies during control-plane work.
- Do not use `eval` or `source` with untrusted input.
- Set reasonable timeouts on CLI calls. Prefer short timeouts for reads and bounded polling for long-running async operations.
- For list APIs, do not trust `total` blindly; inspect the returned array.
- Read the full error message before retrying. Automatic retry is appropriate for throttling, not for arbitrary failures.

### Forbidden Operations

- **Instance deletion (DeleteInstance) is strictly forbidden through this Skill.** If the user requests to delete/release a Milvus instance, do **not** execute the `aliyun milvus delete` command. Instead, instruct the user to delete the instance via the [Alibaba Cloud Milvus Console](https://milvus.console.aliyun.com/#/overview).

### Destructive Operations

Require explicit confirmation before:

- modifying instance config,
- disabling public network access.

Use this template:

> About to execute: `<API>`, Target: `<InstanceId>`, Impact: `<Description>`. Continue?

For config change and network troubleshooting flows, read [references/operations.md](references/operations.md) or [references/instance-lifecycle.md](references/instance-lifecycle.md) first.

### Output Style

- Summarize instance lists as a compact table.
- Highlight `instanceId`, `instanceName`, `status`, `dbVersion`, `ha`, `paymentType`, and connection endpoints when relevant.
- Convert timestamps to readable time.
- Use `--cli-query` or `jq` to trim noisy payloads when useful.

## Data-Plane Rules

### Connection First

Before writing any `pymilvus` code, ask for:

1. deployment type: Milvus Lite, self-hosted standalone/cluster, or Alibaba Cloud managed instance,
2. URI or endpoint,
3. authentication method and credentials if needed,
4. database name if not using `default`.

Do not assume connection parameters. Use Milvus Lite only when the user explicitly wants local embedded mode.

Minimal connection shape:

```python
from pymilvus import MilvusClient

client = MilvusClient(uri="<USER_URI>", token="<USER_TOKEN>")
```

For async usage, schema details, and deployment-specific patterns, load the relevant reference doc.

### Data Safety And Correctness

- Never generate fake or placeholder vectors. Always use a real embedding model.
- The query embedding model must match the model used to create stored vectors.
- Vector dimensions must exactly match the collection schema.
- A collection must be loaded before search or query.
- Confirm destructive operations such as `drop_collection`, `drop_database`, or large deletes before executing.
- Prefer `AUTOINDEX` unless the user has explicit performance requirements.

### Minimal Workflow

For most SDK tasks:

1. load [references/collection.md](references/collection.md) for schema and collection operations,
2. load [references/vector.md](references/vector.md) for insert/search/query/delete patterns,
3. load [references/index.md](references/index.md) if the user cares about index type, metric, or tuning,
4. add partition/database/RBAC references only if the task actually needs them.

### Common Patterns

- quick prototype collection: [references/collection.md](references/collection.md)
- vector CRUD and similarity search: [references/vector.md](references/vector.md)
- hybrid search or full-text search: [references/vector.md](references/vector.md)
- RAG / semantic retrieval patterns: [references/patterns.md](references/patterns.md)
- index tuning: [references/index.md](references/index.md)

## Suggested Response Flow

### If control-plane

1. Confirm region and target instance scope.
2. Read the matching control-plane reference.
3. Run the command with the correct parameter mode.
4. Report the key fields, next state, and any follow-up wait conditions.

### If data-plane

1. Ask for connection details first.
2. Read only the references needed for the requested SDK task.
3. Write or explain `pymilvus` code with real embeddings and real connection placeholders.
4. Call out schema, load-state, index, and dimension pitfalls if they matter.

## Reference Map

- [references/getting-started.md](references/getting-started.md): first Milvus instance from scratch
- [references/instance-lifecycle.md](references/instance-lifecycle.md): create, inspect, scale, rename, release
- [references/operations.md](references/operations.md): config, network, ACL, inspection, troubleshooting
- [references/create-params.md](references/create-params.md): create body fields and component templates
- [references/api-reference.md](references/api-reference.md): raw API signatures and return fields
- [references/collection.md](references/collection.md): schema and collection lifecycle
- [references/vector.md](references/vector.md): insert, search, hybrid search, BM25, iterators
- [references/index.md](references/index.md): index types and metric guidance
- [references/partition.md](references/partition.md): partition operations
- [references/database.md](references/database.md): database operations
- [references/user-role.md](references/user-role.md): users, roles, privileges
- [references/patterns.md](references/patterns.md): RAG and semantic search patterns
- [references/ram-policies.md](references/ram-policies.md): IAM/RAM policies
