# Credentials Configuration

This document describes how to configure access credentials for the `tablestore-agent-storage` SDK using the Alibaba Cloud Credentials tool and the default credential chain.

## Prerequisites

Install the Credentials tool:

```bash
pip install alibabacloud_credentials
```

> See the latest version at [alibabacloud-credentials · PyPI](https://pypi.org/project/alibabacloud-credentials/).

---

## Using the Default Credential Chain (Recommended)

When no configuration parameters are passed to the Credentials client, it will automatically look up credentials from the **default credential chain** in the following order. If none are found, a `CredentialException` is raised.

### Lookup Order

#### 1. Environment Variables

If the following environment variables are set and non-empty, they will be used as default credentials:

- `ALIBABA_CLOUD_ACCESS_KEY_ID` + `ALIBABA_CLOUD_ACCESS_KEY_SECRET` → AK credential
- `ALIBABA_CLOUD_ACCESS_KEY_ID` + `ALIBABA_CLOUD_ACCESS_KEY_SECRET` + `ALIBABA_CLOUD_SECURITY_TOKEN` → STS Token credential

#### 2. OIDC RAM Role

If the following environment variables are all set and non-empty, the Credentials tool will call the STS `AssumeRoleWithOIDC` API to obtain an STS Token:

- `ALIBABA_CLOUD_ROLE_ARN`
- `ALIBABA_CLOUD_OIDC_PROVIDER_ARN`
- `ALIBABA_CLOUD_OIDC_TOKEN_FILE`

#### 3. Configuration File

> Requires `alibabacloud_credentials` >= 1.0rc3.

The Credentials tool will try to load `config.json` from the default path:

| OS | Default Path |
|----|-------------|
| Linux / macOS | `~/.aliyun/config.json` |
| Windows | `C:\Users\USER_NAME\.aliyun\config.json` |

You can configure this file using the [Aliyun CLI](https://help.aliyun.com/zh/cli/), or create it manually. Supported modes:

| Mode | Description |
|------|-------------|
| `AK` | Use AccessKey ID and AccessKey Secret |
| `StsToken` | Use static STS Token |
| `RamRoleArn` | Assume a RAM role via AK to get STS Token (auto-refresh) |
| `EcsRamRole` | Get credentials from ECS instance metadata |
| `OIDC` | Use OIDC provider to get STS Token |
| `ChainableRamRoleArn` | Chain role assumption from another profile |

Example `config.json`:

```json
{
  "current": "default",
  "profiles": [
    {
      "name": "default",
      "mode": "RamRoleArn",
      "access_key_id": "<ALIBABA_CLOUD_ACCESS_KEY_ID>",
      "access_key_secret": "<ALIBABA_CLOUD_ACCESS_KEY_SECRET>",
      "ram_role_arn": "<ROLE_ARN>",
      "ram_session_name": "<ROLE_SESSION_NAME>",
      "expired_seconds": 3600
    }
  ]
}
```

> You can select a specific profile by setting the environment variable `ALIBABA_CLOUD_PROFILE`.

#### 4. ECS Instance RAM Role

If the application runs on an ECS or ECI instance with an attached RAM role, the Credentials tool will obtain the STS Token via instance metadata. This supports auto-refresh.

- Set `ALIBABA_CLOUD_ECS_METADATA` to specify the RAM role name (reduces lookup time)
- Set `ALIBABA_CLOUD_ECS_METADATA_DISABLED=true` to disable this method

#### 5. Credentials URI

If the environment variable `ALIBABA_CLOUD_CREDENTIALS_URI` is set and points to a valid URI, the Credentials tool will fetch the STS Token from that URI.

---

## Code Example: Using Default Credential Chain

```python
from alibabacloud_credentials.client import Client as CredentialClient

# No configuration parameters — uses the default credential chain
credentials_client = CredentialClient()
credential = credentials_client.get_credential()

access_key_id = credential.get_access_key_id()
access_key_secret = credential.get_access_key_secret()
security_token = credential.get_security_token()
```

### Using with tablestore-agent-storage SDK

```python
import json
from alibabacloud_credentials.client import Client as CredentialClient
from tablestore_agent_storage import AgentStorageClient

# Get credentials via default credential chain
credentials_client = CredentialClient()
credential = credentials_client.get_credential()

config = json.load(open("tablestore_agent_storage/ots_kb_config.json", "r"))

client = AgentStorageClient(
    access_key_id=credential.get_access_key_id(),
    access_key_secret=credential.get_access_key_secret(),
    sts_token=credential.get_security_token(),
    ots_endpoint=config["ots_endpoint"],
    ots_instance_name=config["ots_instance_name"]
)
```

---

## Security Best Practices

- **Never hardcode** AccessKey ID / Secret in source code
- **Prefer temporary credentials** (STS Token) over long-lived AK/SK
- Use **environment variables** or **config files** to manage credentials
- Use **RamRoleArn** mode for automatic STS Token refresh
- For ECS/ECI workloads, use **instance RAM roles** for zero-config credential management

---

## References

- [Alibaba Cloud Credentials Tool (Python)](https://help.aliyun.com/zh/sdk/developer-reference/v2-manage-python-access-credentials)
- [Aliyun CLI Configuration](https://help.aliyun.com/zh/cli/configure-credentials)
- [alibabacloud-credentials on PyPI](https://pypi.org/project/alibabacloud-credentials/)
