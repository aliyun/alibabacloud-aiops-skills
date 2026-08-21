# Lua API Reference

This document covers the Lua standard libraries and platform business APIs available when writing extension plugin scripts.

## Lua Standard Library APIs

> **Source note**: the standard library whitelist and prohibition list in this section come from the platform implementation. Function signatures and semantics follow the Lua standard; availability is best confirmed by actual tests via "Run Debug" in the console.

### base — Base Library

`load` (including the `loadstring` alias), `dofile`, `loadfile`, and `collectgarbage` are explicitly disabled by the platform.

| Function | Description |
| --- | --- |
| `assert(v [, message])` | Assertion; raises an error if `v` is falsy |
| `error(message [, level])` | Raises an error and aborts execution |
| `pcall(f, ...)` | Calls a function in protected mode; catches exceptions and returns `true/false, result/errmsg` |
| `xpcall(f, msgh, ...)` | Calls a function in protected mode with a custom error handler |
| `type(v)` | Returns the type string of the value |
| `tostring(v)` | Converts a value to a string |
| `tonumber(e [, base])` | Converts a value to a number with the given base (2~36); returns `nil` on failure |
| `select(index, ...)` | Returns all arguments after the `index`-th one; `"#"` returns the total number of arguments |
| `pairs(t)` | Returns an iterator for traversing all key-value pairs of a table in `for` |
| `ipairs(t)` | Returns an iterator for traversing the array part of a table in order in `for` |
| `next(table [, index])` | Returns the next key-value pair in the table |
| `rawget(table, index)` | Raw table read without triggering metamethods |
| `rawset(table, index, value)` | Raw table write without triggering metamethods |
| `rawlen(v)` | Returns the raw length of a table or string |
| `rawequal(v1, v2)` | Raw equality comparison without triggering metamethods |
| `getmetatable(object)` | Gets the metatable of an object |
| `setmetatable(table, metatable)` | Sets the metatable of a table |
| `print(...)` | Has no effect; do not use for debugging |
| `warn(msg1, ...)` | Has no effect; do not use for debugging |
| `_G` | The global environment table |
| `_VERSION` | The Lua version string |

> Scripts have **no logging capability** (`print`/`warn` have no effect); the only feedback channel is the execution-result panel of "Run Debug" in the console. Do not try to troubleshoot with print statements.

### table — Table Library

| Function | Description |
| --- | --- |
| `table.concat(list [, sep [, i [, j]]])` | Joins the strings in the `[i..j]` range of the list with separator `sep` and returns the result |
| `table.insert(list, [pos,] value)` | Inserts a value at position `pos`; appends to the end if `pos` is omitted |
| `table.remove(list [, pos])` | Removes and returns the element at position `pos`; removes the last element if omitted |
| `table.move(a1, f, e, t [, a2])` | Moves the elements in the `[f..e]` range of table `a1` to table `a2` (defaults to itself) starting at position `t` |
| `table.sort(list [, comp])` | Sorts the list in place with an optional custom comparator |
| `table.pack(...)` | Packs all arguments into a table, with an `n` field recording the count |
| `table.unpack(list [, i [, j]])` | Returns the multiple values in the `[i..j]` range of the list |

### string — String Library

| Function | Description |
| --- | --- |
| `string.byte(s [, i [, j]])` | Returns the character codes of `s[i]` through `s[j]` |
| `string.char(...)` | Converts integer codes to the corresponding characters and concatenates them |
| `string.dump(func)` | Exports the binary bytecode representation of a Lua function |
| `string.find(s, pattern [, init [, plain]])` | Searches for `pattern` in `s`; returns the start and end positions of the match |
| `string.match(s, pattern [, init])` | Returns the content of `s` that matches `pattern` |
| `string.gmatch(s, pattern [, init])` | Returns an iterator that yields all matches one by one |
| `string.gsub(s, pattern, repl [, n])` | Global replacement; returns the replaced string and the replacement count |
| `string.sub(s, i [, j])` | Extracts a substring; supports negative indices |
| `string.len(s)` | Returns the byte length of the string |
| `string.rep(s, n [, sep])` | Repeats `s` `n` times |
| `string.reverse(s)` | Reverses the string |
| `string.lower(s)` | Converts to lowercase |
| `string.upper(s)` | Converts to uppercase |
| `string.format(formatstring, ...)` | C `printf`-style string formatting |
| `string.pack(fmt, v1, v2, ...)` | Packs values into a binary string according to the format string |
| `string.packsize(fmt)` | Returns the binary length corresponding to the `string.pack` format |
| `string.unpack(fmt, s [, pos])` | Unpacks values from a binary string according to the format string |

### math — Math Library

