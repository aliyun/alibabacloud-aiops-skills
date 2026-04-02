# User-Agent Configuration for Non-CLI Invocation Methods

All calls to Alibaba Cloud services must carry unified identifier `AlibabaCloud-Agent-Skills` for platform source tracking and problem diagnosis.

## Python SDK (Tea / Common SDK)

```python
from alibabacloud_tea_openapi.client import Client as OpenApiClient
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models

credential = CredentialClient()
config = open_api_models.Config(credential=credential)
config.endpoint = 'emr.cn-hangzhou.aliyuncs.com'
config.user_agent = 'AlibabaCloud-Agent-Skills'
client = OpenApiClient(config)
```

> **Note**: Must use `CredentialClient` for authentication, never hardcode AccessKey/SecretKey in code.

## Python SDK (Product-specific SDK)

```python
from alibabacloud_emr20210320.client import Client as Emr20210320Client
from alibabacloud_credentials.client import Client as CredentialClient
from alibabacloud_tea_openapi import models as open_api_models

credential = CredentialClient()
config = open_api_models.Config(credential=credential)
config.endpoint = 'emr.cn-hangzhou.aliyuncs.com'
config.user_agent = 'AlibabaCloud-Agent-Skills'
client = Emr20210320Client(config)
```

## Terraform

```hcl
provider "alicloud" {
  region               = "cn-hangzhou"
  configuration_source = "AlibabaCloud-Agent-Skills"
}
```
