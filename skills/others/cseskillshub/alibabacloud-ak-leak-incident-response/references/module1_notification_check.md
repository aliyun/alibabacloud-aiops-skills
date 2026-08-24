# Module 1: Notification Verification

## Purpose
Confirm the AK leakage alert through public Alibaba Cloud APIs before launching the full investigation. This step validates that the reported incident is genuine and extracts the leaked AK from official alerts.

## Step 1.1: Query Security Center for AK Leak Detection

### API — Security Center DescribeAccesskeyLeakList

The **Security Center** `DescribeAccesskeyLeakList` API returns AK leak detection alerts that Security Center has identified through GitHub/Gitee scanning and abnormal usage pattern detection.

**Product**: `sas` (Security Center) — endpoint `tds.{region}.aliyuncs.com`, API version `2018-12-03`.

### Authentication

All calls go through the dual-backend layer in `scripts/_cli.py`: the **aliyun CLI is preferred**, with a direct **V3-signed HTTPS fallback** when the CLI is absent. No product SDK is used. Credentials are resolved by the active backend — CLI profile (`~/.aliyun/config.json`), or env `ALIBABA_CLOUD_ACCESS_KEY_ID` / `ALIBABA_CLOUD_ACCESS_KEY_SECRET` (+ optional `ALIBABA_CLOUD_SECURITY_TOKEN`) for the HTTP fallback.

### Request Parameters

| Parameter | Value | Description |
|-----------|-------|-------------|
| `CurrentPage` | `1` | Page number |
| `PageSize` | `100` | Page size (max 100) |
| `Query` | (optional) | Filter by AccessKey, e.g. `ak:<AK>` |

### Example Code

```python
body = _cli.call("sas", "DescribeAccesskeyLeakList",
                 {"CurrentPage": 1, "PageSize": 100, "Query": "ak:<AK>"},
                 region=region, profile=profile)
records = body.get("AccessKeyLeakList") or []
total = body.get("TotalCount", 0)
```

### Response Shape

Records are under `AccessKeyLeakList` with `TotalCount` total (verified against the live API):

```json
{
  "TotalCount": 1,
  "AkLeakCount": 1,
  "CurrentPage": 1,
  "PageSize": 100,
  "RequestId": "...",
  "AccessKeyLeakList": [
    {
      "Id": 123456,
      "AccesskeyId": "<AK>",
      "Type": "AK_TYPE",
      "Status": "dealt",
      "DealTime": "2026-06-03T10:00:00Z",
      "Url": "https://github.com/..."
    }
  ]
}
```

When Security Center has not flagged the AK, this returns `TotalCount: 0` with an empty `AccessKeyLeakList` (see Behavior Notes). The `Id` field feeds `DescribeAccessKeyLeakDetail` in Step 1.2.

### Behavior Notes

- `DescribeAccesskeyLeakList` is callable with a standard credential and returns HTTP 200. An empty list (`TotalCount: 0`) simply means Security Center has not flagged any leak for this account.
- An empty list is treated as `alert_detected = False`; the script proceeds with the user-provided AK.
- `NoPermission` / `Forbidden` is only a defensive fallback — it indicates the calling credential's RAM policy lacks `yundun-aegis:DescribeAccesskeyLeakList` (note: the RAM authorization action uses the `yundun-aegis:` prefix, not `sas:`, even though the product/CLI name is `sas`). If it occurs, the script gracefully proceeds with the user-provided AK.

## Step 1.2: Leak Detail & Handling (dual-backend)

Two more Security Center APIs are integrated in `scripts/query_notification.py`. All calls go through the dual-backend layer (`_cli.call`, aliyun CLI preferred / V3-signed HTTPS fallback) — no SDK. Both are callable with a standard credential (verified against the live API).

### DescribeAccessKeyLeakDetail — full detail of one leak event (read-only)

| Parameter | Value | Description |
|-----------|-------|-------------|
| `Id` | (required) | Leak event ID, taken from a `DescribeAccesskeyLeakList` record's `Id` |
| `ResourceDirectoryAccountId` | (optional) | Resource-directory member account ID |

```python
body = _cli.call("sas", "DescribeAccessKeyLeakDetail", {"Id": leak_id},
                 region=region, profile=profile)
```

An unknown `Id` returns server error `-106 "data not exist"` (not a permission error). CLI usage: `query_notification.py --account <UID> --detail-id <Id>`.

### Remediation is manual (this skill performs NO write operations)

This skill is strictly **read-only**. It never marks leak-deal status, disables, modifies, or deletes any AccessKey. Instead, when a leak is confirmed the investigation report (`ak_leak_investigation.py`) prints a **prominent URGENT banner** at the top instructing the operator to act manually, in this exact order:

1. **Disable the leaked AK immediately** — RAM Console → AccessKey Management → set it to `Inactive` (or run `aliyun ram update-access-key --user-access-key-id <AK> --status Inactive` yourself). This immediately blocks all API calls made with it.
2. **Replace it with a new AccessKey** in every application / service / pipeline that used the leaked one.
3. **Confirm no service is impacted.**
4. **Only then delete** the disabled AK (RAM Console or `aliyun ram delete-access-key`). Never delete before replacing.

These steps must be executed by the operator via the RAM Console / CLI — the skill only surfaces the warning, it does not carry them out.

### Expected Alert Content

The Security Center alert typically contains:

- Leaked AccessKey ID
- Leak source (GitHub URL, Gitee URL, etc.)
- Detection timestamp
- Deal status (pending / dealt)


## Step 1.3: Infer AK Ban Status from ActionTrail

### Purpose

There is no public API that directly reports an AK's ban/disable status, so the script infers it by examining ActionTrail error codes. When all API calls made with the AK return ban-related error codes, the AK is considered banned.

### Error Codes Indicating Ban

| Error Code | Meaning |
|-----------|---------|
| `InvalidAccessKeyId.Inactive` | AK disabled (e.g. by Alibaba Cloud automated risk control or manually) |
| `Forbidden.AccessKeyDisabled` | AK disabled (variant used by some services) |
| `Forbidden.AccessKey` | AK forbidden |
| `InvalidAccessKeyId.NotFound` | AK permanently deleted |

### Logic

```python
# If ALL events with the AK have ban-related error codes → AK is banned
if total_events > 0 and failed_events == total_events and ban_codes:
    ak_ban_inferred = True
```

### Execution Flow

```
Notification Verification
            |
            v
    Query Security Center DescribeAccesskeyLeakList
    Filter: ak = <leaked_AK>
            |
            +---> Found?
            |       |
            |       v
            |   Extract alert details
            |   Confirm AK leak detection
            |
            +---> Not Found / NoPermission?
                    |
                    v
            Log: no Security Center alert found
            Proceed with user-provided AK
            |
            v
    Infer ban status from ActionTrail error codes
    Filter: EventAccessKeyId = <AK>
            |
            +---> All events failed with ban codes?
            |       |
            |       v
            |   AK ban INFERRED (platform auto-disabled)
            |
            +---> Mix of success/failure?
                    |
                    v
            AK partially active — some operations succeeded
```

## Output to Next Step

Pass to Step 2:

- `leaked_ak`: The AccessKey ID (from alert or user-provided)
- `alert_detected`: Whether Security Center found a leak alert
- `ak_ban_inferred`: Whether the AK appears to be banned based on error codes
- `ban_error_codes`: List of ban-related error codes observed
