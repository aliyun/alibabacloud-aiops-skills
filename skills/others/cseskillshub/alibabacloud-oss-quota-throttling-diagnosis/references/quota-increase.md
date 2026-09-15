# Quota Increase & Dedicated Resource Guidance

Process guidance ONLY - this skill never submits any application and
never changes any quota. Sources (fetched 2026-08-27):
- https://help.aliyun.com/zh/oss/user-guide/limits
- https://help.aliyun.com/zh/oss/user-guide/oss-resource-pool-qos

## 1. QPS limit increase (ticket path)

1. QPS limit increases are NOT self-service: the quota center has no OSS
   QPS entry. Submit a ticket instead.
2. Engineers evaluate the actual usage and decide whether (and by how
   much) the limit can be raised.
3. Before applying, eliminate avoidable pressure: prefix hash
   distribution, concurrency control, SDK retry/backoff
   (references/performance-guide.md) - these often recover more QPS than
   a raise grants.
4. What to include in the ticket: account UID, region, bucket name(s),
   measured peak QPS, time window, business justification.

## 2. Bandwidth increase (ticket path)

1. Bandwidth caps are per account per region (see
   references/throttling-rules.md sec.1). Higher needs are ticket-based:
   describe the required internal/public bandwidth, direction, duration
   (temporary spike vs. permanent), and the workload.
2. Temporary needs (benchmark/migration windows) can be requested as
   time-boxed raises - state the start/end dates explicitly.
3. Verify the real watermark first (console Usage Query > Basic Data or
   CloudMonitor); an increase request without utilization evidence is
   usually rejected or delayed.

## 3. Dedicated bandwidth: resource pool QoS

When multiple buckets in one region fight over the shared account
bandwidth, resource pool QoS provides threshold limits and
priority-guaranteed bandwidth.

1. Prerequisite (official): the account's bandwidth in that region must
   already reach 400 Gbps or more - below that, resource pool creation is
   not offered. Contact technical support / submit a ticket to apply.
2. The ticket should provide: region, resource pool name, bucket list,
   total/internal/public upload and download bandwidth for the pool,
   whether console access to the pool is needed, and the member buckets.
3. Constraints: buckets in one pool must share the same owner, the same
   region, and the same redundancy type; pool creation may involve data
   migration and resource reallocation.
4. After creation, buckets can be added to the pool from the OSS console
   (Resource Pool QoS page) by the customer.

QoS mechanics to explain when advising (official oss-resource-pool-qos doc):

- Two complementary modes: THRESHOLD throttling sets a hard bandwidth cap
  per object (bucket / BucketGroup / requester); PRIORITY throttling
  guarantees a minimum bandwidth per priority level (3-10 levels; a larger
  level number means higher priority).
- Threshold cap always wins: if a bucket has a priority floor of 80 Gbps
  but a threshold cap of 50 Gbps, its usable bandwidth is 50 Gbps.
- Multi-level limits apply together: the effective bandwidth is the MINIMUM
  of all active limits; the sum of lower-level budgets cannot exceed the
  upper level's budget.
- Requester is an INDEPENDENT throttling dimension (not part of the pool
  hierarchy): a RAM-user access is bounded by both the requester limit and
  the bucket limit, taking the minimum.
- Preemption: a higher priority level can preempt bandwidth beyond the
  guaranteed floor of lower levels; idle floors can be used by lower
  priorities, with higher priorities taking them first. The sum of all
  priority floors must be <= the pool total bandwidth.
- Bucket-level alarms can fire for the bucket, the bucket's requester, or
  the bucket group - when a ThresholdExceeded event appears, check all
  three levels before concluding which limit was hit.

## 4. What this skill does / does not do

| Action | This skill |
|---|---|
| Report official quota defaults of a region | YES (script output) |
| Attribute throttling symptoms | YES (decision tree) |
| Explain the ticket / resource-pool process | YES (this doc) |
| Submit a ticket or quota application | NEVER |
| Change any quota/QoS configuration | NEVER |
