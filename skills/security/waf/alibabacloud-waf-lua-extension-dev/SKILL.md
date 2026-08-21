---
name: alibabacloud-waf-lua-extension-dev
description: |
  Use when creating, editing, or reviewing WAF 3.0 custom Lua extension plugins, plugin parameters, or request validation logic.
---

# WAF Extension Plugin (Lua) Development & Review

Alibaba Cloud WAF 3.0 "Extension Plugins" allow custom Lua scripts to hook into the request processing pipeline and implement security logic beyond the native rules.

Official documentation: https://help.aliyun.com/zh/waf/web-application-firewall-3-0/user-guide/extensions

> This feature is supported only on the subscription Enterprise/Flagship editions and the pay-as-you-go edition, and it is a paid service. After a plugin is created, it takes effect only when it is referenced by a "Custom Rules" protection template.

## Key Constraints (Read First)

| Constraint | Impact |
| --- | --- |
| **No OpenAPI / CLI** | Extension plugins can only be configured in the console; there is no corresponding `aliyun` command or SDK interface. Do not try to create/query plugins via CLI, and there is no capability to import local files |
| **Block-only action** | The "plugin action parameter" in debug testing currently supports only block mode; `punish()` means blocking the request |
| **No logging** | `print`/`warn` have no effect; there is no log output mechanism inside scripts. The only feedback is the execution-result panel of "Run Debug" in the console |
| **Association required to take effect** | After a plugin is created, it must be referenced by a "Custom Rules" protection template; the plugin logic executes only when the rule matches |

## Plugin Composition

An extension plugin consists of four parts in the console. This Skill uses a set of local project files to mirror them, for version control and review — **but this file structure is a convention of this Skill; the platform does not consume these files, and they must ultimately be pasted into the console manually**:

| Console Configuration | Local Project File | Description |
| --- | --- | --- |
| Basic information (name/description) | `plugin.json` | Plugin metadata |
| Plugin code | `plugin.lua` | Custom Lua script |
| Parameter definitions | `params.json` | Predefined parameters (including type, value, KMS reference) |
| Debug tests | `tests/*.json` | Simulated traffic and expected action results |

## Workflow

### 1. Create

1. Clarify the protection goal: what kind of requests to block, and which request fields to decide on.
2. Create the plugin directory `<plugin-name>/` in the workspace and generate the four file types (see "Plugin Project Structure").
3. Write `plugin.lua`: read the request → evaluate → call `aliwaf.func.punish()` on a match.
4. Extract hard-coded values in the script (secrets, thresholds, whitelists, etc.) into `params.xxx` and declare them in `params.json`.
5. Write at least one `tests/*.json` case for each key scenario (one hit + one pass).
6. Paste the four configuration blocks into the console → enter the traffic parameters one by one → click "Run Debug", compare the results against the expectations in `tests/*.json`, and associate the plugin with the custom rule only after all cases pass.

### 2. Edit

1. Read the existing `plugin.lua` and `params.json` first; understand the current logic before changing it.
2. When changing logic, maintain the parameter definitions and test cases at the same time, so the script never references an undeclared `params.xxx`.
3. Re-run the review checklist after the change.

### 3. Review

