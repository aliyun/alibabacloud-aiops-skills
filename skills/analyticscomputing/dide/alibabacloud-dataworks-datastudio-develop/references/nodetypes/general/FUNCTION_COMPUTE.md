# Function Compute Node (FUNCTION_COMPUTE)

## Overview

- Compute engine: `GENERAL`
- Content format: JSON (inlined into `script.content`)
- Extension: `.json`

The Function Compute node invokes a **target function** hosted on Alibaba Cloud Function Compute (FC) as a scheduled step of a DataWorks workflow. The node itself runs no user code in the DataWorks runtime — it assembles an event payload, makes the invocation against the configured FC function, waits for the invocation to finish (or to be successfully enqueued, depending on the selected invocation mode), and then reports the outcome as the node's run status.

Typical scenarios:

- Trigger a lightweight serverless function on a schedule.
- Post-process the output of an upstream data task by delegating to an FC function written in any supported FC runtime.
- Fan out to a business service without having to deploy a shell / python runner.

## Differentiators vs. a plain shell / python task

- **No code runs in the DataWorks scheduler** — the heavy lifting is done inside FC. Authentication against FC is handled by the node's configured data source / connection, so you do not inline any credential material into the spec.
- **Event payload is declarative** — the JSON payload is a field of the node's own config, not code your task assembles at runtime.
- **Function target is versioned via a qualifier** — you can pin to `LATEST`, a published version, or an alias, rather than invoking "whatever is currently deployed under this name".

## Schema

A Function Compute node has no custom `spec.xxx` block. All of its configuration lives as a JSON document inside `script.content`.

### `script.runtime`

```json
"script": {
  "runtime": {
    "command": "FUNCTION_COMPUTE",
    "cu": "0.25"
  },
  "content": "<inlined JSON, see below>"
}
```

| Field | Description |
|-------|-------------|
| `command` | Must be `FUNCTION_COMPUTE`. |
| `cu` | A small allocation (e.g. `"0.25"`) is sufficient; the node only brokers the invocation. |

### `script.content` JSON

