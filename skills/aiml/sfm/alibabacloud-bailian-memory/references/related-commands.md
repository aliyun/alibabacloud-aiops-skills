# Related Commands Reference

All commands use Python scripts located in the `scripts/` directory.
Every command must be prefixed with `SKILL_SESSION_ID={session-id}` (see the
Observability section in SKILL.md).

## Prerequisites

```bash
pip3 install -r scripts/requirements.txt
```

### Alibaba Cloud CLI (optional, for API Key auto-create/delete)

```bash
aliyun plugin update
aliyun plugin install --names aliyun-cli-modelstudio --enable-pre
```

| Command | Purpose | Called From |
|---------|---------|-------------|
| `aliyun modelstudio list-workspaces` | Get Bailian Workspace ID | `api_key.py: _get_workspace_id()` |
| `aliyun modelstudio create-api-key` | Create DashScope API Key | `api_key.py: generate_api_key()` |
| `aliyun modelstudio delete-api-key` | Delete cloud API Key | `api_key.py: _delete_cloud_api_key()` |

## Memory Operations

All writes are asynchronous: the request returns an `event_id` while extraction
runs in the background.

### Add Memory — async extract from conversation (default write path)
```bash
SKILL_SESSION_ID={session-id} python3 scripts/add_memory_messages.py \
  --user-id "<user_id>" \
  --messages '[{"role":"user","content":"hello"},{"role":"assistant","content":"hi"}]'
```

### Add Memory — async extract (multi-project)
```bash
SKILL_SESSION_ID={session-id} python3 scripts/add_memory_messages.py \
  --user-id "<user_id>" \
  --messages '<json>' \
  --project-ids "<project_id_1>,<project_id_2>"
```

### Add Memory — async extract with profile extraction
```bash
SKILL_SESSION_ID={session-id} python3 scripts/add_memory_messages.py \
  --user-id "<user_id>" \
  --messages '<json>' \
  --profile-schema "<schema_id>"
```

### Add Memory — async extract (all optional parameters)
```bash
SKILL_SESSION_ID={session-id} python3 scripts/add_memory_messages.py \
  --user-id "<user_id>" \
  --messages '<json>' \
  --timestamp 1700000000 \
  --memory-library-id "<library_id>" \
  --project-id "<project_id>" \
  --profile-schema "<schema_id>" \
  --meta-data '{"source":"chat"}'
```

### Add Memory — async save content as-is (no extraction)
```bash
SKILL_SESSION_ID={session-id} python3 scripts/add_memory_content.py \
  --user-id "<user_id>" \
  --content "<text>"
```

### Get Event (async status; usually NOT needed — fire-and-forget by default)
```bash
SKILL_SESSION_ID={session-id} python3 scripts/get_event.py \
  --event-id "<event_id>"
```

### Search Memory
```bash
SKILL_SESSION_ID={session-id} python3 scripts/search_memory.py \
  --user-id "<user_id>" \
  --query "<search_text>"
```

### Search Memory (with options)
```bash
SKILL_SESSION_ID={session-id} python3 scripts/search_memory.py \
  --user-id "<user_id>" \
  --query "<search_text>" \
  --top-k 5 \
  --project-id "<project_id>"
```

### List Memories
```bash
SKILL_SESSION_ID={session-id} python3 scripts/list_memories.py \
  --user-id "<user_id>"
```

### List Memories (paginated)
```bash
SKILL_SESSION_ID={session-id} python3 scripts/list_memories.py \
  --user-id "<user_id>" \
  --page-num 1 \
  --page-size 20
```

### Get Memory Node (single fragment detail)
```bash
SKILL_SESSION_ID={session-id} python3 scripts/get_memory_node.py \
  --memory-node-id "<memory_node_id>"
```

### Update Memory
```bash
SKILL_SESSION_ID={session-id} python3 scripts/manage_memory.py update \
  --memory-node-id "<memory_node_id>" \
  --user-id "<user_id>" \
  --content "<new_content>"
```

