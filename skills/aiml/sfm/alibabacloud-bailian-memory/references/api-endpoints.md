# API Endpoints Reference

Base URL: `https://dashscope.aliyuncs.com/api/v2/apps/memory` (production)
(Override with env `BAILIAN_MEMORY_BASE_URL` for testing against the pre-release environment.)

Authentication: `Authorization: Bearer $DASHSCOPE_API_KEY` — the key must belong
to the same environment as the endpoint; mismatched keys return 401.

Scope: the 16 REST endpoints used by this skill. All memory writes go through
POST `/add-async`. Management endpoints (memory project create/list/get/update,
profile schema create/list/update) are included; project/schema deletion is not
covered and remains a Bailian console operation.

---

## 1. AddMemoryAsync — POST `/add-async`

Asynchronously extract or save memories; accepted immediately, extraction runs
in the background and results are tracked via the returned `event_id`. The
endpoint has two modes with disjoint parameter sets, exposed as two scripts:

**Messages mode (→ `add_memory_messages.py`):**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Memory entity ID, max 64 chars |
| `messages` | array | Yes | Conversation messages (`role`, `content`), max 50 records. Roles `user`/`assistant`/`tool`; `tool_calls`/`tool_call_id` follow the standard OpenAI format |
| `timestamp` | long | No | Message Unix timestamp in seconds |
| `memory_library_id` | string | No | Memory library ID (max 32 chars) |
| `project_id` | string | No | Single project. Mutually exclusive with `project_ids` |
| `project_ids` | array | No | Extract into multiple projects at once |
| `profile_schema` | string | No | Also extract user profile attributes (separate event resource) |
| `meta_data` | object | No | Custom metadata |

**Content mode (→ `add_memory_content.py`):**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Memory entity ID |
| `custom_content` | string | Yes | Content saved as-is (no LLM extraction) |
| `timestamp` | long | No | Message Unix timestamp in seconds |
| `memory_library_id` | string | No | Memory library ID |
| `project_id` | string | No | Single project only (`project_ids` NOT supported) |
| `meta_data` | object | No | Custom metadata |

> Content mode does NOT support `profile_schema` (profile extraction depends on
> conversation messages, which this mode does not take).

**Response:**
```json
{
  "request_id": "string",
  "event_id": "string",
  "events": [
    {
      "event_id": "string",
      "event_type": "ADD_ASYNC",
      "resource_id": "project or profile schema ID",
      "resource_type": "observation | custom_observation | profile",
      "status": "PENDING | SUCCEEDED | FAILED",
      "user_id": "string",
      "memory_library_id": "string",
      "created_at": 1700000000,
      "updated_at": 1700000000
    }
  ]
}
```

---

## 2. GetEvent — GET `/events/{event_id}`

Query the status of an asynchronous memory operation. Returns one record per
resource (project/profile). **Usually not needed** — async writes are
fire-and-forget; query only on explicit confirmation requests or when a later
step depends on extraction completion.

**Path Parameter:** `event_id` (returned by AddMemoryAsync)

**Response:** `request_id` + `events[]` in the same shape as AddMemoryAsync;
`status` is one of `PENDING`, `SUCCEEDED`, `FAILED`; `FAILED` records carry an
additional `detail` field formatted as `errorCode: errorMessage`. After
`SUCCEEDED` each record carries a `result` array describing the applied
changes: `content` (added/new content, old content for deletes), `event`
(`ADD`/`UPDATE`/`DELETE`), `memory_node_id` (observation memories only)
and `old_content` (updates only).
404 `NotFound` when the event does not exist.

---

## 3. SearchMemory — POST `/memory_nodes/search`

Semantic similarity search across memory fragments.

**Request Body:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Memory entity ID |
| `messages` | array | Yes | Conversation messages for search query |
| `memory_library_id` | string | No | Memory library ID |
| `project_id` | string | No | Memory project ID (defaults to default project) |
| `top_k` | integer | No | Max results (1-100, default 10) |

> Tuning/billing parameters (`min_score`, `plan_version`, `enable_rerank`) are
> server-controlled and not exposed by this skill's scripts; the server applies
> its defaults (`plan_version=pro`, `min_score=0.3`, domain [0,1]).

**Response:**
```json
{
  "request_id": "string",
  "plan_version": "pro | lite",
  "memory_nodes": [
    {
      "memory_node_id": "string",
      "content": "string",
      "memory_type": "observation",
      "score": 0.676,
      "status": "valid",
      "project_id": "string",
      "meta_data": {},
      "timestamp": 1700000000,
      "created_at": 1700000000,
      "updated_at": 1700000000
    }
  ]
}
```