| Function/Constant | Description |
| --- | --- |
| `math.abs(x)` | Absolute value |
| `math.acos(x)` | Arc cosine (radians) |
| `math.asin(x)` | Arc sine (radians) |
| `math.atan(y [, x])` | Arc tangent (radians); supports two arguments |
| `math.atan2(y, x)` | Two-argument arc tangent (compatibility function) |
| `math.ceil(x)` | Rounds up |
| `math.floor(x)` | Rounds down |
| `math.fmod(x, y)` | Floating-point modulo |
| `math.max(x, ...)` | Maximum value |
| `math.min(x, ...)` | Minimum value |
| `math.modf(x)` | Splits into integer and fractional parts |
| `math.sqrt(x)` | Square root |
| `math.exp(x)` | Natural exponent e^x |
| `math.log(x [, base])` | Logarithm with an optional base |
| `math.log10(x)` | Base-10 logarithm |
| `math.pow(x, y)` | x to the power of y (compatibility function; prefer `x^y`) |
| `math.sin(x)` / `math.cos(x)` / `math.tan(x)` | Trigonometric functions (radians) |
| `math.deg(x)` / `math.rad(x)` | Radian/degree conversion |
| `math.ult(m, n)` | Unsigned integer comparison |
| `math.tointeger(x)` | Attempts to convert `x` to an integer |
| `math.type(x)` | Returns `"integer"`, `"float"`, or `nil` |
| `math.random([m [, n]])` | Generates a random number |
| `math.randomseed(x [, y])` | Sets the random seed |
| `math.sinh` / `math.cosh` / `math.tanh` | Hyperbolic functions (compatibility) |
| `math.frexp` / `math.ldexp` | Floating-point decomposition/composition (compatibility) |
| `math.pi` | Pi |
| `math.huge` | Positive infinity |
| `math.maxinteger` | Maximum integer value |
| `math.mininteger` | Minimum integer value |

### utf8 — UTF-8 Library

| Function/Constant | Description |
| --- | --- |
| `utf8.char(...)` | Converts Unicode code points to a UTF-8 string |
| `utf8.charpattern` | The pattern string matching a single UTF-8 character |
| `utf8.codepoint(s [, i [, j]])` | Returns the code point of each UTF-8 character in the range |
| `utf8.codes(s)` | Returns an iterator yielding the position and code point of each UTF-8 character |
| `utf8.len(s [, i [, j]])` | Returns the number of UTF-8 characters in the range |
| `utf8.offset(s, n [, i])` | Returns the byte start position of the `n`-th UTF-8 character |

### cjson — JSON Library

Loaded in `cjson.safe` mode; `encode`/`decode` return `nil, errmsg` on error.

| Function | Description |
| --- | --- |
| `cjson.encode(value)` | Encodes a Lua value into a JSON string |
| `cjson.decode(json_string)` | Decodes a JSON string into a Lua value |
| `cjson.null` | The Lua representation of JSON `null` |
| `cjson.encode_sparse_array([convert [, ratio [, safe]]])` | Configures sparse array encoding behavior |
| `cjson.encode_max_depth([depth])` | Gets/sets the maximum encoding nesting depth |
| `cjson.decode_max_depth([depth])` | Gets/sets the maximum decoding nesting depth |
| `cjson.encode_number_precision([precision])` | Gets/sets number encoding precision (1~14) |
| `cjson.encode_keep_buffer([keep])` | Gets/sets whether the encoding buffer is reused |
| `cjson.encode_invalid_numbers([setting])` | Gets/sets Infinity/NaN encoding behavior |
| `cjson.decode_invalid_numbers([setting])` | Gets/sets Infinity/NaN decoding behavior |
| `cjson.new()` | Creates an independent cjson instance |

### bit32 — Bitwise Library

Performs bitwise operations on 32-bit unsigned integers.

| Function | Description |
| --- | --- |
| `bit32.band(...)` | Bitwise AND |
| `bit32.bor(...)` | Bitwise OR |
| `bit32.bxor(...)` | Bitwise XOR |
| `bit32.bnot(n)` | Bitwise NOT |
| `bit32.btest(...)` | Tests whether the bitwise AND is non-zero |
| `bit32.lshift(n, disp)` | Left shift |
| `bit32.rshift(n, disp)` | Logical right shift |
| `bit32.arshift(n, disp)` | Arithmetic right shift |
| `bit32.lrotate(n, disp)` | Left rotation |
| `bit32.rrotate(n, disp)` | Right rotation |
| `bit32.extract(n, field [, width])` | Extracts the specified bits |
| `bit32.replace(n, v, field [, width])` | Replaces the specified bits |

### pb — Protobuf Library

