# OTTL — function & converter catalog

> Sources:
> - https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/LANGUAGE.md (grammar)
> - https://github.com/open-telemetry/opentelemetry-collector-contrib/blob/main/pkg/ottl/ottlfuncs/README.md (functions)
>
> Editors mutate telemetry; converters return values. Editors are lowercase, converters Capitalized.

## Grammar essentials

| Element | Syntax |
|---|---|
| Strings | Double-quoted: `"abc"` |
| Ints / floats | `1`, `-5`, `1.5`, `-.5` (int64 / float64) |
| Bool / nil | `true`, `false`, `nil` |
| Bytes | `0x0001` |
| Lists | `[v1, v2, ...]` |
| Maps | `{"k": v, ...}` |
| Path | `resource.attributes["host.name"]`, `log.body["status"]` |
| Editor call | `set(...)` (lowercase, mutates) |
| Converter call | `IsMatch(...)`, with optional indexing `Split(x, ",")[1]` |
| Named args | `name = value`, after positional |
| Math | `+ - * /`, with `()` |
| Compare | `==`, `!=`, `<`, `>`, `<=`, `>=` |
| Boolean | `and`, `or`, `not` (precedence: `not` > `and` > `or`) |
| Where clause | `<editor>(...) where <condition>` |
| Enums | UPPERCASE identifiers (e.g. `SEVERITY_NUMBER_ERROR`) |

> The grammar has no `in` or `matches` keyword — use the `IsMatch(...)` converter for regex membership tests.

A statement is one editor call + optional `where`. Components (transformprocessor, filterprocessor) collect statements into lists.

## Editors (mutate state)

| Editor | Signature | Purpose |
|---|---|---|
| `set` | `set(target, value)` | Assign a field. |
| `append` | `append(target, value?, values?)` | Append to a slice; auto-converts scalar→array. |
| `delete_key` | `delete_key(target, key)` | Remove one map key. |
| `delete_matching_keys` | `delete_matching_keys(target, pattern)` | Regex-delete map keys. |
| `keep_keys` | `keep_keys(target, [keys])` | Keep only listed keys. |
| `keep_matching_keys` | `keep_matching_keys(target, pattern)` | Regex-keep keys. |
| `delete_index` | `delete_index(target, start, end?)` | Remove slice elements. |
| `flatten` | `flatten(target, prefix?, depth?, resolveConflicts?)` | Flatten nested maps. |
| `limit` | `limit(target, n, [priority_keys])` | Cap map size, prefer named keys. |
| `merge_maps` | `merge_maps(target, source, strategy)` | Strategies: `insert`, `update`, `upsert`. |
| `replace_pattern` | `replace_pattern(target, regex, replacement, fn?, fmt?)` | Regex replace on a string field. |
| `replace_match` | `replace_match(target, glob, replacement, fn?, fmt?)` | Glob match replace. |
| `replace_all_patterns` | `replace_all_patterns(target, mode, regex, replacement, fn?, fmt?)` | Regex replace map keys/values. |
| `replace_all_matches` | `replace_all_matches(target, glob, replacement, fn?, fmt?)` | Glob replace across map values. |
| `truncate_all` | `truncate_all(target, n, utf8_safe?)` | Truncate all string values in a map. |

## Converters (most-used)

