# DTS API Allowlist

Read this document before calling the DTS service, and execute only an API that matches the user's request.

## General rules

Use DTS API `2020-01-01`. Do not require or reject a DTS plugin version. Standard plugin commands and flags use kebab case. Use only the command and flag formats documented by this Skill; if the CLI rejects one, stop because the command is incompatible and do not guess an alternative argument.

## Allowed APIs

| Class | API | Purpose |
| --- | --- | --- |
| Read-only | `DescribeDtsJobDetail` | Query one job |
| Read-only | `DescribeDtsJobs` | List jobs, locate a job by name, or verify a purchase |
| Read-only | `DescribePreCheckStatus` | Query precheck only, with `JobCode=01` |
| Read-only | `DescribeDtsInstancePrice` | Query prices through `dtscli job price` |
| Read-only | `DescribeInstances` | Resolve an instance ID from an instance name through `dtscli job instances` so a job can be configured; never call it directly |
| Database connection test before purchase | `RunEndpointLinkTest` | Test whether the source and destination databases can be reached from the compiled plan through `dtscli job create test`; never call it directly |
| Management | `CreateDtsInstance` | Purchase the synchronization instance |
| Management | `ConfigureDtsJob` | Configure the purchased instance |
| Management | `ModifyDtsJobName` | Rename a job |
| Management | `StartDtsJob` | Start or resume |
| Management | `SuspendDtsJob` | Suspend while retaining the instance |

## Invocation boundary

Only `dtscli` may call the reviewed generic RPCs. Do not bypass `dtscli` to invoke another API, preview-execution path, unsupported engine, link, or access method, and do not read the same data through another product interface such as the MongoDB or DDS `DescribeDBInstances`.

## Input and output boundary

Do not ask the user to paste raw CLI output. Accept only non-sensitive resource identifiers (`DtsJobId`, `DtsInstanceId`, `RequestId`) or redacted error information. Obtain values available through an allowlisted read-only query yourself.
