# Branch Node（CONTROLLER_BRANCH）

## Overview

- Compute engine: `GENERAL`
- Content format: empty (no `script.content` required)
- Extension: `.branch.json` (legacy UI-facing config; the authoritative config lives in `spec.branch` of `*.spec.json`)

The branch node is a logical control node that dispatches the workflow to one of several mutually-exclusive downstream paths based on condition expressions. Each entry under `branch.branches` defines a condition (`when`) and the output identifier that downstream nodes will depend on. At runtime, conditions are evaluated **in order**; the first branch whose condition holds is activated. Branches whose condition does not hold are marked *not run* (status `"2"`), and any downstream node that depends solely on that branch output is also marked *not run* — the downstream node's code is not executed.

## Usage Patterns

**Branch alone (no merge node needed)** — a branch node can be used on its own to control which downstream arm continues executing. The selected arm runs normally; tasks on the unselected arms are automatically marked *not run* (status `"2"`) and their code is never executed. This is the correct choice when the different arms terminate independently (e.g., they write to different tables or call different services) and no downstream node needs to run regardless of which arm was selected.

**Branch + Join (paired usage)** — insert a downstream `CONTROLLER_JOIN` merge node when either of the following is true:

1. A downstream node must run **regardless of which arm was selected** (for example, a downstream node shared by all arms). Without a merge node, that downstream node would empty-run because the unselected arms propagate *not run*.
2. You need to **explicitly evaluate the outcome of the selected arm** and decide, via the merge node's own success/failure, whether the flow should continue past the merge point. The merge node's `assertion` rules define which upstream run statuses count as "this arm satisfied", and `logic.expression` combines them into a single pass/fail result for the merge node. Downstream nodes then depend on the merge node, so the merge node's status gates whether they run.

See [`CONTROLLER_JOIN.md`](./CONTROLLER_JOIN.md) for the merge-node schema and the correct assertion/logic settings for each pattern.

## Schema

The branch logic is configured via the `branch` field on the node spec.

```json
"branch": {
  "branches": [
    {
      "when": "'${condition1}' == 'hello'",
      "desc": "condition met",
      "output": {
        "data": "${projectIdentifier}.branch_out_condition1_true"
      }
    },
    {
      "when": "'${condition1}' != 'hello'",
      "desc": "condition not met",
      "output": {
        "data": "${projectIdentifier}.branch_out_condition1_false"
      }
    }
  ]
}
```

### `branch.branches[]`

| Sub-field | Type | Required | Description |
|-----------|------|----------|-------------|
| `when` | string | yes | Condition expression evaluated as **Python code** after placeholder substitution. Supports variable substitution via `${variable_name}` referencing entries declared in `script.parameters`. Comparison operators (`==`, `!=`, `<`, `>`, …), boolean operators (`and`, `or`, `not`), parentheses, and string/number literals are supported. See the "Placeholder substitution is textual — quote string values" note below. |
| `desc` | string | optional | Human-readable description shown in the UI. Recommended for documentation. |
| `output` | object | yes | The branch output that downstream nodes will depend on. An object with `data` set to a fully-qualified output identifier of the form `${projectIdentifier}.<name>`. |

**Ordering matters**: conditions are evaluated top-to-bottom, first match wins. Put the most specific conditions first and use a catch-all last if needed.

### Placeholder substitution is textual — quote string values ⚠️

Branch conditions are executed as Python expressions. The execution engine does **not** type-aware binding — it performs a plain **textual substitution** of each `${name}` with the raw parameter value and then parses the resulting string as Python. You must write the `when` expression so that the post-substitution string is still valid Python syntax.

**String-typed parameters must be wrapped in single quotes inside the expression**, because otherwise the substituted value becomes a Python identifier and the expression will raise a `NameError`:

| Parameter | `when` in spec | After substitution | Parsed as Python | Result |
|-----------|----------------|--------------------|--------------------|--------|
| `para1 = "test1"` | `'${para1}' == 'test1'` | `'test1' == 'test1'` | string-to-string comparison | ✅ `True` |
| `para1 = "test1"` | `${para1} == 'test1'` | `test1 == 'test1'` | tries to read an undefined name `test1` | ❌ `NameError` |
| `n = 42` | `${n} > 10` | `42 > 10` | integer comparison | ✅ `True` |
| `n = 42` | `'${n}' > 10` | `'42' > 10` | string vs int comparison | ❌ `TypeError` in Python 3 |