### Delete Memory (🔴 irreversible — confirm with user first)
```bash
# Step 1: show the target to the user
SKILL_SESSION_ID={session-id} python3 scripts/get_memory_node.py --memory-node-id "<memory_node_id>"
# Step 2: only after explicit user confirmation
SKILL_SESSION_ID={session-id} python3 scripts/manage_memory.py delete \
  --memory-node-id "<memory_node_id>"
# Step 3: verify it is gone
SKILL_SESSION_ID={session-id} python3 scripts/list_memories.py --user-id "<user_id>"
```

## User Profile Operations

### Get User Profile
```bash
SKILL_SESSION_ID={session-id} python3 scripts/get_user_profile.py \
  --user-id "<user_id>" \
  --profile-schema-id "<schema_id>"
# Expand value_items (each with item_id, consumed by profile value update/delete)
SKILL_SESSION_ID={session-id} python3 scripts/get_user_profile.py \
  --user-id "<user_id>" \
  --profile-schema-id "<schema_id>" \
  --need-detail
```

### Update User Profile Value (single value item op)
```bash
# op-type=add appends a new value item (no item-id needed)
SKILL_SESSION_ID={session-id} python3 scripts/update_user_profile.py \
  --entity-id "<user_id>" \
  --profile-schema-id "<schema_id>" \
  --attribute-id "<attr_id>" --op-type add --value "swimming"
# op-type=update/delete require item-id (from get_user_profile --need-detail)
SKILL_SESSION_ID={session-id} python3 scripts/update_user_profile.py \
  --entity-id "<user_id>" \
  --profile-schema-id "<schema_id>" \
  --attribute-id "<attr_id>" --op-type update --item-id 5634 --value "volleyball"
SKILL_SESSION_ID={session-id} python3 scripts/update_user_profile.py \
  --entity-id "<user_id>" \
  --profile-schema-id "<schema_id>" \
  --attribute-id "<attr_id>" --op-type delete --item-id 5634
```

## Management Operations

### Manage Memory Projects (create / list / get / update)
```bash
SKILL_SESSION_ID={session-id} python3 scripts/manage_memory_project.py create \
  --name "observation-project" [--plan-version pro|lite] \
  [--instruction-type default|custom] [--custom-instruction "<text>"] \
  [--expired-in-days 30] [--auto-refresh true|false]
SKILL_SESSION_ID={session-id} python3 scripts/manage_memory_project.py list \
  [--page-num 1] [--page-size 10]
SKILL_SESSION_ID={session-id} python3 scripts/manage_memory_project.py get \
  --project-id "<project_id>"
SKILL_SESSION_ID={session-id} python3 scripts/manage_memory_project.py update \
  --project-id "<project_id>" [--name "<name>"] [--plan-version lite] \
  [--instruction-type custom] \
  [--custom-instruction "<text>"] [--expired-in-days 60] [--auto-refresh true|false]
```

### Manage Profile Schemas (create / list / update)
```bash
SKILL_SESSION_ID={session-id} python3 scripts/manage_profile_schema.py create \
  --name "basic-user-profile" \
  --attributes '[{"name":"Name","immutable":true,"default_value":"Zhang San"},{"name":"Hobbies"}]' \
  [--description "<text>"] [--plan-version pro|lite]
SKILL_SESSION_ID={session-id} python3 scripts/manage_profile_schema.py list \
  [--page-num 1] [--page-size 10]
SKILL_SESSION_ID={session-id} python3 scripts/manage_profile_schema.py update \
  --profile-schema-id "<schema_id>" [--name "<name>"] [--description "<text>"] \
  [--plan-version pro|lite] \
  [--attributes-operations '[{"op":"add","name":"Favorite Music"},{"op":"update","attribute_id":"<attr_id>","name":"Regular Sports"},{"op":"delete","attribute_id":"<attr_id2>"}]']
```
