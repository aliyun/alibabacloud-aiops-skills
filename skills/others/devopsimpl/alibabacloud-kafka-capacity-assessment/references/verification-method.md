# Verification Method — Kafka Capacity Assessment Skill

## Step-Level Verification

### Step 2 Verification: Instance Metadata Retrieved Successfully

**Verification command:**

```bash
aliyun alikafka get-instance-list --biz-region-id <RegionId> --instance-id <InstanceId>
```

**Success criteria:**
- The response contains the target instance's information
- The `Series` and `SpecType` fields can be extracted from the response
- For v2 instances: `IoMaxWrite`, `IoMaxRead`, and `DiskSize` fields are present
- For v3 instances: `ReservedPublishCapacity` and `ReservedSubscribeCapacity` fields are present

**Failure handling:**
- If the response returns an empty list: verify that the RegionId and InstanceId are correct
- If a permission error is returned: consult `references/ram-policies.md` to verify the required permissions

### Step 4 Verification: CloudMonitor Data Retrieved Successfully

**Verification command:**

```bash
aliyun cms describe-metric-list \
  --namespace acs_kafka \
  --metric-name <MetricName> \
  --period 60 \
  --start-time "<start time>" \
  --end-time "<end time>" \
  --dimensions '[{"instanceId":"<InstanceId>"}]'
```

**Success criteria:**
- The `Datapoints` field in the response is non-empty
- The data point timestamps cover the incident time range specified by the user
- Each data point contains `Minimum`, `Average`, and `Maximum` aggregated values

**Failure handling:**
- If `Datapoints` is empty: verify the time range, Namespace, MetricName, and Dimensions
- If the MetricName is incorrect: confirm the instance series (v2 / v3) and use the corresponding metric name
- If a time format error occurs: use the `YYYY-MM-DD HH:mm:ss` format

### Step 5 Verification: Diagnostic Report Completeness

**Success criteria:**
- The report contains all five sections: Basic Information, Incident Summary, Monitoring Data Analysis, Diagnostic Conclusion, and Upgrade Recommendations
- Each metric in the Monitoring Data Analysis table has values filled in for: observed value, specification limit, utilization / threshold exceeded, and conclusion
- The Upgrade Recommendations section specifies the exact metrics to scale up and the recommended target values
- The action path points to the correct console page

## Overall Verification Checklist

| Check Item | Pass Criteria |
|:---|:---|
| Instance metadata retrieval | Successfully obtained instance Series, SpecType, and key specification parameters |
| Metric-to-series alignment | v2 instances use only V2-suffixed metrics; v3 instances use only V3-suffixed metrics |
| Bottleneck determination logic | v2: utilization approaching 100% indicates a bottleneck; v3: exceeding elastic ceiling (> 100%) or ThrottleTime > 0 indicates throttling |
| Upgrade recommendation validity | Recommended values are derived from actual business traffic analysis, not arbitrarily assigned |
| Read-only operations confirmed | No write-operation API calls were made throughout the entire workflow |
