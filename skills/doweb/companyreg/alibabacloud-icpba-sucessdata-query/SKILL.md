---
name: alibabacloud-icpba-sucessdata-query
description: |
  Alibaba Cloud ICP Filing Success Data Query Skill. Use for querying ICP filing success information including entity, website, app details and risk alerts after successful filing.
  Triggers: "ICP filing query", "beian query", "filing information", "filing risk", "query filing success", "备案查询", "备案信息", "备案风险".
---

# Alibaba Cloud ICP Filing Success Data Query

## Scenario Description

After successfully completing ICP filing (beian) on Alibaba Cloud, customers need to:
1. Login to the filing system to view their filing success information
2. Query filing details including entity information, website information, and APP information
3. Check if there are any risks associated with their filing that need attention

This skill enables automated querying of ICP filing success data and associated risk information through Alibaba Cloud APIs.

**Architecture**: Alibaba Cloud Beian Service → QuerySuccessIcpData API → Filing Information (Entity + Websites + APPs + Risks)

---

## Installation

### Alibaba Cloud CLI

This skill requires Aliyun CLI version >= 3.3.3.

**Pre-check: Aliyun CLI >= 3.3.3 required**
> Run `aliyun version` to verify >= 3.3.3. If not installed or version too low,
> run `curl -fsSL https://aliyuncli.alicdn.com/setup.sh | bash` to install/update,
> or see `references/cli-installation-guide.md` for installation instructions.

**Pre-check: Aliyun CLI plugin update required**
> [MUST] run `aliyun configure set --auto-plugin-install true` to enable automatic plugin installation.
> [MUST] run `aliyun plugin update` to ensure that any existing plugins are always up-to-date.

### Python Dependencies

Since the CLI command is not yet available in the current plugin version, this skill uses the Python Common SDK:

```bash
pip install -r scripts/requirements.txt
```

---

## Authentication

