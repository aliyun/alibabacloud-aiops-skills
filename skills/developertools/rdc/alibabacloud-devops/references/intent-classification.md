# Intent Classification Decision Tree

## Core Principle

**Determine the core verb/action of the user's instruction, rather than focusing on the noun.** The verb determines which category of tool to call (create/list/get/update/delete/execute); the noun determines which product to map to.

## Action Category Quick Reference

| Action | Typical Verbs | Mapped Tool Prefix | Example Instruction |
|--------|--------------|-------------------|---------------------|
| Create | create, add, build, establish, initialize | `create_*` | "Create a Java build pipeline" |
| Query | view, get, list, search, find | `get_*` / `list_*` / `search_*` | "View my code repository list" |
| Modify | update, modify, change, adjust, edit | `update_*` | "Update the sprint end date" |
| Delete | delete, remove, clean up | `delete_*` (**secondary confirmation**) | "Delete the test branch" |
| Trigger | run, execute, trigger, start, deploy | `create_pipeline_run` / `execute_*` | "Run the build pipeline" |
| Configure | configure, set up, bind, associate | `update_*` / `create_*` | "Configure the pipeline's service connection" |

## Intent Classification Decision Tree

```
User Instruction
  │
  ├─ What is the core verb?
  │   ├─ Create → Confirm creation target → Corresponding product create_* tool
  │   ├─ Query → Confirm query target → get_* / list_* / search_* tool
  │   │           └─ Contains time range ("recent/last week/today") → smart_list_*
  │   ├─ Modify → Confirm modification target and fields → update_*
  │   │           └─ First get_* to read current value, then update_*
  │   ├─ Delete → Requires secondary confirmation → delete_*
  │   ├─ Trigger → Confirm trigger target → create_pipeline_run / execute_*
  │   └─ Configure → Confirm configuration target and parameters → update_* / create_*
  │
  └─ Which product does the target belong to? → See product-mapping.md
```

## Ambiguity Identification & Clarification Strategy

| Ambiguity Type | Identification Condition | Clarification Strategy |
|---------------|------------------------|----------------------|
| Product ambiguity | Instruction contains keywords for multiple products (e.g., "code" + "pipeline") | Ask which specific product to operate on |
| Action ambiguity | Action is unclear (e.g., "handle this requirement") | Ask for the specific operation type |
| Object ambiguity | Missing required identifier (e.g., "update pipeline" without specifying which one) | Ask for the specific resource name or ID |
| Parameter ambiguity | Missing critical parameters (e.g., "create branch" without specifying source branch) | Ask for the missing required parameters |
| Scope ambiguity | Organization or project scope not specified | Ask for the organization/project |

## Clarification Template

```
I understand you want to {action}, but I need you to clarify:
1. [Required info 1]: {specific question}
2. [Required info 2]: {specific question}

Please provide the above information and I will execute the operation for you.
```

## Example Conversations

### Example 1: Action + Object ambiguity
- User: "Help me handle the code"
- Assistant: "I understand you want to perform an operation on code, but I need further clarification:
  1. What operation do you want to perform? (create branch / commit code / create merge request / view files, etc.)
  2. Which target repository? Please provide the repository name or ID."

### Example 2: Product ambiguity
- User: "Help me check the build status"
- Assistant: "Are you referring to:
  1. Viewing pipeline build run history (Flow)? Or
  2. Viewing application release workflow status (AppStack)?
  Please confirm and I will query for you."

### Example 3: Dangerous operation requires secondary confirmation
- User: "Delete the feature branch"
- Assistant: "About to delete branch `feature/*` from repository `<repo>`. This operation is irreversible. Please confirm:
  1. Which specific branches should be deleted? (Please provide full branch names)
  2. Reply YES to confirm."

## Anti-patterns (Prohibited)

❌ User: "Create a pipeline" → Directly create with Node.js defaults → **Wrong**: Did not confirm language, repository, organization

❌ User: "Update the sprint" → Directly call `update_sprint` without first calling `get_sprint` → **Wrong**: May overwrite fields

❌ User: "Check my stuff" → Randomly call some `list_*` → **Wrong**: Must ask for clarification
