# aliyun-log-python-sdk

## Summary

Python SDK for Alibaba Cloud SLS. Full API coverage via `LogClient`: write (`put_logs`), query (`get_logs`), resource management (Project / Logstore / index / machine group), and a managed Consumer Group. The go-to choice for Python scripts, automation, and data-processing jobs.

- Package: `aliyun-log-python-sdk` (pip)
- Language / Platform: Python 2.7+ / 3.7+ (also PyPy)

## Repository

- GitHub: https://github.com/aliyun/aliyun-log-python-sdk
- API reference: http://aliyun-log-python-sdk.readthedocs.io/api.html

## Official Docs

- Overview: https://help.aliyun.com/zh/sls/developer-reference/sdk-for-python/
- Install: https://help.aliyun.com/zh/sls/developer-reference/install-the-log-service-python-sdk
- Quick Start: https://help.aliyun.com/zh/sls/developer-reference/get-started-with-log-service-sdk-for-python

## Install

```bash
pip install -U aliyun-log-python-sdk
```

## Quick Start

```python
import os
from aliyun.log import LogClient

client = LogClient("cn-hangzhou.log.aliyuncs.com",
                   os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"],
                   os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"])
```

## Capability

| Capability | Ref |
| --- | --- |
| Write — Basic / batch (`put_logs`) | [write-logs](write-logs.md) |
| Consume logs (managed Consumer Group) | [consume-logs](consume-logs.md) |
| Query logs (`get_logs`) | inline |
| Manage resources | inline |
