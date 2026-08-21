# Extension Plugin Console Lifecycle

The complete operation flow of extension plugins in the WAF 3.0 console is as follows; it maps one-to-one to the local plugin project.

> The entire flow is **console-only**: extension plugins have no corresponding OpenAPI / `aliyun` CLI / SDK interface, and no capability to import local files. The local project files are a convention of this Skill, used for version control and review.

## Activation

- Applicable editions: subscription Enterprise and Flagship editions, and the pay-as-you-go edition.
- Billing: paid service. The pay-as-you-go edition can be used directly; the subscription edition must be purchased first.
- Entry: WAF 3.0 console → Protection Configuration > Global Configuration > Extension Plugins.

## Creating an Extension Plugin

"Create Extension Plugin" in the console requires configuring four blocks of content — basic information, plugin code, parameter definitions, and debug tests — mapping one-to-one to `plugin.json`, `plugin.lua`, `params.json`, and `tests/*.json` (see the "Plugin Composition" section of SKILL.md).

## Parameter Definitions

Extract hard-coded values in the script into configurable parameters, decoupling logic from data. This makes it easy to dynamically adjust policies or manage secrets securely.

| Field | Description |
| --- | --- |
| Parameter name | Corresponds to the variable name referenced in the script (e.g., `secret_key`, accessed as `params.secret_key` in the script) |
| Parameter type | `string` / `number` / `boolean` / `JSON Object` / `JSON Array`; must match the script's handling logic |
| Parameter description | Describes the purpose of the parameter |
| Parameter value | Two modes: manual input, or use a KMS credential |

**Parameter value - manual input**: fill in the concrete value directly.

**Parameter value - KMS credential**: reference an existing credential in Key Management Service (KMS) to store sensitive data securely. The credential must be bound with a tag before it can be referenced by WAF:

| Tag Key | Tag Value |
| --- | --- |
| `waf:access:enable` | `true` |

## Debug Tests

- **Plugin action parameter**: currently supports only "block mode", i.e., blocking the request.
- **Traffic parameters**: simulate a real HTTP request. Add parameter names (e.g., `method`, `uri`, `args`) and their values **as flat key-value pairs**, one item at a time. For example, use `method=POST`, `uri=/login` to test the protection logic of a login endpoint. Local `tests/*.json` cannot be executed automatically; they must be entered manually in this form and the results compared.
- **Execution result**: click "Run Debug"; the system executes the script with the simulated traffic and returns the result in the result panel. On failure, fix the code according to the error message.
- **Timeout**: the execution limit per traffic entry is **2ms**. During debugging, a timeout fails the test and the creation fails; at runtime, a timeout forcibly skips the current execution (i.e., protection silently fails and the request passes through).

## Association to Take Effect

After a plugin is created, it must be referenced by a "Custom Rules" protection template; the plugin logic executes only when the rule matches. **An unassociated plugin has no effect on any traffic.**

## Daily Operations

| Operation | Description |
| --- | --- |
| View plugin list | The page shows all extension plugins, searchable by name |
| View associated protection rules | Click the icon in the "Associated Rules" column to view the associated rule IDs, which can be copied and searched on the Web Core Protection or Security Report page |
| Edit extension plugin | Use "Edit" in the operation column to modify the configuration |
| Delete extension plugin | Use "Delete" in the operation column to remove the plugin |
