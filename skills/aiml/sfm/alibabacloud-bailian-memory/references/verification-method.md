# Success Verification Method

## Overview

After completing each workflow, use the verification steps below to confirm success.
Workflow numbering matches the "Core Workflows" section in SKILL.md.

---

## WF1: Add Memory — async extract from conversation — Verification

**Expected:** Response contains `event_id` and `events` array (initial status `PENDING`).
Fire-and-forget by default — verify contents via list/search, not by polling events.

```bash
# Confirm the extraction results (allow some seconds for background processing)
SKILL_SESSION_ID={session-id} python3 scripts/list_memories.py --user-id "<user_id>"
SKILL_SESSION_ID={session-id} python3 scripts/search_memory.py \
  --user-id "<user_id>" --query "<original topic>"
```

**Success indicator:** Extracted fragments related to the conversation appear.

---

## WF2: Add Memory — async save content as-is — Verification

**Expected:** Response contains `event_id`; `events[].resource_type` carries the
`custom_` prefix (`custom_observation`).

```bash
SKILL_SESSION_ID={session-id} python3 scripts/list_memories.py --user-id "<user_id>"
```

**Success indicator:** The saved content appears verbatim as a memory fragment.

---

## WF3: Check Async Event — Verification

Only performed when the user asked for confirmation or a later step depends on
extraction completion.

```bash
SKILL_SESSION_ID={session-id} python3 scripts/get_event.py --event-id "<event_id>"
```

**Success indicator:** All records reach `SUCCEEDED`. On `FAILED`, the record's
`detail` field (`errorCode: errorMessage`) is reported to the user — never
silently retried. `PENDING` after 5 re-queries is reported as-is.

---

## WF4: Search Memory — Verification

**Expected:** Response contains `plan_version` and `memory_nodes` array; each node
carries `memory_type`, `score`, `status`.

**Success indicator:** Returned memories are semantically related to the search query,
sorted by `score`.

---

## WF5: List Memories — Verification

**Expected:** Response contains paginated `memory_nodes` with `total`, `page_size`, `page_num`.

```bash
SKILL_SESSION_ID={session-id} python3 scripts/list_memories.py \
  --user-id "<user_id>" --page-num 1 --page-size 5
```

**Success indicator:** `total` matches expected count; `memory_nodes` array is populated.

---

## WF6: Get Memory Node — Verification

**Expected:** Response contains `memory_node` with full detail.

```bash
SKILL_SESSION_ID={session-id} python3 scripts/get_memory_node.py \
  --memory-node-id "<memory_node_id>"
```

**Success indicator:** `memory_node.memory_node_id` matches the requested ID and
`content` is the expected fragment.

---

## WF7: Update Memory — Verification

**Expected:** Response contains `request_id` (success acknowledgment).

```bash
# Verify update by fetching the node and checking content
SKILL_SESSION_ID={session-id} python3 scripts/get_memory_node.py \
  --memory-node-id "<memory_node_id>"
```

**Success indicator:** The fragment shows the new content.

---

## WF8: Delete Memory — Verification

**Expected:** Response contains `request_id` (success acknowledgment).

```bash
# Verify deletion — the deleted memory should not appear
SKILL_SESSION_ID={session-id} python3 scripts/list_memories.py \
  --user-id "<user_id>"
```

**Success indicator:** The deleted `memory_node_id` no longer appears in the list.
(The mandatory pre-delete confirmation flow must have been followed.)

---

## WF9: Get User Profile — Verification

**Expected:** Response contains `profile` with `schema_name` and `attributes`
(each with `id`, `name`, `value`).

**Success indicator:** Extracted attributes have `value` fields populated from
conversation analysis. Empty values are normal before enough conversations have
been processed — not an error.

---

## WF10: Update User Profile Value — Verification

**Expected:** Response contains `request_id`.

```bash
# Verify the value item op via a subsequent detailed get
SKILL_SESSION_ID={session-id} python3 scripts/get_user_profile.py \
  --user-id "<user_id>" --profile-schema-id "<schema_id>" --need-detail
```

**Success indicator:** op=add appends a new `value_items` entry; op=update shows the
new value on the same `item_id`; op=delete removes that `item_id`. Other value items
are unchanged.

---

## WF11: Manage Memory Projects — Verification

**Expected:** create returns `project_id`; list/get return full project detail.

```bash
SKILL_SESSION_ID={session-id} python3 scripts/manage_memory_project.py get \
  --project-id "<project_id>"
```

**Success indicator:** get shows `plan_version`
matching the create/update input; updated fields are reflected, others unchanged.

---

## WF12: Manage Profile Schemas — Verification

**Expected:** create returns `profile_schema_id`; list contains the schema with
`plan_version`.

```bash
SKILL_SESSION_ID={session-id} python3 scripts/manage_profile_schema.py list
```

**Success indicator:** the created/updated schema appears with the expected
`name`/`description`/`plan_version`; attribute add/update/delete ops take effect in
subsequent profile extraction (attribute set changes visible via get_user_profile).

---

## End-to-End Verification Script

Run a complete workflow to verify all components:

```bash
# 0. (Optional) create a project and a profile schema for isolation testing
SKILL_SESSION_ID={session-id} python3 scripts/manage_memory_project.py create --name "verify-project"
SKILL_SESSION_ID={session-id} python3 scripts/manage_profile_schema.py create \
  --name "verify-profile" --attributes '[{"name":"Hobbies"}]'

# 1. Async extract from conversation
SKILL_SESSION_ID={session-id} python3 scripts/add_memory_messages.py \
  --user-id "test_verify_user" \
  --messages '[{"role":"user","content":"I usually code in Python on weekends"}]'

# 2. Async save content as-is
SKILL_SESSION_ID={session-id} python3 scripts/add_memory_content.py \
  --user-id "test_verify_user" --content "User prefers dark mode and Python programming"

# 3. (Optional) confirm events only if needed
# SKILL_SESSION_ID={session-id} python3 scripts/get_event.py --event-id "<event_id>"

# 4. Search memory
SKILL_SESSION_ID={session-id} python3 scripts/search_memory.py \
  --user-id "test_verify_user" --query "programming language preference"

# 5. List memories and get one node detail
SKILL_SESSION_ID={session-id} python3 scripts/list_memories.py --user-id "test_verify_user"
SKILL_SESSION_ID={session-id} python3 scripts/get_memory_node.py \
  --memory-node-id "<memory_node_id_from_step_5>"

# 6. Profile flows (schema from step 0 or an existing one)
# SKILL_SESSION_ID={session-id} python3 scripts/get_user_profile.py \
#   --user-id "test_verify_user" --profile-schema-id "<schema_id>" --need-detail
# SKILL_SESSION_ID={session-id} python3 scripts/update_user_profile.py \
#   --entity-id "test_verify_user" --profile-schema-id "<schema_id>" \
#   --attribute-id "<attr_id>" --op-type add --value "Python"

# 7. Cleanup — follow the 🔴 delete flow (get → confirm → delete → list);
#    test projects/schemas created in step 0 are deleted in the Bailian console
```