Rule of thumb:

- **String parameters** → wrap the placeholder in single quotes: `'${str_param}' == 'expected'`.
- **Numeric parameters** → leave the placeholder unquoted: `${num_param} > 10`.
- **Boolean-ish parameters** → wrap and compare against a literal string (`'${flag}' == 'true'`) since the engine substitutes the raw string value, not a Python `True`/`False`.
- Never embed untrusted/user-supplied free-form text in a placeholder — a value containing a single quote (e.g. `it's`) would break the Python syntax after substitution.

### Condition variables — `script.parameters`

Any `${name}` referenced by a `when` expression **must** be declared in the branch node's own `script.parameters[]`. The parameter value is resolved at runtime (from the configured value, upstream parameter passthrough, or a system parameter) and then substituted into the expression before evaluation.

```json
"script": {
  "runtime": { "command": "CONTROLLER_BRANCH", "cu": "0.25" },
  "parameters": [
    {
      "name": "condition1",
      "scope": "NodeParameter",
      "type": "System",
      "value": "hello"
    }
  ]
}
```

| Parameter field | Description |
|-----------------|-------------|
| `name` | Variable name used inside `${…}` in the `when` expression. |
| `scope` | Typically `NodeParameter`. |
| `type` | `System` for system/constant values; other types are supported for upstream parameter passthrough. |
| `value` | Default or literal value. |

### `script.content` (OpenAPI adapter)

When creating or updating a branch node via OpenAPI, the `branch` field on the spec alone is **not sufficient** — the platform also requires `script.content` to be populated with a JSON string carrying the equivalent branch configuration. If `script.content` is omitted or empty, the branch conditions will not take effect and the node will not dispatch to downstream arms.

**Format**: `script.content` must be a JSON string (stringified array) of branch-condition objects:

```json
[
  {
    "condition": "'${condition1}' == 'hello'",
    "nodeoutput": "${projectIdentifier}.branch_out_condition1_true",
    "description": "condition met"
  },
  {
    "condition": "'${condition1}' != 'hello'",
    "nodeoutput": "${projectIdentifier}.branch_out_condition1_false",
    "description": "condition not met"
  }
]
```

| Field | Type | Description |
|-------|------|-------------|
| `condition` | string | The condition expression — same value as `branch.branches[].when`. Remember to apply the Python quoting rules (wrap string-typed `${var}` in single quotes). |
| `nodeoutput` | string | Fully-qualified branch output identifier — same value as `branch.branches[].output.data`. |
| `description` | string | Human-readable label — same value as `branch.branches[].desc`. |

**Consistency rule**: the `script.content` JSON and the `branch` field must encode the **same** branch logic. The caller is responsible for keeping them in sync — on updates, both must be refreshed together. The `branch` field is the semantic model read by the UI; `script.content` is what the execution engine actually evaluates at runtime.

**Example** (stringified inside `script`):

```json
"script": {
  "runtime": { "command": "CONTROLLER_BRANCH", "cu": "0.25" },
  "content": "[{\"condition\":\"'${condition1}' == 'hello'\",\"nodeoutput\":\"${projectIdentifier}.branch_out_condition1_true\",\"description\":\"condition met\"},{\"condition\":\"'${condition1}' != 'hello'\",\"nodeoutput\":\"${projectIdentifier}.branch_out_condition1_false\",\"description\":\"condition not met\"}]",
  "parameters": [
    {
      "name": "condition1",
      "scope": "NodeParameter",
      "type": "System",
      "value": "hello"
    }
  ]
}
```

## Dependency Wiring

### Upstream → branch node

Standard input wiring: declare a `Normal` dependency under `dependencies[].depends` pointing to the upstream output.

### Branch node → downstream

Each branch output referenced by `branch.branches[].output.data` **must also be declared** in the branch node's own `outputs.nodeOutputs[]`, so the scheduler registers it as a real output that downstream nodes can depend on.

```json
"outputs": {
  "nodeOutputs": [
    { "data": "${projectIdentifier}.my_branch", "refTableName": "my_branch" },
    { "data": "${projectIdentifier}.branch_out_condition1_true" },
    { "data": "${projectIdentifier}.branch_out_condition1_false" }
  ]
}
```