> **Pre-check: Alibaba Cloud Credentials Required**
>
> **Security Rules:**
> - **NEVER** read, echo, or print AK/SK values (e.g., `echo $ALIBABA_CLOUD_ACCESS_KEY_ID` is FORBIDDEN)
> - **NEVER** ask the user to input AK/SK directly in the conversation or command line
> - **NEVER** use `aliyun configure set` with literal credential values
> - **ONLY** use `aliyun configure list` to check credential status
>
> ```bash
> aliyun configure list
> ```
> Check the output for a valid profile (AK, STS, or OAuth identity).
>
> **If no valid profile exists, STOP here.**
> 1. Obtain credentials from [Alibaba Cloud Console](https://ram.console.aliyun.com/manage/ak)
> 2. Configure credentials **outside of this session** (via `aliyun configure` in terminal or environment variables in shell profile)
> 3. Return and re-run after `aliyun configure list` shows a valid profile

---

## RAM Policy

This skill requires the `beian:QuerySuccessIcpData` permission. For the complete RAM policy JSON and configuration instructions, see [references/ram-policies.md](references/ram-policies.md).

> **[MUST] Permission Failure Handling:** When any command or API call fails due to permission errors at any point during execution, follow this process:
> 1. Read `references/ram-policies.md` to get the full list of permissions required by this SKILL
> 2. Use `ram-permission-diagnose` skill to guide the user through requesting the necessary permissions
> 3. Pause and wait until the user confirms that the required permissions have been granted

---

## Parameter Confirmation

> **IMPORTANT: Parameter Confirmation** — Before executing any command or API call,
> ALL user-customizable parameters (e.g., RegionId, instance names, CIDR blocks,
> passwords, domain names, resource specifications, etc.) MUST be confirmed with the
> user. Do NOT assume or use default values without explicit user approval.

| Parameter Name | Required/Optional | Description | Default Value |
|----------------|-------------------|-------------|---------------|
| Caller | Required | Caller identifier for API request | `skill` (fixed value) |
| Region | Optional | Alibaba Cloud region | `cn-hangzhou` |

---

## Core Workflow

> At the **start** of the Core Workflow (before any CLI invocation):
> **[MUST] Enable AI-Mode** — AI-mode is required for Agent Skill execution.
> Run the following commands before any CLI invocation:
> ```bash
> aliyun configure ai-mode enable
> aliyun configure ai-mode set-user-agent --user-agent "AlibabaCloud-Agent-Skills/alibabacloud-icpba-sucessdata-query"
> ```

### Step 1: Query ICP Filing Success Data

Since the CLI command `aliyun companyreg query-success-icp-data` is not yet available in the current plugin version, we'll use the Python Common SDK to call the API directly.

Create a Python script to query the filing data:

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_tea_util import models as util_models
import json

def create_client() -> OpenApiClient:
    """
    Create an OpenAPI client with credential authentication.
    """
    credential = CredentialClient()

    config = open_api_models.Config(
        credential=credential,
        endpoint='companyreg.aliyuncs.com',
        region_id='cn-hangzhou',
        user_agent='AlibabaCloud-Agent-Skills/alibabacloud-icpba-sucessdata-query'
    )

    return OpenApiClient(config)

def query_success_icp_data(caller: str = 'skill') -> dict:
    """
    Query ICP filing success data including entity, website, app, and risk information.

    Args:
        caller: Caller identifier (fixed value: 'skill')

    Returns:
        dict: Filing success data response
    """
    client = create_client()

    params = open_api_models.Params(
        action='QuerySuccessIcpData',
        version='2026-04-23',
        protocol='HTTPS',
        method='POST',
        auth_type='AK',
        style='RPC',
        pathname='/',
        req_body_type='formData',
        body_type='json'
    )

    queries = {
        'Caller': caller
    }

    request = open_api_models.OpenApiRequest(
        query=queries
    )

    runtime = util_models.RuntimeOptions(
        connect_timeout=5000,
        read_timeout=10000
    )

    try:
        response = client.call_api(params, request, runtime)
        return response.get('body', {})
    except Exception as e:
        print(f"Error querying ICP filing data: {str(e)}")
        raise

def main():
    print("Querying ICP Filing Success Data...")
    print("=" * 60)

    # Query filing data
    result = query_success_icp_data(caller='skill')

    # Print formatted result
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Parse and display summary
    if result.get('Success'):
        ba_list = result.get('BaSuccessDataWithRiskList', [])
        print("\n" + "=" * 60)
        print(f"Total Filing Records: {len(ba_list)}")

        for idx, ba_data in enumerate(ba_list, 1):
            print(f"\n--- Filing Record {idx} ---")
            print(f"ICP Number: {ba_data.get('IcpNumber')}")
            print(f"Entity Name: {ba_data.get('OrganizersName')}")
            print(f"Entity Type: {ba_data.get('OrganizersNature')}")
            print(f"Responsible Person: {ba_data.get('ResponsiblePersonName')}")

            # Website information
            websites = ba_data.get('WebsiteList', [])
            print(f"\nWebsites: {len(websites)}")
            for site in websites:
                print(f"  - {site.get('SiteName')} ({site.get('SiteRecordNum')})")
                print(f"    Domains: {', '.join(site.get('DomainList', []))}")

            # APP information
            apps = ba_data.get('AppList', [])
            if apps:
                print(f"\nAPPs: {len(apps)}")
                for app in apps:
                    print(f"  - {app.get('AppName')} ({app.get('AppRecordNum')})")
                    print(f"    Domains: {', '.join(app.get('DomainList', []))}")

            # Risk information
            risks = ba_data.get('RiskList', [])
            if risks:
                print(f"\n⚠️ Risks: {len(risks)}")
                for risk in risks:
                    print(f"  Deadline: {risk.get('DeadLine')}")
                    for detail in risk.get('RiskDetailList', []):
                        print(f"  Source: {detail.get('RiskSource')}")
                        for suggest in detail.get('rectifySuggest', []):
                            print(f"  Suggestion: {suggest}")
    else:
        print("Query failed or returned no data.")

if __name__ == '__main__':
    main()
```

Save this script as `query_icp_filing.py` and run:

```bash
python3 query_icp_filing.py
```

### Step 2: Analyze Results

The API returns the following information structure:

1. **Entity Information (主体信息)**:
   - ICP Number (备案号)
   - Entity Name (主体名称)
   - Entity Type (主体性质: 企业/个人)
   - Responsible Person (负责人)

2. **Website Information (网站信息)**:
   - Site Record Number (网站备案号)
   - Site Name (网站名称)
   - Domain List (域名列表)
   - Responsible Person (网站负责人)

3. **APP Information (APP信息)**:
   - APP Record Number (APP备案号)
   - APP Name (APP名称)
   - Domain List (域名列表)
   - Responsible Person (APP负责人)

4. **Risk Information (风险信息)**:
   - Deadline (处理截止日期)
   - Risk Source (风险来源)
   - Rectify Suggestions (整改建议)

### Example Response Data

**Example 1: Filing with Entity, Websites, and Risks**

```json
{
  "RequestId": "79732597-AB14-1341-9131-D94F48D1AFD7",
  "Success": true,
  "BaSuccessDataWithRiskList": [
    {
      "IcpNumber": "粤ICP测50000001号",
      "OrganizersName": "深圳市星澜美容有限公司变更",
      "OrganizersNature": "企业",
      "ResponsiblePersonName": "于婷",
      "WebsiteList": [
        {
          "SiteRecordNum": "粤ICP测50000001号-1",
          "DomainList": ["13011160846019.com"],
          "SiteName": "于婷广东",
          "ResponsiblePersonName": "于婷"
        },
        {
          "SiteRecordNum": "津ICP备2023010907号-1",
          "DomainList": ["uijikoxjsu.com"],
          "SiteName": "920企业变更网站001",
          "ResponsiblePersonName": "于婷"
        }
      ],
      "AppList": [],
      "RiskList": [
        {
          "DeadLine": "2026年04月28日0点",
          "RiskDetailList": [
            {
              "RiskSource": "网站/APP信息 - 津ICP备2023010907号-1 - 网站域名 - uijikoxjsu.com",
              "rectifySuggest": [
                "<span style=\"font-weight:bold;\">网站内容涉及金融业务</span>,请提交<span style=\"font-weight:bold; color: red;\">变更备案</span>上传有效期内的金融前置文件许可,牌照或批文,传到备案系统,或者修改网站内容,与备案主体一致,符合最新备案规则。"
              ]
            }
          ]
        }
      ]
    }
  ]
}
```

**Example 2: Filing with Entity, Websites, and APPs**

```json
{
  "RequestId": "E36C463A-0869-1318-A851-84C53711984A",
  "Success": true,
  "BaSuccessDataWithRiskList": [
    {
      "IcpNumber": "测BA20251231094500051号",
      "OrganizersName": "LXtest001变更测试",
      "OrganizersNature": "企业",
      "ResponsiblePersonName": "李四",
      "WebsiteList": [
        {
          "SiteRecordNum": "测BA20251231094500051号-1",
          "DomainList": ["lxtest001.com"],
          "SiteName": "测试迁移使用11111111111111111111",
          "ResponsiblePersonName": "张三"
        },
        {
          "SiteRecordNum": "测BA20251230112600098号-2",
          "DomainList": ["test89876868.com"],
          "SiteName": "测试test111",
          "ResponsiblePersonName": "张三"
        }
      ],
      "AppList": [
        {
          "AppRecordNum": "测BA20251231094500051号-2",
          "DomainList": ["lxtest002.com"],
          "AppName": "测试测试11",
          "ResponsiblePersonName": "李四"
        }
      ],
      "RiskList": []
    }
  ]
}
```

> **[MUST] Disable AI-Mode at EVERY exit point** — Before delivering the final response for ANY reason, always disable AI-mode first. This applies to ALL exit paths: workflow success, workflow failure, error/exception, user cancellation, session end, or any other scenario where no further CLI commands will be executed.
> AI-mode is only used for Agent Skill invocation scenarios and MUST NOT remain enabled after the skill stops running.
> ```bash
> aliyun configure ai-mode disable
> ```

---

## Success Verification Method

To verify the query was successful:

1. Check the `Success` field in the response is `true`
2. Verify `BaSuccessDataWithRiskList` contains filing records
3. Confirm each record has:
   - Valid `IcpNumber`
   - Entity information (`OrganizersName`, `OrganizersNature`)
   - At least one website in `WebsiteList` or one app in `AppList`

For detailed verification steps, see [references/verification-method.md](references/verification-method.md).

---

## Cleanup

This is a read-only query operation with no resources to clean up.

---

## Best Practices

1. **Regular Monitoring**: Query filing data regularly to stay informed of any new risks
2. **Risk Response**: When risks are identified, respond before the deadline to avoid filing cancellation
3. **Data Consistency**: Ensure website/APP content matches the filed information to prevent risks
4. **Permission Management**: Use RAM policies to grant minimal required permissions
5. **Error Handling**: Implement proper error handling and retry logic for API calls
6. **Credential Security**: Never hardcode credentials; always use environment variables or credential files
7. **Response Parsing**: Handle both scenarios where AppList or RiskList may be empty arrays
8. **HTML Content**: Be aware that risk suggestions may contain HTML tags for formatting

---

## Reference Links

| Reference | Description |
|-----------|-------------|
| [references/ram-policies.md](references/ram-policies.md) | Detailed RAM permission requirements |
| [references/related-commands.md](references/related-commands.md) | All related CLI commands and SDK methods |
| [references/verification-method.md](references/verification-method.md) | Detailed verification steps |
| [references/cli-installation-guide.md](references/cli-installation-guide.md) | Alibaba Cloud CLI installation guide |
| [references/common-sdk-usage.md](references/common-sdk-usage.md) | Python Common SDK usage patterns |
| [references/error-handling.md](references/error-handling.md) | Common errors and solutions |