| Function | Description |
| --- | --- |
| `pb.clear()` | Clears all loaded .proto definitions |
| `pb.load(data)` | Loads a .proto definition from binary data |
| `pb.encode(type, value)` | Encodes a Lua table into binary data with the given Protobuf type |
| `pb.decode(type, data)` | Decodes binary data into a Lua table with the given Protobuf type |
| `pb.types()` | Returns an iterator over all registered type names |
| `pb.fields(type)` | Returns an iterator over the field information of the given type |
| `pb.type(type)` | Gets the meta information of a type |
| `pb.field(type, name)` | Gets the meta information of a specific field |
| `pb.typefmt(type)` | Gets the format string of a type |
| `pb.enum(name_or_number)` | Converts between enum values and names |
| `pb.defaults(type [, opts])` | Gets the default value table of a type |
| `pb.hook(type [, func])` | Gets/sets the decode hook function |
| `pb.encode_hook(type [, func])` | Gets/sets the pre-encode hook function |
| `pb.tohex(data [, sep])` | Converts binary data to a hex string |
| `pb.fromhex(hex)` | Converts a hex string to binary data |
| `pb.result(...)` | Merges multiple return values into one string |
| `pb.option(name [, value])` | Gets/sets a global option |
| `pb.state()` | Gets the current pb state |
| `pb.pack(fmt, ...)` | Packs values into binary data by format |
| `pb.unpack(data, fmt)` | Unpacks values from binary data by format |

## Platform Business APIs

### aliwaf.req — Request Reading

All read interfaces return string values; an empty string `""` is returned when the field does not exist.

| API | Parameters | Returns | Description |
| --- | --- | --- | --- |
| `aliwaf.req.get_method()` | none | string | HTTP request method |
| `aliwaf.req.get_uri()` | none | string | Request URI path |
| `aliwaf.req.get_domain()` | none | string | Request Host domain |
| `aliwaf.req.get_query()` | none | string | Full query string |
| `aliwaf.req.get_arg(name)` | name: string | string | The specified query parameter value |
| `aliwaf.req.get_cookie(name)` | name: string | string | The specified cookie value |
| `aliwaf.req.get_header(name)` | name: string | string | The specified request header value |
| `aliwaf.req.get_body()` | none | string | Request body content |

### aliwaf.util — General Utilities

All interfaces return an empty string `""` on failure (except integer return values).

#### Encoding/Decoding

| API | Input | Output | Description |
| --- | --- | --- | --- |
| `aliwaf.util.base64_encode(input)` | `input: string` | `string` | Base64 encoding |
| `aliwaf.util.base64_decode(input)` | `input: string` | `string` | Base64 decoding |
| `aliwaf.util.hex_encode(input)` | `input: string` | `string` | Hex encoding (uppercase) |
| `aliwaf.util.hex_decode(input)` | `input: string` | `string` | Hex decoding |
| `aliwaf.util.escape_uri(input)` | `input: string` | `string` | URL encoding |
| `aliwaf.util.unescape_uri(input)` | `input: string` | `string` | URL decoding |

#### Hashing & Checksum

| API | Input | Output | Description |
| --- | --- | --- | --- |
| `aliwaf.util.md5(input)` | `input: string` | `string` | 32-char lowercase hex MD5 digest |
| `aliwaf.util.sha256(input)` | `input: string` | `string` | 64-char lowercase hex SHA-256 digest |
| `aliwaf.util.crc32(input)` | `input: string` | `integer` | CRC32 checksum |

#### Encryption/Decryption

| API | Input | Output | Description |
| --- | --- | --- | --- |
| `aliwaf.util.evp_encrypt(type, key, iv, text)` | `type, key, iv, text: string` | `string` | General encryption (e.g., `"aes-128-cbc"`) |
| `aliwaf.util.evp_decrypt(type, key, iv, text)` | `type, key, iv, text: string` | `string` | General decryption |

#### Signing & Verification

| API | Input | Output | Description |
| --- | --- | --- | --- |
| `aliwaf.util.es256_sign(private_key, input)` | `private_key: string (PEM)`, `input: string` | `string` | ES256 signing |
| `aliwaf.util.es256_verify(public_key, input, signature)` | `public_key: string (PEM)`, `input: string`, `signature: string` | `boolean` | ES256 verification |

#### Others

| API | Input | Output | Description |
| --- | --- | --- | --- |
| `aliwaf.util.get_current_ms()` | none | `integer` | Current millisecond UNIX timestamp |

### aliwaf.func — Business Helper Functions

| API | Input | Output | Description |
| --- | --- | --- | --- |
| `aliwaf.func.punish()` | none | none | Applies the preselected action to the current request; the action mode currently supports "block" only. |
| `aliwaf.func.is_last_fragment_arrived()` | none | `boolean` | Whether the request body has been fully received |
| `aliwaf.func.is_request_body_discarded()` | none | `boolean` | Whether the request body was truncated due to the size limit (128KB) |
| `aliwaf.func.wait_request_body()` | none | none | Tells the framework to wait until the body is fully received, then re-executes the script |

### params — Parameter References

The platform supports extracting hard-coded values in scripts into configurable parameters. Parameters are predefined in the plugin configuration, and scripts reference them via the `params` table.

**For a parameter not declared in the parameter definitions, `params.xxx` is `nil`.**

| Parameter Type | Description |
| --- | --- |
| String | Plain text |
| Number | Numeric parameter |
| Boolean | `true` / `false` |
| JSON Object | Complex structured data; referenced as a Lua table |
| JSON Array | List data; referenced as a Lua table |
