# Network Access Control, IP Whitelists and ECS Security Groups

Covers two independent network access controls for Lindorm instances: **IP whitelists** at the Lindorm application layer and **ECS security groups** at the VPC network layer.

## Trigger Conditions

- "Add an IP to the whitelist" / "Show the whitelist" / "Clear the office group"
- "Bind a security group" / "Which security groups are bound?" / "Unbind a security group"
- Connection timeout diagnosis that requires access-control verification, together with `connection-troubleshoot.md`

---

## [MUST] Universal Rules

**1. `update` replaces the complete list; it does not append.** Both whitelist `--ips` and security-group `--groups` overwrite the target's existing contents. The CLI has no `add` command. Incremental changes must use **read-modify-write**: run `get`, append locally, then write back. Skipping this step silently deletes existing access rules.

**2. Confirm the architecture before choosing a command.** Query APIs are shared by V1 and V2, but update APIs are architecture-specific. The server rejects the wrong architecture. Use `arch` from `instance list` or `service_type` from `instance describe`:

- `arch=v1`, `service_type=lindorm` or `lindorm_multizone*` → use `v1 instance ...`
- `arch=v2`, `service_type=lindorm_v2*` → use `v2 instance ...`
- If uncertain, try `v2` first; the top-level `instance` alias is equivalent to `v2 instance`

> Update operations change the network access surface. Before execution, confirm the final complete list with the user because the operation replaces the entire list. Use `--lindorm-region`, never `--region`.

**3. Separate advice from execution.** If the user only asks whether an update command is correct or safe, answer with the replacement warning and the read-modify-write command template. Do not start an update or ask for instance execution parameters unless the user explicitly asks to perform the change. When execution is requested, obtain the instance ID and region, read the current list, merge the user's requested entry, and confirm the complete list before writing.

---

## 1. IP Whitelists

### API Mapping

| Operation | V1 | V2 | CLI command |
|---|---|---|---|
| Query | `GetInstanceIpWhiteList`, shared | Same | `<arch> instance whitelist get <id>` |
| Update | `UpdateInstanceIpWhiteList` | `ModifyLindormV2WhiteIpList` | `<arch> instance whitelist update <id>` |

### Query

```bash
aliyun lindorm v1 instance whitelist get <instance-id> --lindorm-region <r> --output json
aliyun lindorm v2 instance whitelist get <instance-id> --lindorm-region <r> --output json
```

Output:

```json
{
  "instance_id": "ld-bp1xxxxxxxxxx",
  "ip_list": ["1.2.3.4", "10.0.0.0/8"],
  "groups": [
    { "group_name": "default", "security_ip_list": "1.2.3.4" },
    { "group_name": "office",  "security_ip_list": "10.0.0.0/8" }
  ],
  "request_id": "..."
}
```

| Field | Meaning |
|---|---|
| `ip_list` | Flattened IP entries from all groups |
| `groups[].group_name` | Group name; `default` is the default group |
| `groups[].security_ip_list` | Comma-separated IP addresses or CIDR blocks in the group |

### Update, Full Replacement

```bash
# Replace the default group. Omitting --group selects default.
aliyun lindorm v1 instance whitelist update <id> --lindorm-region <r> --ips 1.2.3.4,10.0.0.0/8

# Replace the custom group office.
aliyun lindorm v2 instance whitelist update <id> --lindorm-region <r> \
  --group office --ips 10.0.0.0/8,172.16.0.0/12
```

| Parameter | Description |
|---|---|
| `--ips` | Comma-separated IP addresses or CIDR blocks; repeatable. Replaces the entire group. |
| `--group` | Group name, default `default` |
| `--delete` | Delete the entire group. `--group` is required and cannot be `default`. |
| `--yes` | Skip CLI confirmation; use only after confirming with the user |

### Incremental Addition, Recommended Flow

```bash
# 1. Read existing IP entries.
existing=$(aliyun lindorm v2 instance whitelist get ld-xxxx --lindorm-region <r> -o json \
  | jq -r '.groups[] | select(.group_name=="default") | .security_ip_list')

# 2. Append the new IP locally.
new="$existing,5.6.7.8"

# 3. Confirm the complete merged list with the user, then write it back.
aliyun lindorm v2 instance whitelist update ld-xxxx --lindorm-region <r> --ips "$new"
```

### Delete or Clear a Group

```bash
# Clear group contents while retaining the group.
aliyun lindorm v2 instance whitelist update <id> --lindorm-region <r> --group office --ips ""

# Delete the entire group. The default group cannot be deleted.
aliyun lindorm v2 instance whitelist update <id> --lindorm-region <r> --group office --delete
```

### Typical Conversation Flows

**The user says "Add an IP to the whitelist"**

