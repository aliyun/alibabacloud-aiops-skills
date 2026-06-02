# Acceptance Criteria

This document defines the test acceptance criteria for the `alibabacloud-aes-sysom-pai-diagnosis` skill.

---

## Test Case 1: EAS Real-Time Diagnosis (Auto-Inferred Product)

**Input from user:**
> Diagnose my EAS service `eas-m-bp79exq2lzbd0ctdfu` in `cn-hangzhou` — inference latency seems high.

**Expected Agent behavior:**

1. ✅ Auto-infer `product=EAS` from the `eas-` prefix (no user confirmation needed)
2. ✅ Default to real-time diagnosis (`start_time=0`, `end_time=0`)
4. ✅ Execute Phase 1 environment setup (Steps 0–3)
5. ✅ Initialize SysOM role (Step 5)
6. ✅ Call `aliyun eas list-services --region cn-hangzhou --filter eas-m-bp79exq2lzbd0ctdfu` (Step 6)
7. ✅ Verify the service exists (matching `ServiceId` found in response)
8. ✅ Call `invoke-diagnosis` with params containing `instance=eas-m-bp79exq2lzbd0ctdfu`, `product=EAS`, `type=ocd`
9. ✅ Poll `get-diagnosis-result` until `Success`
10. ✅ Present diagnosis summary to the user

---

## Test Case 2: DLC Historical Diagnosis (Explicit Time Range)

**Input from user:**
> DLC job `dlcabc123def456` in `cn-beijing` was stuck for ~30 minutes around 3am this morning. Please diagnose.

**Expected Agent behavior:**

1. ✅ Auto-infer `product=DLC` from the `dlc` prefix (no user confirmation needed)
2. ✅ Recognize past temporal reference ("around 3am this morning") and ask for the exact time range
3. ✅ After user confirms, set `start_time` and `end_time` to the corresponding Unix timestamps (historical mode)
4. ✅ Execute Phase 1 environment setup (Steps 0–3)
5. ✅ Initialize SysOM role (Step 5)
6. ✅ Call `aliyun pai-dlc get-job --region cn-beijing --job-id dlcabc123def456` (Step 6B) and verify `ResourceType` is `Lingjun`
7. ✅ Call `invoke-diagnosis` with params containing `instance=dlcabc123def456`, `product=DLC`, `type=ocd`, `start_time=<ts>`, `end_time=<ts>`
8. ✅ Poll `get-diagnosis-result` until `Success`
9. ✅ Present diagnosis summary to the user

---

## Test Case 3: Ambiguous Product (Cannot Infer)

**Input from user:**
> Diagnose `my-pai-resource-001` in `cn-shanghai`.

**Expected Agent behavior:**

1. ✅ Cannot infer `product` from the prefix
2. ✅ Explicitly ask the user: "Is this an EAS service or a DLC job?"
3. ✅ Wait for user response before proceeding
4. ❌ Must NOT silently default to either `EAS` or `DLC`

---

## Test Case 4: Invalid EAS ServiceId

**Input from user:**
> Diagnose EAS service `eas-m-nonexistent` in `cn-hangzhou`.

**Expected Agent behavior:**

1. ✅ Auto-infer `product=EAS`
2. ✅ Call `ListServices` in Step 6
3. ✅ Receive empty `Services` array
4. ✅ Inform the user: "The EAS service `eas-m-nonexistent` does not exist in `cn-hangzhou`. Please verify the service ID and region."
5. ✅ Stop the pipeline; do NOT call `invoke-diagnosis`

---

## Test Case 5: User Overrides Inferred Product

**Input from user:**
> Diagnose `eas-m-xxx` in `cn-hangzhou`, this is actually a DLC job (typo in the ID).

**Expected Agent behavior:**

1. ✅ Initial inference: `product=EAS` (from `eas-` prefix)
2. ✅ User explicitly stated `DLC` → user value takes priority over inference
3. ✅ User's explicit statement takes priority over prefix inference
4. ✅ Execute Step 6B (`aliyun pai-dlc get-job --region cn-hangzhou --job-id eas-m-xxx`) to validate — if job exists and ResourceType is Lingjun, proceed

---

## Test Case 6: Permission Failure on ListServices

**Setup:** User identity lacks `eas:ListServices` permission.

**Expected Agent behavior:**

1. ✅ Step 6 `ListServices` returns `Forbidden.RAM`
2. ✅ Identify the missing permission (`eas:ListServices`)
3. ✅ Use `ram-permission-diagnose` skill to guide the user
4. ✅ Pause execution; wait for user to confirm permission grant before retrying

---

## Common Negative Acceptance Rules (MUST NOT happen)

| ❌ Forbidden Behavior | Why |
|---------------------|-----|
| Silently default `product` when prefix is unrecognizable | Could route diagnosis to wrong sub-product; must ask user when inference fails |
| Skip `ListServices` validation for EAS before invoking diagnosis | Must verify EAS service exists first |
| Omit `"product"` field from params JSON | Engine falls back to ECS mode and produces wrong results |
| Omit `"type": "ocd"` from params JSON | Engine cannot identify diagnosis type |
| Change `--channel ecs` to `--channel eas` or `--channel dlc` | Channel is fixed; routing is by `product` field internally |
| Attempt agent installation / instance enrollment | PAI is fully managed; this skill has no enrollment phase |
| Suggest configuring DingTalk alerts | Out of scope for this skill |
| Print AccessKey values in conversation or commands | Credential security violation |
