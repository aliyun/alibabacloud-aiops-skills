# Verified Invocation Examples

Every command below was run successfully against the real service. For the meaning and
constraints of each parameter, see [tool-reference.md](tool-reference.md) (the verbatim
MCP descriptions); this file only gives copy-pasteable forms.

## Command prefix

The examples use `mcpx` to stand for the script. Define this function in your shell first.

bash / zsh:

```bash
mcpx() { uv run --python 3.11 scripts/mcpx.py "$@"; }
```

PowerShell:

```powershell
function mcpx { uv run --python 3.11 scripts/mcpx.py @args }
```

`$args` is PowerShell's automatic array variable; `@args` splats it element by element —
equivalent to bash's `"$@"`.

If you would rather not define a function, replace every `mcpx` with
`uv run --python 3.11 scripts/mcpx.py`.

Most examples wrap the JSON argument in **single quotes**, which bash / zsh / PowerShell
all accept verbatim: in these three shells single quotes are literal, so the `{}`, `[]`
and `:` inside the JSON are not reinterpreted. (`cmd.exe` does not work this way — it
passes the single quotes through as part of the argument.)

## PowerShell equivalents for bash-only syntax

The examples are written in bash. Six constructs are bash/Unix-specific; convert them per
this table on PowerShell, and copy the rest as-is:

| bash | PowerShell | Note |
|---|---|---|
| `cat > /tmp/s.py <<'PY' … PY` | `Set-Content /tmp/s.py @' … '@` | The five RunScript examples write source to disk this way. The closing `'@` of a here-string must be at column zero |
| `cmd - <<'EOF' … EOF` | `@' … '@ \| cmd -` | The here-string opener `@'` must end the line right before the pipe; the closing `'@` must be at column zero, indentation breaks it |
| trailing `\` line continuation | trailing backtick `` ` `` | No space may follow the backtick |
| `/tmp/s.py` | `$env:TEMP\s.py` | The examples all write `/tmp/s.py`; swap it on Windows |
| `$(python3 -c '…json.load…')` | `$(Get-Content <file> -Raw \| ConvertFrom-Json)` | Reading one key out of a JSON file; see "Key behaviors" item 2 in SKILL.md for both forms |
| `\| jq`, `tail -n1` | `\| ConvertFrom-Json`, `Get-Content -Tail 1` | The script guarantees stdout is only the tool payload, so both shells can pipe it directly |

A single-quoted here-string (`@' … '@`) is equivalent to bash's `<<'EOF'`: the content is
treated as literal, so a `\"` inside it is not parsed a second time.

When the JSON must be **built dynamically** (for example, putting a local `.py` file into
the `script` parameter of `RunScript`), do not hand-write the quotes — use the bundled
helper, whose form is identical in both shells:

```bash
uv run --python 3.11 scripts/to_json.py script /tmp/s.py | mcpx call RunScript -
```

It places the file content verbatim into `{"<KEY>": ...}`; use `script` for `RunScript`
and `code` for `RunIaC`. It does not depend on a system `python3`, and `json.dumps`
handles the escaping, so you never hand-write nested quotes in the shell.

## CallCLI examples

```bash
# 1. 基础查询：产品 + 动作 + 参数
mcpx call CallCLI '{"command":"aliyun ecs describe-regions --region cn-hangzhou"}'

# 2. 用 jmespath 只取需要的字段，避免整个响应进上下文
mcpx call CallCLI '{"command":"aliyun ecs describe-regions","x_output_jmespath_filter":"Regions.Region[].RegionId"}'

# 3. 分页 + 字段重命名
mcpx call CallCLI '{"command":"aliyun ecs describe-instances --biz-region-id cn-hangzhou --page-size 5","x_output_jmespath_filter":"{total: TotalCount, ids: Instances.Instance[].InstanceId}"}'

# 4. 换产品同样写法：VPC，一次取多个字段
mcpx call CallCLI '{"command":"aliyun vpc describe-vpcs --biz-region-id cn-hangzhou --page-size 3","x_output_jmespath_filter":"Vpcs.Vpc[].{id: VpcId, cidr: CidrBlock}"}'

# 5. 换产品：RDS，切片只取前 3 条
mcpx call CallCLI '{"command":"aliyun rds describe-regions","x_output_jmespath_filter":"Regions.RDSRegion[0:3].RegionId"}'

# 6. 跨地域：换地域即可
mcpx call CallCLI '{"command":"aliyun ecs describe-instances --biz-region-id cn-beijing --page-size 2","x_output_jmespath_filter":"TotalCount"}'

# 7. 钉住 API 版本
mcpx call CallCLI '{"command":"aliyun ecs describe-regions --version 2014-05-26","x_output_jmespath_filter":"Regions.Region[0].RegionId"}'

# 8. 查可用区
mcpx call CallCLI '{"command":"aliyun ecs describe-zones --biz-region-id cn-hangzhou","x_output_jmespath_filter":"Zones.Zone[0:3].ZoneId"}'
```

