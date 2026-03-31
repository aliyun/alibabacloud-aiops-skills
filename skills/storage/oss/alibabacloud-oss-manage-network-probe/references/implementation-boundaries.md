# Implementation Boundaries: alibabacloud-oss-manage-network-probe

## Overview

This skill centers on `aliyun ossutil probe` and uses the Alibaba Cloud CLI to perform OSS network diagnostics.
However, there are clear boundaries: some capabilities are composite client-side behaviors, and some can only detect issues but cannot auto-fix them.

## Supported with Aliyun CLI

| Item | CLI/Code Status | Notes |
| --- | --- | --- |
| `aliyun ossutil probe --upload ... --user-agent AlibabaCloud-Agent-Skills` | Supported | Tests local-to-OSS link status via upload or temporary object |
| `aliyun ossutil probe --download ... --user-agent AlibabaCloud-Agent-Skills` | Supported | Supports URL download probe or Bucket/Object download probe |
| `aliyun ossutil probe --probe-item upload-speed ... --user-agent AlibabaCloud-Agent-Skills` | Supported | Outputs upload bandwidth and suggested concurrency |
| `aliyun ossutil probe --probe-item download-speed ... --user-agent AlibabaCloud-Agent-Skills` | Supported | Outputs download bandwidth and suggested concurrency |
| `aliyun ossutil probe --probe-item download-time ... --user-agent AlibabaCloud-Agent-Skills` | Supported | Outputs download time and throughput statistics |
| `aliyun ossutil probe --probe-item cycle-symlink ... --user-agent AlibabaCloud-Agent-Skills` | Supported for detection only | Local symlink anomaly detection only |
| `aliyun ossutil presign ... --user-agent AlibabaCloud-Agent-Skills` | Supported | Generates presigned URL for private object download probe |
| `aliyun ossutil cp ... --user-agent AlibabaCloud-Agent-Skills` | Supported | Prepares test objects for `download-speed` |


## Not a Single OpenAPI Primitive

| Item | Status | Why it matters |
| --- | --- | --- |
| `probe` | Not a single OpenAPI | There is no `aliyun oss api probe`; `probe` is a composite client-side diagnostic command in ossutil |
| `cycle-symlink` | Local-only logic | Detection occurs on the local filesystem, not via an OSS remote API |
| `--addr` network probing | Partially environment-dependent | Affected by local DNS, ICMP policies, proxies, and corporate network policies; failure does not necessarily indicate an OSS issue |

## Steps That Cannot Be Fully Automated Safely

| Item | CLI/Code Status | Reason |
| --- | --- | --- |
| Auto-fix abnormal symlinks | Not safely supported | Requires knowledge of the correct target path and business intent; cannot be safely guessed |
| Auto-determine root cause of all network issues | Partially supported | `probe` provides symptoms, throughput, and logs, but manual analysis of the network environment is still needed |
| Construct a `download-speed` test object without an existing object or local file | Not purely CLI-only | `download-speed` requires an existing object; if none is available, the user must confirm an existing object path or provide a local file to upload via `aliyun ossutil cp` |
| Auto-decide whether to retain test objects or local downloaded files | Requires user confirmation | This affects user data and cleanup strategy; confirmation is required first |

## Practical Guidance

1. If the user only needs link diagnostics, do not force creation of persistent objects; prefer using `probe`'s temporary object capability.
2. If the user wants to test `download-speed`, prefer asking the user to confirm an existing object larger than 5 MiB.
3. If `--addr` detection fails but OSS upload/download succeeds, do not conclude an OSS failure; suggest checking local network, proxy, DNS, and security policies.
4. If `cycle-symlink` detects anomalies, only report the abnormal paths and impact; do not auto-rewrite link targets.
5. If the user requests "implement everything via code", clarify that this scenario is covered by `ossutil` integrated with the Alibaba Cloud CLI, and there is no standalone OSS OpenAPI `probe` that can replace this command.
