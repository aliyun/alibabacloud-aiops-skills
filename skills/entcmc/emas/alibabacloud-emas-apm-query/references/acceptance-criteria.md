# Acceptance criteria (correct / incorrect CLI examples)

This file lists the correct / incorrect usages of `aliyun-cli-emas-appmonitor` inside this Skill for code review and self-check.

## 1. Product / command group existence

```bash
aliyun emas-appmonitor --help
```

- Correct: the subcommand list contains `get-issues` / `get-issue` / `get-errors` / `get-error` / `get-activity-event` / `get-activity-events` / ...
- Incorrect: `product not exists` is returned -> plugin not installed; run `aliyun plugin install --names emas-appmonitor`

## 2. `get-issues`

### Correct

```bash
aliyun emas-appmonitor get-issues \
  --app-key 335581386 \
  --os android \
  --biz-module crash \
  --time-range StartTime=1714800000000 EndTime=1715404800000 Granularity=1 GranularityUnit=day \
  --filter '{"Operator":"and","SubFilters":["{\"operator\":\"in\",\"key\":\"issueStatus\",\"values\":[1,2,3,4]}"]}' \
  --order-by ErrorCount --order-type desc \
  --page-index 1 --page-size 5
```

### Incorrect examples

| Wrong usage | Problem | Correct usage |
| --- | --- | --- |
| `--app-key 335581386abc` | App Key is int | use pure digits |
| Missing `--os` | Backend returns no data -> `Model=null` | add `--os android` |
| `--biz-module CRASH` | Enum is case-sensitive | `--biz-module crash` |
| `--biz-module exception_type` | Illegal enum | use one of `crash`/`anr`/`lag`/`custom`/`memory_leak`/`memory_alloc` |
| `--time-range '{"StartTime":...}'` | Object cannot be parsed as a JSON string | use `StartTime=... EndTime=... Granularity=1 GranularityUnit=day` |
| `--filter '[{...}]'` | Filter is an object, not an array | `--filter '{"Operator":"and","SubFilters":[...]}'` |
| `--filter '{"operator":"and","subFilters":[...]}'` | Root `Operator` / `SubFilters` keys lowercased | Root keys must be TitleCase: `"Operator"`, `"SubFilters"` |
| `--filter '{"Operator":"and","SubFilters":[{"operator":"in",...}]}'` | Each element of `SubFilters` must be a JSON string | `SubFilters:["{\"operator\":\"in\",...}"]` |
| `--order-by errorCount` | Enum is case-sensitive | `--order-by ErrorCount` |

## 3. `get-issue`

### Correct

```bash
aliyun emas-appmonitor get-issue \
  --app-key 335581386 --os android --biz-module crash \
  --digest-hash 3Q758M33DP0AV \
  --time-range StartTime=1714800000000 EndTime=1715404800000 Granularity=1 GranularityUnit=day
```

### Incorrect examples

| Wrong usage | Problem |
| --- | --- |
| Missing `--os` | CLI reports `required flags missing: --os` |
| Missing `--digest-hash` | CLI does not enforce it, but the response is incomplete; per Skill convention always pass it |
| `--biz-module lag` (but the hash belongs to crash) | `Model` is empty; biz-module must match the module the hash belongs to |
| `--time-range StartTime=...,EndTime=...` | CLI separates key=value pairs by space, not comma |

## 4. `get-errors`

### Correct

```bash
aliyun emas-appmonitor get-errors \
  --app-key 335581386 --os android --biz-module crash \
  --digest-hash 3Q758M33DP0AV \
  --time-range StartTime=1714800000000 EndTime=1715404800000 \
  --page-index 1 --page-size 10
```

### Incorrect examples

| Wrong usage | Problem |
| --- | --- |
| `--time-range StartTime=... EndTime=... Granularity=1 GranularityUnit=day` | `get-errors`' TimeRange does not include Granularity (it will be ignored but may affect other validation) |
| Missing `--page-index` / `--page-size` | CLI rejects with `required flags missing` |
| Blind `--page-size 100` | Poor performance; recommend <= 20 and paginate as needed |

## 5. `get-error`

### Correct

```bash
aliyun emas-appmonitor get-error \
  --app-key 335581386 --os android --biz-module crash \
  --digest-hash 3Q758M33DP0AV \
  --client-time 1774517852369 \
  --uuid 4422affc-e43f-4739-8718-10ac71fa585a \
  --did -4963409598449270935
```

### Incorrect examples

| Wrong usage | Problem | Fix |
| --- | --- | --- |
| Missing `--did` | `Code: 100011 Parameter Not Enough` (even though `--help` marks it optional) | Take `Did` from the same item in the `get-errors` response |
| `--client-time 1774517852` | Seconds-level timestamp | Use milliseconds (13 digits) |
| `--did "-4963409598449270935"` (extra quotes) | Most shells do not need the quotes; pass the raw value | If `Did` starts with `-`, the `--did=-4963409598449270935` form is safer |
| Daily use of `--biz-force true` | Pointless cost | Only when the cache is stale |

## 6. Filter emphasized again

| Good/Bad | Example |
| --- | --- |
| Good | `'{"Operator":"and","SubFilters":["{\"operator\":\"in\",\"key\":\"issueStatus\",\"values\":[1,2,3,4]}"]}'` |
| Good | `'{"Operator":"or","SubFilters":["{\"operator\":\"like\",\"key\":\"appVersion\",\"values\":[\"2.%\"]}"]}'` |
| Bad | `'{"Operator":"AND", ...}'` (case) |
| Bad | `'{"Operator":"and","SubFilters":[{"operator":"in",...}]}'` (SubFilter not stringified) |
| Bad | `--filter Key=and Operator=and SubFilters='[...]'` (attempts the key=value object format) |

## 7. OS / BizModule combinations

| biz-module | android | iphoneos | harmony | h5 | Notes |
| --- | --- | --- | --- | --- | --- |
| crash | Yes | Yes | Yes | No | available on all 3 mobile platforms |
| anr | Yes | No | No | No | Android only |
| lag | Yes | Yes | Yes | No | 3 platforms |
| custom | Yes | Yes | Yes | No | 3 platforms; Flutter/Unity custom exceptions go here too |
| memory_leak | Yes | Yes | No | No | no Harmony |
| memory_alloc | Yes | Yes | No | No | no Harmony |

When the Skill scans all 6 biz-modules by default, **filter out the unsupported combinations** per the table above to avoid wasted RPCs.

## 8. AI-mode closure

| Scenario | Must execute |
| --- | --- |
| Skill entry | `aliyun configure ai-mode enable` + `set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-emas-apm-query"` |
| Skill normal exit | `aliyun configure ai-mode disable` |
| Skill error / user interrupt | `aliyun configure ai-mode disable` |

## 9. Other

- Do NOT print / log AK / SK / STS Token / OAuth token inside the Skill.
- Do NOT call `aliyun configure set --access-key-id ... --access-key-secret ...` with plaintext credentials.
- Do NOT log `AppSecret` / `AppRsaSecret`.
- When credentials need to be supplied, ask the user to run `aliyun configure` out-of-band (OAuth preferred) or set environment variables.