When the command itself contains double quotes (array parameters, tag filters, etc.), pass
the JSON via `-` from stdin to avoid escaping. **Wrap an array parameter's JSON value in
single quotes**, so the outer layer uses a heredoc rather than `echo`:

```bash
# 9. 数组型参数：JSON 数组值外面要加单引号
mcpx call CallCLI - <<'EOF'
{"command":"aliyun ecs describe-instances --biz-region-id cn-hangzhou --instance-ids '[\"i-abc\",\"i-def\"]'","x_output_jmespath_filter":"TotalCount"}
EOF

# 10. 按标签过滤
mcpx call CallCLI - <<'EOF'
{"command":"aliyun ecs describe-instances --biz-region-id cn-hangzhou --tag Key=env Value=prod","x_output_jmespath_filter":"Instances.Instance[].InstanceId"}
EOF
```

On PowerShell, use a here-string instead; both `@'` and the closing `'@` must be at column
zero:

```powershell
# 9. 数组型参数：JSON 数组值外面要加单引号
@'
{"command":"aliyun ecs describe-instances --biz-region-id cn-hangzhou --instance-ids '[\"i-abc\",\"i-def\"]'","x_output_jmespath_filter":"TotalCount"}
'@ | mcpx call CallCLI -

# 10. 按标签过滤
@'
{"command":"aliyun ecs describe-instances --biz-region-id cn-hangzhou --tag Key=env Value=prod","x_output_jmespath_filter":"Instances.Instance[].InstanceId"}
'@ | mcpx call CallCLI -
```

If a jmespath key contains non-ASCII or other non-identifier characters, it **must be
double-quoted**: `{"总数": TotalCount}` works, `{总数: TotalCount}` errors.

## RunScript examples

The signature is fixed: `await call_cli(product=..., action=..., params=..., user_agent=UA)`.
None of these four kwargs may be omitted, and the final value is assigned to `result`. (These are
sandbox `call_cli` calls using API operation names, not `aliyun` CLI strings, so they keep
PascalCase action names.)

For every submitted script, replace the placeholders below with the current conversation's
real session ID and the current skill manifest's real version. Pass the resulting `UA` to
every `call_cli(..., user_agent=UA)` invocation; setting environment variables on the local
`mcpx.py` command does not inject them into the remote script.

```bash
# 1. 单次调用。无参数时 params 传空对象
mcpx call RunScript '{"script":"UA = \"AlibabaCloud-Agent-Skills/alibabacloud-mcp-connector/{session-id} skill-version/{skill-version}\"\nresult = await call_cli(product=\"Ecs\", action=\"DescribeRegions\", params={}, user_agent=UA)"}'
```

For a multi-line script, write it to a file first and wrap it into JSON — far more reliable
than piling up escapes on the command line:

```bash
# 2. 多次调用后汇总
cat > /tmp/s.py <<'PY'
UA = "AlibabaCloud-Agent-Skills/alibabacloud-mcp-connector/{session-id} skill-version/{skill-version}"
regions = await call_cli(product="Ecs", action="DescribeRegions", params={}, user_agent=UA)
zones = await call_cli(product="Ecs", action="DescribeZones",
                       params={"RegionId": "cn-hangzhou"}, user_agent=UA)
result = {"region_count": len(regions["Regions"]["Region"]),
          "hangzhou_zones": len(zones["Zones"]["Zone"])}
PY
uv run --python 3.11 scripts/to_json.py script /tmp/s.py | mcpx call RunScript -
```

```bash
# 3. 遍历多地域批量统计 —— RunScript 的主场，别用循环调 CallCLI
cat > /tmp/s.py <<'PY'
UA = "AlibabaCloud-Agent-Skills/alibabacloud-mcp-connector/{session-id} skill-version/{skill-version}"
summary = {}
for rid in ["cn-hangzhou", "cn-beijing", "cn-shanghai"]:
    resp = await call_cli(product="Ecs", action="DescribeInstances",
                          params={"RegionId": rid, "PageSize": 10}, user_agent=UA)
    summary[rid] = resp.get("TotalCount", 0)
result = summary
PY
uv run --python 3.11 scripts/to_json.py script /tmp/s.py | mcpx call RunScript -
```

