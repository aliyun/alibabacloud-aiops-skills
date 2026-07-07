# aliyun-log-rust-sdk

## Summary

Rust SDK for Alibaba Cloud SLS. Async client for writing and querying logs and basic resource operations.

- Package: `aliyun-log-rust-sdk` (crates.io)
- Language / Platform: Rust

## Repository

- GitHub: https://github.com/aliyun/aliyun-log-rust-sdk
- API docs: https://docs.rs/aliyun-log-rust-sdk/0.3.0/aliyun_log_rust_sdk/struct.Client.html

## Install

```bash
cargo add aliyun-log-rust-sdk
```

## Quick Start

```rust
use aliyun_log_rust_sdk::{Client, Config, FromConfig};

let config = Config::builder()
    .endpoint("cn-hangzhou.log.aliyuncs.com")
    .access_key(
        &std::env::var("ALIBABA_CLOUD_ACCESS_KEY_ID").unwrap(),
        &std::env::var("ALIBABA_CLOUD_ACCESS_KEY_SECRET").unwrap(),
    )
    .build()?;
let client = Client::from_config(config)?;
```

> Full examples (write / query / manage): see the `examples/` directory in the repo.

## Capability

| Capability | Ref |
| --- | --- |
| Write — Basic / batch (PutLogs / PostLogStoreLogs) | GitHub `examples/` |
| Query logs | GitHub `examples/` |
| Manage resources | GitHub `examples/` |