**Rate limit:** 300 QPM

---

## 4. ListMemory — GET `/memory_nodes`

Paginated listing of memory fragments.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Memory entity ID |
| `memory_library_id` | string | No | Memory library ID |
| `project_id` | string | No | Memory project ID |
| `page_num` | integer | No | Page number (starts at 1, default 1) |
| `page_size` | integer | No | Items per page (default 10) |

**Response:**
```json
{
  "request_id": "string",
  "memory_nodes": [
    {
      "memory_node_id": "string",
      "content": "string",
      "memory_type": "observation",
      "status": "valid",
      "project_id": "string",
      "meta_data": {},
      "timestamp": 1700000000,
      "created_at": 1700000000,
      "updated_at": 1700000000
    }
  ],
  "total": 100,
  "page_size": 10,
  "page_num": 1
}
```

---

## 5. GetMemoryNode — GET `/memory_nodes/{memory_node_id}`

Get the detail of a single memory fragment.

**Path Parameter:** `memory_node_id`

**Response:**
```json
{
  "request_id": "string",
  "memory_node": {
    "memory_node_id": "string",
    "content": "string",
    "memory_type": "observation",
    "status": "valid",
    "project_id": "string",
    "meta_data": {},
    "timestamp": 1700000000,
    "created_at": 1700000000,
    "updated_at": 1700000000
  }
}
```

---

## 6. UpdateMemory — PATCH `/memory_nodes/{memory_node_id}`

Update an existing memory fragment (overwrites content). The node's library
and project ownership cannot be changed.

**Path Parameter:** `memory_node_id`

**Request Body:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `custom_content` | string | Yes | New content (max 512 chars) |
| `user_id` | string | Yes | Memory entity ID |
| `memory_library_id` | string | No | Memory library ID (ownership check) |
| `timestamp` | long | No | Unix timestamp (seconds) |
| `meta_data` | object | No | Incremental merge: keys not specified remain unchanged |

**Response:** `{ "request_id": "string" }`

---

## 7. DeleteMemory — DELETE `/memory_nodes/{memory_node_id}`

Delete a memory fragment. **Irreversible**; ownership is not verified by
`user_id`, so always display the target content (GetMemoryNode) and obtain
user confirmation first.

**Path Parameter:** `memory_node_id`

**Query Parameter:** `memory_library_id` (optional)

**Response:** `{ "request_id": "string" }`

---

## 8. GetUserProfile — GET `/profile_schemas/{profile_schema_id}/user_profile`

Get extracted user profile based on a profile schema.

**Query Parameters:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `user_id` | string | Yes | Memory entity ID |
| `memory_library_id` | string | No | Memory library ID |
| `need_detail` | boolean | No | `true` returns expanded `value_items` per attribute instead of a joined `value` string. Default `false` |

**Response (`need_detail=false`, default):**
```json
{
  "request_id": "string",
  "profile": {
    "schema_name": "string",
    "schema_description": "string",
    "attributes": [
      {
        "id": "string",
        "name": "string",
        "value": "joined values, e.g. \"swimming; volleyball\" (null until extracted)"
      }
    ]
  }
}
```

**Response (`need_detail=true`):** each attribute carries `value_items` instead of `value`:
```json
{
  "id": "string",
  "name": "string",
  "value_items": [
    { "item_id": 5634, "value": "swimming", "status": "valid" }
  ]
}
```

The `attributes[].id` field is the `attribute_id` and `value_items[].item_id`
is the `item_id` consumed by UpdateUserProfileValues.

---

## 9. UpdateUserProfileValues — PATCH `/profile_schemas/{profile_schema_id}/profile_values`

Operate on a single user profile attribute value item (add / update / delete).
Use when the user explicitly states new facts that should correct the profile.

**Request Body:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `entity_id` | string | Yes | Profile owner entity ID; for user profiles pass the user ID |
| `attribute_id` | string | Yes | Attribute ID (from GetUserProfile `attributes[].id`); must exist in the schema |
| `op_type` | string | Yes | `add` / `update` / `delete`, case-insensitive; invalid values are rejected |
| `item_id` | long | Conditional | Value item ID (from GetUserProfile `need_detail=true`); required for `update`/`delete` |
| `value` | string | Conditional | Attribute value content; used for `add`/`update` |
| `memory_library_id` | string | No | Memory library ID (ownership check) |