```bash
# 4. 分页取全量
cat > /tmp/s.py <<'PY'
UA = "AlibabaCloud-Agent-Skills/alibabacloud-mcp-connector/{session-id} skill-version/{skill-version}"
page, items = 1, []
while True:
    resp = await call_cli(product="Ecs", action="DescribeInstances",
                          params={"RegionId": "cn-hangzhou",
                                  "PageNumber": page, "PageSize": 50},
                          user_agent=UA)
    batch = resp.get("Instances", {}).get("Instance", [])
    items.extend(batch)
    if len(batch) < 50:
        break
    page += 1
result = {"fetched": len(items)}
PY
uv run --python 3.11 scripts/to_json.py script /tmp/s.py | mcpx call RunScript -
```

```bash
# 5. 单个调用失败不中断整体：try/except 包住，用 str(exc) 取错误信息
cat > /tmp/s.py <<'PY'
UA = "AlibabaCloud-Agent-Skills/alibabacloud-mcp-connector/{session-id} skill-version/{skill-version}"
ok, errs = {}, {}
for rid in ["cn-hangzhou", "not-a-real-region"]:
    try:
        resp = await call_cli(product="Ecs", action="DescribeZones",
                              params={"RegionId": rid}, user_agent=UA)
        ok[rid] = len(resp["Zones"]["Zone"])
    except Exception as exc:
        errs[rid] = str(exc)[:120]
result = {"ok": ok, "errs": errs}
PY
uv run --python 3.11 scripts/to_json.py script /tmp/s.py | mcpx call RunScript -
```

```bash
# 6. 钉住 API 版本：version 是 call_cli 的 kwarg
cat > /tmp/s.py <<'PY'
UA = "AlibabaCloud-Agent-Skills/alibabacloud-mcp-connector/{session-id} skill-version/{skill-version}"
result = await call_cli(product="Ecs", action="DescribeRegions",
                        params={}, version="2014-05-26", user_agent=UA)
PY
uv run --python 3.11 scripts/to_json.py script /tmp/s.py | mcpx call RunScript -
```

Write operations must carry `costManifest`; the gateway prices the whole manifest before
executing:

```json
{"script": "...", "costManifest": {"steps": [
  {"product": "Ecs", "action": "RunInstances", "count": 2,
   "parameters": {"InstanceType": "ecs.g6.large", "InstanceChargeType": "PostPaid"}}]}}
```

## Other execution tools

```bash
mcpx call GetTask '{"processID":"proc_xxx","waitTimeoutSeconds":30}'

mcpx call RunIaC '{"action":"plan","code":"provider \"alicloud\" {\n  region = \"cn-hangzhou\"\n  configuration_source = \"AlibabaCloud-Agent-Skills/alibabacloud-mcp-connector/{session-id} skill-version/{skill-version}\"\n}\nresource \"alicloud_vpc\" \"v\" {\n  cidr_block = \"172.16.0.0/16\"\n}"}'

mcpx call GetPresignedUrl '{"requests":[{"operation":"upload","objectName":"bundle.zip"}]}'
```

## API discovery tools

```bash
mcpx call SearchApis '{"prompt":"list ECS instances","limit":3}'

mcpx call ListProducts '{"filter":"Ecs"}'

mcpx call ListApis '{"product":"Ecs","filter":"DescribeInstances"}'

mcpx call GetApiDefinition '{"product":"Ecs","apiName":"DescribeInstances","apiVersion":"2014-05-26"}'

mcpx call ListProductRegions '{"product":"Oss"}'

mcpx call GenerateCLICommand '{"product":"Ecs","apiName":"DescribeInstances","apiVersion":"2014-05-26","regionId":"cn-hangzhou"}'
```

## Documentation tools

```bash
mcpx call SearchDocuments '{"query":"ECS instance family","product":"ecs","limit":5}'

mcpx call GetDocument '{"doc_id":25378,"max_length":8000}'

mcpx call GetDocumentTree '{"product":"ecs","depth":2}'

mcpx call GrepDocuments '{"product":"oss","pattern":"lifecycle rule","limit":10}'
```
