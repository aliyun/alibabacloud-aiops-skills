# Write Logs — aliyun-log-python-sdk

## Overview

Use the Python SDK's `LogClient.put_logs` for direct, synchronous batch writes. Each call sends one `PutLogsRequest` containing a list of `LogItem`s.

- Docs: https://help.aliyun.com/zh/sls/developer-reference/get-started-with-log-service-sdk-for-python
- API reference: http://aliyun-log-python-sdk.readthedocs.io/api.html
- Tests / examples: https://github.com/aliyun/aliyun-log-python-sdk/tree/master/tests

## Basic Write Example

```python
import os, time
from aliyun.log import LogClient, LogItem, PutLogsRequest

client = LogClient(
    "cn-hangzhou.log.aliyuncs.com",
    os.environ["ALIBABA_CLOUD_ACCESS_KEY_ID"],
    os.environ["ALIBABA_CLOUD_ACCESS_KEY_SECRET"])

item = LogItem()
item.set_time(int(time.time()))
item.set_contents([("level", "INFO"), ("message", "Application started")])

req = PutLogsRequest("your_project", "your_logstore", "", "", [item])
client.put_logs(req)
```

## Batch Write

```python
items = []
for i in range(100):
    item = LogItem()
    item.set_time(int(time.time()))
    item.set_contents([("level", "INFO"), ("message", f"Event {i}")])
    items.append(item)

req = PutLogsRequest("your_project", "your_logstore", "", "", items)
client.put_logs(req)
```

## Notes

- `put_logs` sends one batch per call — accumulate `LogItem` entries for bulk writes.
- `topic` and `source` parameters (3rd and 4th args) help organize and filter logs in queries.
- For STS token authentication, pass `securityToken` to `LogClient`.
- The Python SDK does not have a built-in Producer library — for high-throughput async writes from Python, consider the CLI (`aliyun-log-cli`) or batching in application code.