Check item by item against the [Code Review Checklist](#code-review-checklist). The review output should indicate: matched items, risk level, specific line numbers/APIs, and fix suggestions.

## Plugin Project Structure

```
<plugin-name>/
├── plugin.json      # Basic information: name, description
├── plugin.lua       # Custom Lua script
├── params.json      # Parameter definitions (array)
└── tests/           # Debug test cases
    ├── hit.json     # Expected hit (punish)
    └── pass.json    # Expected pass
```

Fields of a single parameter in `params.json`: `name` (corresponds to `params.xxx` in the script), `type` (`string`/`number`/`boolean`/`json_object`/`json_array`), `description`, and either `value` or `kms_secret_name` (one of the two).

Fields of `tests/*.json`: `traffic` (`method`/`uri`/`query`/`args`/`headers`/`cookies`/`request_body`), `expect_punish` (boolean). The console's traffic parameters are flat key-value pairs; the nested fields above are the local record format and must be mapped manually when entered.

See [references/examples.md](references/examples.md) for complete templates.

## Runtime Environment

> The standard library whitelist and prohibition list below, as well as the static-check hints in "Common Errors", come from the platform implementation and **are not fully covered in the official documentation**.

### Available Lua Standard Libraries

- `base`: core basic functions (globally available)
- `table`, `string`, `math`, `utf8`
- `cjson`: JSON encoding/decoding (safe mode)
- `bit32`: 32-bit bitwise operations
- `pb`: Protobuf encoding/decoding

### Unavailable Standard Libraries

Accessing the following libraries raises an error: `os`, `io`, `package`, `debug`, `coroutine`

### Explicitly Disabled Functions

`load` / `loadstring`, `dofile`, `loadfile`, `collectgarbage`

## Coding Conventions

1. **No global variables or global functions** — use `local` everywhere
2. **No access to system-level globals** — `os`, `io`, `package`, `debug`
3. **No `require`**
4. **Only call APIs exported by `aliwaf`**
5. **Avoid infinite loops and long-running operations** — the execution timeout is 2ms, and **a timeout at runtime forcibly skips the current execution**, meaning the protection logic silently fails and the request passes through.
6. **Make the failure strategy explicit** — on parse failure or missing parameters, explicitly choose pass or block; do not leave an implicit default branch.

## Business API Overview

The platform exposes APIs only under the `aliwaf` namespace; full signatures and descriptions are in [references/lua-api-reference.md](references/lua-api-reference.md).

- `aliwaf.req.*` — request reading (method, URI, domain, query, args, cookies, headers, body). Returns an empty string `""` when a field does not exist.
- `aliwaf.util.*` — encoding/hashing/crypto helpers (base64, hex, URI escape, md5, sha256, crc32, evp encrypt/decrypt, ES256 sign/verify, millisecond timestamp). Returns `""` on failure (except `crc32` / `get_current_ms` / `es256_verify`).
- `aliwaf.func.*` — business helpers: `punish()` applies the preconfigured action (currently block only), plus the body-reception functions used in the flow below.

**Body handling must follow the three-step flow** — (1) if `is_last_fragment_arrived()` is false, call `wait_request_body()` and return so the framework re-executes the script after the body fully arrives; (2) if `is_request_body_discarded()` is true, the body was truncated over the size limit — give up the action; (3) only then call `get_body()`. Missing any step may read an incomplete or empty body. The complete code pattern is in [references/examples.md](references/examples.md) ("Standard Pattern for Request Body Handling").

### params — Predefined Parameters

Scripts reference predefined parameters from the plugin configuration via `params.xxx`. Strings, numbers, booleans, and JSON Object/Array are supported. An undeclared parameter is `nil` and must be validated first — see "Parameter Pitfall".

#### Parameter Pitfall

`params.xxx` is `nil` when it is not declared in the parameter definitions. If you write `if token ~= params.token then punish() end` directly, a missing parameter makes **every request** match the block condition, causing site-wide false positives. Always validate the parameter itself before use:

```lua
local expected = params.token
if expected == nil then
  return                     -- Pass through when the configuration is missing, to avoid blocking the entire site
end
if aliwaf.req.get_arg("token") ~= expected then
  aliwaf.func.punish()
  return
end
```

## Code Review Checklist

### Security
- [ ] No global variable/function definitions (all `local`)
- [ ] No access to `os`, `io`, `package`, `debug`
- [ ] No calls to `load`, `loadstring`, `dofile`, `loadfile`, `collectgarbage`
- [ ] No use of `require`
- [ ] No hard-coded sensitive information: secrets/credentials go through `params` + KMS credentials and do not appear in comments

### API Calls
- [ ] The trigger condition of `punish()` is correct and can never become constantly true due to missing parameters
- [ ] Only `aliwaf.req.*`, `aliwaf.util.*`, `aliwaf.func.*` are called
- [ ] The `get_body()` flow is correct

### Parameters
- [ ] Every `params.xxx` referenced by the script is declared in `params.json` / the console parameter definitions
- [ ] Type and non-nil checks are performed before use, and the behavior on `nil` is a deliberate choice (pass or block)
- [ ] Parameter types match the script's handling logic (do not compare a numeric parameter as a string)

### Robustness
- [ ] Worst-case execution time is under control, with no 2ms timeout risk (timeout = fail-open, protection silently fails)
- [ ] No infinite loops, no high-cost operations


## Common Errors

| Error Message | Cause | Fix |
| --- | --- | --- |
| `attempt to call a nil value (global 'xxx')` | Calling a disabled function or a nonexistent API | Remove the call |
| `attempt to index a nil value (global 'os')` | Accessing an unloaded standard library | Do not use `os`/`io`/`package`/`debug` |
| `lua run timeout` | Exceeding the 2ms execution limit | Reduce computation; avoid complex loops |
| `access to forbidden global '%s' is not allowed` | Static check: accessing a forbidden global variable | Remove the access |
| `defining global function '%s' is not allowed` | Static check: defining a global function | Use `local function` instead |
| `defining or modifying global variable '%s' is not allowed` | Static check: defining/modifying a global variable | Use `local` instead |


## Reference Links

| Resource | Path |
| --- | --- |
| Full reference of Lua standard libraries and `aliwaf.*` APIs | [references/lua-api-reference.md](references/lua-api-reference.md) |
| Console lifecycle (activation/create/parameters/debug/association/operations) | [references/console-lifecycle.md](references/console-lifecycle.md) |
| Project templates and script examples | [references/examples.md](references/examples.md) |
| Official documentation | [Extension Plugins](https://help.aliyun.com/zh/waf/web-application-firewall-3-0/user-guide/extensions) |