**Response:** `{ "request_id": "string" }`

Success also refreshes the entity's active time.

---

## 10. CreateMemoryProject — POST `/memory_projects`

Create a memory project (second-level memory isolation).

**Request Body:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Project name, max 32 chars |
| `plan_version` | string | No | Billing plan `pro` (default) / `lite`, case-insensitive |
| `instruction_type` | string | No | `default` / `custom` |
| `custom_instruction` | string | No | Custom extraction instruction content |
| `expired_in_days` | integer | No | Memory expiration: 1-180, or -1 for never |
| `auto_refresh` | boolean | No | Whether access refreshes expiration |
| `memory_library_id` | string | No | Memory library ID |

**Response:** `{ "request_id": "string", "project_id": "string" }`

---

## 11. ListMemoryProjects — GET `/memory_projects`

List memory projects with pagination.

**Query Parameters:** `page_num` (default 1), `page_size` (default 10),
`memory_library_id` (optional).

**Response:** `request_id`, `memory_projects[]` (each with `project_id`,
`memory_library_id`, `name`, `instruction_type`, `custom_instruction`,
`expired_in_days`, `auto_refresh`,
`plan_version`, `created_at`, `updated_at`), `page_num`, `page_size`, `total`.

---

## 12. GetMemoryProject — GET `/memory_projects/{project_id}`

Get the detail of a memory project. Optional query parameter `memory_library_id`.

**Response:** `request_id` + the same project fields as ListMemoryProjects items.

---

## 13. UpdateMemoryProject — PATCH `/memory_projects/{project_id}`

Update a memory project. At least one updatable field must be provided.

**Request Body (all optional, at least one):** `name`, `instruction_type`,
`custom_instruction`, `expired_in_days`, `auto_refresh`,
`plan_version`; plus optional `memory_library_id`.

**Response:** `{ "request_id": "string" }`

---

## 14. CreateProfileSchema — POST `/profile_schemas`

Create a user profile schema.

**Request Body:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | Yes | Schema name, max 32 chars |
| `description` | string | No | Schema description (length limit is system-configured) |
| `plan_version` | string | No | Billing plan `pro` (default) / `lite`, case-insensitive |
| `attributes` | array | Yes | Non-empty attribute definitions |
| `attributes[].name` | string | Yes | Attribute name |
| `attributes[].description` | string | No | Attribute description |
| `attributes[].immutable` | boolean | No | Default `false`. `true` keeps `default_value` and is never changed by extraction |
| `attributes[].default_value` | string | Conditional | Required when `immutable=true` |
| `memory_library_id` | string | No | Memory library ID |

**Response:** `{ "request_id": "string", "profile_schema_id": "string" }`

---

## 15. ListProfileSchemas — GET `/profile_schemas`

List profile schemas with pagination.

**Query Parameters:** `page_num` (default 1), `page_size` (default 10),
`memory_library_id` (optional).

**Response:** `request_id`, `profile_schemas[]` (each with `profile_schema_id`,
`name`, `description`, `plan_version`), `total`.

---

## 16. UpdateProfileSchema — PATCH `/profile_schemas/{profile_schema_id}`

Update a profile schema. At least one of `name`, `description`, `plan_version`,
`attributes_operations` must be provided.

**Request Body:**

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `name` | string | No | Schema name, max 32 chars |
| `description` | string | No | Schema description |
| `plan_version` | string | No | Billing plan `pro` / `lite`, case-insensitive |
| `attributes_operations` | array | No | Attribute change operations |
| `attributes_operations[].op` | string | Yes | `add` / `update` / `delete` |
| `attributes_operations[].name` | string | Conditional | Required for `op=add` |
| `attributes_operations[].description` | string | No | Attribute description |
| `attributes_operations[].immutable` | boolean | No | Only supported for `op=add`; cannot be updated afterwards |
| `attributes_operations[].default_value` | string | Conditional | Required when `op=add` with `immutable=true` |
| `attributes_operations[].attribute_id` | string | Conditional | Required for `op=update`/`delete` |
| `memory_library_id` | string | No | Memory library ID |

> `op=update` requires at least one of `name`/`description`/`default_value`.

**Response:** `{ "request_id": "string" }`

---

## Rate Limits (Account-Level)

| API | Rate Limit |
|-----|-----------|
| All endpoints combined | 3000 QPM total |
| SearchMemory (`/memory_nodes/search`) | 300 QPM |
