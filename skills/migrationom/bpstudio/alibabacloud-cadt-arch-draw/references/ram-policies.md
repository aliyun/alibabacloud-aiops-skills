# RAM Policies — alibabacloud-cadt-arch-draw

> This file lists all RAM permissions required to execute this skill. If `Forbidden` / `NoPermission` / `401` / `403` errors occur during execution, refer to the **Permission Failure Handling** section below.

## 1. Why Broad Read Permissions Are Needed

Architecture drawing involves more than just calling the BPStudio gateway. The AI Agent backend queries product specifications, available configurations, pricing, and performs validation on behalf of the user. These internal queries require the user's RAM identity to have **read access** to the target cloud products (e.g., ECS specs, VPC/vSwitch availability, RDS engine versions, Redis instance types).

## 2. Recommended Policy

| Option | Policy Name | Description | Risk Level |
|---|---|---|---|
| **Recommended** | `PowerUserAccess` | Full access to all services except RAM identity management. Covers all product read queries needed during architecture drawing. | Medium (no IAM mutation) |
| Alternative | Per-product ReadOnly | Attach `AliyunECSReadOnlyAccess` + `AliyunVPCReadOnlyAccess` + `AliyunRDSReadOnlyAccess` + ... for each product to be drawn | Low (minimal privilege) |

> **Why not just `bpstudio:ExecuteOperationSync`?**
> The AI Agent backend queries product catalogs, instance specs, AZ availability, and runs resource validation using the caller's identity. A gateway-only policy will result in `NoPermission` errors during spec lookup and validation phases.

### Per-Product ReadOnly Policies (if not using PowerUserAccess)

| Product | Policy | When Needed |
|---|---|---|
| BPStudio (gateway) | Custom: `bpstudio:ExecuteOperationSync` | Always |
| ECS | `AliyunECSReadOnlyAccess` | Drawing includes ECS |
| VPC | `AliyunVPCReadOnlyAccess` | Drawing includes VPC/vSwitch |
| SLB/ALB/NLB | `AliyunSLBReadOnlyAccess` + `AliyunALBReadOnlyAccess` | Drawing includes load balancer |
| RDS | `AliyunRDSReadOnlyAccess` | Drawing includes RDS |
| Redis | `AliyunKvstoreReadOnlyAccess` | Drawing includes Redis |
| MongoDB | `AliyunMongoDBReadOnlyAccess` | Drawing includes MongoDB |
| NAT Gateway | `AliyunNATGatewayReadOnlyAccess` | Drawing includes NAT |
| OSS | `AliyunOSSReadOnlyAccess` | Drawing includes OSS |

> Since architecture drawing may involve any Alibaba Cloud product, **`PowerUserAccess` is the pragmatic choice** to avoid per-product policy chasing.

## 3. Minimum Gateway Policy (insufficient alone, for reference only)

```json
{
  "Version": "1",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "bpstudio:ExecuteOperationSync"
      ],
      "Resource": "*"
    }
  ]
}
```

> ⚠️ This alone is **NOT sufficient** for architecture drawing. It only allows the gateway call itself but not the backend's product queries. Use `PowerUserAccess` or combine with per-product ReadOnly policies above.

## 4. Permission Failure Handling

1. If `aliyun bpstudio execute-operation-sync` returns `Unauthorized` / `Forbidden` / `NoPermission`:
   - Check the `Message` field for the denied action/product name
   - **Quick fix**: Attach `PowerUserAccess` to the current RAM identity
   - **Minimal fix**: Attach the corresponding per-product ReadOnly policy from §2
2. If the error mentions `source ip` denial (IP whitelist):
   - Follow the instructions in the error message, or submit a support ticket via [Alibaba Cloud Console](https://ticket.console.aliyun.com)
   - Or switch to a profile/network without IP restrictions
3. Wait for user confirmation that permissions are in place before retrying

## 5. Related References

- [SKILL.md](../SKILL.md) → Prerequisites section
- [`references/related-commands.md`](related-commands.md) → CLI command format and credentials
