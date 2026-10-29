# Tag Management Reference

This document describes how to create, query, and remove tags on GA accelerators and sub-resources (listeners, endpoint groups, ACLs).

---

## 1. Supported Resource Types

| Resource Type | ARN Example |
|---|---|
| Accelerator | `acs:ga:cn-hangzhou:<account-id>:ga/<ga-id>` |
| Listener | `acs:ga:cn-hangzhou:<account-id>:listener/<listener-id>` |
| Endpoint group | `acs:ga:cn-hangzhou:<account-id>:endpointgroup/<epg-id>` |
| ACL | `acs:ga:cn-hangzhou:<account-id>:acl/<acl-id>` |

---

## 2. Tag an Accelerator

```bash
GA_ID="ga-bp1xxxx"

aliyun ga tag-resources \
  --biz-region-id cn-hangzhou \
  --resource-type "ACCELERATOR" \
  --resource-id.1 "$GA_ID" \
  --user-agent "$GA_USER_AGENT" \
  --tag '[{"Key":""Environment"","Value":""Production""},{"Key":""Owner"","Value":""SRE""}]'
```

### Parameter Reference

| Parameter | Description |
|---|---|
| ResourceType | Resource type, e.g., `ACCELERATOR`, `LISTENER`, `ENDPOINTGROUP`, `ACL` |
| ResourceId.N | Resource ID |
| Tag.N.Key | Tag key |
| Tag.N.Value | Tag value |

---

## 3. Tag a Listener

```bash
LISTENER_ID="lsr-bp1xxxx"

aliyun ga tag-resources \
  --biz-region-id cn-hangzhou \
  --resource-type "LISTENER" \
  --resource-id.1 "$LISTENER_ID" \
  --user-agent "$GA_USER_AGENT" \
  --tag Key="Service" Value="api-gateway"
```

---

## 4. List Tags

### Tags for a specific resource

```bash
aliyun ga list-tag-resources \
  --biz-region-id cn-hangzhou \
  --resource-type "ACCELERATOR" \
  --user-agent "$GA_USER_AGENT" | jq '.TagResources[] | {ResourceId, TagKey, TagValue}'
```

### Filter resources by tag

```bash
aliyun ga list-tag-resources \
  --biz-region-id cn-hangzhou \
  --resource-type "ACCELERATOR" \
  --user-agent "$GA_USER_AGENT" \
  --tag Key="Environment" | jq '.TagResources[] | {ResourceId, TagKey, TagValue}'
```

---

## 5. Remove Tags

```bash
aliyun ga untag-resources \
  --biz-region-id cn-hangzhou \
  --resource-type "ACCELERATOR" \
  --resource-id.1 "$GA_ID" \
  --user-agent "$GA_USER_AGENT" \
  --tag-key.1 "Owner"
```

---

## 6. Tag an Entire Accelerator Tree

```bash
#!/bin/bash
GA_ID="${1:?Please provide GA accelerator ID}"
REGION="cn-hangzhou"

TAG_KEY="Environment"
TAG_VALUE="Production"

echo "=== Tagging accelerator $GA_ID and its sub-resources ==="

# 1. Tag accelerator
aliyun ga tag-resources \
  --biz-region-id "$REGION" \
  --resource-type "ACCELERATOR" \
  --resource-id.1 "$GA_ID" \
  --user-agent "$GA_USER_AGENT" \
  --tag Key="$TAG_KEY" Value="$TAG_VALUE"

# 2. Tag listeners
LISTENER_IDS=$(aliyun ga list-listeners \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --page-size 50 \
  --user-agent "$GA_USER_AGENT" | jq -r '.Listeners[].ListenerId' )
for LID in $LISTENER_IDS; do
aliyun ga tag-resources \
  --biz-region-id "$REGION" \
  --resource-type "LISTENER" \
  --resource-id.1 "$LID" \
  --user-agent "$GA_USER_AGENT" \
  --tag Key="$TAG_KEY" Value="$TAG_VALUE"
  echo "Tagged: $LID"
done

# 3. Tag endpoint groups
EPG_IDS=$(aliyun ga list-endpoint-groups \
  --biz-region-id "$REGION" \
  --accelerator-id "$GA_ID" \
  --page-size 50 \
  --user-agent "$GA_USER_AGENT" | jq -r '.EndpointGroups[].EndpointGroupId // empty' )
for EPG_ID in $EPG_IDS; do
aliyun ga tag-resources \
  --biz-region-id "$REGION" \
  --resource-type "ENDPOINTGROUP" \
  --resource-id.1 "$EPG_ID" \
  --user-agent "$GA_USER_AGENT" \
  --tag Key="$TAG_KEY" Value="$TAG_VALUE"
  echo "Tagged: $EPG_ID"
done

echo "=== Done ==="
```

---

## 7. Skill Integration Notes

During Step 1 (create accelerator), optionally ask:

```
Question: Do you want to add tags to the GA accelerator?
- Option 1: No (default)
- Option 2: Yes

If yes:
1. Ask for tag key-value pairs (multiple allowed).
2. Pass Tag parameters directly in CreateAccelerator/CreateListener/CreateEndpointGroup.
3. Call ListTagResources after creation to verify.
```

---

## 8. Notes

1. Each resource supports up to 20 tags.
2. Tag keys cannot start with `aliyun`, `acs:`, `http://`, or `https://`.
3. Tag keys are case-insensitive inside Alibaba Cloud; use lowercase consistently.
4. Basic accelerators and their sub-resources also support tags.
