# ACL Access Control Reference

This document describes how to create, manage, and associate GA access control lists (ACLs) for listeners.

> **Important**: ACLs apply only to **Standard routing listeners**. Basic accelerators and CustomRouting listeners do not support ACLs.

---

## 1. Core Concepts

- **ACL**: A collection of IP addresses or CIDR blocks.
- **Whitelist (`white`)**: Only IPs/CIDRs in the ACL can access the listener.
- **Blacklist (`black`)**: IPs/CIDRs in the ACL are blocked from the listener.
- **Listener association**: A listener can be associated with up to 2 ACLs.

---

## 2. Create an ACL

### Empty ACL

```bash
aliyun ga create-acl \
  --biz-region-id cn-hangzhou \
  --acl-name "ga-whitelist-prod" \
  --user-agent "$GA_USER_AGENT" \
  --address-ip-version IPv4
```

### ACL with Initial Entries

```bash
aliyun ga create-acl \
  --biz-region-id cn-hangzhou \
  --acl-name "ga-whitelist-prod" \
  --address-ip-version IPv4 \
  --acl-entries '[{"Entry":"192.168.1.0/24","EntryDescription":"office-network"},{"Entry":"10.0.0.10","EntryDescription":"bastion-host"}]' \
  --user-agent "$GA_USER_AGENT"
```

### Response Field

| Field | Description |
|---|---|
| AclId | Access control list ID |

---

## 3. Add or Remove ACL Entries

### Add entries

```bash
ACL_ID="nacl-bp1xxxx"

aliyun ga add-entries-to-acl \
  --biz-region-id cn-hangzhou \
  --acl-id "$ACL_ID" \
  --acl-entries '[{"Entry":"172.16.0.0/16","EntryDescription":"vpc-network"},{"Entry":"203.0.113.0/24","EntryDescription":"partner-network"}]' \
  --user-agent "$GA_USER_AGENT"
```

> Up to 50 entries can be added at a time.

### Remove entries

```bash
aliyun ga remove-entries-from-acl \
  --biz-region-id cn-hangzhou \
  --acl-id "$ACL_ID" \
  --acl-entries '[{"Entry":"203.0.113.0/24"}]' \
  --user-agent "$GA_USER_AGENT"
```

---

## 4. Associate ACL with Listener

### Whitelist

```bash
LISTENER_ID="lsr-bp1xxxx"
ACL_ID="nacl-bp1xxxx"

aliyun ga associate-acls-with-listener \
  --biz-region-id cn-hangzhou \
  --listener-id "$LISTENER_ID" \
  --acl-ids "$ACL_ID" \
  --user-agent "$GA_USER_AGENT" \
  --acl-type white
```

### Blacklist

```bash
aliyun ga associate-acls-with-listener \
  --biz-region-id cn-hangzhou \
  --listener-id "$LISTENER_ID" \
  --acl-ids "$ACL_ID" \
  --user-agent "$GA_USER_AGENT" \
  --acl-type black
```

### Multiple ACLs

```bash
aliyun ga associate-acls-with-listener \
  --biz-region-id cn-hangzhou \
  --listener-id "$LISTENER_ID" \
  --acl-ids "$ACL_ID_1" "$ACL_ID_2" \
  --user-agent "$GA_USER_AGENT" \
  --acl-type white
```

---

## 5. Dissociate ACL

```bash
aliyun ga dissociate-acls-from-listener \
  --biz-region-id cn-hangzhou \
  --listener-id "$LISTENER_ID" \
  --acl-ids "$ACL_ID" \
  --user-agent "$GA_USER_AGENT"
```

---

## 6. Query ACLs

### Single ACL

```bash
aliyun ga get-acl \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '{
    AclId,
    AclName,
    AddressIPVersion,
    AclEntries,
    Status
  }'
```

### ACL List

```bash
aliyun ga list-acls \
  --biz-region-id cn-hangzhou \
  --user-agent "$GA_USER_AGENT" | jq '.Acls[] | {AclId, AclName, AddressIPVersion, Status}'
```

### ACLs Associated with Listeners

```bash
aliyun ga list-listeners \
  --biz-region-id cn-hangzhou \
  --accelerator-id "$GA_ID" \
  --user-agent "$GA_USER_AGENT" | jq '.Listeners[] | {ListenerId, AclType, RelatedAcls}'
```

---

## 7. Update ACL Attributes

```bash
aliyun ga update-acl-attribute \
  --biz-region-id cn-hangzhou \
  --acl-id "$ACL_ID" \
  --user-agent "$GA_USER_AGENT" \
  --acl-name "ga-whitelist-renamed"
```

---

## 8. Complete Example

```bash
#!/bin/bash
GA_ID="ga-bp1xxxx"
LISTENER_ID="lsr-bp1xxxx"
REGION="cn-hangzhou"

echo "=== Creating and associating whitelist ACL ==="

# Step 1: Create ACL
ACL_RESULT=$(aliyun ga create-acl \
  --biz-region-id "$REGION" \
  --acl-name "whitelist-$(date +%s)" \
  --address-ip-version IPv4 \
  --acl-entries '[{"Entry":"192.168.0.0/16","EntryDescription":"internal-network"}]' \
  --user-agent "$GA_USER_AGENT")

ACL_ID=$(echo "$ACL_RESULT" | jq -r '.AclId')
echo "ACL ID: $ACL_ID"

# Step 2: Wait for ACL to become active
for i in $(seq 1 20); do
  STATE=$(aliyun ga get-acl --biz-region-id "$REGION" --acl-id "$ACL_ID" --user-agent "$GA_USER_AGENT" | jq -r '.Status // "init"')
  [ "$STATE" = "active" ] && break
  echo "Waiting for ACL to become active... [$i/20] state: $STATE"
  sleep 5
done

# Step 3: Associate with listener (whitelist)
aliyun ga associate-acls-with-listener \
  --biz-region-id "$REGION" \
  --listener-id "$LISTENER_ID" \
  --acl-ids "$ACL_ID" \
  --user-agent "$GA_USER_AGENT" \
  --acl-type white

echo "ACL associated with listener $LISTENER_ID"
```

---

## 9. Skill Integration Notes

After Step 4 (create listener), optionally ask:

```
Question: Do you want to configure access control (ACL) for this listener?
- Option 1: No (default)
- Option 2: Yes, whitelist
- Option 3: Yes, blacklist

If yes:
1. Ask whether to use an existing ACL or create a new one.
2. For a new ACL, ask for the ACL name and IP entry list.
3. Call create-acl / add-entries-to-acl to create and populate the ACL.
4. Call associate-acls-with-listener to attach it to the listener.
```

---

## 10. Notes

1. **Whitelist risk**: After enabling a whitelist, only IPs in the whitelist can access the listener. An empty whitelist allows all requests.
2. **Blacklist risk**: An empty blacklist allows all requests by default.
3. **Concurrency**: `associate-acls-with-listener` does not support concurrent operations within the same accelerator.
4. **Listener type**: CustomRouting listeners do not support ACLs.
