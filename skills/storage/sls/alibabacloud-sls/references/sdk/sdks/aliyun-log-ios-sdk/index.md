# aliyun-log-ios-sdk

## Summary

iOS client-side log Producer for Alibaba Cloud SLS. Batches, compresses (lz4), caches, and asynchronously uploads logs. Objective-C and Swift. Companion libraries add crash / block / network-quality / Trace collection.

- Package: `AliyunLogProducer` (CocoaPods)
- Language / Platform: iOS, Objective-C / Swift

## Repository

- GitHub: https://github.com/aliyun/aliyun-log-ios-sdk

## Official Docs

- Overview: https://help.aliyun.com/zh/sls/developer-reference/overview-of-log-service-sdk-for-ios
- Install: https://help.aliyun.com/zh/sls/developer-reference/install-log-service-sdk-for-ios
- Quick Start: https://help.aliyun.com/zh/sls/developer-reference/get-started-with-log-service-sdk-for-ios

## Install

```ruby
# Podfile
pod 'AliyunLogProducer', '~> 4.3.4'
```

```bash
pod install --repo-update
```

## Quick Start

```objc
LogProducerConfig *config = [[LogProducerConfig alloc]
    initWithEndpoint:@"cn-hangzhou.log.aliyuncs.com"
    project:@"your_project"
    logstore:@"your_logstore"];
// Prefer STS tokens on mobile — see Notes.
// For quick testing only:
[config setAccessKeyId:[[[NSProcessInfo processInfo] environment] objectForKey:@"ALIBABA_CLOUD_ACCESS_KEY_ID"]];
[config setAccessKeySecret:[[[NSProcessInfo processInfo] environment] objectForKey:@"ALIBABA_CLOUD_ACCESS_KEY_SECRET"]];

LogProducerClient *client = [[LogProducerClient alloc]
    initWithLogProducerConfig:config callback:nil];
```

## Capability

| Capability | Ref |
| --- | --- |
| Write — Producer (high-perf, auto-batch + auto-retry) | [write-logs](write-logs.md) |

## Notes

- Auth on mobile: prefer STS (`ResetSecurityToken`) or the mobile log direct-transfer service; avoid shipping a static AccessKey.
- Companion libraries (Core, OT/OTSwift, CrashReporter, NetworkDiagnosis, Trace) enable mobile APM / RUM — see the Overview doc.
