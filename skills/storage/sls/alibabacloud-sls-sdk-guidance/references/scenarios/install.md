# Install SLS SDKs

Route installation questions to the appropriate SDK `index.md` based on the user's ecosystem or package manager.

## Package Manager Mapping

| Ecosystem | SDKs | Install reference |
| --- | --- | --- |
| Maven / Gradle | Java SDK, Java Producer, Java Consumer, Log4j Appender, Log4j2 Appender, Logback Appender, Android SDK | See each SDK's [index](../sdks/) under `references/sdks/` |
| pip | Python SDK | [aliyun-log-python-sdk](../sdks/aliyun-log-python-sdk/index.md) |
| go get | Go SDK | [aliyun-log-go-sdk](../sdks/aliyun-log-go-sdk/index.md) |
| Composer | PHP SDK | [aliyun-log-php-sdk](../sdks/aliyun-log-php-sdk/index.md) |
| npm / yarn / pnpm | Node.js SDK | [aliyun-log-nodejs-sdk](../sdks/aliyun-log-nodejs-sdk/index.md) |
| dotnet / NuGet | .NET Core SDK | [aliyun-log-dotnetcore-sdk](../sdks/aliyun-log-dotnetcore-sdk/index.md) |
| Cargo | Rust SDK | [aliyun-log-rust-sdk](../sdks/aliyun-log-rust-sdk/index.md) |
| CocoaPods | iOS SDK | [aliyun-log-ios-sdk](../sdks/aliyun-log-ios-sdk/index.md) |
| source build | C SDK, C++ SDK | [aliyun-log-c-sdk](../sdks/aliyun-log-c-sdk/index.md), [aliyun-log-cpp-sdk](../sdks/aliyun-log-cpp-sdk/index.md) |
| Maven | SLS OpenAPI Java SDK | [alibabacloud-sls-java-sdk](../sdks/alibabacloud-sls-java-sdk/index.md) |
| go get | SLS OpenAPI Go SDK | [alibabacloud-sls-go-sdk](../sdks/alibabacloud-sls-go-sdk/index.md) |
| pip | SLS OpenAPI Python SDK | [alibabacloud-sls-python-sdk](../sdks/alibabacloud-sls-python-sdk/index.md) |
| Composer | SLS OpenAPI PHP SDK | [alibabacloud-sls-php-sdk](../sdks/alibabacloud-sls-php-sdk/index.md) |
| dotnet / NuGet | SLS OpenAPI .NET SDK | [alibabacloud-sls-dotnet-sdk](../sdks/alibabacloud-sls-dotnet-sdk/index.md) |
| npm | SLS OpenAPI Node.js SDK | [alibabacloud-sls-nodejs-sdk](../sdks/alibabacloud-sls-nodejs-sdk/index.md) |

## Quick Links by SDK

| SDK | Install reference |
| --- | --- |
| aliyun-log-java-sdk | [index](../sdks/aliyun-log-java-sdk/index.md) |
| aliyun-log-python-sdk | [index](../sdks/aliyun-log-python-sdk/index.md) |
| aliyun-log-go-sdk | [index](../sdks/aliyun-log-go-sdk/index.md) |
| aliyun-log-php-sdk | [index](../sdks/aliyun-log-php-sdk/index.md) |
| aliyun-log-nodejs-sdk | [index](../sdks/aliyun-log-nodejs-sdk/index.md) |
| aliyun-log-dotnetcore-sdk | [index](../sdks/aliyun-log-dotnetcore-sdk/index.md) |
| aliyun-log-cpp-sdk | [index](../sdks/aliyun-log-cpp-sdk/index.md) |
| aliyun-log-rust-sdk | [index](../sdks/aliyun-log-rust-sdk/index.md) |
| aliyun-log-c-sdk | [index](../sdks/aliyun-log-c-sdk/index.md) |
| aliyun-log-ios-sdk | [index](../sdks/aliyun-log-ios-sdk/index.md) |
| aliyun-log-android-sdk | [index](../sdks/aliyun-log-android-sdk/index.md) |
| aliyun-log-java-producer | [index](../sdks/aliyun-log-java-producer/index.md) |
| aliyun-log-consumer-java | [index](../sdks/aliyun-log-consumer-java/index.md) |
| aliyun-log-log4j-appender | [index](../sdks/aliyun-log-log4j-appender/index.md) |
| aliyun-log-log4j2-appender | [index](../sdks/aliyun-log-log4j2-appender/index.md) |
| aliyun-log-logback-appender | [index](../sdks/aliyun-log-logback-appender/index.md) |
| alibabacloud-sls-java-sdk | [index](../sdks/alibabacloud-sls-java-sdk/index.md) |
| alibabacloud-sls-go-sdk | [index](../sdks/alibabacloud-sls-go-sdk/index.md) |
| alibabacloud-sls-python-sdk | [index](../sdks/alibabacloud-sls-python-sdk/index.md) |
| alibabacloud-sls-php-sdk | [index](../sdks/alibabacloud-sls-php-sdk/index.md) |
| alibabacloud-sls-dotnet-sdk | [index](../sdks/alibabacloud-sls-dotnet-sdk/index.md) |
| alibabacloud-sls-nodejs-sdk | [index](../sdks/alibabacloud-sls-nodejs-sdk/index.md) |

## Notes

- For Maven / Gradle SDKs, always use version property placeholders. Do not invent exact versions. Tell users to check Maven Central or use `mvn versions:display-dependency-updates`.
- For source-build SDKs (C, C++), recommend pinning a specific commit or tag for production use.
- For CocoaPods (iOS), omit version constraints by default and mention committing `Podfile.lock` for reproducibility.
