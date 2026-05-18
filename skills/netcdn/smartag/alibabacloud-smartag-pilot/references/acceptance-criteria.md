# Acceptance Criteria: alibabacloud-smartag-pilot

**Scenario**: SAG Configuration Query and Status Inspection
**Purpose**: Skill testing acceptance criteria — correct vs incorrect command patterns

---

## 1. CLI Command Patterns

### 1.1 Product Invocation — Plugin Mode

#### CORRECT
```bash
aliyun smartag describe-smart-access-gateways \
  --biz-region-id cn-shanghai
```

#### INCORRECT
```bash
# --RegionId in plugin mode (plugin uses --biz-region-id)
aliyun smartag describe-smart-access-gateways --RegionId cn-shanghai
```

**Why**: Plugin mode uses `--biz-region-id` for business region parameter, not `--RegionId`.

---

### 1.2 Endpoint Routing Format

#### CORRECT
```bash
# --endpoint is REQUIRED for deterministic endpoint routing
aliyun smartag describe-smart-access-gateways \
  --endpoint smartag.cn-shanghai.aliyuncs.com \
  --biz-region-id cn-shanghai

aliyun smartag describe-smart-access-gateways \
  --endpoint smartag.eu-west-1.aliyuncs.com \
  --biz-region-id eu-west-1
```

#### INCORRECT
```bash
# Missing --endpoint (routing relies on plugin's incomplete region mapping)
aliyun smartag describe-smart-access-gateways \
  --biz-region-id eu-west-1

# Using --region (fails for eu-west-1, us-east-1, cn-zhangjiakou-spe)
aliyun smartag describe-smart-access-gateways \
  --region eu-west-1 \
  --biz-region-id eu-west-1

--endpoint smartag.aliyuncs.com                 # Missing region segment
--endpoint cn-shanghai.smartag.aliyuncs.com     # Wrong order
--endpoint smartag.cn-shanghai.amazonaws.com    # Wrong domain
```

**Why**: The plugin's `--region` and implicit `--biz-region-id` routing have incomplete region mappings — eu-west-1, us-east-1, cn-zhangjiakou-spe are not recognized and fallback to cn-hangzhou. `--endpoint smartag.<RegionId>.aliyuncs.com` provides deterministic routing for ALL regions.

---

### 1.3 describe-dnat-entries — Uses --sag-id parameter

#### CORRECT (Plugin Mode)
```bash
aliyun smartag describe-dnat-entries \
  --biz-region-id cn-shanghai \
  --sag-id sag-xxxxx
```

#### INCORRECT
```bash
# Wrong parameter name (returns MissingSagId error)
aliyun smartag describe-dnat-entries \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx
```

**Why**: describe-dnat-entries is the only SAG API that uses `--sag-id` instead of `--smart-ag-id`.

---

### 1.4 Device-Level APIs — Must include --smart-ag-sn

#### CORRECT (Plugin Mode)
```bash
aliyun smartag describe-sag-wan-list \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx \
  --smart-ag-sn sag61dacczh
```

#### INCORRECT
```bash
# Missing --smart-ag-sn (returns MissingSmartAGSn error)
aliyun smartag describe-sag-wan-list \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx

# Multi-SN not split (returns Sag.DeviceNotExist)
aliyun smartag describe-sag-wan-list \
  --biz-region-id cn-shanghai \
  --smart-ag-id sag-xxxxx \
  --smart-ag-sn "sag61dacczh,sag61daccq6"
```

**Why**: Device-level APIs operate on a single physical device identified by its serial number. HA instances have multiple SNs that must be queried individually.

---

## 2. Instance Classification Patterns

### 2.1 SAG-Software Skip Logic

#### CORRECT
```python
if instance.get("HardwareVersion") == "sag-software":
    # Only query: #1(instance), #5(CCN/CEN), #6(ACL), #7(QoS), #9(FlowLog), #11(APP clients)
    skip_functions = {2, 3, 4, 8, 12}
```

#### INCORRECT
```python
# Querying device hardware for software instances (will fail)
if instance.get("HardwareVersion") == "sag-software":
    device_info = query_device_info(sag_id, sn)  # No SN exists!
```

---

### 2.2 Empty SN Skip Logic

#### CORRECT
```python
sn = instance.get("SerialNumber", "")
if not sn:
    # Skip device-level queries: #2, #3, #4, #12
    pass
```

#### INCORRECT
```python
# Not checking SN before device query (returns MissingSmartAGSn)
device_info = query_device_info(sag_id, instance.get("SerialNumber"))
```

---

## 3. Response Parsing Patterns

### 3.1 safe_extract_list Pattern

#### CORRECT
```python
container = data.get("Wans", {})
if isinstance(container, list):
    items = container
elif isinstance(container, dict):
    items = container.get("Wan", [])
    if isinstance(items, dict):
        items = [items]
else:
    items = []
```