```json
{
  "serviceName":    "<your-fc-service-name>",
  "functionName":   "<your-fc-function-name>",
  "qualifierType":  "DEFAULT_VERSION",
  "qualifier":      "LATEST",
  "invocationType": "Async",
  "eventBody":      "{\n    \"var1\": \"payload1\",\n    \"var2\": \"${bizdate}\",\n    \"triggerName\": \"triggerName1\"\n}"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `serviceName` | string | yes | Name of the target FC service containing the function. |
| `functionName` | string | yes | Name of the target function within that service. |
| `qualifierType` | string | yes | How `qualifier` is interpreted. In the real sample the value observed is `DEFAULT_VERSION`. Other values exist for pinning to a published version or an alias — pick the one that matches how your FC function is deployed. |
| `qualifier` | string | yes | The concrete version / alias selector. `LATEST` resolves to the current LATEST version; a version number pins to that published version; an alias name routes to whatever version the alias currently points at. |
| `invocationType` | `Sync` \| `Async` | yes | Invocation mode. `Async` enqueues the invocation and returns as soon as FC accepts it (the DataWorks node succeeds once the enqueue is acknowledged). `Sync` waits for the FC function to complete and reflects the function's outcome in the node's run status. Pick `Sync` when the downstream flow must gate on the FC function having actually finished. |
| `eventBody` | string | yes | The event payload delivered to the FC function. It is a **JSON string** (the inner document is itself JSON, serialized). The inner document may use `${var}` placeholders referencing node parameters or built-in system parameters (e.g. `${bizdate}`); they are substituted before the invocation is made. |

**Authentication**: FC access credentials are resolved by DataWorks from the node's configured connection / data source, **not** from any inline credential material in the spec. Do not place secrets inside `script.content`.

**Output extraction**: the node does not automatically parse the FC function's response into FlowSpec variables. If downstream nodes need to consume data produced by the FC function, have the function persist the result to a shared store (a table, an object store, a queue) and have the downstream node read it from there. The Function Compute node's own output is status-only: it signals whether the invocation succeeded.

**Timeout / retry**: the node honors the standard FlowSpec `timeout` / `timeoutUnit` / `rerunMode` / `rerunTimes` / `rerunInterval` fields declared on the node itself. There is no separate retry policy inside `script.content`; configure retries via the standard node-level fields.

### Dependency wiring

Dependency wiring is standard: the Function Compute node is an ordinary FlowSpec node with `outputs.nodeOutputs[]` and a `spec.dependencies[].depends` entry.

```json
"outputs": { "nodeOutputs": [ { "sourceType": "System", "data": "${projectIdentifier}.my_fc_node", "refTableName": "my_fc_node" } ] }
```

## Full example

A daily-cycle Function Compute node `my_fc_node` that asynchronously invokes the LATEST version of `<your-function-name>` inside service `<your-service-name>`, delivering an event payload that includes the scheduling `bizdate`.

```json
{
  "version": "2.0.0",
  "kind": "Node",
  "spec": {
    "nodes": [
      {
        "name": "my_fc_node",
        "recurrence": "Normal",
        "script": {
          "path": "my_fc_node",
          "runtime": {
            "command": "FUNCTION_COMPUTE",
            "cu": "0.25"
          },
          "content": "{\n  \"serviceName\": \"<your-service-name>\",\n  \"functionName\": \"<your-function-name>\",\n  \"qualifierType\": \"DEFAULT_VERSION\",\n  \"qualifier\": \"LATEST\",\n  \"invocationType\": \"Async\",\n  \"eventBody\": \"{\\n    \\\"var1\\\": \\\"payload1\\\",\\n    \\\"var2\\\": \\\"${bizdate}\\\",\\n    \\\"triggerName\\\": \\\"triggerName1\\\"\\n}\"\n}"
        },
        "trigger": {
          "type": "Scheduler",
          "cron": "00 09 00 * * ?",
          "cycleType": "Daily",
          "timezone": "Asia/Shanghai"
        },
        "outputs": { "nodeOutputs": [ { "sourceType": "System", "data": "${projectIdentifier}.my_fc_node", "refTableName": "my_fc_node" } ] }
      }
    ],
    "dependencies": [
      {
        "nodeId": "my_fc_node",
        "depends": [
          { "type": "Normal", "output": "${projectIdentifier}_root" }
        ]
      }
    ]
  }
}
```

## Authoring checklist

Before submitting a Function Compute node, verify:

- [ ] `script.runtime.command` is `FUNCTION_COMPUTE`.
- [ ] `script.content` is the full JSON document (stringified) containing `serviceName`, `functionName`, `qualifierType`, `qualifier`, `invocationType`, and `eventBody`.
- [ ] `serviceName` / `functionName` point to a real, deployed FC target — no placeholder values committed to the spec.
- [ ] `qualifier` is a deliberate choice (`LATEST`, a version, or an alias) — `LATEST` is fine for development but consider pinning for production.
- [ ] `invocationType` matches downstream expectations: `Sync` if the downstream flow must wait for FC completion, `Async` if a fire-and-forget dispatch is acceptable.
- [ ] `eventBody` is a valid JSON string (inner JSON properly escaped). All `${var}` placeholders referenced in the body either resolve to a system parameter (e.g. `${bizdate}`) or to a declared node parameter.
- [ ] No secrets (credentials, tokens, webhook URLs) are embedded in `script.content` — FC authentication is handled by the node's configured data source / connection.
- [ ] Timeout / retry come from the standard node-level fields (`timeout`, `rerunMode`, `rerunTimes`, `rerunInterval`), not from anything inside `script.content`.
- [ ] If downstream nodes need to consume the FC function's result, the function persists its output to a shared store and the downstream node reads from there — the node itself does not expose the FC response as FlowSpec variables.
