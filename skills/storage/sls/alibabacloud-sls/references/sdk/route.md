# SLS SDK Route

This is the primary routing document for Alibaba Cloud SLS (Simple Log Service) / Aliyun Log SDK guidance.

## Intent Routing

| User asks about | Reference |
| --- | --- |
| install, dependency, Maven, Gradle, pip, npm, Go module, NuGet, CocoaPods, Composer, build from source | [install](scenarios/install.md) |
| write logs, put logs, producer, appender, mobile logs, client logs, ingestion | [write-logs](scenarios/write-logs.md) |
| consume logs, LogHub, consumer group, checkpoint, shard allocation, cursor consumption | [consume-logs](scenarios/consume-logs.md) |
| PullLogs, GetCursor, BatchGetLogs, manual cursor-based reads | [Cursor-based reads](scenarios/consume-logs.md#sdk-routing-by-situation) |
| query logs, search logs, SQL, GetLogs, histogram | [query-logs](scenarios/query-logs.md) |
| Project, Logstore, index, dashboard or alert management through an SDK | [SDK selection](#selection-rules) |

## SDK Capability Matrix

| SDK | Type | Language / Platform | Install | Write | Consumer library | Query | Best For | Ref |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| aliyun-log-java-sdk | language-sdk | Java | yes | yes | see consumer-java | yes | Java general SLS REST API operations, resource management, query, basic write | [index](sdks/aliyun-log-java-sdk/index.md) |
| aliyun-log-python-sdk | language-sdk | Python | yes | yes | yes | yes | Python scripts, automation, processing jobs, service integration | [index](sdks/aliyun-log-python-sdk/index.md) |
| aliyun-log-go-sdk | language-sdk-plus-producer-consumer | Go | yes | yes | yes | yes | Go API usage, Producer Library, Consumer Library | [index](sdks/aliyun-log-go-sdk/index.md) |
| aliyun-log-php-sdk | language-sdk | PHP | yes | yes | no | yes | PHP API integration, protobuf/compressed log submit, batch submit | [index](sdks/aliyun-log-php-sdk/index.md) |
| aliyun-log-nodejs-sdk | language-sdk | Node.js | yes | yes | no | yes | Node.js Client, query, index and log operations | [index](sdks/aliyun-log-nodejs-sdk/index.md) |
| aliyun-log-dotnetcore-sdk | language-sdk | .NET | yes | yes | no | yes | .NET Core / .NET Standard SLS REST API access | [index](sdks/aliyun-log-dotnetcore-sdk/index.md) |
| aliyun-log-cpp-sdk | language-sdk | C++ | source build | yes | no | yes | C++ application integration, indexed search and SQL | [index](sdks/aliyun-log-cpp-sdk/index.md) |
| aliyun-log-rust-sdk | language-sdk | Rust | yes | yes | no | yes | Rust services and tools for write and query | [index](sdks/aliyun-log-rust-sdk/index.md) |
| aliyun-log-c-sdk | producer | C / embedded Linux | source build | yes | no | no | Lightweight C Producer, embedded Linux, high-performance collection | [index](sdks/aliyun-log-c-sdk/index.md) |
| aliyun-log-ios-sdk | mobile-producer | iOS | yes | yes | no | no | iOS client log ingestion | [index](sdks/aliyun-log-ios-sdk/index.md) |
| aliyun-log-android-sdk | mobile-producer | Android | yes | yes | no | no | Android client log ingestion | [index](sdks/aliyun-log-android-sdk/index.md) |
| aliyun-log-java-producer | producer | Java | yes | yes | no | no | Java high-throughput async batch writes | [index](sdks/aliyun-log-java-producer/index.md) |
| aliyun-log-consumer-java | consumer | Java | yes | no | yes | no | Java Consumer Group, shard assignment, checkpoint, load balancing | [index](sdks/aliyun-log-consumer-java/index.md) |
| aliyun-log-log4j-appender | appender | Java / Log4j | yes | yes | no | no | Existing Log4j application log ingestion | [index](sdks/aliyun-log-log4j-appender/index.md) |
| aliyun-log-log4j2-appender | appender | Java / Log4j2 | yes | yes | no | no | Existing Log4j2 application log ingestion | [index](sdks/aliyun-log-log4j2-appender/index.md) |
| aliyun-log-logback-appender | appender | Java / Logback | yes | yes | no | no | Existing Logback application log ingestion | [index](sdks/aliyun-log-logback-appender/index.md) |
| alibabacloud-sls-java-sdk | openapi-sdk | Java | yes | yes | no | yes | Java resource management, query (OpenAPI, newer evolution) | [index](sdks/alibabacloud-sls-java-sdk/index.md) |
| alibabacloud-sls-go-sdk | openapi-sdk | Go | yes | yes | no | yes | Go resource management, query (OpenAPI, newer evolution) | [index](sdks/alibabacloud-sls-go-sdk/index.md) |
| alibabacloud-sls-python-sdk | openapi-sdk | Python | yes | yes | no | yes | Python resource management, query (OpenAPI, newer evolution) | [index](sdks/alibabacloud-sls-python-sdk/index.md) |
| alibabacloud-sls-php-sdk | openapi-sdk | PHP | yes | yes | no | yes | PHP resource management, query (OpenAPI, newer evolution) | [index](sdks/alibabacloud-sls-php-sdk/index.md) |
| alibabacloud-sls-dotnet-sdk | openapi-sdk | .NET | yes | yes | no | yes | .NET resource management, query (OpenAPI, newer evolution) | [index](sdks/alibabacloud-sls-dotnet-sdk/index.md) |
| alibabacloud-sls-nodejs-sdk | openapi-sdk | Node.js | yes | yes | no | yes | Node.js resource management, query (OpenAPI, newer evolution) | [index](sdks/alibabacloud-sls-nodejs-sdk/index.md) |

## Selection Rules

### By scenario — alibabacloud (OpenAPI) vs aliyun SDK

| Scenario | Priority | Reason |
| --- | --- | --- |
| Write logs | 1. Producer (`aliyun-log-java-producer`, Go/Python SDK built-in Producer, C/iOS/Android Producer) 2. aliyun language SDK (`aliyun-log-*-sdk`) | Producer libraries provide async batching, retry and compression; language SDKs also offer direct write APIs. |
| Consume logs (Consumer Group) | 1. Consumer (`aliyun-log-consumer-java`, Go/Python SDK built-in Consumer) | Consumer libraries handle shard assignment, checkpoints and load balancing. |
| Cursor-based reads | 1. aliyun language SDK (`aliyun-log-*-sdk`) | Useful for manual shard/cursor control. API names and availability vary by package; OpenAPI SDKs also expose cursor and pull APIs. |
| Query logs | 1. alibabacloud OpenAPI SDK or aliyun language SDK (both work) | Both families support queries; method names and response types vary by package. |
| Resource management (Project, Logstore, index, dashboard, alert, etc.) | 1. alibabacloud OpenAPI SDK (`alibabacloud-sls-*-sdk`) 2. aliyun language SDK | OpenAPI SDK has full, auto-generated API coverage and is the newer evolution direction. Language SDK covers common APIs but may lag behind on newer resources. |

For SDK-based index management, see [index configuration](../index/index-configuration.md#top-level-parameters)
for field types and settings, or [generation from log samples](../index/generate-index-from-logs.md)
for inferred configurations.

### Language-specific rules

- **Java write**: prefer `aliyun-log-java-producer` for high-throughput. For existing Log4j / Log4j2 / Logback apps, prefer the matching Appender.
- **Java consume**: prefer `aliyun-log-consumer-java`.
- **Go**: start with `aliyun-log-go-sdk` — it bundles API SDK + Producer + Consumer in one module.
- **Python**: `aliyun-log-python-sdk` covers write + consume + query + management. `alibabacloud-sls-python-sdk` is another option for queries and resource management (Python 3 only).
- **iOS / Android**: prefer the corresponding mobile Producer SDK.
- **Embedded Linux / C**: prefer `aliyun-log-c-sdk`.
- Do not recommend Producer/Appender SDKs for query, resource management, or consuming logs unless their documentation explicitly supports it.