#### INCORRECT
```python
# Assumes fixed structure (crashes on single-item or direct-list responses)
items = data["Wans"]["Wan"]

# No type checking (KeyError or TypeError on edge cases)
items = data.get("Wans", {}).get("Wan", [])
```

**Why**: SAG APIs return inconsistent structures: standard nested list, single-item dict (not wrapped in array), or container directly as array.

---

## 4. Region Discovery Pattern

### 4.1 Dynamic Region Discovery

#### CORRECT
```python
# Always query describe-regions first
regions = call_api("describe-regions")
for region in regions:
    if "已关停" not in region["LocalName"]:
        query_region(region["RegionId"])
```

#### INCORRECT
```python
# Hardcoded region list (misses cn-zhangjiakou-spe, future regions)
regions = ["cn-shanghai", "cn-hangzhou", "cn-beijing", ...]
for region in regions:
    query_region(region)
```

---

## 5. Batch Query Patterns

### 5.1 Region-Level vs Instance-Level

#### CORRECT
```python
# Region-level: call once per region
acls = call_api("describe-acls", region)
qos = call_api("describe-qoses", region)

# Instance-level: call per instance
for instance in instances:
    attr = call_api("describe-smart-access-gateway-attribute", instance["SmartAGId"])
```

#### INCORRECT
```python
# Calling region-level API per instance (redundant)
for instance in instances:
    acls = call_api("describe-acls", region)  # Same result every time!
```

---

## 6. Specialized API Call Contract (No Field-Reuse Substitution)

The response of `describe-smart-access-gateways` is a **classifier** (telling you what to call next), NOT a **substitute** for specialized API calls.

### 6.1 VPN tunnel state

#### CORRECT
```python
attr = call_api("describe-smart-access-gateway-attribute", sag_id)
vpn_status = attr.get("VpnStatus")   # authoritative source
```

#### INCORRECT
```python
# Reusing Status field from basic info to infer VPN state
basic = call_api("describe-smart-access-gateways")
vpn_status = basic["Status"]   # WRONG — Status is device status, not VPN status
```

### 6.2 CCN binding details

#### CORRECT
```python
ccn_list = call_api("describe-cloud-connect-networks", region)
# Returns CcnName, AssociatedCenId, CidrBlock, IsDefault, etc.
```

#### INCORRECT
```python
# Relying on AssociatedCcnId alone
basic = call_api("describe-smart-access-gateways")
ccn_id = basic["AssociatedCcnId"]   # You get ID only, no name/CEN/CIDR/status
```

### 6.3 ACL / QoS

#### CORRECT
```python
acls = call_api("describe-acls", region)
qoses = call_api("describe-qoses", region)
```

#### INCORRECT
```python
# Using AclIds from basic info without resolving the rules/entries
basic = call_api("describe-smart-access-gateways")
acl_ids = basic["AclIds"]   # IDs only, no rules, no bound-instance count
```

### 6.4 Device hardware

#### CORRECT
```python
dev = call_api("describe-sag-device-info", sag_id, sn)
# Returns firmware version, hardware model, serial detail, 4G module info
```

#### INCORRECT
```python
# Taking HardwareVersion string alone as the device info
hw_only = basic["HardwareVersion"]   # Missing firmware/model/SN
```

**Why**: Scenario evaluations assert the full set of specialized APIs is invoked (see SKILL.md § Mandatory Call Contracts). Field-reuse shortcuts cause both information loss and missed API invocation expectations.

---

## 7. DropTopN and Deprecated API Handling

### 7.1 DropTopN with graceful region skip

#### CORRECT
```python
try:
    data = call_api("describe-sag-drop-topn", region_id,
                    sag_id=sag_id, size=10)
    drop_rate = parse_drop_rate(data)
except SagQueryTopNError:
    mark_item_as_skipped(
        item="#5 packet drop",
        reason=f"region {region_id} does not support DropTopN")
    continue   # DO NOT abort the whole inspection
```

#### INCORRECT
```python
# Silently dropping the call because "it may fail"
# (testcase expects DescribeSagDropTopN to be invoked)
if region_id == "cn-zhangjiakou-spe":
    skip_drop_topn()   # But agent never called it in cn-shanghai either
```

### 7.2 Deprecated / unavailable APIs — do NOT call, declare in report

#### CORRECT
```markdown
| Item | Status | Note |
| Health check probes | skipped | describe-health-checks is unavailable in current API version (InvalidApi.NotFound) |
```

#### INCORRECT
```bash
# Calling known-unavailable APIs (wastes a request and triggers evaluation forbidden list)
aliyun smartag describe-health-checks --biz-region-id cn-shanghai --smart-ag-id sag-xxx
aliyun smartag describe-sag-online-client-statistics --biz-region-id cn-shanghai
```

**Why**: `describe-health-checks` / `describe-health-check-attribute` and `describe-sag-online-client-statistics` return `InvalidApi.NotFound` in the current SAG API version. Use `describe-smart-access-gateway-client-users` for APP user lists instead, and explicitly skip health checks with a note in the report.
