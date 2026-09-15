# Performance Optimization Guide

Manual guidance only - this skill never applies any change. All advice
follows the official OSS performance best practices (source:
https://help.aliyun.com/zh/oss/user-guide/oss-performance-best-practices/,
fetched 2026-08-27).

## 1. Prefix hash distribution (anti-hotspot)

OSS partitions data by the UTF-8 order of object keys. Sequential prefixes
(timestamps, alphabetical ids) pile requests onto one partition that
sustains about 2,000 req/s. Fix options:

- Hex hash prefix: prepend a 4-char MD5 hash of a high-cardinality field,
  e.g. `bucket/9b11/2024-07-19/customer-1/file1`. 4 hex chars give 65,536
  possible slots; size the hash width to your request rate / 2,000.
- Reverse timestamp keys: `bucket/5421000613151.log` instead of
  `bucket/1513160001245.log` - the fast-changing low digits lead.
- Listing by date still works: list the bucket prefix in batches
  (ListObjects) and merge results for the target date.

## 2. Concurrency control & horizontal scaling

- Scale parallel requests across threads/instances to saturate the
  available bandwidth; OSS has no connection-count limit per bucket.
- Measure first: start from one request, watch CPU/network to find the
  bottleneck, then raise concurrency (e.g. 10% CPU per request ~ 10
  concurrent requests).
- Reduce concurrency immediately when throttle-family 503s appear; the
  quota is account+region scoped, so several heavy buckets compete.

## 3. Multipart & range transfer

- Large objects (> 100 MB): multipart upload / parallel part download, or
  HTTP Range requests to fetch byte ranges in parallel and survive
  unstable links.
- Multipart keeps single-connection stalls from wasting the bandwidth
  budget and enables part-level retry.

## 4. Retry with exponential backoff

- Management-plane 503s (MetaOperationQpsLimitExceeded): delay a few
  seconds and retry.
- General pattern: retry after 2s, then 4s, then stop; for many
  heterogeneous requests, retry the slowest 5%; for fixed-size requests,
  retry the slowest 1%.
- Latest OSS SDKs embed 503 retry handling, optimized transfer
  management, and multi-threading - prefer upgrading the SDK.

## 5. Offload and placement

- Hot public read traffic: put CDN in front (raise cache TTL, preheat
  popular objects) to lower origin bandwidth pressure.
- Same-region clients on Alibaba Cloud should use the internal endpoint
  (lower latency, no public traffic charge).
- Distant/cross-border access slowness is a link problem, not throttling;
  transfer acceleration selection belongs to the dedicated
  transfer-acceleration skill.
- Deploy clients and buckets in the same region whenever possible.
