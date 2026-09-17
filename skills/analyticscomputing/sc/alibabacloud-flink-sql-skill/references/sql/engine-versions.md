# VVR Engine Versions

## Version Labels

| Label | Meaning | Recommendation |
|-------|---------|----------------|
| **Recommend** | The latest Minor Version under the current Major Version | Preferred for new SQL jobs |
| **Stable** | The latest Minor Version still supported under the previous Major Version | Suitable for production SQL jobs that prioritize stability |
| **Normal** | Another Minor Version still within its support period | Use only when required by a Connector, SQL syntax, or State compatibility |
| **EOS (Deprecated)** | A version past its end-of-service date | Migrate to a supported version |

Before selecting or changing an engine version, verify current labels and the compatibility matrix in online documentation.

## Region Considerations

- Confirm that the target region provides the selected SQL engine version and required Connectors.
- Place an SQL job close to its upstream Sources and downstream Sinks when possible to reduce network latency.
- Before upgrading a stateful SQL job, check State compatibility and create a Savepoint when required.

## Official Documentation

- [Engine Versions](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/engine-version)
- [Version Lifecycle Policy](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/lifecycle-policies)
- [Release Notes](https://help.aliyun.com/zh/flink/realtime-flink/product-overview/release-notes/)
