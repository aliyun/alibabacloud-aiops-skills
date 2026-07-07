# Query Logs

Recommend SDKs for querying / searching logs in Alibaba Cloud SLS.

## SDK Routing by Runtime

| Runtime | Recommended ref |
| --- | --- |
| Java | [aliyun-log-java-sdk index](../sdks/aliyun-log-java-sdk/index.md) |
| Python | [aliyun-log-python-sdk index](../sdks/aliyun-log-python-sdk/index.md) |
| Go | [aliyun-log-go-sdk index](../sdks/aliyun-log-go-sdk/index.md) |
| Node.js | [aliyun-log-nodejs-sdk index](../sdks/aliyun-log-nodejs-sdk/index.md) |
| .NET | [aliyun-log-dotnetcore-sdk index](../sdks/aliyun-log-dotnetcore-sdk/index.md) |
| Rust | [aliyun-log-rust-sdk index](../sdks/aliyun-log-rust-sdk/index.md) |
| PHP | [aliyun-log-php-sdk index](../sdks/aliyun-log-php-sdk/index.md) |
| C++ | [aliyun-log-cpp-sdk index](../sdks/aliyun-log-cpp-sdk/index.md) |
| Java (OpenAPI) | [alibabacloud-sls-java-sdk index](../sdks/alibabacloud-sls-java-sdk/index.md) |
| Go (OpenAPI) | [alibabacloud-sls-go-sdk index](../sdks/alibabacloud-sls-go-sdk/index.md) |
| Python (OpenAPI) | [alibabacloud-sls-python-sdk index](../sdks/alibabacloud-sls-python-sdk/index.md) |
| PHP (OpenAPI) | [alibabacloud-sls-php-sdk index](../sdks/alibabacloud-sls-php-sdk/index.md) |
| .NET (OpenAPI) | [alibabacloud-sls-dotnet-sdk index](../sdks/alibabacloud-sls-dotnet-sdk/index.md) |
| Node.js (OpenAPI) | [alibabacloud-sls-nodejs-sdk index](../sdks/alibabacloud-sls-nodejs-sdk/index.md) |

## Selection Guidance

- Use the language SDK that matches the user's runtime.
- Producer, Consumer, Appender, and mobile SDKs do **not** support log query operations.
- For query examples (GetLogs, GetHistograms, SQL analytics), refer to each SDK's `query-logs.md` when available, or the SDK's `index.md`.
- For advanced query patterns (pagination, SQL-based paging), refer to the SDK's `query-logs.md`.
