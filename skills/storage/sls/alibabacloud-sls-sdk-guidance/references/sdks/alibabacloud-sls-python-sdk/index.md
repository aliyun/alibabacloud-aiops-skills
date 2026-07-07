# alibabacloud-sls-python-sdk (OpenAPI)

## Summary

Alibaba Cloud OpenAPI SDK for SLS (Python). Auto-generated from API metadata — full, consistent API coverage for resource management (Project, Logstore, index, machine group, dashboard, alert, etc.) and log query. This is the newer OpenAPI evolution direction; for log writing and consumption, use the dedicated Python SDK.

- Package: `alibabacloud_sls20201230` (pip)
- Language / Platform: Python

## Repository

- GitHub: https://github.com/aliyun/alibabacloud-python-sdk (mono-repo, `sls-20201230` module)

## Official Docs

- OpenAPI overview: https://help.aliyun.com/zh/sls/developer-reference/api-overview
- API list: https://next.api.aliyun.com/document/Sls/2020-12-30/overview
- Per-API doc: `https://next.api.aliyun.com/document/Sls/2020-12-30/<ApiName>` (e.g. `CreateProject`, `GetLogsV2`)
- Online debugging & sample code: `https://next.api.aliyun.com/api/Sls/2020-12-30/<ApiName>?sdkStyle=dara&tab=DEMO&lang=PYTHON`

## Install

```bash
pip install -U alibabacloud_sls20201230 alibabacloud_credentials
```

## Quick Start

```python
import os, time
from alibabacloud_sls20201230.client import Client
from alibabacloud_sls20201230 import models
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_credentials.models import Config as CredentialConfig
from alibabacloud_tea_openapi.models import Config

credential_config = CredentialConfig(
    type="access_key",
    access_key_id=os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_ID"),
    access_key_secret=os.environ.get("ALIBABA_CLOUD_ACCESS_KEY_SECRET"),
)
credential = CredentialClient(credential_config)

config = Config(credential=credential)
config.endpoint = "cn-hangzhou.log.aliyuncs.com"
client = Client(config)

now = int(time.time())
request = models.GetLogsV2Request(
    query="*",
    line=100,
    offset=0,
    from_=now - 3600,
    to=now,
)
response = client.get_logs_v2("your_project", "your_logstore", request)
print(response.body)
```

## Capability

| Capability | Ref |
| --- | --- |
| Query logs (`get_logs_v2`) | inline |
| Manage resources | inline |

## Notes

- For log writing (`put_logs`) and consumption (Consumer Group), use [aliyun-log-python-sdk](../aliyun-log-python-sdk/index.md).
- Python parameter `from_` (trailing underscore) avoids conflict with the `from` keyword.
- Python 3 only. For Python 2 support, use [aliyun-log-python-sdk](../aliyun-log-python-sdk/index.md).
- Compared to `aliyun-log-python-sdk`, this OpenAPI SDK has broader resource-management API coverage and is the recommended path for new resource-management integrations.