| Converter | Signature | Purpose |
|---|---|---|
| `Concat` | `Concat([v1,v2,...], delim)` | Join values into a string. |
| `ConvertCase` | `ConvertCase(s, "lower"\|"upper"\|"snake"\|"camel")` | String case. |
| `Format` | `Format(fmt, [args])` | `fmt.Sprintf`. |
| `Int` / `Double` / `Bool` / `String` | `Int(v)` etc. | Type conversion. |
| `Hex` | `Hex(v)` | Hex string. |
| `IsBool` / `IsInt` / `IsDouble` / `IsString` / `IsList` / `IsMap` | `IsX(v)` | Type predicates. |
| `IsMatch` | `IsMatch(target, regex)` | Regex match (use this for "matches"/membership). |
| `IsValidLuhn` | `IsValidLuhn(v)` | Credit-card / Luhn check. |
| `Keys` / `Values` | `Keys(map)`, `Values(map)` | Map keys/values as slice. |
| `Len` | `Len(target)` | Length of string/slice/map. |
| `ParseJSON` | `ParseJSON(s)` | JSON string → map/slice. |
| `ParseCSV` | `ParseCSV(s, headers, delim?, headerDelim?, mode?)` | CSV row → map. |
| `ParseKeyValue` | `ParseKeyValue(s, delim?, pairDelim?)` | "k=v k2=v2" → map. |
| `ParseXML` / `ParseSimplifiedXML` | `ParseXML(s)` | XML → map. |
| `Split` | `Split(s, delim)` | String → slice; index with `[i]`. |
| `Substring` | `Substring(s, start, len)` | Substring. |
| `Trim` / `TrimPrefix` / `TrimSuffix` | `Trim(s, cutset)` | Trim chars. |
| `HasPrefix` / `HasSuffix` | `HasPrefix(s, p)` | Predicate. |
| `Time` | `Time(s, layout)` | Parse string to `time.Time`. |
| `FormatTime` | `FormatTime(t, layout)` | Format time to string. |
| `TruncateTime` | `TruncateTime(t, duration)` | Floor time to bucket. |
| `Now` | `Now()` | Current time. |
| `Seconds` / `Milliseconds` / `Microseconds` / `Nanoseconds` / `Minutes` / `Hours` | `Seconds(d)` | Duration → number. |
| `Unix` / `UnixMilli` / `UnixMicro` / `UnixNano` / `UnixSeconds` | `UnixMilli(t)` | Time → epoch. |
| `Day` / `Hour` / `Minute` / `Second` / `Month` / `Year` / `Weekday` / `Nanosecond` | `Day(t)` | Time component. |
| `SHA1` / `SHA256` / `SHA512` / `MD5` / `FNV` / `Murmur3Hash` / `Murmur3Hash128` / `XXH3` / `XXH128` | `SHA256(s)` | Hashes. |
| `UUID` / `UUIDv7` | `UUID()` | Generate ID. |
| `URL` | `URL(s)` | Parse URL into a map. |
| `UserAgent` | `UserAgent(s)` | Parse UA string. |
| `Coalesce` | `Coalesce(v1, v2, ...)` | First non-nil. |
| `ContainsValue` | `ContainsValue(slice, v)` | Slice membership. |
| `IsInCIDR` | `IsInCIDR(ip, cidr)` | IP-in-CIDR predicate. |
| `ExtractPatterns` / `ExtractGrokPatterns` | `ExtractPatterns(s, regex)` | Capture groups → map. |
| `Sort` | `Sort(slice, "asc"\|"desc")` | Sort slice. |
| `SliceToMap` | `SliceToMap(slice, key, value?)` | Slice of maps → map. |
| `Decode` / `Base64Encode` / `Base64Decode` | `Base64Encode(s)` | Encoding. |
| `IsRootSpan` | `IsRootSpan()` | (spans only) |
| `SpanID` / `TraceID` / `ProfileID` | `SpanID(0x...)` | Construct typed IDs. |
| `Index` | `Index(slice, v)` | Position of v. |
| `ToKeyValueString` | `ToKeyValueString(map, delim?, pairDelim?)` | map → "k=v k2=v2". |
| `ConvertAttributesToElementsXML` / `ConvertTextToElementsXML` / `GetXML` / `InsertXML` / `RemoveXML` | XML manipulation. |
| `CommunityID` | `CommunityID(...)` | Network flow ID. |

(For the full list including XML helpers and time-component converters, see the upstream README.)

## Design constraints

Built-in functions cannot touch the filesystem, network, or any I/O. They must terminate (no infinite loops).

## Examples

```
# Tag high-severity logs and copy a body field into attributes
set(log.attributes["high_severity"], true) where log.severity_number >= SEVERITY_NUMBER_ERROR
set(log.attributes["http.status_code"], log.body["status"]) where log.body["status"] != nil

# Regex on a resource attribute
set(log.attributes["pod_log"], true) where IsMatch(resource.attributes["host.name"], "pod-.*")

# Redact secrets in body
replace_pattern(log.body, "password=[^ ]+", "password=***")

# Drop debug logs unless force_keep
delete_key(log.attributes, "debug") where not (IsMatch(log.body, "DEBUG.*") and log.severity_number < SEVERITY_NUMBER_INFO)
```
