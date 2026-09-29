# Corrected-Call Templates (both versions, all channels)

After the offending parameter is located, return the **corrected call in the same channel and version the
customer used**. Never switch channels on them, and never change the version unless the version itself was the
root cause (then say so explicitly).

Placeholders in `<...>` are user-specific and must be confirmed with the customer — do not invent values.

## A. CLI plugin mode (most common)

### WAF 3.0 (2021-10-01, the plugin default)
```bash
# Read-only example
aliyun waf-openapi describe-instance --biz-region-id <cn-hangzhou|ap-southeast-1> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-openapi-error-diagnosis/<session-id> skill-version/<skill-version>"

# A parameterized call (Rules is a JSON *string*)
aliyun waf-openapi create-defense-rule --biz-region-id <region> --instance-id <instance_id> \
  --template-id <template_id> --defense-scene <scene> --rules '<json-string>'
```

### WAF 2.0 (2019-09-10, MUST pass `--api-version`)
```bash
aliyun waf-openapi describe-instance-info --api-version 2019-09-10 --biz-region-id <region> \
  --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-waf-openapi-error-diagnosis/<session-id> skill-version/<skill-version>"

# create-domain: IsAccessProduct is an INTEGER (0/1); ports/IPs are JSON list strings
aliyun waf-openapi create-domain --api-version 2019-09-10 \
  --instance-id <instance_id> --domain <www.example.com> --biz-region-id <region> \
  --is-access-product <0|1> --source-ips '["<origin_ip>"]' --http-port '[80]'
```

CLI rules that fix the most errors:
- Flags are **lowercase-hyphen** (`--instance-id`, not `--InstanceId`).
- The region flag is **`--biz-region-id`** (the plugin renames `RegionId`), not `--region-id`.
- WAF 2.0 actions **require `--api-version 2019-09-10`**.
- Add and invoke `--cli-dry-run` only when the customer explicitly requests verification; otherwise omit it.

## B. Python Common SDK (RPC style)

```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
from alibabacloud_openapi_util.client import Client as OpenApiUtilClient
from alibabacloud_credentials.client import Client as CredentialClient
import os

SKILL_NAME = 'alibabacloud-waf-openapi-error-diagnosis'
SESSION_ID = os.environ.get('SKILL_SESSION_ID', '')
SKILL_VERSION = os.environ.get('SKILL_VERSION', '')   # injected by the Agent at runtime (see SKILL.md Observability)
ua = f'AlibabaCloud-Agent-Skills/{SKILL_NAME}' + (f'/{SESSION_ID}' if SESSION_ID else '') \
     + (f' skill-version/{SKILL_VERSION}' if SKILL_VERSION else '')

config = open_api_models.Config(
    credential=CredentialClient(),                 # never hardcode AK/SK
    endpoint='wafopenapi.<region>.aliyuncs.com',   # e.g. cn-hangzhou / ap-southeast-1
    user_agent=ua,
)
client = OpenApiClient(config)

params = open_api_models.Params(
    action='<Action>',                 # PascalCase, e.g. CreateDefenseRule
    version='<2021-10-01|2019-09-10>', # MUST match the WAF generation
    protocol='HTTPS', method='POST', auth_type='AK', style='RPC',
    pathname='/', req_body_type='json', body_type='json',
)

queries = {
    'RegionId': '<cn-hangzhou|ap-southeast-1>',   # PascalCase API names, NOT CLI flags
    'InstanceId': '<instance_id>',
    # nested / array params use dot + index notation:
    # 'Rules.1.RuleName': '<name>',
}
request = open_api_models.OpenApiRequest(query=OpenApiUtilClient.query(queries))
resp = client.call_api(params, util_models.RuntimeOptions())
print(resp.get('statusCode'), resp.get('body'))
```

SDK rules that fix the most errors:
- `version` must equal the action's generation — a WAF 2.0 action with `version='2021-10-01'` fails.
- Query keys are **PascalCase API names** (`RegionId`), not CLI flags (`--biz-region-id`).
- Nested/array params use `Parent.N.Child` dot-index notation, flattened by `OpenApiUtilClient.query`.
- Endpoint host is `wafopenapi.<region>.aliyuncs.com`; confirm the region matches `RegionId`.

## C. Raw RPC / OpenAPI portal

Query string with PascalCase params plus the common request params:
```
Action=<Action>&Version=<2021-10-01|2019-09-10>&RegionId=<region>&InstanceId=<instance_id>&...
```
- `Version` must match the action's generation.
- Boolean-ish WAF 2.0 fields are integers (`IsAccessProduct=1`).
- List fields are JSON strings or `HttpPort.1=80&HttpPort.2=443` indexed form.

## Assembling the corrected call

1. Start from the customer's original call — change **only** what the diff flagged.
2. Apply every finding (version, name/style, required, type, enum, format, region, notation, dependency).
3. Keep placeholders for values you do not have; ask, do not fabricate.
4. Invoke `--cli-dry-run` only when the customer explicitly asks for verification; otherwise omit it.
5. State, in one line, **which parameter was wrong and why**, then show the corrected call.