1. Ask for the instance ID and IP or CIDR block.
2. Run `whitelist get <id>` and read `security_ip_list` from the current default group.
3. Append the entry and present the complete final list for confirmation.
4. Write it back with `whitelist update <id> --ips "<old>,<new>"`.
5. Explicitly state that the command replaces the full list and includes both existing and new entries.

**The user says "Reset default to allow only 1.2.3.4"**

```bash
aliyun lindorm v2 instance whitelist update <id> --lindorm-region <r> --ips 1.2.3.4
```

### Whitelist Notes

- **Full replacement**: `--ips` replaces rather than appends. Run `get` before an incremental update.
- **The `default` group cannot be deleted**: every instance has at least one default group, and the CLI rejects `--group default --delete`.
- **CIDR is supported**: the server accepts entries such as `10.0.0.0/8` and `172.16.0.0/12`.
- **Effective time**: usually seconds; no instance restart is required.
- **Update output is minimal**: success prints only `OK (request_id=...)`. Run `get` again to verify.

---

## 2. ECS Security Groups

### API Mapping

| Operation | V1 | V2 | CLI command |
|---|---|---|---|
| Query | `GetInstanceSecurityGroups`, shared | Same | `<arch> instance security-group get <id>` |
| Update | `UpdateInstanceSecurityGroups` | `ModifyLindormV2InstanceSecurityGroups` | `<arch> instance security-group update <id>` |

`security-group` can be abbreviated as `sg`.

### Query

```bash
aliyun lindorm v1 instance security-group get <instance-id> --lindorm-region <r> --output json
aliyun lindorm v2 instance sg get <instance-id> --lindorm-region <r> --output json
```

Output:

```json
{
  "instance_id": "ld-bp1xxxxxxxxxx",
  "security_groups": ["sg-bp1xxxxxxxxxxxxxx1", "sg-bp1xxxxxxxxxxxxxx2"],
  "request_id": "..."
}
```

`security_groups` is the currently bound ECS security group ID list in server-returned order.

### Update, Full Replacement

```bash
# Replace with two security groups.
aliyun lindorm v2 instance security-group update <id> --lindorm-region <r> \
  --groups sg-bp1xxxxxx1,sg-bp1xxxxxx2

# Reduce to one security group.
aliyun lindorm v1 instance security-group update <id> --lindorm-region <r> --groups sg-bp1xxxxxx1

# Clear all groups by explicitly passing an empty string.
aliyun lindorm v2 instance sg update <id> --lindorm-region <r> --groups ""
```

| Parameter | Description |
|---|---|
| `--groups` | Comma-separated ECS security group IDs, `sg-xxx`. Required; pass `""` to clear all. |
| `--yes` | Skip CLI confirmation; use only after confirming with the user |

### Incremental Addition, Recommended Flow

```bash
# 1. Read the current list.
current=$(aliyun lindorm v2 instance sg get ld-xxxx --lindorm-region <r> -o json \
  | jq -r '.security_groups | join(",")')

# 2. Append the new ID locally.
new="$current,sg-bp1xxxxxxNEW"

# 3. Confirm the complete list with the user, then write it back.
aliyun lindorm v2 instance sg update ld-xxxx --lindorm-region <r> --groups "$new"
```

### Typical Conversation Flows

**The user says "Bind a new security group"**: run `sg get`, append the new ID, present the complete list for confirmation, run `sg update --groups "<old1>,<old2>,<new>"`, and state that the command replaces the full list.

**The user says "Unbind every group except sg-aaa"**:

```bash
aliyun lindorm v2 instance sg update <id> --lindorm-region <r> --groups sg-aaa
```

### Security Group Notes

- **Full replacement**: `--groups` replaces rather than appends.
- **Required validation**: the CLI requires `--groups` to prevent accidental clearing. Pass `""` explicitly when clearing is intended.
- **VPC restriction**: the security group and instance must be in the same VPC, or the server returns an error.
- **Effective time**: usually seconds; no instance restart is required.
- **Update output is minimal**: success prints only `OK (request_id=...)`. Run `get` again to verify.

---

## Whitelist vs. Security Group

| | IP whitelist | ECS security group |
|---|---|---|
| Layer | Lindorm application-layer IP access | VPC network-layer rules |
| Target | Client IP / CIDR | ECS security group ID |
| Relationship | Independent controls; check both when a connection fails | |

Check both when diagnosing connection issues. See `connection-troubleshoot.md`.

---

## Related Scenarios

- Connection timeout / refusal diagnosis → `connection-troubleshoot.md`
- Instance queries and architecture detection → `instance-management.md`
- Accounts and permissions, which are independent of network access → `user-permission.md`
- CLI quick reference and region rules → `../03-ref/related-commands.md`