A downstream node then depends on the specific **branch output data** (not on the branch node's own output):

```json
// Downstream node that runs when the "condition met" branch is selected
"dependencies": [
  {
    "nodeId": "downstream_when_true",
    "depends": [
      { "type": "Normal", "output": "${projectIdentifier}.branch_out_condition1_true" }
    ]
  }
]
```

Because unselected branches end in status `"2"` (*not run*), any downstream node that depends only on an unselected branch output will itself be *not run* — which is the intended branching behavior. If you need a downstream node to run **regardless of which branch was selected**, insert a `CONTROLLER_JOIN` merge node; see [`CONTROLLER_JOIN.md`](./CONTROLLER_JOIN.md).

## Other Requirements

| Requirement | Detail |
|-------------|--------|
| `script.runtime.command` | Must be `CONTROLLER_BRANCH`. |
| `script.runtime.cu` | Small allocation (e.g. `"0.25"`) is sufficient; the branch node performs no computation. |
| `script.content` | **Required when submitting via OpenAPI** — must carry the branch-condition array as a JSON string (see "`script.content` (OpenAPI adapter)" section above). Must be kept in sync with the `branch` field. |
| Branches count | At least 2 branches; all branches should collectively cover the expected value space (add a catch-all branch for safety). |
| Product version | DataWorks Standard Edition or above. |

## Full Example

A branch node `my_branch` that dispatches on a system variable `condition1`. One downstream shell runs when the condition holds, the other runs when it does not. A merge node downstream of both consolidates the two paths.

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "my_branch",
        "recurrence": "Normal",
        "script": {
          "runtime": { "command": "CONTROLLER_BRANCH", "cu": "0.25" },
          "content": "[{\"condition\":\"'${condition1}' == 'hello'\",\"nodeoutput\":\"${projectIdentifier}.branch_out_condition1_true\",\"description\":\"condition met\"},{\"condition\":\"'${condition1}' != 'hello'\",\"nodeoutput\":\"${projectIdentifier}.branch_out_condition1_false\",\"description\":\"condition not met\"}]",
          "parameters": [
            {
              "name": "condition1",
              "scope": "NodeParameter",
              "type": "System",
              "value": "hello"
            }
          ]
        },
        "branch": {
          "branches": [
            {
              "when": "'${condition1}' == 'hello'",
              "desc": "condition met",
              "output": {
                "data": "${projectIdentifier}.branch_out_condition1_true"
              }
            },
            {
              "when": "'${condition1}' != 'hello'",
              "desc": "condition not met",
              "output": {
                "data": "${projectIdentifier}.branch_out_condition1_false"
              }
            }
          ]
        },
        "outputs": {
          "nodeOutputs": [
            { "data": "${projectIdentifier}.my_branch", "refTableName": "my_branch" },
            { "data": "${projectIdentifier}.branch_out_condition1_true" },
            { "data": "${projectIdentifier}.branch_out_condition1_false" }
          ]
        }
      }
    ],
    "dependencies": [
      {
        "nodeId": "my_branch",
        "depends": [
          { "type": "Normal", "output": "${projectIdentifier}_root" }
        ]
      }
    ]
  }
}
```

## Authoring Checklist

Before submitting a branch node, verify:

- [ ] `script.runtime.command` is `CONTROLLER_BRANCH`.
- [ ] **`script.content` carries a valid branch-condition JSON string** when submitting via OpenAPI — an array of `{condition, nodeoutput, description}` objects matching 1:1 with `branch.branches[]`. The `condition` values must apply the same Python quoting rules as `when`. Both `script.content` and `branch` must encode the same logic. Without `script.content`, the branch conditions will not take effect at runtime.
- [ ] Every `${name}` referenced inside a `when` expression is declared in `script.parameters[]`.
- [ ] Every `${name}` that refers to a **string-typed** parameter is wrapped in single quotes inside the `when` expression (e.g. `'${str}' == 'expected'`, not `${str} == 'expected'`), so that the post-substitution string is valid Python. Unquoted placeholders are acceptable only for numeric parameters.
- [ ] `branch.branches[]` contains at least two entries; the condition set covers all expected input values (add a catch-all if needed).
- [ ] Each `branch.branches[].output` is an **object** `{ data: "${projectIdentifier}.<name>" }`, not a bare string.
- [ ] Every `branch.branches[].output.data` also appears in the branch node's own `outputs.nodeOutputs[]`.
- [ ] Downstream nodes depend on the **branch output data** (`${projectIdentifier}.<branch_output_name>`), not on the branch node's own output.
- [ ] If any downstream node needs to run regardless of which branch was selected, a `CONTROLLER_JOIN` merge node is inserted before it.
