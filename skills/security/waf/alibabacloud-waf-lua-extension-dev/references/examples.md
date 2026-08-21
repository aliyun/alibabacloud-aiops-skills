# Examples

## Project Template Example

A complete local plugin project directory:

```
token-check/
├── plugin.json
├── plugin.lua
├── params.json
└── tests/
    ├── hit.json
    └── pass.json
```

> **The local project is a convention of this Skill; the platform does not consume these files.** The console has no import interface and no corresponding OpenAPI/CLI; the four files must ultimately be pasted manually into the corresponding configuration blocks in the console. `tests/*.json` cannot be executed locally; they only serve as the entry checklist and regression record for "Debug Tests" in the console.

**plugin.json** — basic information (corresponds to "Basic Information" in the console):

```json
{
  "name": "token-check",
  "description": "Validates the query parameter token against the predefined value; blocks on mismatch"
}
```

**params.json** — parameter definitions (array, corresponds to "Parameter Definitions" in the console):

```json
[
  {
    "name": "token",
    "type": "string",
    "description": "The expected valid token",
    "value": "expected_token_value"
  }
]
```

> `value` (manual input) and `kms_secret_name` (KMS credential) are mutually exclusive. For real secrets, use `kms_secret_name` instead; the credential must be bound with the tag `waf:access:enable = true`.

**plugin.lua** — plugin code:

```lua
local expected = params.token
if expected == nil then
  return
end

local token = aliwaf.req.get_arg("token")
if token ~= expected then
  aliwaf.func.punish()
end
```

**tests/hit.json** — expected hit (block):

```json
{
  "traffic": {
    "method": "GET",
    "uri": "/api/v1/orders",
    "args": { "token": "wrong-value" }
  },
  "expect_punish": true
}
```

**tests/pass.json** — expected pass:

```json
{
  "traffic": {
    "method": "GET",
    "uri": "/api/v1/orders",
    "args": { "token": "expected_token_value" }
  },
  "expect_punish": false
}
```

> The traffic parameters of "Debug Tests" in the console are added **as flat key-value pairs**, one item at a time. The nested `traffic` format above is the local record format; when entering it into the console, flatten it into key-value pairs yourself. `expect_punish` is a local assertion field that the console does not recognize; the execution-result panel must be compared manually.

## Lua Script Examples

### 1. Standard Pattern for Request Body Handling

The body arrives as a stream; it may not be fully received when the script runs for the first time. The script must be written in the order "wait → truncation check → read & parse → type validation → handling".

```lua
-- 1. Body not fully received: tell the framework to wait and re-execute this script after the body fully arrives
if not aliwaf.func.is_last_fragment_arrived() then
  aliwaf.func.wait_request_body()
  return
end

-- 2. Body truncated: content is incomplete, give up the action
if aliwaf.func.is_request_body_discarded() then
  return
end

-- 3. Get the body
local body = aliwaf.req.get_body()
local ok, data = pcall(cjson.decode, body)
if not ok or not data then
  return
end

if data["action"] == "sensitive_operation" then
  local token = aliwaf.req.get_header("X-Auth-Token")
  if not token or token == "" then
    aliwaf.func.punish()
    return
  end
end
```

### 2. Signature Timestamp Anti-Replay Validation

```lua
-- Timestamp unit: get_current_ms() returns milliseconds, so the timestamp passed by the client must also be in milliseconds.
-- If the business actually sends seconds, you must first do ts = ts * 1000; otherwise the time difference is always greater than the window, causing site-wide false positives.
local WINDOW_MS = 5 * 60 * 1000

local sign = aliwaf.req.get_arg("sign")
local timestamp = aliwaf.req.get_arg("timestamp")

if sign == "" or timestamp == "" then
  aliwaf.func.punish()
  return
end

-- tonumber returns nil on failure; this must be checked, otherwise the subsequent arithmetic operation raises an error
local ts = tonumber(timestamp)
if not ts then
  aliwaf.func.punish()
  return
end

if math.abs(aliwaf.util.get_current_ms() - ts) > WINDOW_MS then
  aliwaf.func.punish()
  return
end
```
