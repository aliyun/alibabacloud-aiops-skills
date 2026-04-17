# Acceptance Criteria: Build AI Animation Story Creation App

**Scenario**: `Build AI Animation Story Creation App — Auto Deploy`
**Purpose**: Skill testing acceptance criteria

---

# Correct CLI Command Patterns

## 1. OSS — Product: `oss`

#### ✅ CORRECT
```bash
aliyun oss mb oss://my-animation-bucket --region cn-hangzhou --ua AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
aliyun oss stat oss://my-animation-bucket --ua AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
```

#### ❌ INCORRECT
```bash
# Wrong: using ossutil as separate command
ossutil mb oss://my-bucket
```

## 2. Devs — Product: `devs` (FC app template deployment)

#### ✅ CORRECT
```bash
# Create project (with template config, parameter names confirmed)
aliyun devs create-project --body '{"name":"my-project","spec":{"templateConfig":{"templateName":"animation-creation","parameters":{"region":"cn-hangzhou","bailian_api_key":"sk-xxx","ossBucket":"my-bucket"}}}}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy

# Render template (must pass namespace, otherwise functionName starts with "-" causing deployment failure)
aliyun devs render-services-by-template --template-name animation-creation --project-name my-project --variable-values '{"shared":{"namespace":"my-project"}}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy

# Update environment (must use --body; --spec cannot correctly handle deeply nested JSON; must include roleArn; only comfyui and web services)
aliyun devs update-environment --project-name my-project --name production --body '{"name":"production","spec":{"roleArn":"acs:ram::123456:role/aliyundevscustomrole","stagedConfigs":{"services":{"comfyui":{...},"web":{...}}}}}' --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy

# Trigger deployment
aliyun devs deploy-environment --project-name my-project --name production --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy

# Query environment details
aliyun devs get-environment --project-name my-project --name production --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
```

#### ❌ INCORRECT
```bash
# Wrong: using fc create-function instead of devs template (this solution requires template deployment)
aliyun fc create-function --function-name my-func --runtime python3.10 --handler index.handler

# Wrong: using old fc-open product
aliyun fc-open create-function --service-name svc --function-name func

# Wrong: using variableValues instead of parameters for template variables
aliyun devs create-project --body '{"name":"my-project","spec":{"templateConfig":{"templateName":"animation-creation","variableValues":{"bailian_api_key":{"value":"sk-xxx"}}}}}'

# Wrong: wrong parameter names (bucketName instead of ossBucket, dashScopeApiKey instead of bailian_api_key)
aliyun devs create-project --body '{"name":"my-project","spec":{"templateConfig":{"templateName":"animation-creation","parameters":{"bucketName":"my-bucket","dashScopeApiKey":"sk-xxx"}}}}'

# Wrong: putting custom-domain service in UpdateEnvironment (causes "Unknown service type" error)
aliyun devs update-environment --spec '{"stagedConfigs":{"services":{"comfyui":{...},"web":{...},"custom-domain":{...}}}}'

# Wrong: missing roleArn in UpdateEnvironment
aliyun devs update-environment --spec '{"stagedConfigs":{"services":{"comfyui":{...},"web":{...}}}}'

# Wrong: using --spec instead of --body for UpdateEnvironment (deep-nested JSON gets corrupted)
aliyun devs update-environment --spec '{"roleArn":"...","stagedConfigs":{"services":{...}}}'

# Wrong: not passing namespace to render-services-by-template (functionName becomes "-comfyui", fails FC naming rule)
aliyun devs render-services-by-template --template-name animation-creation --project-name my-project

# Wrong: expecting CreateProject to auto-deploy (it only creates project + empty environment)
# Must follow up with render → update-environment → deploy-environment
```

## 3. FC Custom Domain — Product: `fc`

#### ✅ CORRECT
```bash
# Get domain verification token (use --data-urlencode)
curl -s --connect-timeout 10 --max-time 30 -A AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy -X POST "https://domain.devsapp.net/token" \
  --data-urlencode "type=fc" --data-urlencode "user=<UID>" \
  --data-urlencode "region=cn-hangzhou" --data-urlencode "service=fcv3" \
  --data-urlencode "function=<ProjectName>-web"

# Helper function uses FC 2.0 API (fc-open)
aliyun fc-open create-service --body '{"serviceName":"serverless-devs-check"}' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
aliyun fc-open create-function --service-name serverless-devs-check --body '<JSON>' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy

# Create FC custom domain
aliyun fc create-custom-domain --body '{"domainName":"<DOMAIN>","protocol":"HTTP","routeConfig":{"routes":[...]}}' --region cn-hangzhou --user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy
```

#### ❌ INCORRECT
```bash
# Wrong: using FC trigger URL as access URL (adds Content-Disposition: attachment, browser downloads instead of rendering)
# https://<func>.cn-hangzhou.fcapp.run is NOT a valid application URL

# Wrong: using FC 3.0 API for helper function (function name with $ not supported)
aliyun fc create-function --function-name "serverless-devs-check$domain<TOKEN>" ...

# Wrong: using -F instead of --data-urlencode for curl (causes "failed to change user ID" error)
curl -X POST "https://domain.devsapp.net/token" -F "user=<UID>" ...

# Wrong: not cleaning up helper function after domain creation
# Must delete trigger, function, and service from serverless-devs-check after domain is registered
```

---

# Key Validation Points

1. Template parameters are passed via `parameters`, **not** `variableValues`
2. Confirmed template parameter names: `region` (fixed `cn-hangzhou`), `bailian_api_key`, `ossBucket`
3. FC application is deployed via Devs API, **not** `aliyun fc create-function`
4. Template name is `animation-creation`
5. DashScope API Key — auto-created via `aliyun modelstudio create-api-key` (requires `list-workspaces` first to get workspace-id)
6. OSS Bucket creation uses `aliyun oss mb`
7. `UpdateEnvironment` must include `roleArn` (format: `acs:ram::<UID>:role/aliyundevscustomrole`)
8. `UpdateEnvironment` services **must NOT include `custom-domain`** (only `comfyui` and `web`)
9. `UpdateEnvironment` **must use `--body`**, not `--spec` (CLI cannot correctly serialize deeply nested JSON)
10. `render-services-by-template` **must pass `--variable-values '{"shared":{"namespace":"<ProjectName>"}}'`**, otherwise function names start with `-`
11. Full deployment chain: CreateProject → RenderServicesByTemplate → UpdateEnvironment → DeployEnvironment → GetEnvironment polling → Create custom domain
12. Deployment status is queried via `aliyun devs get-environment`, waiting for both `comfyui` and `web` `latestDeployment.phase` to be `"Finished"`
13. FC trigger URL (`*.fcapp.run`) cannot be used as the application URL (forces `Content-Disposition: attachment`) — a custom domain must be created
14. Custom domain is registered via the devsapp.net community DNS service + FC `CreateCustomDomain` API
15. Helper function must use FC 2.0 API (`aliyun fc-open`) — FC 3.0 does not support `$` in function names
16. Domain format: `<ProjectName>-web.fcv3.<UID>.cn-hangzhou.fc.devsapp.net`
17. Access URL is the custom domain `http://<DOMAIN>/` (HTTP protocol)
18. All `aliyun` CLI commands must include User-Agent: OSS commands use `--ua AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy`, all others use `--user-agent AlibabaCloud-Agent-Skills/alibabacloud-tech-solution-animation-creation-auto-deploy`
